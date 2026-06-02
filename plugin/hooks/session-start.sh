#!/usr/bin/env bash
# Claude Code SessionStart hook for netmeter.
# Reads stdin JSON, spawns the daemon detached, exits 0.

set -u
DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Read the entire stdin (Claude Code provides session metadata as JSON).
PAYLOAD="$(cat)"

# Extract session_id. Prefer jq, fall back to python3.
if command -v jq >/dev/null 2>&1; then
    SESSION_ID="$(printf '%s' "$PAYLOAD" | jq -r '.session_id // empty' 2>/dev/null)"
else
    SESSION_ID="$(printf '%s' "$PAYLOAD" | python3 -c \
        'import json,sys; print(json.load(sys.stdin).get("session_id",""))' 2>/dev/null)"
fi

# The hook runs as a child of Claude Code; its parent PID is Claude Code.
CLAUDE_PID="$PPID"

# Bail silently if we couldn't get a session id — never break the session.
[ -z "$SESSION_ID" ] && exit 0

LOG_DIR="${NETMETER_STATE_DIR:-$HOME/.claude/plugins/data/netmeter}"
mkdir -p "$LOG_DIR" 2>/dev/null

# Spawn detached. nohup + & + redirect to log file.
nohup "$DIR/bin/netmeter-daemon" \
    --session-id "$SESSION_ID" \
    --claude-pid "$CLAUDE_PID" \
    > "$LOG_DIR/${SESSION_ID}.log" 2>&1 &

# disown so the daemon survives this hook process exiting.
disown 2>/dev/null || true
exit 0
