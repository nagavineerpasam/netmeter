# netmeter

Per-session network usage in the Claude Code statusline.

```
↓ 12.3 MB  ↑ 4.1 MB
```

Counts bytes sent and received by the `claude` process and all its descendants — WebFetch, Bash-spawned `curl`, MCP servers, package downloads. The counter resets at every new session.

## Install

Currently macOS only.

1. Clone the repo:
   ```
   git clone https://github.com/nagavineerpasam/netmeter ~/projects/netmeter
   ```

2. Install the plugin (one of the following):

   **Option A — symlink (development):**
   ```
   mkdir -p ~/.claude/plugins
   ln -s ~/projects/netmeter/plugin ~/.claude/plugins/netmeter
   ```

   **Option B — copy (release):**
   ```
   mkdir -p ~/.claude/plugins
   cp -R ~/projects/netmeter/plugin ~/.claude/plugins/netmeter
   ```

3. Enable the statusline. The plugin tries to register a default `statusLine` automatically via `plugin/settings.json`. If your Claude Code version does not yet pick that up from plugin settings, add this block to your user settings at `~/.claude/settings.json`:

   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "~/.claude/plugins/netmeter/statusline.sh",
       "padding": 0,
       "refreshInterval": 5
     }
   }
   ```

4. Restart Claude Code. The statusline should show `↓ 0 B  ↑ 0 B` within ~1 second of starting a new session.

## Requirements

- macOS (uses `nettop` — preinstalled).
- Python 3.9+ (preinstalled on macOS).
- Optional: `jq` (the hook falls back to `python3` if missing).

No sudo required. No external dependencies.

## Configuration

Environment variables, all optional:

| Variable | Default | Description |
|---|---|---|
| `NETMETER_FORMAT` | `compact` | One of `compact`, `total`, `verbose` |
| `NETMETER_STALE_THRESHOLD_SEC` | `10` | Show a stale-marker if the state file is older than this |
| `NETMETER_STATE_DIR` | `~/.claude/plugins/data/netmeter` | Where the daemon writes per-session JSON |
| `NETMETER_NETTOP_BIN` | `nettop` | Override the nettop binary (for testing) |

Format examples:
- `compact` (default): `↓ 12.3 MB  ↑ 4.1 MB`
- `total`: `16.4 MB`
- `verbose`: `net: 16.4 MB (↓12.3 MB ↑4.1 MB)`

## How it works

- `SessionStart` hook spawns a small Python daemon scoped to one Claude Code session.
- The daemon streams `nettop -P -d` and accumulates byte deltas for the PIDs in the claude process tree (root + all descendants), refreshed every 2 seconds.
- It writes a JSON state file at `~/.claude/plugins/data/netmeter/<session_id>.json` atomically every ~1 second.
- The statusline command reads that file each render (a single file read; no `nettop` shell-out per render).
- The daemon self-terminates when the claude PID disappears.

## Uninstall

```
rm ~/.claude/plugins/netmeter
rm -rf ~/.claude/plugins/data/netmeter  # optional: removes per-session state and logs
```

If you added a `statusLine` block to your user settings, remove it.

## Limitations

- macOS only in v1.
- Counts kernel-attributed bytes per process; not strictly equal to TLS-wire bytes.
- Per session only; no daily/lifetime/destination rollups yet.

## Development

```
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/pytest
```

Design and plan documents:
- `docs/superpowers/specs/2026-06-03-netmeter-design.md`
- `docs/superpowers/plans/2026-06-03-netmeter.md`

## License

TBD by the repository owner.
