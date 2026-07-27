#!/usr/bin/env bash
#
# Local development supervisor.
#
# Runs the controller against the Launchpad plugged into this machine and
# restarts it automatically every time a new commit lands, so each change can
# be tested on the hardware immediately. Logs stream to this terminal.
#
#   ./scripts/dev.sh              # run, restart on every commit
#   LOG_LEVEL=DEBUG ./scripts/dev.sh
#
# Ctrl-C stops the supervisor and the controller together.

set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON=".venv/bin/python"
POLL_SECONDS=1
RESTART_BACKOFF=2

C_START=$'\033[0;36m'
C_STOP=$'\033[0;33m'
C_COMMIT=$'\033[0;35m'
C_DIED=$'\033[0;31m'
C_BYE=$'\033[0;32m'
C_OFF=$'\033[0m'

if [ ! -x "$PYTHON" ]; then
	echo "error: $PYTHON not found." >&2
	echo "       create it with:  uv sync   (or: python3.11 -m venv .venv)" >&2
	exit 1
fi

child_pid=""

start_controller() {
	printf '\n%s▶ starting @ %s — %s%s\n' \
		"$C_START" "$(git rev-parse --short HEAD)" "$(git log -1 --format=%s)" "$C_OFF"

	# LOG_FILE="" forces logging_config to use the stderr handler instead of
	# writing to the file the daemon uses, so output lands in this terminal.
	LOG_FILE="" .venv/bin/ha-launchpad &
	child_pid=$!
}

stop_controller() {
	if [ -n "$child_pid" ] && kill -0 "$child_pid" 2>/dev/null; then
		printf '%s■ stopping (pid %s)%s\n' "$C_STOP" "$child_pid" "$C_OFF"
		kill -TERM "$child_pid" 2>/dev/null || true
		wait "$child_pid" 2>/dev/null || true
	fi
	child_pid=""
}

on_exit() {
	trap - INT TERM
	stop_controller
	printf '%s✓ dev supervisor stopped%s\n' "$C_BYE" "$C_OFF"
	exit 0
}
trap on_exit INT TERM

last_sha="$(git rev-parse HEAD)"
start_controller

while true; do
	sleep "$POLL_SECONDS"

	sha="$(git rev-parse HEAD)"
	if [ "$sha" != "$last_sha" ]; then
		printf '\n%s⟳ new commit — restarting%s\n' "$C_COMMIT" "$C_OFF"
		last_sha="$sha"
		stop_controller
		start_controller
		continue
	fi

	# Mirror launchd's KeepAlive: if the controller exits on its own (lost
	# Launchpad, restart chord, crash), bring it back up.
	if [ -n "$child_pid" ] && ! kill -0 "$child_pid" 2>/dev/null; then
		wait "$child_pid" 2>/dev/null || true
		printf '%s✗ controller exited — restarting in %ss%s\n' "$C_DIED" "$RESTART_BACKOFF" "$C_OFF"
		sleep "$RESTART_BACKOFF"
		start_controller
	fi
done
