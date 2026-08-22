"""리포트 피드 + 상세 + UI 진입점 (설계문서 §5-1, §5-2).
[UI 세션 작업] 피드 카드 리스트 / 상세(신호 겹침 시각화 + 증거 + AI 서사).
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config import config
from db import fetch_all, fetch_one
from analyzer import run_analysis
import watchlist_state

router = APIRouter(tags=["reports"])

templates = Jinja2Templates(directory="web/templates")

_LIST_SQL = """
SELECT pno, target_agent_id, target_user_name, target_user_id,
       severity, risk_score, signals_json->'channels' AS channels,
       signals_json->'recurrence_weeks' AS recurrence_weeks,
       summary_text, status, reg_time
FROM ai_analysis_result_t
WHERE license_code = %(license_code)s
  AND analysis_window = %(window)s
{status_clause}
ORDER BY CASE severity WHEN 'high' THEN 4 WHEN 'mid' THEN 3 WHEN 'watch' THEN 2 WHEN 'low' THEN 1 ELSE 0 END DESC,
         risk_score DESC
"""

_DETAIL_SQL = """
SELECT *
FROM ai_analysis_result_t
WHERE license_code = %(license_code)s AND pno = %(pno)s
"""


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    """UI 메인 페이지 (설계문서 §5)."""
    return templates.TemplateResponse("index.html", {"request": request})


_ALLOWED_WINDOWS = {"1d", "7d", "30d"}


def _norm_window(window: str | None) -> str:
    """window 파라미터 정규화 — 허용값 외엔 기본 '7d'(주)."""
    return window if window in _ALLOWED_WINDOWS else "7d"


@router.get("/api/reports")
def list_reports(status: str | None = None, window: str | None = None):
    """ai_analysis_result_t 목록. 기간 렌즈(window)별, severity/risk_score 내림차순."""
    params = {"license_code": config.DEMO_LICENSE_CODE, "window": _norm_window(window)}
    status_clause = ""
    if status:
        status_clause = "AND status = %(status)s"
        params["status"] = status
    sql = _LIST_SQL.format(status_clause=status_clause)
    items = fetch_all(sql, params)
    return {"items": items}


@router.get("/api/reports/{pno}")
def get_report(pno: int):
    """리포트 1건 상세(signals_json 포함)."""
    row = fetch_one(_DETAIL_SQL, {"license_code": config.DEMO_LICENSE_CODE, "pno": pno})
    return row or {}


_EVENTS_SQL = """
SELECT log_time, 'media'::text AS channel, agent_json->>'com_name' AS pc, log_json
  FROM log_dlp_media_t
  WHERE license_code=%(lic)s AND agent_id=%(aid)s AND log_time BETWEEN %(s)s AND %(e)s
UNION ALL SELECT log_time, 'fileattach', agent_json->>'com_name', log_json
  FROM log_dlp_fileattach_t
  WHERE license_code=%(lic)s AND agent_id=%(aid)s AND log_time BETWEEN %(s)s AND %(e)s
UNION ALL SELECT log_time, 'chatgpt', agent_json->>'com_name', log_json
  FROM log_dlp_chatgpt_t
  WHERE license_code=%(lic)s AND agent_id=%(aid)s AND log_time BETWEEN %(s)s AND %(e)s
UNION ALL SELECT log_time, 'website', agent_json->>'com_name', log_json
  FROM log_dlp_website_t
  WHERE license_code=%(lic)s AND agent_id=%(aid)s AND log_time BETWEEN %(s)s AND %(e)s
UNION ALL SELECT log_time, 'sharedfolder', agent_json->>'com_name', log_json
  FROM log_dlp_sharedfolder_t
  WHERE license_code=%(lic)s AND agent_id=%(aid)s AND log_time BETWEEN %(s)s AND %(e)s
ORDER BY log_time DESC
"""


@router.get("/api/reports/{pno}/events")
def get_report_events(pno: int):
    """리포트 판정의 원본 로그 근거 — 대상 에이전트의 분석 창 내 5채널 실제 반출 로그(탐지=SQL 사실)."""
    rpt = fetch_one(
        "SELECT target_agent_id, period_start, period_end "
        "FROM ai_analysis_result_t WHERE pno=%(pno)s AND license_code=%(lic)s",
        {"pno": pno, "lic": config.DEMO_LICENSE_CODE},
    )
    if not rpt or rpt.get("target_agent_id") is None:
        return {"events": [], "count": 0}
    events = fetch_all(_EVENTS_SQL, {
        "lic": config.DEMO_LICENSE_CODE,
        "aid": rpt["target_agent_id"],
        "s": rpt["period_start"],
        "e": rpt["period_end"],
    })
    return {"events": events, "count": len(events)}


@router.post("/api/reports/run")
def run_reports():
    """데모 '지금 분석' 버튼 — analyzer.run_analysis 수동 트리거."""
    loaded = run_analysis(config.DEMO_LICENSE_CODE)
    return {"loaded": loaded}


_SUMMARY_SQL = """
SELECT
  (SELECT count(*) FROM agent_t a
     WHERE a.license_code = %(license_code)s
       AND to_jsonb(a.*)::text LIKE %(cohort)s) AS scanned,
  count(*) FILTER (WHERE severity = 'high')  AS high,
  count(*) FILTER (WHERE severity = 'mid')   AS mid,
  count(*) FILTER (WHERE severity = 'watch') AS watch,
  count(*)                                   AS reports
FROM ai_analysis_result_t
WHERE license_code = %(license_code)s
  AND analysis_window = %(window)s
"""


@router.get("/api/summary")
def get_summary(window: str | None = None):
    """피드 상단 요약: 데모 스캔 코호트(owl-demo 마커) 총원 + 해당 기간 렌즈의 심각도별 선별 결과.
    스키마 무관하게 동작하도록 to_jsonb(a.*)::text 로 행 전체에서 마커를 찾는다:
      - 도커 데모(DEMO0001): 시드가 user_info 에 _cohort=owl-demo 를 심음
      - 네이티브(oa233262): owl-demo 에이전트가 agent_info 에 마커 보유(실 스키마)
    구버전은 데모 스키마에 없는 agent_info/is_deleted 컬럼을 직접 참조해 500이 났음."""
    row = fetch_one(_SUMMARY_SQL, {
        "license_code": config.DEMO_LICENSE_CODE,
        "cohort": "%owl-demo%",
        "window": _norm_window(window),
    })
    return row or {}


@router.get("/api/config")
def get_config():
    """UI가 정책 적용(apply) 호출 시 필요한 license_code 조회."""
    return {"license_code": config.DEMO_LICENSE_CODE}


# ── 감시목록 '지속 관찰' 핀 ──

class PinRequest(BaseModel):
    pno: int
    pinned: bool


@router.get("/api/watchlist/pins")
def get_watchlist_pins():
    """핀(지속 관찰) 목록 — 감시목록 뷰가 로드 시 반영."""
    return {"pinned": watchlist_state.list_pins()}


@router.post("/api/watchlist/pin")
def set_watchlist_pin(req: PinRequest):
    """리포트를 '지속 관찰'로 고정/해제. 재분석과 무관하게 로컬 유지."""
    pinned = watchlist_state.set_pin(req.pno, req.pinned)
    return {"ok": True, "pinned": pinned}
