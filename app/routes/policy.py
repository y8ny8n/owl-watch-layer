"""정책 승인 → 실제 반영 (설계문서 §5-4, §6).
[정책 세션 작업] 미리보기 승인 시 policy_t/policy_sub_t 반영.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from db import execute, fetch_one
from policy import apply_media_separate, build_policy_json

router = APIRouter(prefix="/api/policy", tags=["policy"])


class ApplyRequest(BaseModel):
    license_code: str
    agent_id: int
    slots: dict          # 미리보기에서 확정된 슬롯
    report_pno: int | None = None   # 어떤 리포트에서 나온 조치인지(status 갱신용)


def _find_target_name(license_code: str, agent_id: int) -> str | None:
    row = fetch_one(
        "SELECT user_info->>'user_name' AS user_name FROM agent_t "
        "WHERE license_code = %(lic)s AND agent_id = %(agent_id)s",
        {"lic": license_code, "agent_id": agent_id},
    )
    return row["user_name"] if row else None


@router.post("/apply")
def apply(req: ApplyRequest):
    """승인 → policy.apply_media_separate() 호출 + 리포트 status='actioned' 갱신.
    최종 정책 JSON 은 서버(build_policy_json)가 재조립한다 — 신뢰경계.
    """
    target_name = _find_target_name(req.license_code, req.agent_id) or req.slots.get("target_name")
    policy_json = build_policy_json(req.slots, target_name)

    result = apply_media_separate(req.license_code, req.agent_id, policy_json)

    if result["applied"] and req.report_pno is not None:
        execute(
            "UPDATE ai_analysis_result_t SET status = 'actioned' "
            "WHERE pno = %(pno)s AND license_code = %(lic)s",
            {"pno": req.report_pno, "lic": req.license_code},
        )

    return {"applied": result["applied"], "pvn": result["pvn"]}
