"""감시목록 '지속 관찰' 핀 저장 — 로컬 JSON(실 pfdb 스키마 안 건드림).

관리자가 리포트를 "지속 관찰"로 고정하면 pno 를 여기 저장한다. 감시목록 뷰는 핀된 항목을
recurrence 와 무관하게 '지속 관찰' 그룹에 고정한다(무기한 감시 개념, 방법 A). ai_analysis_result_t
에 컬럼을 추가하면 재분석 시 pno 가 바뀌므로, 데모에선 로컬 마커로 분리 저장한다.
"""
import json
import os
import threading

_DIR = os.path.join(os.path.dirname(__file__), "data")
_FILE = os.path.join(_DIR, "owl_watchlist.json")
_lock = threading.Lock()


def _load_raw() -> dict:
    if not os.path.exists(_FILE):
        return {"pinned": []}
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data.get("pinned"), list):
            data["pinned"] = []
        return data
    except (json.JSONDecodeError, OSError):
        return {"pinned": []}


def _save_raw(data: dict) -> None:
    os.makedirs(_DIR, exist_ok=True)
    tmp = _FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _FILE)


def list_pins() -> list[int]:
    return [int(p) for p in _load_raw().get("pinned", [])]


def is_pinned(pno: int) -> bool:
    return int(pno) in set(list_pins())


def set_pin(pno: int, pinned: bool) -> list[int]:
    """핀 on/off. 갱신된 핀 목록 반환."""
    with _lock:
        data = _load_raw()
        pins = {int(p) for p in data.get("pinned", [])}
        if pinned:
            pins.add(int(pno))
        else:
            pins.discard(int(pno))
        data["pinned"] = sorted(pins)
        _save_raw(data)
        return data["pinned"]
