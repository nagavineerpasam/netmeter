---
description: Configure the netmeter statusLine in your user settings (with safety checks)
argument-hint: [--dry-run] [--force]
allowed-tools: Bash
---

Run the netmeter setup script with whatever arguments the user passed:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/bin/netmeter-setup" $ARGUMENTS
```

Then show the script's full stdout/stderr to the user verbatim. Do not
paraphrase or interpret what the script reported — its output is designed
to be human-readable as-is.

If the script exits non-zero, tell the user the exit code and what they
should do next (the script's stderr already explains).
