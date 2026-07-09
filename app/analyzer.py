"""분석 루프 — 후보 산출 → 스코어 → Ollama 요약 → ai_analysis_result_t 적재.
설계문서 §1.2 [분석 루프], §7 단계4.

넷을 엮는 글루:
  recipes.exfil.find_exfil_candidates  (탐지=SQL)
  scoring.score/severity/build_signals_json
  ollama_client.summarize              (AI=요약만)
  db.execute                           (적재)

데모에선 스케줄러 대신 수동 실행(엔드포인트/CLI)으로도 트리거 가능 — 발표 타이밍 리스크 회피.
"""
import json
from datetime import datetime, timedelta, timezone

from config import config
from recipes.exfil import find_exfil_candidates
from scoring import score, severity, build_signals_json
from ollama_client import summarize
from db import execute

# 일/주/월 기간 렌즈 — 프리베이크로 3개 window 를 미리 구워두면 UI 토글이 즉시(ollama 대기 0).
WINDOWS = [("1d", 24), ("7d", 168), ("30d", 720)]

_INSERT_SQL = """
INSERT INTO ai_analysis_result_t
    (license_code, analysis_type, target_agent_id, target_user_id, target_user_name,
     period_start, period_end, risk_score, severity, signals_json, summary_text,
     analysis_window, model_name, status)
VALUES
    (%(license_code)s, 'exfil_candidate', %(target_agent_id)s, %(target_user_id)s, %(target_user_name)s,
     %(period_start)s, %(period_end)s, %(risk_score)s, %(severity)s, %(signals_json)s::jsonb, %(summary_text)s,
     %(analysis_window)s, %(model_name)s, 'new')
"""

# 재분석 시 해당 라이선스의 직전 exfil 리포트를 전량 제거해 중복 방지(전체 갱신).
# (status='new'만 지우면 승인(actioned)된 대상이 재분석 때 중복 생성되는 버그가 있었음)
_PURGE_SQL = """
DELETE FROM ai_analysis_result_t
WHERE license_code = %(license_code)s AND analysis_type = 'exfil_candidate'
"""


def run_analysis(license_code: str | None = None, window_hours: int | None = None,
                 replace: bool = True) -> int:
    """한 사이클 실행. 적재된 리포트 수 반환.

    1) find_exfil_candidates() 로 후보 조회
    2) score()/severity(), 임계(WATCH_THRESHOLD, 기본 20) 미만 스킵
    3) build_signals_json() → summarize() 서사 생성
    4) ai_analysis_result_t 적재
    """
    lic = license_code or config.DEMO_LICENSE_CODE
    if not lic:
        raise ValueError("license_code 가 필요합니다 (.env DEMO_LICENSE_CODE 또는 인자로 전달)")

    if replace:
        execute(_PURGE_SQL, {"license_code": lic})

    # 같은 사람+같은 신호조합이면 요약 재사용 — 7d/30d 겹치는 대상의 중복 ollama 호출 방지
    summary_cache = {}
    loaded = 0
    # window_hours 인자가 주어지면 그 창만, 없으면 일/주/월 전체를 프리베이크
    windows = [(_win_key(window_hours), window_hours)] if window_hours else WINDOWS
    for win_key, win_hours in windows:
        period_end = datetime.now(timezone.utc)
        period_start = period_end - timedelta(hours=win_hours)
        candidates = find_exfil_candidates(lic, win_hours)
        for cand in candidates:
            fired_codes = list(cand.get("fired", {}).keys())
            risk = score(fired_codes)
            if risk < config.WATCH_THRESHOLD:
                continue  # 관심 임계(20) 미만 = 정상, 리포트 안 올림 (오탐 억제)
                # 20~34=관심(watch), 35+=주의/고위험 — severity가 구분

            signals_json = build_signals_json(cand)
            cache_key = (cand.get("agent_id"), tuple(sorted(fired_codes)), risk)
            summary = summary_cache.get(cache_key)
            if summary is None:
                summary = summarize(signals_json, {
                    "user_id": cand.get("target_user_id"),
                    "user_name": cand.get("target_user_name"),
                })
                summary_cache[cache_key] = summary

            execute(_INSERT_SQL, {
                "license_code": lic,
                "target_agent_id": cand.get("agent_id"),
                "target_user_id": cand.get("target_user_id"),
                "target_user_name": cand.get("target_user_name"),
                "period_start": period_start,
                "period_end": period_end,
                "risk_score": risk,
                "severity": severity(risk),
                "signals_json": json.dumps(signals_json, ensure_ascii=False),
                "summary_text": summary,
                "analysis_window": win_key,
                "model_name": config.OLLAMA_MODEL,
            })
            loaded += 1

    return loaded


def _win_key(window_hours: int) -> str:
    """시간(h) → window 라벨. WINDOWS 에 없으면 '7d' 로 폴백."""
    for k, h in WINDOWS:
        if h == window_hours:
            return k
    return "7d"


if __name__ == "__main__":
    # 수동 실행:  python analyzer.py [license_code]
    #   컨테이너 안:  docker exec -it onpilot python analyzer.py DEMO0001
    import sys
    lic = sys.argv[1] if len(sys.argv) > 1 else None
    n = run_analysis(lic)
    print(f"[onpilot] 분석 완료 — 리포트 {n}건 적재")
