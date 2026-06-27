---
name: kor-to-eng
description: Use when the user wants Korean Codex prompts translated to English before the agent reads them, wants English correction, or wants to configure Lazy Eng Study Codex.
---

# Lazy Eng Study Codex

This plugin installs a `UserPromptSubmit` hook. When a prompt contains Korean
text, the hook asks a translator to produce English, then adds that English as
visible hook output and Codex-readable context.

Default behavior:

- Fluent English prompts are left untouched.
- Awkward English prompts with obvious correction markers are rewritten into
  natural English.
- Korean prompts use `codex exec` with `gpt-5.4-mini` and medium reasoning
  effort.
- The hook finds the Codex executable automatically from `PATH`, the Codex app
  install folder, or an explicit `CODEX_KOR_TO_ENG_CODEX_BIN` override.
- The hook starts through `scripts/bootstrap.ps1` or `scripts/bootstrap.sh`;
  bootstrap uses Python 3.11+ when available and otherwise prepares portable
  Python in the plugin runtime cache.
- Run `$kortoeng` only when translation looks broken and you need diagnostics.
- Run `$kortoeng-on` or `$kortoeng-off` to toggle translation.
- Run `$kortoeng-model` to choose Spark, Mini, or GPT-5.5.
- Run `$kortoeng-bin` to find the current Codex executable and save that path.
- Run `$gram <English sentence>` to correct one English sentence on demand.
- Run `scripts/configure_model.ps1` to write the same model setting as
  `$kortoeng-model`. It can choose one of:
  - `gpt-5.3-codex-spark`
  - `gpt-5.4-mini`
  - `gpt-5.5`
- `CODEX_KOR_TO_ENG_MODEL` and `CODEX_KOR_TO_ENG_TIMEOUT_SECONDS` are fallback
  defaults only when the settings file has no stored model or timeout.
- Set `CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND` to use a different translator.

If translation fails, the hook reports the failure instead of silently falling
back to the Korean original.
