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

COMPOSE_FILE="${HOME}/.claude/plugins/data/netmeter/compose_with"
if [ -f "$COMPOSE_FILE" ]; then
  compose_cmd="$(cat "$COMPOSE_FILE" 2>/dev/null || true)"
  if [ -n "$compose_cmd" ]; then
    compose_out="$(printf '%s' "$input" | sh -c "$compose_cmd" 2>/dev/null || true)"
    [ -n "$compose_out" ] && printf '%s\n' "$compose_out"
  fi
fi

printf '%s' "$input" | exec "$DIR/bin/netmeter-render"
