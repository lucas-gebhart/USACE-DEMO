#!/usr/bin/env bash
# Mounted at /opt/oracle/scripts/startup. container-registry.oracle.com/database/free ships a prebuilt
# database, so its scripts/setup hook never fires; scripts/startup is sourced by runOracle.sh after
# "DATABASE IS READY TO USE!" on every start. This wrapper makes that a one-time initialisation:
# steps/*.sh run in order in their own bash process, and the marker the compose healthcheck waits for
# is written only when all of them succeed. Later starts see the marker and skip.
emt_init() {
  local marker="/opt/oracle/oradata/.emt-initdb-done"
  local steps_dir; steps_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/steps"
  if [ -f "$marker" ]; then
    echo "[initdb] already initialised ($(cat "$marker")); skipping"
    return 0
  fi
  local step
  for step in "$steps_dir"/*.sh; do
    echo "[initdb] running $(basename "$step")"
    if ! bash "$step"; then
      echo "[initdb] FAILED in $(basename "$step"); marker not written, healthcheck will not pass" >&2
      return 0
    fi
  done
  date -Iseconds > "$marker"
  echo "[initdb] complete"
}
emt_init
