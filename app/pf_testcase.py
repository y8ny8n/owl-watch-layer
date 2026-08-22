"""pf_testcase — 데모 로그를 '지금' 기준으로 되살려 지금분석이 항상 리포트를 만들게 한다.

배경: '지금 분석'(run_analysis)은 리포트(ai_analysis_result_t)만 지우고 **원본 로그는 안 지운다.**
그런데 데모 로그가 며칠 전 날짜라 최근 분석창(7일)을 벗어나면 후보가 0이 되어 리포트가 빈다.
이 스크립트는 owl-demo 태그가 붙은 로그의 log_time 만 최근으로 당긴 뒤 분석을 다시 돌린다.

안전: 실데이터는 절대 안 건드린다. `log_json->>'_td' = 'owl-demo'` 인 로그만 UPDATE 한다
(cleanup_owldemo.sql 과 같은 대상 집합). 에이전트·정책·실로그는 그대로.

야간/주말 판정 보존: 이동량을 **7일의 배수**로 잡아 요일·시각을 그대로 유지한다
(exfil.py 의 S6 야간/주말 신호가 흔들리지 않게).

사용:
    cd onpilot/app
    ../.venv/bin/python pf_testcase.py          # 당기고 + 지금분석
    ../.venv/bin/python pf_testcase.py --shift-only   # 당기기만(분석 스킵)
"""
import math
import sys
from datetime import datetime, timedelta, timezone

from config import config
from db import fetch_one, execute

LIC = config.DEMO_LICENSE_CODE
TAG = "owl-demo"
TABLES = [
    "log_dlp_media_t",
    "log_dlp_fileattach_t",
    "log_dlp_website_t",
    "log_dlp_sharedfolder_t",
    "log_dlp_chatgpt_t",
]
# 최신 로그를 '며칠 전 이내'로 당긴다(0이면 어제/오늘까지 당김). 3이면 최근 3일 안에 최신이 들어옴.
TARGET_RECENT_DAYS = 2


def _latest_owldemo_time():
    parts = " UNION ALL ".join(
        f"SELECT max(log_time) AS m FROM {t} "
        f"WHERE license_code = %(lic)s AND log_json->>'_td' = %(tag)s"
        for t in TABLES
    )
    row = fetch_one(f"SELECT max(m) AS m FROM ({parts}) x", {"lic": LIC, "tag": TAG})
    return row["m"] if row else None


def _count_owldemo():
    parts = " UNION ALL ".join(
        f"SELECT count(*) AS c FROM {t} "
        f"WHERE license_code = %(lic)s AND log_json->>'_td' = %(tag)s"
        for t in TABLES
    )
    row = fetch_one(f"SELECT sum(c) AS c FROM ({parts}) x", {"lic": LIC, "tag": TAG})
    return int(row["c"]) if row and row["c"] is not None else 0


def refresh(shift_only: bool = False) -> None:
    total = _count_owldemo()
    if total == 0:
        print(f"[pf_testcase] owl-demo 로그가 없습니다 (license={LIC}).")
        print("  → 원본 데모 생성 스크립트로 먼저 데이터를 심어야 합니다. (당길 로그가 없음)")
        return

    latest = _latest_owldemo_time()
    now = datetime.now(latest.tzinfo or timezone.utc)
    gap = now - latest

    # 최신 로그가 이미 최근이면 이동 불필요
    if gap <= timedelta(days=TARGET_RECENT_DAYS):
        print(f"[pf_testcase] 이미 최신입니다 (최신 로그 {latest}). 이동 불필요.")
    else:
        # 요일·시각 보존을 위해 7일 배수로 이동. 최신이 최근 TARGET_RECENT_DAYS 안에 들어오게.
        weeks = math.ceil((gap - timedelta(days=TARGET_RECENT_DAYS)).total_seconds() / (7 * 86400))
        shift_days = weeks * 7
        moved = 0
        for t in TABLES:
            n = execute(
                f"UPDATE {t} SET log_time = log_time + make_interval(days => %(d)s) "
                f"WHERE license_code = %(lic)s AND log_json->>'_td' = %(tag)s",
                {"d": shift_days, "lic": LIC, "tag": TAG},
            )
            moved += n
            print(f"  {t}: {n}건 +{shift_days}일")
        print(f"[pf_testcase] owl-demo 로그 {moved}건을 {shift_days}일 앞당김 (요일·시각 보존).")

    if shift_only:
        print("[pf_testcase] --shift-only: 분석은 스킵. 앱에서 '지금 분석'을 눌러 리포트를 채우세요.")
        return

    # 분석 재실행(1d/7d/30d 프리베이크). Ollama 요약 때문에 후보 수만큼 시간이 걸릴 수 있음.
    print("[pf_testcase] 지금 분석 재실행 중… (Ollama 요약 때문에 수십 초~몇 분 걸릴 수 있어요)")
    from analyzer import run_analysis  # db 연결 후 import (import 시 pool 오픈)
    loaded = run_analysis(LIC)
    print(f"[pf_testcase] 완료 — 리포트 {loaded}건 적재. 브라우저 새로고침하면 보입니다.")


if __name__ == "__main__":
    refresh(shift_only=("--shift-only" in sys.argv))
