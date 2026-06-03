---
name: netmeter-setup
description: Configure the netmeter statusLine in your user settings. Composes safely with any existing statusLine you already have configured, so nothing is overwritten by accident. Pass --dry-run to preview, --replace to discard your existing statusline.
argument-hint: [--dry-run] [--replace]
allowed-tools: [Bash]
---

# netmeter-setup

Run the netmeter setup shell script with whatever arguments the user passed.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/bin/netmeter-setup" $ARGUMENTS
```

After the script finishes, show its complete stdout and stderr to the user verbatim — do not paraphrase. The script's output is human-readable on purpose and contains the exact next-step guidance the user needs (backup path, action taken, whether they need to restart).

If the script exits non-zero, surface the exit code and let the user know they can re-run `/netmeter-teardown` if anything looks wrong.
