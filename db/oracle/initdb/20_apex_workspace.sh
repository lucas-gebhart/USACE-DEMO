#!/usr/bin/env bash
# Runs once after 10_apex_install.sh. Creates the EMT workspace on the application schema, a
# developer login for the APEX Builder, and imports the legacy EMT application (db/apex/f100.sql).
set -euo pipefail
APP_USER="${APP_USER:-emt}"
APEX_ADMIN_PASSWORD="${APEX_ADMIN_PASSWORD:-Apex_Passw0rd!1}"
APEX_APP_DIR="${APEX_APP_DIR:-/apex-app}"
PDB="${PDB:-FREEPDB1}"

echo "[apex] creating workspace EMT on schema ${APP_USER}"
sqlplus -s / as sysdba <<SQL
whenever sqlerror exit failure
alter session set container = ${PDB};
begin
  apex_instance_admin.add_workspace(
    p_workspace      => 'EMT',
    p_primary_schema => upper('${APP_USER}'));
  apex_util.set_security_group_id(apex_util.find_security_group_id('EMT'));
  apex_util.create_user(
    p_user_name                    => 'EMT_DEV',
    p_email_address                => 'emt.dev@example.mil',
    p_web_password                 => '${APEX_ADMIN_PASSWORD}',
    p_developer_privs              => 'ADMIN:CREATE:DATA_LOADER:EDIT:HELP:MONITOR:SQL',
    p_change_password_on_first_use => 'N');
  commit;
end;
/
SQL

shopt -s nullglob
for f in "$APEX_APP_DIR"/f*.sql; do
  echo "[apex] importing $(basename "$f") into workspace EMT"
  app_id="$(basename "$f" .sql)"; app_id="${app_id#f}"   # f100.sql -> 100, matches migration_routes / APEX_APP_ID
  sqlplus -s / as sysdba <<SQL
whenever sqlerror exit failure
set define off
alter session set container = ${PDB};
begin
  apex_application_install.set_workspace('EMT');
  apex_application_install.set_schema(upper('${APP_USER}'));
  apex_application_install.set_application_id(${app_id});
  apex_application_install.set_application_alias('EMT');
  apex_application_install.generate_offset;
  apex_application_install.set_keep_sessions(false);
end;
/
@${f}
SQL
done
echo "[apex] workspace EMT ready"
