"""설치 마법사 상태 저장 — 첫 실행 온보딩(설계문서 §설치).

config 마커 파일 하나(data/owl_setup.json)에 마법사에서 고른 값을 누적 저장한다.
`complete: true` 가 찍히면 온보딩이 끝난 것으로 보고, main.py 미들웨어가 /setup 강제
리다이렉트를 해제한다. 파일이 없거나 complete=false 면 아직 미설치 상태.
"""
import json
import os
import threading

_DIR = os.path.join(os.path.dirname(__file__), "data")
_FILE = os.path.join(_DIR, "owl_setup.json")
_lock = threading.Lock()

# 마법사가 채우는 기본 골격
_DEFAULT = {
    "complete": False,
    "ai_engine": None,     # {"engine": "local|internal|cloud", "model": "...", ...}
    "datasource": None,    # {"sources": ["file_transfer", ...]}
    "analysis": None,      # {"sensitivity": "balanced", "workhour_start": 9, ...}
}


def load() -> dict:
    """저장된 설치 상태를 읽어온다. 없으면 기본 골격."""
    if not os.path.exists(_FILE):
        return dict(_DEFAULT)
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(_DEFAULT)
        merged.update(data or {})
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT)


def _save(data: dict) -> None:
    os.makedirs(_DIR, exist_ok=True)
    tmp = _FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _FILE)  # 원자적 교체


def is_complete() -> bool:
    return bool(load().get("complete"))


def save_step(key: str, value: dict) -> dict:
    """마법사 한 단계 값을 저장(ai_engine/datasource/analysis)."""
    with _lock:
        data = load()
        data[key] = value
        _save(data)
        return data


def mark_complete() -> dict:
    """마법사 완료 — complete 플래그를 올린다."""
    with _lock:
        data = load()
        data["complete"] = True
        _save(data)
        return data


def reset() -> None:
    """(개발용) 설치 상태 초기화 — 마커 파일 삭제."""
    with _lock:
        if os.path.exists(_FILE):
            os.remove(_FILE)
