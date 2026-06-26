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
   - Windows: `py -3 .\scripts\kortoeng_control.py status`
   - macOS/Linux: `python3 ./scripts/kortoeng_control.py status`
2. Report `enabled=...`, `model=...`, `timeout_seconds=...`, `codex_bin=...`,
   `codex_bin_source=...`, `codex_found=...`, and `settings_file=...`.
3. If it prints `codex_found=false` or `codex executable was not found`, tell
   the user to install Codex CLI or put `codex` on `PATH`, then rerun
   `$kortoeng`.

Do not set `CODEX_KOR_TO_ENG_CODEX_BIN` to a versioned Codex app folder unless
the user explicitly asks for a manual override.

For actual control, use:

- `$kortoeng-on`
- `$kortoeng-off`
- `$kortoeng-model`
- `$kortoeng-bin`
