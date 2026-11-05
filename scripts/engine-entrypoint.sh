#!/usr/bin/env bash
# The engine image's command: starts unoserver on localhost and the engine API, and stops both when either stops.
# The supervised unoserver pool (ADR 004) replaces this later.
set -u

# unoserver and LibreOffice listen on the container's localhost only; the engine reaches them there.
# setsid gives unoserver its own process group, which LibreOffice's processes join.
setsid unoserver --interface 127.0.0.1 --uno-interface 127.0.0.1 &
unoserver_pid=$!

# The API listens on every interface inside the container; publish it only where the consumer's app can reach it.
uvicorn diplex.api:app --host 0.0.0.0 --port 8000 &
engine_pid=$!

stop_both() {
  # The whole unoserver group: signalling unoserver alone leaves LibreOffice's oosplash running, so stopping hangs.
  kill -TERM -- "-$unoserver_pid" "$engine_pid" 2>/dev/null || true
}
# docker stop sends SIGTERM to this script only; pass it on, so both shut down cleanly.
trap stop_both TERM INT

# Wait for either to exit (or a signal), then stop the other, so Docker sees the container stop.
wait -n "$unoserver_pid" "$engine_pid"
exit_status=$?
stop_both
wait
exit "$exit_status"
