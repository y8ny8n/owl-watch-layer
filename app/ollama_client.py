"""Ollama 호출 — 두 역할만 (설계문서 §4).

역할 1) summarize(): 신호 사실(signals_json) → 사람 말 리포트 서사.
역할 2) extract_slots(): 관리자 자연어 → 정책 슬롯 JSON '추출만'.
        ★ 최종 정책 JSON 은 절대 AI 가 만들지 않는다. policy.py 가 템플릿으로 조립. (환각 리스크 0)

Ollama REST:  POST {OLLAMA_URL}/api/generate   (JSON 강제는 "format":"json")
"""
import json
import logging

import httpx
from config import config

logger = logging.getLogger(__name__)

_TIMEOUT = 60.0

CHANNEL_LABEL = {
    "media": "매체(USB)", "fileattach": "파일첨부", "website": "웹사이트",
    "sharedfolder": "공유폴더", "chatgpt": "생성형AI",
}

_SUMMARY_FALLBACK = "(AI 요약 생성 실패 — 신호 근거만 확인하세요)"
_SLOT_FALLBACK = {"intent": None, "target_agent_id": None, "scope": None, "confidence": 0.0}


def _generate(prompt: str, *, json_mode: bool = False) -> str:
    payload = {"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False}
    if json_mode:
        payload["format"] = "json"
    r = httpx.post(f"{config.OLLAMA_URL}/api/generate", json=payload, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json().get("response", "")


# ── 역할 1: 분석 요약 ──────────────────────────────────────────
SUMMARY_SYSTEM = (
    "너는 보안관제 로그를 사람이 읽기 쉽게 정리하는 분석가다. 주어진 사실만으로 한국어 요약을 쓴다. 규칙:\n"
    "1) 평문으로만 작성. 마크다운·별표(**)·번호목록·불릿 절대 금지.\n"
    "2) 3문장 이내로 간결하게. 군더더기·인사말 없이 바로 본론.\n"
    "3) 사실에 없는 수치·동기·추측 금지. 각 반출은 정책상 '허용'된 건임을 전제한다.\n"
    "4) 중립적·사실 위주로 쓴다. '관찰되었다·확인되었다·나타났다'처럼 일어난 일을 담담히 기술하고, "
    "'의심스럽다·불법·위법·범죄·악의·심각·혐의·정황' 같은 단정하거나 부정적으로 몰아가는 표현은 쓰지 않는다. 판단은 관리자에게 맡긴다.\n"
    "5) 어떤 신호가 겹쳐 나타났는지 사실 중심으로 짚는다.\n"
    "6) 마지막에 '조치 제안: ...' 한 줄로, 단정적 처분이 아니라 '추가 확인' 수준의 담백한 권고를 붙인다.\n"
    "7) 대상자는 제공된 이름만 사용하고, 아이디(영문)나 다른 호칭을 지어내지 않는다."
)


def _format_evidence(signals_json: dict) -> str:
    lines = []
    for sig in signals_json.get("signals", []):
        if not sig.get("fired"):
            continue
        lines.append(f"- {sig.get('name')} (가중치 {sig.get('weight')}): {sig.get('evidence')}")
    return "\n".join(lines) if lines else "(신호 없음)"


def summarize(signals_json: dict, target: dict) -> str:
    """signals_json + 대상 정보 → 사람 말 서사."""
    name = (target or {}).get("user_name") or (target or {}).get("user_id") or "대상자"
    channels = signals_json.get("channels") or []
    channel_ko = ", ".join(CHANNEL_LABEL.get(c, c) for c in channels)
    evidence = _format_evidence(signals_json)
    prompt = (
        f"{SUMMARY_SYSTEM}\n\n"
        f"[사실]\n"
        f"대상자 이름: {name}\n"
        f"위험 점수: {signals_json.get('risk_score')}/100\n"
        f"관련 채널: {channel_ko}\n"
        f"겹친 신호와 근거:\n{evidence}\n\n"
        f"위 사실만으로 '{name}'에 대한 보안관제 보고를 3문장 이내 평문으로 쓰고, "
        f"마지막 줄에 '조치 제안: ...'을 붙여라."
    )
    try:
        return _generate(prompt).strip()
    except httpx.HTTPError as e:
        logger.warning("Ollama summarize 미가용 → 폴백 (%s)", e)
        return _SUMMARY_FALLBACK


# ── 역할 2: 자연어 → 정책 슬롯 추출 ────────────────────────────
SLOT_SYSTEM = (
    "관리자 발화에서 정책 슬롯만 JSON 으로 추출하라. 추측 금지, 없는 값은 null. "
    '형식: {"intent":"block_media","target_agent_id":<int|null>,"scope":"night|weekend|all|null"}'
)


def _keyword_slots(utterance: str, context: dict) -> dict:
    """Ollama 미가용 시 키워드 기반 폴백 슬롯 추출 (데모 안정성 — 설계문서 §7-7).
    LLM 이 아니라 규칙이므로 confidence 를 낮게(0.3) 표시. Ollama 있으면 이건 안 탄다.
    """
    slots = dict(_SLOT_FALLBACK)
    if any(k in utterance for k in ("막", "차단", "block", "금지")):
        slots["intent"] = "block_media"
    if any(k in utterance for k in ("야간", "밤", "심야", "night")):
        slots["scope"] = "night"
    elif any(k in utterance for k in ("주말", "토요일", "일요일", "weekend")):
        slots["scope"] = "weekend"
    elif any(k in utterance for k in ("상시", "항상", "전면", "always")):
        slots["scope"] = "all"
    slots["target_agent_id"] = context.get("target_agent_id")
    slots["confidence"] = 0.3
    return slots


def extract_slots(utterance: str, context: dict) -> dict:
    """자연어 → 슬롯 JSON(dict). Ollama 우선, 실패/파싱오류 시 키워드 폴백.
    반환 예: {"intent":"block_media","target_agent_id":123,"scope":"night","confidence":0.9}
    """
    prompt = (
        f"{SLOT_SYSTEM}\n\n"
        f"발화: {utterance}\n"
        f"컨텍스트: {context}"
    )
    try:
        raw = _generate(prompt, json_mode=True)
        slots = json.loads(raw)
        if not isinstance(slots, dict):
            raise ValueError("응답이 JSON 객체가 아님")
        merged = {**_SLOT_FALLBACK, **slots}
        # 컨텍스트의 대상은 항상 신뢰(모델이 빠뜨려도 채움)
        if merged.get("target_agent_id") is None:
            merged["target_agent_id"] = context.get("target_agent_id")
        return merged
    except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning("extract_slots Ollama 미가용/파싱실패 → 키워드 폴백 (%s)", e)
        return _keyword_slots(utterance, context)
