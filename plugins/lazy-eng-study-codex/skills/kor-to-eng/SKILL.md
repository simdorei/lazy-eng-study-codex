---
name: kor-to-eng
description: Use when the user wants Korean Codex prompts translated to English before the agent reads them, wants English correction, or wants to configure Lazy Eng Study Codex.
---

# Lazy Eng Study Codex

This plugin installs a `UserPromptSubmit` hook. When a prompt contains Korean
text, the hook asks a translator to produce English, then adds that English as
visible hook output that Codex should answer.

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
- Run `$gram <English request>` to show Codex's understood English request, then
  handle that request normally.
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

## Existing-Session Fallback

Normally the `UserPromptSubmit` hook adds the visible `번역:` or `교정:` line
before the assistant sees the prompt. If a Korean prompt, `$kor ...`, or
`$gram ...` reaches the assistant without that visible line, the current Codex
session did not load this plugin hook.

In that case, do not answer the untranslated prompt directly. Run the plugin
hook once with the submitted prompt, show the returned visible line first, and
then answer the translated or understood request.

Use the same hook entrypoint the plugin installs:

- Windows: pipe a `UserPromptSubmit` JSON payload into
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1`
- macOS: pipe the same payload into `sh ./scripts/bootstrap.sh`

If the hook returns empty output, continue normally; that means the prompt did
not need translation or correction under the saved settings. If it returns a
failure JSON, show the failure instead of silently falling back to the original
prompt.
