# Codex Kor To Eng installed

Type `$kortoeng` in Codex to check the Codex executable path. The hook normally
finds it automatically, so you do not need to save a hard-coded `codex.exe`
path.

For repo-level setup, run from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

On Apple Silicon macOS:

```sh
sh ./install.sh
```

The hook starts through `scripts/bootstrap.ps1` or `scripts/bootstrap.sh`. If
Python 3.11+ is missing, bootstrap prepares a plugin-scoped portable Python
runtime. It does not system-install Python.

Useful skills:

- `$kortoeng-on`: turn translation on.
- `$kortoeng-off`: turn translation off.
- `$kortoeng-model`: choose the translation model.
- `$kortoeng-bin`: find the current Codex executable and save that static path.
- `$kortoeng`: diagnose path lookup when translation looks broken.

The on/off/model/bin skills write a small settings file that the hook reads on
each Korean prompt. That setting is global, but only threads where Codex has
loaded this plugin's `UserPromptSubmit` hook can read it. If an existing app
thread does not show a visible `번역:` line, restart or reopen Codex so the hook
list is loaded for that thread.

You can also choose the translation model from PowerShell:

From the plugin root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_model.ps1
```

Options:

- `1` Spark: `gpt-5.3-codex-spark`
- `2` Mini: `gpt-5.4-mini`
- `3` GPT-5.5: `gpt-5.5`

The script stores the choice in the same JSON settings file used by
`$kortoeng-model`. It also stores the matching timeout: 45 seconds for Mini, 90
seconds for Spark and GPT-5.5. Environment variables are only fallback defaults
when the settings file has no stored model.
