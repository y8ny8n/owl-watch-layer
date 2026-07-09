"""[세션 작업: 신호 SQL] 유출 후보 산출 — 허용로그(is_block=false) 대상.

설계문서 §3.3 채널교차 후보 SQL 을 구현. agent_id 단위로 5채널(media/fileattach/
website/sharedfolder/chatgpt) 허용 로그를 UNION ALL 로 모아 신호(S1~S8) 발동 여부와
증거를 SQL 에서 직접 판정한다(탐지=SQL, AI는 결과를 설명만 함 — 안전벨트).

반환 계약: list[dict], 각 원소:
    {
      "agent_id": int,
      "distinct_channels": int, "total_allowed": int,
      "fired": {"S1_ext_spoof": {evidence...}, "S7_cross_channel": {...}, ...},  # fired 신호만
      "target_user_id": str, "target_user_name": str
    }

근거(스카우트 확인):
  - 허용 판별: media/fileattach is_block='false', website block_type=1,
              sharedfolder block_type=0, chatgpt block_type=0 (capture 제외)
  - 필드: log_json->>'file_name'/'dst_file_name'/'zip_filelist'/'hash_extract_fail_reason'/'total_pri_cnt'
  - 사용자 표시: agent_json->>'id'/'name'
"""
from datetime import datetime, timedelta, timezone

from db import fetch_all
from config import config

# S4_mass_pri 임계 (설계문서 §3.1 "임계 이상" 예시값)
_MASS_PRI_THRESHOLD = 10

# S5_unofficial 대상 fileattach category: 1웹하드/2메신저/7클라우드/10원격
# psycopg3 는 튜플을 IN 절이 아닌 composite 타입으로 매핑하므로 list + ANY() 사용
_UNOFFICIAL_CATEGORIES = [1, 2, 7, 10]

# S9_persistence(지속 반복): 최근 N일에서 "의심 반출"이 걸린 서로 다른 주(week)가 K개 이상이면 발동.
# low-and-slow(조금씩 오래 새는) 장기 유출 탐지. (설계문서 확장 — MITRE T1029)
_RECURRENCE_HORIZON_DAYS = 56   # 8주 회고
_RECURRENCE_MIN_WEEKS = 2       # 2주 이상 반복이면 지속 신호

