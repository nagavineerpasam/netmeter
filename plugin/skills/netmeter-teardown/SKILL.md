---
name: netmeter-teardown
description: Restore your settings.json from the most recent netmeter-setup backup, undoing whatever netmeter-setup changed (the original statusLine, env vars, padding all come back exactly as they were). Pass --list to see available backups without restoring.
argument-hint: "[--list]"
allowed-tools: [Bash]
---

# netmeter-teardown

Run the netmeter teardown shell script with whatever arguments the user passed.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/bin/netmeter-teardown" $ARGUMENTS
```

After the script finishes, show its complete stdout and stderr to the user verbatim — do not paraphrase. The script's output explains exactly which backup was restored and where the pre-teardown state was saved (in case the user wants to redo).
