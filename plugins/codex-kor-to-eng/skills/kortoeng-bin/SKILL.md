---
name: kortoeng-bin
description: Use when the user wants to find the current Codex executable and save it as a static hook path.
---

# Kortoeng Bin

Find the current Codex executable and save that exact path into the hook
settings file.

Run from this plugin root:

- Windows: `py -3 .\scripts\kortoeng_control.py codex-bin`
- macOS/Linux: `python3 ./scripts/kortoeng_control.py codex-bin`

Report the printed `codex_bin=...`, `source=...`, and `settings_file=...` lines.
If the command reports that `codex` was not found, surface that exact failure
instead of guessing another path.
