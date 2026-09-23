#!/usr/bin/env bash
# Runs once, on first database creation (container-registry.oracle.com/database/free sources
# /opt/oracle/scripts/setup/*.sh as the oracle user). Creates the application schema that both the
# legacy APEX app and the FastAPI service read from. Passwords are dev-only defaults; set them in compose.
set -euo pipefail
APP_USER="${APP_USER:-emt}"
APP_USER_PASSWORD="${APP_USER_PASSWORD:-emt_Passw0rd}"
PDB="${PDB:-FREEPDB1}"

echo "[initdb] creating application user ${APP_USER} in ${PDB}"
sqlplus -s / as sysdba <<SQL
whenever sqlerror exit failure
alter session set container = ${PDB};
create user ${APP_USER} identified by "${APP_USER_PASSWORD}" default tablespace users quota unlimited on users;
grant create session, create table, create view, create sequence, create procedure, create trigger,
      create type, create synonym to ${APP_USER};
SQL
