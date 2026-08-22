"""환경설정 로딩 — .env 값을 한 곳에서 읽어 앱 전체가 공유한다.

설치 마법사(setup_state)에서 고른 값은 apply_setup() 이 .env 기본값 위에 덮어쓴다:
  민감도 → WATCH_THRESHOLD (적재 임계), 근무시간 → WORKHOUR_START/END(야간 판정),
  AI 엔진 모델 → OLLAMA_MODEL. 마법사 미완료 시엔 .env 기본값 그대로.
"""
import os
from dotenv import load_dotenv

import setup_state

load_dotenv()

# 민감도 프리셋 → 적재 임계(WATCH_THRESHOLD). 낮을수록 더 많이 잡음(엄격).
_SENSITIVITY_THRESHOLD = {"strict": 15, "balanced": 20, "lenient": 28}

# 채널교차 분석이 스캔하는 실제 DLP 채널(exfil.py UNION 대상). 설치 마법사 데이터소스 토글과 1:1.
ALL_CHANNELS = ["media", "fileattach", "website", "sharedfolder", "chatgpt"]


def _parse_hour(value, default=None):
    """'09:00' / '9' / 9 → 정수 시(hour). 파싱 실패 시 default."""
    if value is None:
        return default
    try:
        s = str(value).strip()
        return int(s.split(":")[0])
    except (ValueError, IndexError):
        return default


class Config:
    # DB
    PFDB_HOST = os.getenv("PFDB_HOST", "pfdb")
    PFDB_PORT = int(os.getenv("PFDB_PORT", "5432"))
    PFDB_NAME = os.getenv("PFDB_NAME", "pfdb")
    PFDB_USER = os.getenv("PFDB_USER", "postgres")
    PFDB_PASSWORD = os.getenv("PFDB_PASSWORD", "postgres")

    # Ollama
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma:2b")

    # 분석 파라미터 (설계문서 §3.2)
    # 적재 임계: 이 점수 이상이면 리포트로 올린다(관심 이상). mid(35)/high(60) 경계는 scoring.severity() 참조.
    WATCH_THRESHOLD = int(os.getenv("WATCH_THRESHOLD", "20"))
    WORKHOUR_START = int(os.getenv("WORKHOUR_START", "8"))
    WORKHOUR_END = int(os.getenv("WORKHOUR_END", "19"))
    ANALYSIS_WINDOW_HOURS = int(os.getenv("ANALYSIS_WINDOW_HOURS", "168"))

    DEMO_LICENSE_CODE = os.getenv("DEMO_LICENSE_CODE", "")
    # 정책 반영 대상 media_separate pid (실 라이선스 기존 정책과 충돌 방지)
    POLICY_SEPARATE_PID = int(os.getenv("POLICY_SEPARATE_PID", "1"))

    # 분석에 사용할 채널(설치 마법사 데이터소스). 기본 전체. exfil.py 가 이 목록만 UNION.
    ENABLED_CHANNELS = list(ALL_CHANNELS)

    @property
    def dsn(self) -> str:
        return (
            f"host={self.PFDB_HOST} port={self.PFDB_PORT} dbname={self.PFDB_NAME} "
            f"user={self.PFDB_USER} password={self.PFDB_PASSWORD}"
        )

    def apply_setup(self) -> "Config":
        """설치 마법사에서 고른 값을 config 위에 덮어쓴다(런타임 반영).
        마법사 미완료거나 값이 없으면 해당 항목은 .env 기본값 유지.
        """
        data = setup_state.load()
        ana = data.get("analysis") or {}
        eng = data.get("ai_engine") or {}

        sens = ana.get("sensitivity")
        if sens in _SENSITIVITY_THRESHOLD:
            self.WATCH_THRESHOLD = _SENSITIVITY_THRESHOLD[sens]

        ws = _parse_hour(ana.get("workhour_start"))
        we = _parse_hour(ana.get("workhour_end"))
        if ws is not None:
            self.WORKHOUR_START = ws
        if we is not None:
            self.WORKHOUR_END = we

        model = eng.get("model")
        if model:
            self.OLLAMA_MODEL = model

        ds = data.get("datasource") or {}
        srcs = ds.get("sources")
        if isinstance(srcs, list):
            enabled = [c for c in ALL_CHANNELS if c in srcs]
            if enabled:  # 최소 1개는 있어야 분석 의미가 있음
                self.ENABLED_CHANNELS = enabled

        return self

    def effective(self) -> dict:
        """현재 유효 설정 요약 — 디버그·상태 확인용."""
        return {
            "watch_threshold": self.WATCH_THRESHOLD,
            "workhour_start": self.WORKHOUR_START,
            "workhour_end": self.WORKHOUR_END,
            "ollama_model": self.OLLAMA_MODEL,
            "enabled_channels": self.ENABLED_CHANNELS,
        }


config = Config()
# 부팅 시 설치 마법사 값 반영(있으면). 미설치면 .env 기본값 그대로.
config.apply_setup()
