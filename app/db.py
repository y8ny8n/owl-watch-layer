"""pfdb 연결 헬퍼 — psycopg3 커넥션 풀.

사용 예:
    from db import fetch_all, fetch_one, execute
    rows = fetch_all("SELECT * FROM ai_analysis_result_t WHERE license_code=%(lic)s", {"lic": lic})
"""
from contextlib import contextmanager
from psycopg_pool import ConnectionPool  # psycopg[binary] 에 포함
from psycopg.rows import dict_row

from config import config

# 앱 수명 동안 재사용하는 전역 풀
# 야간·주말 판정의 KST 고정은 SQL에서 log_time AT TIME ZONE 'Asia/Seoul'로 처리(recipes/exfil.py).
pool = ConnectionPool(conninfo=config.dsn, min_size=1, max_size=5, open=True)


@contextmanager
def cursor():
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            yield cur


def fetch_all(sql: str, params: dict | None = None) -> list[dict]:
    with cursor() as cur:
        cur.execute(sql, params or {})
        return cur.fetchall()


def fetch_one(sql: str, params: dict | None = None) -> dict | None:
    with cursor() as cur:
        cur.execute(sql, params or {})
        return cur.fetchone()


def execute(sql: str, params: dict | None = None) -> int:
    """INSERT/UPDATE 실행, 영향 행 수 반환. 트랜잭션은 connection 컨텍스트가 커밋."""
    with cursor() as cur:
        cur.execute(sql, params or {})
        return cur.rowcount
