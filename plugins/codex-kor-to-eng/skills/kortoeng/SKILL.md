---
name: kortoeng
description: Use when the user invokes $kortoeng or asks Codex Kor To Eng to find and apply the local Codex CLI path.
---

# Kortoeng

This skill is for diagnostics when Korean-to-English translation looks broken.
It checks the Codex executable path used by the hook. It must not run on every
prompt, and it must not hard-code a versioned, user-specific Codex app path.

When invoked:

1. Run the status script from this plugin root:
   - Windows: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 kortoeng_control.py status`
   - macOS: `sh ./scripts/bootstrap.sh kortoeng_control.py status`
2. Report `enabled=...`, `model=...`, `timeout_seconds=...`, `codex_bin=...`,
   `codex_bin_source=...`, `codex_found=...`, `settings_file=...`,
   `hook_scope=...`, and `hook_reload_note=...`.
3. If it prints `codex_found=false` or `codex executable was not found`, tell
   the user to install Codex CLI or put `codex` on `PATH`, then rerun
   `$kortoeng`.

The bootstrap may prepare portable Python under
`CODEX_KOR_TO_ENG_RUNTIME_DIR` when Python 3.11+ is missing. This does not spend
model tokens.

Do not set `CODEX_KOR_TO_ENG_CODEX_BIN` to a versioned Codex app folder unless
the user explicitly asks for a manual override.

Important: `$kortoeng-on` and `$kortoeng-off` update one global settings file,
but Codex still has to load this plugin's `UserPromptSubmit` hook in each app
thread. If a thread does not show the visible `번역:` line, the hook is not
loaded there yet; restart or reopen Codex so the hook list is loaded.

For actual control, use:

- `$kortoeng-on`
- `$kortoeng-off`
- `$kortoeng-model`
- `$kortoeng-bin`
