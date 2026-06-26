# Codex Kor To Eng

Codex app plugin for people who naturally type Korean but want Codex to receive
an English version too.

The plugin runs before each Codex turn starts. If the prompt contains Korean, it
asks a translator for English, asks the next assistant reply to start with a
visible `번역: ...` line, and gives Codex the English translation as extra
context. The original Korean is kept beside it so translation mistakes are
easier to notice.

## Why Spark Is Optional

OpenAI currently describes `gpt-5.3-codex-spark` as a research-preview Codex
model for ChatGPT Pro users. Plus plans list the regular Codex models, not
Spark. Because of that, this plugin does not require Spark.

Default translation path:

```text
gpt-5.4-mini + medium reasoning effort
```

If Spark is available on your account, set:

```powershell
$env:CODEX_KOR_TO_ENG_MODEL = "gpt-5.3-codex-spark"
```

If Spark is not available, leave the default alone.

References:

- https://developers.openai.com/codex/models
- https://developers.openai.com/codex/pricing
- https://openai.com/index/introducing-gpt-5-3-codex-spark/

## Install In Codex

This repository is shaped as a local plugin marketplace. The actual plugin is in
`plugins/codex-kor-to-eng`.

From this repository root:

```powershell
codex plugin marketplace add .
```

Then open the Codex app, go to Plugins, find `Codex Kor To Eng`, install it, and
restart Codex so the hook is loaded.

After install, these skills are available inside Codex:

| Skill | Use |
| --- | --- |
| `$kortoeng-on` | Turn Korean translation on. |
| `$kortoeng-off` | Turn Korean translation off. |
| `$kortoeng-model` | Choose `mini`, `spark`, or `gpt55`. |
| `$kortoeng-bin` | Find the current Codex executable and save that static path. |
| `$kortoeng` | Diagnose path lookup when translation looks broken. |

The hook does not hard-code a versioned Codex app folder. It looks for:

1. `CODEX_KOR_TO_ENG_CODEX_BIN`, only if that file still exists.
2. `codex` on `PATH`.
3. The Codex app install folder on Windows or macOS.

On macOS, the hook command uses `python3`. If `codex` is on `PATH` or installed
in the normal Codex app location, no extra Mac setting is needed.

## Configure

The plugin works without Discord. It only needs Codex plus Python on the machine
that runs Codex.

The Python control script writes a small JSON settings file. By default it lives
under your Codex home folder. For tests or unusual setups, set
`CODEX_KOR_TO_ENG_SETTINGS_FILE`.

Examples from the plugin root:

```powershell
py -3 .\scripts\kortoeng_control.py off
py -3 .\scripts\kortoeng_control.py on
py -3 .\scripts\kortoeng_control.py model mini
py -3 .\scripts\kortoeng_control.py codex-bin
```

Useful environment variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `CODEX_KOR_TO_ENG_MODEL` | `gpt-5.4-mini` | Model used by the built-in Codex fallback translator. |
| `CODEX_KOR_TO_ENG_EFFORT` | `medium` | Reasoning effort for translation. |
| `CODEX_KOR_TO_ENG_CODEX_BIN` | auto-detected | Optional manual override for unusual Codex CLI installs. Missing stale paths are ignored. |
| `CODEX_KOR_TO_ENG_TIMEOUT_SECONDS` | `45` | Maximum time to wait for translation. |
| `CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND` | empty | Custom translator command. Receives the translation prompt on stdin and must print English to stdout. |

The hook sets `CODEX_KOR_TO_ENG_DISABLED=1` when it calls a child Codex process.
That prevents an endless loop where the translation Codex run triggers this same
translation hook again.

## What You See

For Korean input:

```text
테스트 스레드 상태 확인해줘
```

Codex receives extra context like:

```text
Korean original:
테스트 스레드 상태 확인해줘

English translation:
Check the test thread status.
```

The assistant reply should start with a visible line like:

```text
번역: Check the test thread status.
```

For English-only input, the hook outputs nothing.

If translation fails, the hook reports the actual failure instead of silently
pretending translation worked.

## Test

This repo has no runtime Python package dependency. The current Windows test
command is:

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m compileall plugins tests
```

Manual hook smoke test with a custom translator:

```powershell
$env:CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND = 'py -3 .\tests\fixtures\fake_translator.py'
@'
{"hook_event_name":"UserPromptSubmit","prompt":"\ud14c\uc2a4\ud2b8 \uc2a4\ub808\ub4dc \uc0c1\ud0dc \ud655\uc778\ud574\uc918","cwd":"C:\\repos\\simdorei\\codex-kor-to-eng","session_id":"manual"}
'@ | py -3 .\plugins\codex-kor-to-eng\scripts\kor_to_eng_hook.py
```

The output should be JSON with `systemMessage` and
`hookSpecificOutput.additionalContext`.

## Non-Goals

- No Discord dependency.
- No automatic rewrite of your original prompt text inside Codex.
- No silent fallback when translation fails.
