#!/usr/bin/env bash
# Applies db/migrations/V*.sql as the application user before the APEX application is imported, so the
# legacy app's regions (v_emt_* views, emt_legacy package) resolve the moment ORDS comes up. Versions are
# recorded in schema_migrations exactly as api/app/migrate.py does, so the API start-up migration is a no-op.
set -euo pipefail
APP_USER="${APP_USER:-emt}"
APP_USER_PASSWORD="${APP_USER_PASSWORD:-emt_Passw0rd}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-/migrations}"
PDB="${PDB:-FREEPDB1}"

shopt -s nullglob
files=("$MIGRATIONS_DIR"/V*.sql)
if [ ${#files[@]} -eq 0 ]; then
  echo "[schema] no migrations mounted at ${MIGRATIONS_DIR}; the API will apply them on start"
  exit 0
fi

sqlplus -s -L "${APP_USER}/${APP_USER_PASSWORD}@//localhost:1521/${PDB}" <<SQL
whenever sqlerror exit failure
set define off
declare
  n number;
begin
  select count(*) into n from user_tables where table_name = 'SCHEMA_MIGRATIONS';
  if n = 0 then
    execute immediate 'CREATE TABLE schema_migrations (
       version    VARCHAR2(20) PRIMARY KEY,
       filename   VARCHAR2(200) NOT NULL,
       applied_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL)';
  end if;
end;
/
SQL

for f in "${files[@]}"; do
  name="$(basename "$f")"
  version="${name%%__*}"
  echo "[schema] applying ${name}"
  sqlplus -s -L "${APP_USER}/${APP_USER_PASSWORD}@//localhost:1521/${PDB}" <<SQL
whenever sqlerror exit failure
set define off
@${f}
insert into schema_migrations (version, filename) values ('${version}', '${name}');
commit;
SQL
done
echo "[schema] ${#files[@]} migrations applied"
