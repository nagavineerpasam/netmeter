# netmeter

**See how much internet data your Claude Code session is using — right in the statusline.**

```
                                                                       16.4 MB used
```

netmeter is a Claude Code plugin (macOS). It counts every byte the `claude`
process and its children send and receive — API calls, WebFetch, Bash-spawned
`curl`, MCP servers, `git push`, package downloads. The counter resets at
each new session, so you always see *this session's* usage.

---

## Install

Three commands inside Claude Code, plus one restart in the middle.

### 1. Add the marketplace

```
/plugin marketplace add nagavineerpasam/netmeter
```

### 2. Install the plugin

```
/plugin install netmeter@toolbelt
```

### 3. Restart Claude Code

`/exit`, then run `claude` again. This restart is **required**, because:

- New plugin slash commands (like `/netmeter-setup` below) only register at
  session start ([upstream issue #37862](https://github.com/anthropics/claude-code/issues/37862)).
- On first-install from a GitHub marketplace, the SessionStart hook can race
  the async marketplace fetch and miss firing
  ([upstream issue #10997](https://github.com/anthropics/claude-code/issues/10997)).
  A restart guarantees the daemon starts cleanly.

### 4. Configure the statusline

After the restart, run:

```
/netmeter-setup --dry-run     # preview, writes nothing
/netmeter-setup               # apply
```

That's it. Whether or not you already have a statusline configured,
`/netmeter-setup` does the right thing:

- **No existing statusline?** It installs netmeter as your statusline.
- **You already have one** (model + context bar, git status, anything)?
  It composes: your existing statusline stays as the top row, and
  netmeter shows on the row below it. **You don't have to merge scripts
  by hand or lose your existing UI.**

Claude Code auto-reloads `~/.claude/settings.json`, so your next message
refreshes the statusline — no second restart required.

The command is idempotent (re-run is a no-op), writes a timestamped backup
of `settings.json` before any change, and writes atomically (`settings.json`
is never half-written). Pass `--replace` if you *want* to throw away your
existing statusline and use netmeter only.

#### Option B — manual paste

If you'd rather not run a script, open `~/.claude/settings.json` and merge
in this block:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/plugins/cache/toolbelt/netmeter/0.1.0/statusline.sh",
    "padding": 0,
    "refreshInterval": 5
  }
}
```

Save the file. No restart needed — Claude Code reloads settings automatically
([per the official docs](https://code.claude.com/docs/en/statusline)).

#### Option C — terminal script

If you'd rather run the script from your shell:

```
bash ~/.claude/plugins/cache/toolbelt/netmeter/0.1.0/bin/netmeter-setup --dry-run
bash ~/.claude/plugins/cache/toolbelt/netmeter/0.1.0/bin/netmeter-setup
```

Same script as Option A, just invoked outside Claude Code.

---

## Uninstall

**Order matters.** Run these in sequence:

### 1. Restore your settings first

```
/netmeter-teardown
```

This restores `settings.json` from the most recent backup
`netmeter-setup` made, removing the `statusLine` block. You must do this
**before** uninstalling the plugin — once the plugin is gone, so is the
`/netmeter-teardown` command.

If you used the manual paste (Option B above) instead of `/netmeter-setup`,
edit `~/.claude/settings.json` and remove the `statusLine` block yourself.

### 2. Uninstall the plugin

```
/plugin uninstall netmeter@toolbelt
```

### 3. Remove the marketplace (optional)

Only if you don't plan to reinstall, or you have no other plugins from the
`toolbelt` marketplace:

```
/plugin marketplace remove toolbelt
```

### 4. Optional cleanup

```
rm -rf ~/.claude/plugins/data/netmeter
```

This removes per-session state files and logs. Not required for uninstall;
they're inert and small.

---

## Recovery — if something goes wrong

| Symptom | Fix |
|---|---|
| Statusline appears empty after install | Restart Claude Code one more time. SessionStart hooks can race the marketplace fetch on the very first install. |
| `/netmeter-setup` says "Unknown command" | The plugin was installed in the current session but slash commands only register at session start. Restart Claude Code. |
| You already had a statusline and don't want to lose it | You don't have to. `/netmeter-setup` composes by default — your existing statusline shows on top, netmeter on the row below. Pass `--replace` only if you want netmeter to take over the whole thing. |
| Your existing statusline shows but no netmeter row appears below | The daemon may not have started this session yet. Restart Claude Code. |
| You want your old settings back | `/netmeter-teardown` (if the plugin is still installed) or manually restore from `~/.claude/settings.json.bak.netmeter-<timestamp>`. |
| The statusline line wraps or gets cut off | Set `COLUMNS` in your terminal, or upgrade to Claude Code v2.1.153+ which provides terminal width to statusline scripts. |

---

## What you'll see

Default — a single, friendly total:

```
                                                          16.4 MB used
```

Other formats via the `NETMETER_FORMAT` environment variable (set under
`statusLine.env` in your settings):

| `NETMETER_FORMAT` | Looks like |
|---|---|
| `compact` *(default)* | `16.4 MB used` |
| `total` | `16.4 MB` |
| `split` | `↓ 12.3 MB  ↑ 4.1 MB` |
| `verbose` | `net: 16.4 MB (↓12.3 MB ↑4.1 MB)` |

> Note: in long Claude Code sessions, **upload usually exceeds download**.
> That's normal — the Claude API is stateless, so every turn re-sends the
> full conversation history. The single-total default avoids that confusion.

---

## Configuration

All optional. Set under `statusLine.env` in `~/.claude/settings.json`.

| Variable | Default | Effect |
|---|---|---|
| `NETMETER_FORMAT` | `compact` | `compact` / `total` / `split` / `verbose` |
| `NETMETER_ALIGN` | `right` | `right` / `center` / `left` |
| `NETMETER_STALE_THRESHOLD_SEC` | `10` | Append `⚠` if state is older than this |

Example block:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/plugins/cache/toolbelt/netmeter/0.1.0/statusline.sh",
    "padding": 0,
    "refreshInterval": 5,
    "env": {
      "NETMETER_FORMAT": "total",
      "NETMETER_ALIGN": "right"
    }
  }
}
```

---

## Try it

Ask Claude to download something:

> Run: `curl -sSL --limit-rate 3M https://speed.cloudflare.com/__down?bytes=30000000 -o /dev/null`

Watch `0 B used` climb to roughly `28 MB used` over ~10 seconds.

---

## How it works

- The `SessionStart` hook spawns a small Python daemon scoped to the
  current Claude Code session.
- The daemon streams `nettop -P -d` and accumulates byte deltas for every
  PID in the claude process tree (refreshed every 2 s).
- It writes a per-session JSON state file at
  `~/.claude/plugins/data/netmeter/<session_id>.json` atomically every second.
- The statusline command reads that file each render — no `nettop`
  shell-out per render, so it stays fast (~40 ms).
- The daemon self-terminates when the claude PID disappears.

No sudo. No external services. No telemetry.

---

## Requirements

- macOS (uses the preinstalled `nettop` tool).
- Python 3.9+ (preinstalled on macOS).
- `jq` is optional; the hook falls back to `python3` if it's missing.

---

## Limitations

- **macOS only** in v1. Linux and Windows support are possible.
- Counts **kernel-attributed** bytes per process. Very close to wire bytes
  but includes TLS overhead and may miss sub-second network blips that
  `nettop`'s 1-second sample window cannot resolve.
- **Per session only** — no daily/lifetime totals or per-host breakdowns
  in v1.
- One-time manual setup of the `statusLine` block is required because
  Claude Code does not currently support `statusLine` in plugin-shipped
  defaults (only `agent` and `subagentStatusLine` are honored). The
  `/netmeter-setup` command exists to make this one click instead of a
  manual edit.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Development

```
git clone https://github.com/nagavineerpasam/netmeter
cd netmeter
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/pytest
```
