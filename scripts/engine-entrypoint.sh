#!/usr/bin/env bash
# The engine image's command: runs the engine API, which starts and stops its own unoserver pool (ADR 011).
# This script stays as PID 1 rather than exec'ing uvicorn: when the engine kills an instance's process group, the
# orphaned LibreOffice processes are adopted by PID 1, and bash reaps them, where Python would leave them as zombies.
set -u

# The API listens on every interface inside the container; publish it only where the consumer's app can reach it.
# unoserver and LibreOffice listen on the container's localhost only; the engine starts them there.
uvicorn diplex.api:app --host 0.0.0.0 --port 8000 &
engine_pid=$!

stop_engine() {
  # uvicorn shuts down on SIGTERM, and its shutdown kills the unoserver pool.
  kill -TERM "$engine_pid" 2>/dev/null || true
}
# docker stop sends SIGTERM to this script only; pass it on, so the engine and its pool shut down cleanly.
trap stop_engine TERM INT

# A signal interrupts wait; keep waiting until the engine has exited, then exit with its status.
wait "$engine_pid"
exit_status=$?
while kill -0 "$engine_pid" 2>/dev/null; do
  wait "$engine_pid"
  exit_status=$?
done
exit "$exit_status"
