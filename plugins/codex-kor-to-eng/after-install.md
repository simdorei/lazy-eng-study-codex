# Codex Kor To Eng installed

Type `$kortoeng` in Codex to check the Codex executable path. The hook normally
finds it automatically, so you do not need to save a hard-coded `codex.exe`
path.

Useful skills:

- `$kortoeng-on`: turn translation on.
- `$kortoeng-off`: turn translation off.
- `$kortoeng-model`: choose the translation model.
- `$kortoeng-bin`: find the current Codex executable and save that static path.
- `$kortoeng`: diagnose path lookup when translation looks broken.

The on/off/model/bin skills write a small settings file that the hook reads on
each Korean prompt.

You can also choose the translation model from PowerShell:

From the plugin root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_model.ps1
```

Options:

- `1` Spark: `gpt-5.3-codex-spark`
- `2` Mini: `gpt-5.4-mini`
- `3` GPT-5.5: `gpt-5.5`

The script stores the choice in `CODEX_KOR_TO_ENG_MODEL`. It also stores
`CODEX_KOR_TO_ENG_TIMEOUT_SECONDS`: 45 seconds for Mini, 90 seconds for Spark
and GPT-5.5.