_CROSS_CHANNEL_SQL = """
WITH allowed AS (
    SELECT agent_id, 'media'::text AS ch, log_time,
           log_json->>'file_name' AS fn,
           log_json->>'dst_file_name' AS dfn,
           log_json->>'zip_filelist' AS zip,
           log_json->>'hash_extract_fail_reason' AS hef,
           (log_json->>'total_pri_cnt')::int AS total_pri,
           NULL::int AS category,
           NULL::int AS chatgpt_pri,
           agent_json
    FROM log_dlp_media_t
    WHERE license_code = %(lic)s
      AND log_json->>'is_block' = 'false'
      AND log_time >= %(win_start)s

    UNION ALL

    SELECT agent_id, 'fileattach', log_time,
           log_json->>'file_name',
           log_json->>'dst_file_name',
           log_json->>'zip_filelist',
           log_json->>'hash_extract_fail_reason',
           (log_json->>'total_pri_cnt')::int,
           (log_json->>'category')::int,
           NULL::int,
           agent_json
    FROM log_dlp_fileattach_t
    WHERE license_code = %(lic)s
      AND log_json->>'is_block' = 'false'
      AND log_time >= %(win_start)s

    UNION ALL

    SELECT agent_id, 'website', log_time,
           NULL::text, NULL::text, NULL::text, NULL::text,
           NULL::int, NULL::int, NULL::int,
           agent_json
    FROM log_dlp_website_t
    WHERE license_code = %(lic)s
      AND (log_json->>'block_type')::int = 1
      AND log_time >= %(win_start)s

    UNION ALL

    SELECT agent_id, 'sharedfolder', log_time,
           log_json->>'file_name', NULL::text, NULL::text, NULL::text,
           NULL::int, NULL::int, NULL::int,
           agent_json
    FROM log_dlp_sharedfolder_t
    WHERE license_code = %(lic)s
      AND (log_json->>'block_type')::int = 0
      AND log_time >= %(win_start)s

    UNION ALL

    SELECT agent_id, 'chatgpt', log_time,
           NULL::text, NULL::text, NULL::text, NULL::text,
           NULL::int, NULL::int,
           (log_json->>'pri_cnt')::int,
           agent_json
    FROM log_dlp_chatgpt_t
    WHERE license_code = %(lic)s
      AND (log_json->>'block_type')::int = 0
      AND log_time >= %(win_start)s
)
SELECT
    agent_id,
    COUNT(DISTINCT ch)                                     AS distinct_channels,
    COUNT(*)                                               AS total_allowed,
    array_agg(DISTINCT ch)                                 AS channels,
    -- 채널 교차는 "의심 활동이 있는" 채널이 2개 이상일 때만 (정상 다채널 사용자 오탐 방지)
    (COUNT(DISTINCT ch) FILTER (WHERE
        (fn IS NOT NULL AND fn <> '' AND dfn IS NOT NULL AND dfn <> ''
         AND lower(split_part(fn, '.', -1)) <> lower(split_part(dfn, '.', -1)))
        OR (zip IS NOT NULL AND zip <> '')
        OR (hef IS NOT NULL)
        OR (total_pri >= %(mass_pri_threshold)s)
        OR (category = ANY(%(unofficial_categories)s))
        OR (chatgpt_pri > 0)
     ) >= 2)                                               AS cross_channel_flag,
    array_agg(DISTINCT ch) FILTER (WHERE
        (fn IS NOT NULL AND fn <> '' AND dfn IS NOT NULL AND dfn <> ''
         AND lower(split_part(fn, '.', -1)) <> lower(split_part(dfn, '.', -1)))
        OR (zip IS NOT NULL AND zip <> '')
        OR (hef IS NOT NULL)
        OR (total_pri >= %(mass_pri_threshold)s)
        OR (category = ANY(%(unofficial_categories)s))
        OR (chatgpt_pri > 0)
     )                                                     AS susp_channels,

    bool_or(fn IS NOT NULL AND fn <> '' AND dfn IS NOT NULL AND dfn <> ''
            AND lower(split_part(fn, '.', -1)) <> lower(split_part(dfn, '.', -1)))
                                                            AS ext_spoof_flag,
    (array_agg(jsonb_build_object('channel', ch, 'file_name', fn, 'dst_file_name', dfn, 'log_time', log_time)
               ORDER BY log_time DESC)
     FILTER (WHERE fn IS NOT NULL AND fn <> '' AND dfn IS NOT NULL AND dfn <> ''
             AND lower(split_part(fn, '.', -1)) <> lower(split_part(dfn, '.', -1))))[1]
                                                            AS ext_spoof_evidence,

    bool_or(zip IS NOT NULL AND zip <> '')                 AS zip_hide_flag,
    (array_agg(jsonb_build_object('channel', ch, 'zip_filelist', zip, 'log_time', log_time)
               ORDER BY log_time DESC)
     FILTER (WHERE zip IS NOT NULL AND zip <> ''))[1]      AS zip_hide_evidence,

    bool_or(hef IS NOT NULL)                               AS enc_evade_flag,
    (array_agg(jsonb_build_object('channel', ch, 'hash_extract_fail_reason', hef, 'log_time', log_time)
               ORDER BY log_time DESC)
     FILTER (WHERE hef IS NOT NULL))[1]                    AS enc_evade_evidence,

    bool_or(total_pri >= %(mass_pri_threshold)s)           AS mass_pri_flag,
    (array_agg(jsonb_build_object('channel', ch, 'total_pri_cnt', total_pri, 'log_time', log_time)
               ORDER BY total_pri DESC)
     FILTER (WHERE total_pri >= %(mass_pri_threshold)s))[1]
                                                            AS mass_pri_evidence,

    bool_or(category = ANY(%(unofficial_categories)s))     AS unofficial_flag,
    (array_agg(jsonb_build_object('channel', ch, 'category', category, 'log_time', log_time)
               ORDER BY log_time DESC)
     FILTER (WHERE category = ANY(%(unofficial_categories)s)))[1]
                                                            AS unofficial_evidence,

    bool_or(EXTRACT(hour FROM log_time AT TIME ZONE 'Asia/Seoul') NOT BETWEEN %(workhour_start)s AND %(workhour_end)s
            OR EXTRACT(dow FROM log_time AT TIME ZONE 'Asia/Seoul') IN (0, 6))       AS night_flag,
    (array_agg(jsonb_build_object('channel', ch, 'log_time', log_time)
               ORDER BY log_time DESC)
     FILTER (WHERE EXTRACT(hour FROM log_time AT TIME ZONE 'Asia/Seoul') NOT BETWEEN %(workhour_start)s AND %(workhour_end)s
             OR EXTRACT(dow FROM log_time AT TIME ZONE 'Asia/Seoul') IN (0, 6)))[1]  AS night_evidence,

    bool_or(chatgpt_pri > 0)                               AS genai_flag,
    (array_agg(jsonb_build_object('channel', ch, 'pri_cnt', chatgpt_pri, 'log_time', log_time)
               ORDER BY log_time DESC)
     FILTER (WHERE chatgpt_pri > 0))[1]                    AS genai_evidence,

    (array_agg(agent_json ORDER BY log_time DESC))[1]      AS latest_agent_json
FROM allowed
GROUP BY agent_id
HAVING COUNT(*) > 0
ORDER BY distinct_channels DESC, total_allowed DESC;
"""

