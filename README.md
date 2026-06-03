# netmeter

**See how much internet data your Claude Code session is using — right in the statusline.**

```
Opus 4.7  [████████░░░░░░░░░░░░] 42% used                              net  16.4 MB used
```

netmeter is a Claude Code plugin (macOS). It counts every byte the `claude`
process and its children send and receive — API calls, WebFetch, Bash-spawned
`curl`, MCP servers, `git push`, package downloads. The counter resets at
each new session, so you always see *this session's* usage.

If you already have a statusline (model + context bar, git status, etc.),
netmeter coexists: your existing line stays as the top row, netmeter shows
on the row below it. You don't have to edit anything by hand.

---

## Install (three commands, no restart)

In any Claude Code window:

```
/plugin marketplace add nagavineerpasam/netmeter
/plugin install netmeter@toolbelt
/reload-skills
/netmeter-setup
```

That's it.

- `/plugin marketplace add` registers this repo as a plugin source.
- `/plugin install` fetches the plugin from GitHub.
- `/reload-skills` makes the `/netmeter-setup` slash command available
  immediately, without restarting Claude Code.
- `/netmeter-setup` writes the statusline config to your `~/.claude/settings.json`
  (with a backup), composes with any existing statusline you had, and lets
  Claude Code auto-reload. The daemon lazy-spawns from the first render.

Within a few seconds of your next message, the statusline shows `net  0 B used`
on the right (or stacked under your existing line if you have one).

> **Want to preview before applying?** `/netmeter-setup --dry-run` prints what
> it would change to `settings.json` without writing.
>
> **Want to replace your existing statusline instead of stacking under it?**
> `/netmeter-setup --replace`.

---

## Uninstall (two commands)

```
/netmeter-teardown
/plugin uninstall netmeter@toolbelt
```

- `/netmeter-teardown` restores your `settings.json` from the most recent
  backup `netmeter-setup` made (your original statusline returns exactly as
  it was), and removes the compose pointer.
- `/plugin uninstall` removes the plugin itself.

Optional cleanup if you want every trace gone:

```
/plugin marketplace remove toolbelt    # only if no other plugins use it
rm -rf ~/.claude/plugins/data/netmeter # session state + logs
```

---

## What you'll see

Default format — a single, friendly total with subtle colour for size:

```
net  16.4 MB used
```

- `net` in cyan (matches the colour of model labels in Claude Code).
- Value in your terminal's default colour up to 50 MB, **yellow** from 50 MB
  to 500 MB, **red** above 500 MB.
- `used` in dim gray.

Other formats via `NETMETER_FORMAT` (set under `statusLine.env` in
`~/.claude/settings.json`):

| `NETMETER_FORMAT` | Looks like |
|---|---|
| `compact` *(default)* | `net  16.4 MB used` |
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
| `NETMETER_COLOR` | `1` | Set to `0` to disable ANSI styling |
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

## Recovery — when something looks off

| Symptom | Fix |
|---|---|
| `/netmeter-setup` says "Unknown command" | You haven't run `/reload-skills` since installing. Run it, then try again. |
| Statusline empty after the first message | The daemon is still spawning. Send one more message — it appears within ~1 second. |
| You see `net X MB used` but your previous statusline disappeared | Composition wasn't applied. Run `/netmeter-teardown` (restores your old statusline) and then `/netmeter-setup` again. |
| You want netmeter removed but your previous statusline back | `/netmeter-teardown`. |
| You want netmeter only, drop the row above it | `rm ~/.claude/plugins/data/netmeter/compose_with` — netmeter's wrapper stops calling the inner line. |

---

## Try it

Ask Claude to download something:

> Run: `curl -sSL --limit-rate 3M https://speed.cloudflare.com/__down?bytes=30000000 -o /dev/null`

Watch `net  0 B used` climb to roughly `net  28 MB used` over ~10 seconds. Past
50 MB the value turns yellow; past 500 MB it turns red.

---

## How it works

- A `SessionStart` hook spawns a small Python daemon when Claude Code
  starts. If the hook misses (e.g., first-install marketplace fetch race),
  the statusline script **lazy-spawns** the daemon on the first render.
- The daemon streams `nettop -P -d` and accumulates byte deltas for every
  PID in the claude process tree (refreshed every 2 s).
- It writes a per-session JSON state file at
  `~/.claude/plugins/data/netmeter/<session_id>.json` atomically every
  second.
- The statusline command reads that file each render — fast (~40 ms) and
  doesn't shell out to `nettop` per render.
- The daemon self-terminates when the claude PID disappears.

No sudo. No external services. No telemetry.

---

## Requirements

- macOS (uses the preinstalled `nettop` tool).
- Python 3.9+ (preinstalled on macOS).
- Claude Code v2.1.140+ recommended (older versions may need `/exit` and
  reopen instead of `/reload-skills`).
- `jq` is optional; the hook falls back to `python3` if it's missing.

---

## Limitations

- **macOS only** in v1. Linux and Windows support are possible.
- Counts **kernel-attributed** bytes per process. Very close to wire bytes
  but includes TLS overhead and may miss sub-second network blips that
  `nettop`'s 1-second sample window cannot resolve.
- **Per session only** — no daily/lifetime totals or per-host breakdowns
  in v1.

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
