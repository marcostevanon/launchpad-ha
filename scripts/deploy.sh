#!/usr/bin/env bash
#
# Deploy to the always-on Mac as an atomic, versioned release.
#
#   ./scripts/deploy.sh [ssh-host]      # default: macmini
#
# The new release is unpacked, built and self-tested while the running one is
# still serving. Only then is the `current` symlink swapped, in a single
# rename(2). If the new release does not report a healthy heartbeat, the
# symlink is flipped back and the previous release restarted.
#
# Secrets are never shipped: HA_URL and HA_TOKEN live in shared/env on the
# target, outside the release directories, created once by hand.

set -euo pipefail

REMOTE="${1:-macmini}"
LABEL="com.launchpad.ha"
KEEP_RELEASES=5
HEALTH_TIMEOUT=40

cd "$(dirname "$0")/.."

if [ -n "$(git status --porcelain)" ]; then
	echo "error: working tree is dirty. Commit or stash before deploying." >&2
	exit 1
fi

SHA="$(git rev-parse --short HEAD)"
REL_ID="$(date -u +%Y%m%dT%H%M%S)-$SHA"

echo "==> packaging $REL_ID"
TARBALL="$(mktemp -t ha-launchpad-deploy)"
# Tracked files only: no .git, no .venv, no .env, no .DS_Store.
git archive --format=tar HEAD | gzip >"$TARBALL"
scp -q "$TARBALL" "$REMOTE:/tmp/$REL_ID.tgz"
rm -f "$TARBALL"

echo "==> deploying to $REMOTE"
ssh "$REMOTE" \
	REL_ID="$REL_ID" \
	LABEL="$LABEL" \
	KEEP_RELEASES="$KEEP_RELEASES" \
	HEALTH_TIMEOUT="$HEALTH_TIMEOUT" \
	bash -euo pipefail -s <<'REMOTE_SCRIPT'
BASE="$HOME/.local/launchpad-ha"
DOM="gui/$(id -u)"
REL="$BASE/releases/$REL_ID"
LOGDIR="$HOME/Library/Logs/$LABEL"
HEARTBEAT="$LOGDIR/heartbeat"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$REL" "$BASE/shared" "$BASE/bin" "$LOGDIR" "$HOME/Library/LaunchAgents"
tar -xzf "/tmp/$REL_ID.tgz" -C "$REL"
rm -f "/tmp/$REL_ID.tgz"

if [ ! -f "$BASE/shared/env" ]; then
	echo "error: $BASE/shared/env is missing." >&2
	echo "       Create it with HA_URL and HA_TOKEN, then chmod 600, and re-run." >&2
	exit 1
fi
chmod 600 "$BASE/shared/env"

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
if ! command -v uv >/dev/null; then
	echo "error: uv is not installed on this host." >&2
	echo "       Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
	exit 1
fi

echo "--> building release environment"
# --frozen: install exactly what uv.lock pins, never re-resolve.
# uv also provisions the interpreter named in .python-version, so the system
# Python is irrelevant.
(cd "$REL" && uv sync --frozen --no-dev)

echo "--> self-test (current release still live)"
(
	cd "$REL"
	HA_ENV_FILE="$BASE/shared/env" \
		LAUNCHPAD_RELEASE_ID="$REL_ID" \
		LOG_FILE="" \
		"$REL/.venv/bin/ha-launchpad" --selftest
)

install -m 755 "$REL/packaging/bin/run" "$BASE/bin/run"

sed -e "s|__BASE__|$BASE|g" -e "s|__LOGDIR__|$LOGDIR|g" \
	"$REL/packaging/com.launchpad.ha.plist.template" >"$PLIST.new"
chmod 644 "$PLIST.new"
plutil -lint "$PLIST.new" >/dev/null

PLIST_CHANGED=0
cmp -s "$PLIST.new" "$PLIST" 2>/dev/null || PLIST_CHANGED=1
mv "$PLIST.new" "$PLIST"

PREV="$(readlink "$BASE/current" 2>/dev/null || true)"
T0="$(date +%s)"

echo "--> switching to $REL_ID"
# `mv -h` renames the symlink itself rather than following it into the target
# directory, and is a single rename(2). `ln -sfn` would unlink first, leaving a
# window where `current` does not exist.
ln -s "$REL" "$BASE/current.tmp"
mv -h "$BASE/current.tmp" "$BASE/current"

# A disable set in System Settings > Login Items persists across boots and
# survives plist replacement, so bootstrap would "succeed" while nothing runs.
launchctl enable "$DOM/$LABEL" 2>/dev/null || true

if launchctl print "$DOM/$LABEL" >/dev/null 2>&1; then
	if [ "$PLIST_CHANGED" = 1 ]; then
		echo "--> plist changed, reloading service"
		launchctl bootout "$DOM/$LABEL" 2>/dev/null || true
		for _ in $(seq 20); do
			launchctl print "$DOM/$LABEL" >/dev/null 2>&1 || break
			sleep 0.5
		done
		launchctl bootstrap "$DOM" "$PLIST"
	else
		launchctl kickstart -k "$DOM/$LABEL"
	fi
else
	launchctl bootstrap "$DOM" "$PLIST"
fi

echo "--> waiting for heartbeat (up to ${HEALTH_TIMEOUT}s)"
# The heartbeat is written by the poll loop, so it only appears once Home
# Assistant answered and the Launchpad opened. `launchctl print` cannot tell us
# that, and its own man page says the output is not API.
healthy=0
for _ in $(seq "$HEALTH_TIMEOUT"); do
	sleep 1
	[ -f "$HEARTBEAT" ] || continue
	[ "$(stat -f %m "$HEARTBEAT")" -ge "$T0" ] || continue
	[ "$(cat "$HEARTBEAT")" = "$REL_ID" ] || continue
	healthy=1
	break
done

if [ "$healthy" != 1 ]; then
	echo "!! $REL_ID did not become healthy - rolling back" >&2
	tail -n 30 "$LOGDIR/app.log" "$LOGDIR/launchd.err.log" 2>/dev/null || true
	if [ -n "$PREV" ]; then
		ln -s "$PREV" "$BASE/current.tmp"
		mv -h "$BASE/current.tmp" "$BASE/current"
		launchctl kickstart -k "$DOM/$LABEL" || true
		echo "rolled back to $(basename "$PREV")" >&2
	else
		echo "no previous release to roll back to" >&2
	fi
	exit 1
fi

echo "OK: $REL_ID healthy"

# Keep a handful of releases so a rollback stays a symlink flip.
ls -1dt "$BASE"/releases/* 2>/dev/null | tail -n "+$((KEEP_RELEASES + 1))" |
	while read -r old; do rm -rf "$old"; done
REMOTE_SCRIPT

echo "==> done: $REL_ID live on $REMOTE"
