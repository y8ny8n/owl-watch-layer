"""환경설정 로딩 — .env 값을 한 곳에서 읽어 앱 전체가 공유한다."""
import os
from dotenv import load_dotenv

load_dotenv()


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
    RISK_THRESHOLD = int(os.getenv("RISK_THRESHOLD", "35"))   # 이 이상 = 고위험/주의 후보
    WATCH_THRESHOLD = int(os.getenv("WATCH_THRESHOLD", "20"))  # 이 이상~RISK 미만 = 관심(watch)
    WORKHOUR_START = int(os.getenv("WORKHOUR_START", "8"))
    WORKHOUR_END = int(os.getenv("WORKHOUR_END", "19"))
    ANALYSIS_WINDOW_HOURS = int(os.getenv("ANALYSIS_WINDOW_HOURS", "168"))

    DEMO_LICENSE_CODE = os.getenv("DEMO_LICENSE_CODE", "")
    # 정책 반영 대상 media_separate pid (실 라이선스 기존 정책과 충돌 방지)
    POLICY_SEPARATE_PID = int(os.getenv("POLICY_SEPARATE_PID", "1"))

    @property
    def dsn(self) -> str:
        return (
            f"host={self.PFDB_HOST} port={self.PFDB_PORT} dbname={self.PFDB_NAME} "
            f"user={self.PFDB_USER} password={self.PFDB_PASSWORD}"
        )


config = Config()
