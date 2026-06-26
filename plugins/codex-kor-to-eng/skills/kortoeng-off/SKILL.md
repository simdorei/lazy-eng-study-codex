---
name: kortoeng-off
description: Use when the user wants to turn Codex Kor To Eng translation off.
---

# Kortoeng Off

Disable Korean-to-English prompt translation.

Run from this plugin root:

- Windows: `py -3 .\scripts\kortoeng_control.py off`
- macOS/Linux: `python3 ./scripts/kortoeng_control.py off`

Report the printed `translation=off` and `settings_file=...` lines. The hook
reads this settings file on each Korean prompt, so a Codex app restart is not
needed for this on/off setting.
