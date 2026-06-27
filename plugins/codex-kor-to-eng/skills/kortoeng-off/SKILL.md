---
name: kortoeng-off
description: Use when the user wants to turn Codex Kor To Eng translation off.
---

# Kortoeng Off

Disable Korean-to-English prompt translation.

Run from this plugin root:

- Windows: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 kortoeng_control.py off`
- macOS: `sh ./scripts/bootstrap.sh kortoeng_control.py off`

Report the printed `translation=off`, `settings_file=...`, `hook_scope=...`,
and `hook_reload_note=...` lines. The setting is global. Already-open Codex app
threads read the on/off value every time the hook runs, so changes apply after
the settings file is saved. Restart or reopen Codex only if the
`UserPromptSubmit` hook itself was not loaded in that thread.
