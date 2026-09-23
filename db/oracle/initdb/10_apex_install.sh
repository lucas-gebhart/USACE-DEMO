#!/usr/bin/env bash
# Runs once, on first database creation (container-registry.oracle.com/database/free sources
# /opt/oracle/scripts/setup/*.sh). Installs Oracle APEX into FREEPDB1 and configures the REST database
# users so the legacy EMT APEX application can be served by the `ords` compose service.
# The APEX distribution is kept unzipped inside the oradata volume; the ords service mounts that
# subpath at /opt/oracle/apex (static /i/ files + version detection).
set -euo pipefail

APEX_VERSION="${APEX_VERSION:-24.2}"
APEX_ZIP_URL="${APEX_ZIP_URL:-https://download.oracle.com/otn_software/apex/apex_${APEX_VERSION}.zip}"
APEX_CACHE="${APEX_CACHE:-/opt/oracle/oradata/apex-cache}"
APEX_ADMIN_PASSWORD="${APEX_ADMIN_PASSWORD:-Apex_Passw0rd!1}"
APEX_REST_PASSWORD="${APEX_REST_PASSWORD:-Rest_Passw0rd!1}"
PDB="${PDB:-FREEPDB1}"

mkdir -p "$APEX_CACHE"
zip="$APEX_CACHE/apex_${APEX_VERSION}.zip"
if [ ! -s "$zip" ]; then
  echo "[apex] downloading APEX ${APEX_VERSION} (~300 MB, cached in ${APEX_CACHE})"
  curl -fsSL -o "$zip.part" "$APEX_ZIP_URL" && mv "$zip.part" "$zip"
fi
if [ ! -f "$APEX_CACHE/apex/apexins.sql" ]; then
  rm -rf "$APEX_CACHE/apex" && unzip -q "$zip" -d "$APEX_CACHE"
fi
cd "$APEX_CACHE/apex"

echo "[apex] installing APEX ${APEX_VERSION} into ${PDB} (about 5 minutes)"
sqlplus -s / as sysdba <<EOF
whenever sqlerror exit failure
alter session set container = ${PDB};
@apexins.sql SYSAUX SYSAUX TEMP /i/
EOF

echo "[apex] configuring REST users and the instance ADMIN account"
sqlplus -s / as sysdba <<EOF
whenever sqlerror exit failure
alter session set container = ${PDB};
@apex_rest_config_core.sql @ ${APEX_REST_PASSWORD} ${APEX_REST_PASSWORD}
alter user APEX_PUBLIC_USER identified by "${APEX_REST_PASSWORD}" account unlock;
alter user APEX_LISTENER identified by "${APEX_REST_PASSWORD}" account unlock;
alter user APEX_REST_PUBLIC_USER identified by "${APEX_REST_PASSWORD}" account unlock;
alter profile default limit password_life_time unlimited;
begin
  apex_util.set_security_group_id(10);
  apex_util.create_user(
    p_user_name                    => 'ADMIN',
    p_email_address                => 'admin@example.mil',
    p_web_password                 => '${APEX_ADMIN_PASSWORD}',
    p_developer_privs              => 'ADMIN:CREATE:DATA_LOADER:EDIT:HELP:MONITOR:SQL',
    p_change_password_on_first_use => 'N');
  commit;
end;
/
EOF

sqlplus -s / as sysdba <<EOF
set heading off feedback off
alter session set container = ${PDB};
select '[apex] registry: APEX '||version||' '||status from dba_registry where comp_id='APEX';
EOF
