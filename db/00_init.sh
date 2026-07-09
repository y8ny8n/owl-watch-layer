#!/bin/bash
# pfdb 최초 기동 시 실행 — schema/*.sql 먼저, seed/*.sql 나중 (파일명 정렬 순).
# postgres 엔트리포인트가 /docker-entrypoint-initdb.d 의 .sh 는 실행하지만
# 하위 디렉터리(schema/, seed/)는 재귀하지 않으므로 이 스크립트가 대신 순회한다.
set -e

apply_dir() {
  local dir="$1" label="$2"
  for f in "$dir"/*.sql; do
    [ -e "$f" ] || continue   # 파일 없으면(빈 디렉터리) 건너뜀
    echo "[onpilot init] applying ${label}: $(basename "$f")"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$f"
  done
}

apply_dir /onpilot-db/schema schema
apply_dir /onpilot-db/seed   seed
echo "[onpilot init] done."
