---
name: kortoeng-on
description: Use when the user wants to turn Codex Kor To Eng translation on.
---

# Kortoeng On

Enable Korean-to-English prompt translation.

Run from this plugin root:

- Windows: `py -3 .\scripts\kortoeng_control.py on`
- macOS/Linux: `python3 ./scripts/kortoeng_control.py on`

Report the printed `translation=on` and `settings_file=...` lines. The hook
reads this settings file on each Korean prompt, so a Codex app restart is not
needed for this on/off setting.
