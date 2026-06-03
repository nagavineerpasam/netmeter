#!/usr/bin/env bash
# Claude Code statusline command for netmeter.
#
# Output is one or two lines:
#   - If NETMETER_COMPOSE_WITH is set to a shell command, that command is
#     invoked first with the same stdin and its output is emitted as the
#     top line(s).
#   - The netmeter line is always emitted last (on its own row).
#
# This lets the plugin coexist with a pre-existing statusLine the user
# already had configured. /netmeter-setup populates NETMETER_COMPOSE_WITH
# automatically when it detects one.

set -u
DIR="$(cd "$(dirname "$0")" && pwd)"

# Capture stdin once so we can feed both children the same payload.
input=$(cat)

if [ -n "${NETMETER_COMPOSE_WITH:-}" ]; then
  # Capture with $(...) which strips trailing newlines, then re-add exactly
  # one — guarantees the netmeter line below starts on a fresh row regardless
  # of whether the inner script ended its output with a newline or not.
  compose_out="$(printf '%s' "$input" | sh -c "$NETMETER_COMPOSE_WITH" 2>/dev/null || true)"
  [ -n "$compose_out" ] && printf '%s\n' "$compose_out"
fi

printf '%s' "$input" | exec "$DIR/bin/netmeter-render"
