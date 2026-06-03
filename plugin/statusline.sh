#!/usr/bin/env bash
# Claude Code statusline command for netmeter.
#
# Output is one or two rows:
#   - If ~/.claude/plugins/data/netmeter/compose_with exists, it is read as
#     a shell command and invoked first with the same stdin. Its output is
#     emitted as the top row(s).
#   - The netmeter line is always emitted last (on its own row).
#
# /netmeter-setup writes the compose_with file when it detects a pre-existing
# statusLine, so the plugin coexists with whatever the user already had —
# no env var plumbing required (statusLine.env is not honoured by Claude
# Code).

set -u
DIR="$(cd "$(dirname "$0")" && pwd)"

# Capture stdin once so we can feed both children the same payload.
input=$(cat)

# Lazy-spawn the daemon if no state file exists for this session.
# Covers the case where the SessionStart hook missed firing — first-install
# on GitHub marketplaces races the async marketplace fetch (upstream
# issue #10997) — and the "user installed mid-session and only ran
# /reload-skills" path where hooks don't re-fire.
SESSION_ID="$(printf '%s' "$input" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("session_id",""))' 2>/dev/null || true)"
STATE_DIR="${NETMETER_STATE_DIR:-$HOME/.claude/plugins/data/netmeter}"
if [ -n "$SESSION_ID" ] && [ ! -f "$STATE_DIR/$SESSION_ID.json" ]; then
  DAEMON_BIN="$DIR/bin/netmeter-daemon"
  if [ -x "$DAEMON_BIN" ] && ! pgrep -f "netmeter.daemon --session-id $SESSION_ID" >/dev/null 2>&1; then
    mkdir -p "$STATE_DIR" 2>/dev/null
    nohup "$DAEMON_BIN" --session-id "$SESSION_ID" --claude-pid "$PPID" \
      > "$STATE_DIR/$SESSION_ID.log" 2>&1 &
    disown 2>/dev/null || true
  fi
fi

COMPOSE_FILE="${HOME}/.claude/plugins/data/netmeter/compose_with"
if [ -f "$COMPOSE_FILE" ]; then
  compose_cmd="$(cat "$COMPOSE_FILE" 2>/dev/null || true)"
  if [ -n "$compose_cmd" ]; then
    compose_out="$(printf '%s' "$input" | sh -c "$compose_cmd" 2>/dev/null || true)"
    [ -n "$compose_out" ] && printf '%s\n' "$compose_out"
  fi
fi

printf '%s' "$input" | exec "$DIR/bin/netmeter-render"
