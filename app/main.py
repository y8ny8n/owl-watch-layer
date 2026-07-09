"""온파일럿 FastAPI 진입점 — 라우터를 엮고 헬스체크를 노출한다.

부팅 확인:  docker compose up  →  http://localhost:8080/health  →  {"status":"ok"}
각 라우터(reports/chat/policy)는 세션별로 채워나가는 stub 이다.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routes import reports, chat, policy

app = FastAPI(title="OnPilot", version="0.1.0")

# 정적 파일 / 템플릿(UI 세션에서 채움)
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# 기능 라우터
app.include_router(reports.router)
app.include_router(chat.router)
app.include_router(policy.router)


@app.get("/health")
def health():
    return {"status": "ok"}
