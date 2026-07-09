"""위험 점수 계산 — 걸린 신호 가중치 합산 → risk_score / severity.

설계문서 §3.2:
  risk_score = min(100, Σ 가중치)
  severity   = high(≥60) / mid(≥35) / low(그 외)
  적재 임계   = RISK_THRESHOLD(기본 35) 이상만
설계 의도: 단일 신호 최대 30점 → 혼자선 high 불가. "겹침이 신뢰를 만든다"를 점수로 강제.

이 모듈은 순수 함수라 SQL/AI 없이 단위테스트 가능. 세션에서 테스트와 함께 완성 권장.
"""
from recipes.base import BY_CODE


def score(fired_codes: list[str]) -> int:
    total = sum(BY_CODE[c].weight for c in fired_codes if c in BY_CODE)
    return min(100, total)


def severity(risk_score: int) -> str:
    if risk_score >= 60:
        return "high"
    if risk_score >= 35:
        return "mid"
    if risk_score >= 20:
        return "watch"   # 관심: 신호는 있으나 단독으론 임계 미달 (오탐 억제 실증)
    return "low"


def build_signals_json(candidate: dict) -> dict:
    """recipes.exfil 결과 1건 → ai_analysis_result_t.signals_json 구조로 변환.
    설계문서 §2 signals_json 구조 참조.
    """
    fired = candidate.get("fired", {})
    fired_codes = list(fired.keys())
    risk_score = score(fired_codes)

    signals = []
    for code, evidence in fired.items():
        signal = BY_CODE.get(code)
        if signal is None:
            continue
        signals.append({
            "code": signal.code,
            "name": signal.name,
            "weight": signal.weight,
            "fired": True,
            "evidence": evidence,
            "mitre": signal.mitre,
        })

    return {
        "risk_score": risk_score,
        "severity": severity(risk_score),
        "channels": candidate.get("channels", []),
        "recurrence_weeks": candidate.get("recurrence_weeks", 0),
        "signals": signals,
    }
