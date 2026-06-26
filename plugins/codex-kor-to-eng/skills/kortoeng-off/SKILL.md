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
and `hook_reload_note=...` lines. The setting is global, but it only affects
Codex app threads where the `UserPromptSubmit` hook is already loaded. If an
existing thread still shows translation after turning it off, Codex must be
restarted or the thread reopened so the hook list is loaded there too.
