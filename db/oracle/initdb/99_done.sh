#!/usr/bin/env bash
# Marker checked by the compose healthcheck: only written when every setup script above succeeded,
# so the api and ords services start against a fully initialised database (schema + APEX + legacy app).
touch /opt/oracle/oradata/.emt-initdb-done
echo "[initdb] complete"
