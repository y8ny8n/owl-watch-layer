"""챗 패널 — 자연어 → 슬롯추출 → 정책 미리보기 (설계문서 §5-3, §4.2, §6).
[챗/슬롯 세션 작업]
"""
from fastapi import APIRouter
from pydantic import BaseModel

from config import config
from db import fetch_one
from ollama_client import extract_slots
from policy import build_policy_json

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    utterance: str = ""
    target_agent_id: int | None = None
    scope: str | None = None   # 추천 칩 경로: 'night'|'weekend'|'all' 직접 지정(결정적, ollama 우회)


_SCOPE_LABEL = {"night": "야간(오늘 22:00~내일 06:00)", "weekend": "이번 주말", "all": "상시"}

# 아직 지원 안 하는(=USB 외) 채널 키워드 — 우아한 거절용
_UNSUPPORTED_HINT = ("생성형", "chatgpt", "gpt", "파일첨부", "첨부", "출력", "프린트", "캡처", "웹사이트", "메일", "클라우드", "공유폴더")
_USB_HINT = ("usb", "매체", "이동식", "저장장치")


def _find_target_name(agent_id: int | None) -> str | None:
    if agent_id is None:
        return None
    row = fetch_one(
        "SELECT user_info->>'user_name' AS user_name FROM agent_t "
        "WHERE license_code = %(lic)s AND agent_id = %(agent_id)s",
        {"lic": config.DEMO_LICENSE_CODE, "agent_id": agent_id},
    )
    return row["user_name"] if row else None


def _scope_line(policy_json: dict, scope: str | None) -> str:
    if scope == "night" and policy_json.get("s_time"):
        return f"적용: 오늘 {policy_json['s_time'][-5:]}~내일 {policy_json['e_time'][-5:]}"
    if scope == "weekend" and policy_json.get("s_time"):
        return f"적용: 이번 주말 ({policy_json['s_time'][5:10]}~{policy_json['e_time'][5:10]})"
    return "적용: 상시"


def _diff_lines(target_name: str | None, policy_json: dict, scope: str | None) -> list[str]:
    return [
        f"대상: {target_name or '미지정'}",
        "차단: USB 매체",
        _scope_line(policy_json, scope),
    ]


@router.post("/preview")
def preview(req: ChatRequest):
    """자연어/추천칩 → 슬롯 → build_policy_json() → diff 미리보기(적용 X).

    - 칩(scope 직접): ollama 우회, 결정적. 무대 리스크 0.
    - 자유입력: USB 외 채널만 언급하면 우아하게 거절(현재 지원=USB 차단).
    """
    if req.scope in ("night", "weekend", "all"):
        slots = {"intent": "block_media", "target_agent_id": req.target_agent_id,
                 "scope": req.scope, "confidence": 1.0}
    else:
        u = (req.utterance or "").lower()
        if any(h in u for h in _UNSUPPORTED_HINT) and not any(h in u for h in _USB_HINT):
            return {
                "understood": False,
                "message": "지금은 매체(USB) 차단 정책만 지원해요. 아래 추천에서 고르거나 'USB 차단'으로 말씀해주세요.",
            }
        context = {"target_agent_id": req.target_agent_id}
        slots = extract_slots(req.utterance, context)

    agent_id = req.target_agent_id if req.target_agent_id is not None else slots.get("target_agent_id")
    target_name = _find_target_name(agent_id) or slots.get("target_name")
    policy_json = build_policy_json(slots, target_name)
    scope = slots.get("scope") or "all"

    return {
        "understood": True,
        "message": f"이해했어요 — {target_name or '대상'}에게 매체(USB)를 {_SCOPE_LABEL.get(scope, '상시')} 차단할게요. 미리보기를 확인해주세요.",
        "slots": slots,
        "target_name": target_name,
        "policy_json": policy_json,
        "diff_lines": _diff_lines(target_name, policy_json, scope),
    }