_USB_ONLY_SQL = """
SELECT
    agent_id,
    1                                                      AS distinct_channels,
    COUNT(*)                                               AS total_allowed,

    bool_or(fn IS NOT NULL AND fn <> '' AND dfn IS NOT NULL AND dfn <> ''
            AND lower(split_part(fn, '.', -1)) <> lower(split_part(dfn, '.', -1)))
                                                            AS ext_spoof_flag,
    (array_agg(jsonb_build_object('file_name', fn, 'dst_file_name', dfn, 'log_time', log_time)
               ORDER BY log_time DESC)
     FILTER (WHERE fn IS NOT NULL AND fn <> '' AND dfn IS NOT NULL AND dfn <> ''
             AND lower(split_part(fn, '.', -1)) <> lower(split_part(dfn, '.', -1))))[1]
                                                            AS ext_spoof_evidence,

    bool_or(zip IS NOT NULL AND zip <> '')                 AS zip_hide_flag,
    (array_agg(jsonb_build_object('zip_filelist', zip, 'log_time', log_time)
               ORDER BY log_time DESC)
     FILTER (WHERE zip IS NOT NULL AND zip <> ''))[1]      AS zip_hide_evidence,

    bool_or(hef IS NOT NULL)                               AS enc_evade_flag,
    (array_agg(jsonb_build_object('hash_extract_fail_reason', hef, 'log_time', log_time)
               ORDER BY log_time DESC)
     FILTER (WHERE hef IS NOT NULL))[1]                    AS enc_evade_evidence,

    bool_or(total_pri >= %(mass_pri_threshold)s)           AS mass_pri_flag,
    (array_agg(jsonb_build_object('total_pri_cnt', total_pri, 'log_time', log_time)
               ORDER BY total_pri DESC)
     FILTER (WHERE total_pri >= %(mass_pri_threshold)s))[1]
                                                            AS mass_pri_evidence,

    bool_or(EXTRACT(hour FROM log_time AT TIME ZONE 'Asia/Seoul') NOT BETWEEN %(workhour_start)s AND %(workhour_end)s
            OR EXTRACT(dow FROM log_time AT TIME ZONE 'Asia/Seoul') IN (0, 6))       AS night_flag,
    (array_agg(jsonb_build_object('log_time', log_time)
               ORDER BY log_time DESC)
     FILTER (WHERE EXTRACT(hour FROM log_time AT TIME ZONE 'Asia/Seoul') NOT BETWEEN %(workhour_start)s AND %(workhour_end)s
             OR EXTRACT(dow FROM log_time AT TIME ZONE 'Asia/Seoul') IN (0, 6)))[1]  AS night_evidence,

    (array_agg(agent_json ORDER BY log_time DESC))[1]      AS latest_agent_json
FROM (
    SELECT agent_id, log_time,
           log_json->>'file_name' AS fn,
           log_json->>'dst_file_name' AS dfn,
           log_json->>'zip_filelist' AS zip,
           log_json->>'hash_extract_fail_reason' AS hef,
           (log_json->>'total_pri_cnt')::int AS total_pri,
           agent_json
    FROM log_dlp_media_t
    WHERE license_code = %(lic)s
      AND log_json->>'is_block' = 'false'
      AND log_time >= %(win_start)s
) media_allowed
GROUP BY agent_id
HAVING COUNT(*) > 0
ORDER BY total_allowed DESC;
"""


