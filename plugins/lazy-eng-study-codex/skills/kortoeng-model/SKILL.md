---
name: kortoeng-model
description: Use when the user wants to choose the Lazy Eng Study Codex translation model.
---

# Kortoeng Model

Select the translation model used by the hook.

Supported choices:

- `spark`: `gpt-5.3-codex-spark`, timeout 90 seconds
- `gpt55`: `gpt-5.5`, timeout 90 seconds

If the user did not name a model, recommend `gpt55` and ask which model to set.
When the model is known, run from this plugin root:

- Windows: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 kortoeng_control.py model gpt55`
- macOS: `sh ./scripts/bootstrap.sh kortoeng_control.py model gpt55`

Replace `gpt55` with the chosen model. Report the printed `model=...`,
`timeout_seconds=...`, and `settings_file=...` lines.
