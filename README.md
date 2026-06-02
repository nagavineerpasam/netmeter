# netmeter

**See how much internet data your Claude Code session is using — right in the statusline.**

```
                                                                       16.4 MB used
```

netmeter is a Claude Code plugin (macOS). It counts every byte the `claude`
process and its children send and receive — API calls, WebFetch, Bash-spawned
`curl`, MCP servers, `git push`, package downloads. The counter resets at the
start of every session, so you always see *this session's* usage.

---

## Install (about a minute)

There are three small steps. The first two run inside Claude Code; the third
is a one-time edit to your user settings.

### Step 1 — install the plugin

In any Claude Code window:

```
/plugin marketplace add nagavineerpasam/netmeter
/plugin install netmeter@toolbelt
```

Claude Code will fetch the plugin from GitHub and register it.

### Step 2 — enable the statusline (required, one-time)

Claude Code does not yet auto-load `statusLine` from plugin defaults, so add
the block below to your **`~/.claude/settings.json`** by hand. Merge it in —
don't overwrite the file.

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

> If `~` isn't expanded by Claude Code on your system and you see nothing
> after restart, replace `~` with your absolute home path
> (e.g. `/Users/yourname/.claude/...`).

### Step 3 — restart Claude Code

`/exit` and reopen `claude`. Within a second of the new session loading,
you should see `0 B used` on the statusline. As you use Claude, it will
climb to `42 MB used`, etc.

---

## What you'll see

Default format — a single, friendly total:

```
                                                          16.4 MB used
```

Other formats are available via the `NETMETER_FORMAT` environment variable
(set under `statusLine.env` in your settings):

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

Example block in `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "${CLAUDE_PLUGIN_ROOT}/statusline.sh",
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

After installing, ask Claude to do something networky:

> Download 30 MB with `curl -sSL --limit-rate 3M https://speed.cloudflare.com/__down?bytes=30000000 -o /dev/null`

Watch the number climb from `0 B used` to roughly `28 MB used` over ~10 seconds.

---

## Uninstall

```
/plugin uninstall netmeter@toolbelt
/plugin marketplace remove toolbelt
```

If you added the `statusLine` block manually, remove it from
`~/.claude/settings.json`. Optional cleanup:

```
rm -rf ~/.claude/plugins/data/netmeter
```

---

## How it works

- `SessionStart` hook spawns a small Python daemon scoped to the current
  Claude Code session.
- The daemon streams `nettop -P -d` and accumulates byte deltas for every
  PID in the claude process tree (refreshed every 2 s).
- It writes a per-session JSON state file at
  `~/.claude/plugins/data/netmeter/<session_id>.json` atomically every second.
- The statusline command just reads that file each render — no `nettop`
  shell-out per render, so it's fast (~40 ms).
- The daemon self-terminates when the claude PID disappears.

No sudo. No external services. No telemetry.

---

## Requirements

- macOS (uses the preinstalled `nettop` tool).
- Python 3.9+ (preinstalled on macOS).
- `jq` is optional; the hook falls back to `python3` if it's missing.

---

## Limitations

- **macOS only** in v1. Linux and Windows support are possible (see issues).
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

Design and plan documents live under `docs/superpowers/`.
