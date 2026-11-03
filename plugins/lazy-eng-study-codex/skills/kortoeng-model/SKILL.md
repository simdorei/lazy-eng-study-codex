---
name: kortoeng-model
description: Use when the user wants to choose the Lazy Eng Study Codex translation model.
---

# Kortoeng Model

Select the translation model used by the hook.

Supported choices:

- `auto` (default, recommended): discover the oldest visible GPT generation in
  Codex's current `model/list` that supports text and `medium`; use medium
  reasoning and a 90-second translation timeout. Ties keep Codex's picker order.
- `spark`: `gpt-5.3-codex-spark`, timeout 90 seconds
- `gpt55`: `gpt-5.5`, timeout 90 seconds

The last two choices are retained for existing configurations; they may be
unavailable with ChatGPT sign-in. Recommend `auto` instead of pinning a version.
If the user did not name a model, use `auto`.
When the model is known, run from this plugin root:

- Windows: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 kortoeng_control.py model auto`
- macOS: `sh ./scripts/bootstrap.sh kortoeng_control.py model auto`

Replace `auto` only if the user explicitly chose a legacy model. Report the printed `model=...`,
`timeout_seconds=...`, and `settings_file=...` lines.