_RECURRENCE_SQL = """
WITH allowed AS (
    SELECT agent_id, log_time,
           log_json->>'file_name' AS fn, log_json->>'dst_file_name' AS dfn,
           log_json->>'zip_filelist' AS zip, log_json->>'hash_extract_fail_reason' AS hef,
           (log_json->>'total_pri_cnt')::int AS total_pri
    FROM log_dlp_media_t
    WHERE license_code=%(lic)s AND log_json->>'is_block'='false' AND log_time >= %(horizon_start)s
    UNION ALL
    SELECT agent_id, log_time,
           log_json->>'file_name', log_json->>'dst_file_name',
           log_json->>'zip_filelist', log_json->>'hash_extract_fail_reason',
           (log_json->>'total_pri_cnt')::int
    FROM log_dlp_fileattach_t
    WHERE license_code=%(lic)s AND log_json->>'is_block'='false' AND log_time >= %(horizon_start)s
)
SELECT agent_id,
       COUNT(DISTINCT date_trunc('week', log_time)) AS recur_weeks,
       to_char(min(log_time), 'YYYY-MM-DD') AS first_seen
FROM allowed
WHERE (fn IS NOT NULL AND fn <> '' AND dfn IS NOT NULL AND dfn <> ''
       AND lower(split_part(fn, '.', -1)) <> lower(split_part(dfn, '.', -1)))
   OR (zip IS NOT NULL AND zip <> '')
   OR (hef IS NOT NULL)
   OR (total_pri >= %(mass_pri_threshold)s)
GROUP BY agent_id
"""


def get_recurrence(license_code: str) -> dict:
    """agent_id → {weeks, first_seen}. 최근 8주에서 의심 반출이 걸린 서로 다른 주 수."""
    params = {
        "lic": license_code,
        "horizon_start": datetime.now(timezone.utc) - timedelta(days=_RECURRENCE_HORIZON_DAYS),
        "mass_pri_threshold": _MASS_PRI_THRESHOLD,
        "workhour_start": config.WORKHOUR_START,
        "workhour_end": config.WORKHOUR_END,
    }
    out = {}
    for row in fetch_all(_RECURRENCE_SQL, params):
        out[row["agent_id"]] = {"weeks": row["recur_weeks"], "first_seen": row["first_seen"]}
    return out


def _window_start(window_hours: int | None) -> datetime:
    hours = window_hours or config.ANALYSIS_WINDOW_HOURS
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def _pack_fired(row: dict, mapping: list[tuple[str, str, str]]) -> dict:
    """(신호코드, flag 컬럼, evidence 컬럼) 목록을 순회해 발동된 신호만 dict 로 구성."""
    fired = {}
    for code, flag_col, evidence_col in mapping:
        if row.get(flag_col):
            fired[code] = row.get(evidence_col) or {}
    return fired


