"""정책 반영 — 기존 PCFILTER 자산(policy_t media_separate) 재사용. 신규 스키마 0.
설계문서 §6. 스카우트가 확인한 setMediaSeparatePolicyAdd 경로를 raw SQL 로 재현.

핵심 함정(스카우트 확인):
  - s_time/e_time 은 반복 스케줄이 아니라 특정 기간(datetime range) → 데모는 '오늘 밤 1회성'.
  - 모든 정책 UPDATE 에 pvn = pvn + 1 필수 (에이전트 갱신 감지).

안전벨트: 최종 정책 JSON 은 여기(코드)가 조립한다. AI 는 슬롯만 추출(ollama_client.extract_slots).
"""
import json
from datetime import datetime, timedelta

from db import pool
from config import config

# 데모 placeholder — 실제 차단 프리셋 pid 로 교체 필요 (설계문서 §9 미결)
_BLOCK_MEDIA_PID = 0
# 반영 대상 media_separate pid — 설정값(실 라이선스 기존 정책과 충돌 방지). 데모 seed=1, oa233262=9001
DEFAULT_SEPARATE_PID = config.POLICY_SEPARATE_PID


def build_policy_json(slots: dict, target_name: str) -> dict:
    """슬롯 → 정책 JSON 조립 (AI 아님, 코드가 조립 — 환각 리스크 0). 설계문서 §6 템플릿.

    slots 예: {"intent":"block_media","target_agent_id":123,"scope":"night"}
    scope=='night' → 오늘 22:00 ~ 내일 06:00 1회성 기간. 그 외 → 기간제한 없음(상시).
    """
    scope = slots.get("scope")
    night = scope == "night"
    weekend = scope == "weekend"
    timed = night or weekend
    suffix = "(야간)" if night else "(주말)" if weekend else ""

    policy = {
        "name": "온파일럿 자동제안-USB차단" + suffix,
        "target_name": target_name,
        "use": True,
        "alarm": True,
        "media_pid": _BLOCK_MEDIA_PID,
        "time_set": timed,
        "offline": {"use": True, "policy": {"pid": "", "alarm": True}},
    }

    if night:
        today = datetime.now()
        start = today.replace(hour=22, minute=0, second=0, microsecond=0)
        end = (today + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
        policy["s_time"] = start.strftime("%Y-%m-%d %H:%M")
        policy["e_time"] = end.strftime("%Y-%m-%d %H:%M")
    elif weekend:
        today = datetime.now()
        days_to_sat = (5 - today.weekday()) % 7  # 월=0 … 토=5. 다가오는 토요일(오늘이 토면 오늘)
        sat = (today + timedelta(days=days_to_sat)).replace(hour=0, minute=0, second=0, microsecond=0)
        mon = sat + timedelta(days=2)  # 일요일 끝 = 월요일 00:00
        policy["s_time"] = sat.strftime("%Y-%m-%d %H:%M")
        policy["e_time"] = mon.strftime("%Y-%m-%d %H:%M")
    else:
        policy["s_time"] = ""
        policy["e_time"] = ""

    return policy


# ── 정책 반영 SQL (설계문서 §6) ──────────────────────────────────
_UPDATE_SEPARATE = """
UPDATE policy_t
SET policy_json = %(policy_json)s::jsonb,
    modify_json = jsonb_build_object('modify_time', now()::text, 'modify_id', %(admin)s::text),
    pvn = pvn + 1
WHERE license_code = %(lic)s AND service_type = 'dlp'
  AND policy_type = 'media_separate' AND pid = %(pid)s
RETURNING pvn
"""

# 재실행 대비: 같은 pid 의 target_user 를 갈아끼움 (idempotent)
_DELETE_TARGET = """
DELETE FROM policy_sub_t
WHERE license_code = %(lic)s AND service_type = 'dlp'
  AND policy_type = 'media_separate' AND sub_name = 'target_user' AND pid = %(pid)s
"""

_INSERT_TARGET = """
INSERT INTO policy_sub_t (license_code, pid, service_type, policy_type, sub_name, sub_text)
VALUES (%(lic)s, %(pid)s, 'dlp', 'media_separate', 'target_user', ARRAY[%(agent_id)s]::text[])
"""

# 부모 매체정책도 pvn 동기화 (에이전트 갱신 감지)
_BUMP_PARENT = """
UPDATE policy_t SET pvn = pvn + 1
WHERE license_code = %(lic)s AND service_type = 'dlp' AND policy_type = 'media'
"""


def apply_media_separate(license_code: str, agent_id: int, policy_json: dict,
                         pid: int = DEFAULT_SEPARATE_PID, admin: str = "onpilot") -> dict:
    """policy_t(media_separate) UPDATE + policy_sub_t(target_user) 교체 + pvn+1.
    3개 SQL 을 한 트랜잭션으로. 반환: {"applied": bool, "pvn": int|None}.
    """
    params = {
        "lic": license_code,
        "pid": pid,
        "agent_id": str(agent_id),
        "policy_json": json.dumps(policy_json, ensure_ascii=False),
        "admin": admin,
    }
    with pool.connection() as conn:   # with 블록 정상 종료 시 커밋, 예외 시 롤백
        with conn.cursor() as cur:
            cur.execute(_UPDATE_SEPARATE, params)
            row = cur.fetchone()
            new_pvn = row[0] if row else None
            if new_pvn is None:
                # 대상 media_separate 정책이 없음 → 반영 실패 (시드/데이터 확인 필요)
                return {"applied": False, "pvn": None}
            cur.execute(_DELETE_TARGET, params)
            cur.execute(_INSERT_TARGET, params)
            cur.execute(_BUMP_PARENT, params)
    return {"applied": True, "pvn": new_pvn}
