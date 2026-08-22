"""설치 마법사 라우트 — 첫 실행 온보딩(준비체크→AI엔진→데이터소스→분석설정→완료).

탐지는 실제 환경을 가볍게 확인한다:
- pfdb 연결: 짧은 타임아웃으로 실제 접속 시도
- AI 엔진: 로컬 Ollama /api/tags 로 모델 감지
접속이 안 되면 실패 상태로 정직하게 반환(막지 않고 안내). 저장은 setup_state 로.
"""
import json
import platform
import urllib.request
from urllib.error import URLError

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from config import config
import setup_state

router = APIRouter(tags=["setup"])
templates = Jinja2Templates(directory="web/templates")


@router.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request):
    """설치 마법사 UI (5단계 클라이언트 스테퍼)."""
    return templates.TemplateResponse("setup.html", {"request": request})


@router.get("/api/setup/status")
def setup_status():
    """현재 설치 상태 + 누적 설정."""
    data = setup_state.load()
    return {"complete": bool(data.get("complete")), "config": data}


def _check_pfdb() -> dict:
    """pfdb 실제 접속 시도(짧은 타임아웃). 성공 시 로그 테이블 수도 세어본다."""
    try:
        import psycopg

        with psycopg.connect(config.dsn, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name LIKE 'log_%'"
                )
                n = cur.fetchone()[0]
        return {"ok": True, "detail": f"{config.PFDB_HOST}:{config.PFDB_PORT} · 로그 테이블 {n}개"}
    except Exception as e:  # 접속 불가/드라이버 없음 등 — 정직하게 실패
        return {"ok": False, "detail": f"연결 안 됨 ({type(e).__name__})"}


def _check_ollama() -> dict:
    """로컬 Ollama /api/tags 로 실행·모델 감지."""
    url = config.OLLAMA_URL.rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        models = [m.get("name", "") for m in body.get("models", [])]
        if models:
            return {"ok": True, "detail": "실행 중 · " + ", ".join(models[:3]), "models": models}
        return {"ok": True, "detail": "실행 중 · 설치된 모델 없음", "models": []}
    except (URLError, OSError, ValueError) as e:
        return {"ok": False, "detail": f"대기 중 ({type(e).__name__})", "models": []}


@router.get("/api/setup/checks")
def setup_checks():
    """준비 체크(시작 화면) — 서버환경/pfdb/localhost/AI엔진 4항목."""
    pfdb = _check_pfdb()
    ollama = _check_ollama()
    return {
        "server": {"ok": True, "detail": f"{platform.system()} {platform.machine()} · Python {platform.python_version()}"},
        "pfdb": pfdb,
        "localhost": {"ok": True, "detail": "localhost 전용 바인딩 · 외부 포트 없음"},
        "ai_engine": ollama,
    }


@router.get("/api/setup/models")
def setup_models():
    """AI 엔진 단계 — 로컬 Ollama 모델 목록·GPU 감지."""
    ollama = _check_ollama()
    return {"ok": ollama["ok"], "models": ollama.get("models", []), "detail": ollama["detail"]}


@router.post("/api/setup/ai-engine")
async def save_ai_engine(request: Request):
    payload = await request.json()
    data = setup_state.save_step("ai_engine", payload)
    return {"ok": True, "config": data.get("ai_engine")}


@router.post("/api/setup/datasource")
async def save_datasource(request: Request):
    payload = await request.json()
    data = setup_state.save_step("datasource", payload)
    return {"ok": True, "config": data.get("datasource")}


@router.post("/api/setup/analysis")
async def save_analysis(request: Request):
    payload = await request.json()
    data = setup_state.save_step("analysis", payload)
    return {"ok": True, "config": data.get("analysis")}


@router.post("/api/setup/complete")
def complete_setup():
    """마법사 완료 — /setup 강제 리다이렉트 해제 + 고른 값을 즉시 config 에 반영."""
    data = setup_state.mark_complete()
    config.apply_setup()  # 재시작 없이 민감도·근무시간·모델 반영
    return JSONResponse({"ok": True, "config": data, "effective": config.effective()})