def _target_user(row: dict) -> tuple[str | None, str | None]:
    agent_json = row.get("latest_agent_json") or {}
    return agent_json.get("id"), agent_json.get("name")


def find_exfil_candidates(license_code: str, window_hours: int | None = None) -> list[dict]:
    """5채널 허용로그 채널교차 유출 후보 산출 (설계문서 §3.3)."""
    params = {
        "lic": license_code,
        "win_start": _window_start(window_hours),
        "mass_pri_threshold": _MASS_PRI_THRESHOLD,
        "unofficial_categories": _UNOFFICIAL_CATEGORIES,
        "workhour_start": config.WORKHOUR_START,
        "workhour_end": config.WORKHOUR_END,
    }
    rows = fetch_all(_CROSS_CHANNEL_SQL, params)
    recurrence = get_recurrence(license_code)   # agent_id → {weeks, first_seen}

    mapping = [
        ("S1_ext_spoof", "ext_spoof_flag", "ext_spoof_evidence"),
        ("S2_zip_hide", "zip_hide_flag", "zip_hide_evidence"),
        ("S3_enc_evade", "enc_evade_flag", "enc_evade_evidence"),
        ("S4_mass_pri", "mass_pri_flag", "mass_pri_evidence"),
        ("S5_unofficial", "unofficial_flag", "unofficial_evidence"),
        ("S6_night", "night_flag", "night_evidence"),
        ("S8_genai_secret", "genai_flag", "genai_evidence"),
    ]

    candidates = []
    for row in rows:
        fired = _pack_fired(row, mapping)
        if row.get("cross_channel_flag"):
            fired["S7_cross_channel"] = {"channels": row.get("susp_channels")}
        rec = recurrence.get(row["agent_id"])
        recur_weeks = rec["weeks"] if rec else 0
        if recur_weeks >= _RECURRENCE_MIN_WEEKS:
            fired["S9_persistence"] = {"weeks": recur_weeks, "first_seen": rec["first_seen"]}
        target_user_id, target_user_name = _target_user(row)
        candidates.append({
            "agent_id": row["agent_id"],
            "distinct_channels": row["distinct_channels"],
            "total_allowed": row["total_allowed"],
            "channels": row.get("channels") or [],   # scoring.build_signals_json 이 채널칩에 사용
            "recurrence_weeks": recur_weeks,          # UI "지속 N주" 뱃지용
            "fired": fired,
            "target_user_id": target_user_id,
            "target_user_name": target_user_name,
        })
    return candidates


def find_usb_candidates(license_code: str, window_hours: int | None = None) -> list[dict]:
    """USB(media) 단독 시나리오(데모 B) 검증용 축소판 — S1~S4, S6 만 판정."""
    params = {
        "lic": license_code,
        "win_start": _window_start(window_hours),
        "mass_pri_threshold": _MASS_PRI_THRESHOLD,
        "workhour_start": config.WORKHOUR_START,
        "workhour_end": config.WORKHOUR_END,
    }
    rows = fetch_all(_USB_ONLY_SQL, params)

    mapping = [
        ("S1_ext_spoof", "ext_spoof_flag", "ext_spoof_evidence"),
        ("S2_zip_hide", "zip_hide_flag", "zip_hide_evidence"),
        ("S3_enc_evade", "enc_evade_flag", "enc_evade_evidence"),
        ("S4_mass_pri", "mass_pri_flag", "mass_pri_evidence"),
        ("S6_night", "night_flag", "night_evidence"),
    ]

    candidates = []
    for row in rows:
        fired = _pack_fired(row, mapping)
        target_user_id, target_user_name = _target_user(row)
        candidates.append({
            "agent_id": row["agent_id"],
            "distinct_channels": row["distinct_channels"],
            "total_allowed": row["total_allowed"],
            "channels": ["media"],   # USB 단독 시나리오 — 채널은 media 고정
            "fired": fired,
            "target_user_id": target_user_id,
            "target_user_name": target_user_name,
        })
    return candidates
