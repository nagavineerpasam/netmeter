# netmeter — plugin payload

This directory is what gets symlinked or copied into `~/.claude/plugins/netmeter/`. See the project root `README.md` for installation and configuration.

Contents:
- `.claude-plugin/plugin.json` — plugin manifest (hooks)
- `settings.json` — plugin-default statusLine
- `statusline.sh` — statusline render entry
- `hooks/session-start.sh` — SessionStart hook (spawns the daemon)
- `bin/netmeter-daemon` — long-running per-session network meter
- `bin/netmeter-render` — statusline render command
- `bin/netmeter/` — Python package (formatter, state, parser, proctree, daemon, render)
