#!/usr/bin/env bash
# Claude Code statusline command for netmeter.
# Receives the session payload on stdin; prints one line to stdout.

set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/bin/netmeter-render"
