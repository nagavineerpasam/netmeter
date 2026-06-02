---
description: Restore your settings.json from the most recent netmeter-setup backup
argument-hint: [--list]
allowed-tools: Bash
---

Run the netmeter teardown script with whatever arguments the user passed:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/bin/netmeter-teardown" $ARGUMENTS
```

Show the script's stdout/stderr to the user verbatim.
