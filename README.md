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

There are two steps: **install the plugin**, then **enable the statusline**.
Pick whichever enable-method you prefer.

### Step 1 — install the plugin (everyone does this)

In any Claude Code window:

```
/plugin marketplace add nagavineerpasam/netmeter
/plugin install netmeter@toolbelt
```

Claude Code fetches the plugin from GitHub and registers it. The
`SessionStart` hook (which spawns the network-measuring daemon) is now
wired up.

### Step 2 — enable the statusline

The plugin runs the daemon successfully, but Claude Code does not yet
auto-load a `statusLine` from plugins. You need to add a one-time block to
your `~/.claude/settings.json`. Three options, easiest first:

#### Option A — automatic, with safety checks (recommended)

After Step 1, in the same Claude Code window:

```
/netmeter-setup --dry-run
```

This prints exactly what will change — it writes nothing. Read it, then
apply for real:

```
/netmeter-setup
```

The command:
- Looks up the actual install path of netmeter from Claude Code's plugin
  registry (so it never goes stale across updates).
- Writes a timestamped backup of your settings.json before changing it.
- Refuses to overwrite an existing `statusLine` set by another plugin or by
  you (unless you pass `--force`).
- Is idempotent — running twice is a no-op the second time.

Then `/exit` and reopen `claude`. The statusline shows `0 B used` within
~1 second.

#### Option B — manual (paste a block yourself)

If you'd rather not run a script that touches your settings, open
`~/.claude/settings.json` in your editor and merge in this block:

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

> Replace `~` with your absolute home path (e.g. `/Users/yourname/...`) if
> Claude Code doesn't expand `~` on your system.

Save the file, `/exit`, reopen `claude`.

#### Option C — run the script directly from your terminal

If you prefer not to use a slash command:

```
bash ~/.claude/plugins/cache/toolbelt/netmeter/0.1.0/bin/netmeter-setup --dry-run
bash ~/.claude/plugins/cache/toolbelt/netmeter/0.1.0/bin/netmeter-setup
```

Same script as Option A, just invoked from your shell instead of from
Claude Code.

---

## Undo / recovery

Whichever option you used, every change is recoverable.

### If you used Option A or C

```
/netmeter-teardown
```

Restores your most recent settings.json backup (the one made just before
the last `netmeter-setup` run). The command also saves your current state
before restoring, so you can redo if needed.

You can list the available backups without restoring:

```
/netmeter-teardown --list
```

### If you used Option B

Open `~/.claude/settings.json` in your editor and remove the `statusLine`
block you pasted. Save the file and restart Claude Code.

### Full plugin uninstall

```
/plugin uninstall netmeter@toolbelt
/plugin marketplace remove toolbelt
```

(Then remove the `statusLine` block from your settings via Option B's
manual edit, or use `/netmeter-teardown` if you used the setup script.)

Optional cleanup:

```
rm -rf ~/.claude/plugins/data/netmeter
```

---

## What you'll see

Default format — a single, friendly total:

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

Ask Claude to download something networky:

> Download 30 MB with `curl -sSL --limit-rate 3M https://speed.cloudflare.com/__down?bytes=30000000 -o /dev/null`

Watch `0 B used` climb to roughly `28 MB used` over ~10 seconds.

---

## How it works

- The `SessionStart` hook spawns a small Python daemon scoped to the
  current Claude Code session.
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
