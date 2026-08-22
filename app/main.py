"""온파일럿 FastAPI 진입점 — 라우터를 엮고 헬스체크를 노출한다.

부팅 확인:  uvicorn main:app  →  http://localhost:8080/health  →  {"status":"ok"}
첫 실행(미설치) 시 모든 페이지 요청은 /setup 마법사로 리다이렉트된다(setup_state).
각 라우터(reports/chat/policy/setup)는 세션별로 채워나가는 stub 이다.
"""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from routes import reports, chat, policy, setup
import setup_state

app = FastAPI(title="OnPilot", version="0.1.0")

# 정적 파일 / 템플릿(UI 세션에서 채움)
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# 기능 라우터
app.include_router(reports.router)
app.include_router(chat.router)
app.include_router(policy.router)
app.include_router(setup.router)

# 리다이렉트 예외 경로 — 이 접두사는 미설치 상태에서도 통과시킨다.
_SETUP_ALLOW = ("/setup", "/static", "/api/setup", "/health", "/docs", "/openapi.json", "/redoc")


@app.middleware("http")
async def gate_setup(request: Request, call_next):
    """미설치 상태면 페이지 요청을 /setup 마법사로 보낸다(온보딩 게이트)."""
    path = request.url.path
    if not setup_state.is_complete() and not path.startswith(_SETUP_ALLOW):
        return RedirectResponse(url="/setup", status_code=307)
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}
