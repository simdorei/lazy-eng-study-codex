# Lazy Eng Study Codex

Codex app plugin for people who naturally type Korean but want to study English
while using Codex.

The plugin runs before each Codex turn starts. Korean prompts are translated to
visible English context, obvious awkward English can be corrected, and
`$gram <English request>` gives an on-demand `교정: ...` line, then Codex handles
the corrected request normally.

## Why Spark Is Optional

OpenAI currently describes `gpt-5.3-codex-spark` as a research-preview Codex
model for ChatGPT Pro users. Plus plans list the regular Codex models, not
Spark. Because of that, this plugin does not require Spark.

Default translation path:

```text
gpt-5.4-mini + medium reasoning effort
```

If Spark is available on your account, choose it after install:

```text
$kortoeng-model spark
```

Or from the plugin root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 kortoeng_control.py model spark
```

If Spark is not available, leave the default alone.

References:

- https://developers.openai.com/codex/models
- https://developers.openai.com/codex/pricing
- https://openai.com/index/introducing-gpt-5-3-codex-spark/

## Install In Codex

This repository is shaped as a local plugin marketplace. The public repository
is `lazy-eng-study-codex`; the internal plugin id remains
`plugins/codex-kor-to-eng` for install compatibility.

From this repository root:

```powershell
codex plugin marketplace add .
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

Then open the Codex app, go to Plugins, find `Lazy Eng Study Codex`, install it,
and restart Codex so the hook is loaded.

On Apple Silicon macOS, run:

```sh
codex plugin marketplace add .
sh ./install.sh
```

After install, these commands are available inside Codex:

| Command | Use |
| --- | --- |
| `$kortoeng-on` | Turn Korean translation on. |
| `$kortoeng-off` | Turn Korean translation off. |
| `$kortoeng-model` | Choose `mini`, `spark`, or `gpt55`. |
| `$kortoeng-bin` | Find the current Codex executable and save that static path. |
| `$kortoeng` | Diagnose path lookup when translation looks broken. |
| `$gram <request>` | Show `교정: ...`, then handle the corrected English request normally. |

These commands update one global settings file. They do not inject a hook into
an already-open Codex app thread that never loaded the plugin. If a thread does
not show the visible `번역:` line after `$kortoeng-on`, restart or reopen Codex
so the `UserPromptSubmit` hook is loaded there too.

The hook does not hard-code a versioned Codex app folder. It looks for:

1. `CODEX_KOR_TO_ENG_CODEX_BIN`, only if that file still exists.
2. `codex` on `PATH`.
3. The Codex app install folder on Windows or macOS.

The hook does not assume Python is already installed. It starts through
`scripts/bootstrap.ps1` on Windows and `scripts/bootstrap.sh` on macOS. The
bootstrap first looks for Python 3.11 or newer. If it cannot find one, it
downloads a plugin-scoped portable Python runtime and uses that. It does not
install Python into the operating system.

Portable Python support is for Windows x64/ARM64 and Apple Silicon macOS. Intel
macOS is intentionally not supported.

## Configure

The plugin works without Discord. It needs Codex. Python is prepared by the
bootstrap when the host does not already have Python 3.11 or newer.

The Python control script writes a small JSON settings file. By default it lives
under your Codex home folder. For tests or unusual setups, set
`CODEX_KOR_TO_ENG_SETTINGS_FILE`.

The hook reads this file every time it runs. That makes on/off/model changes
global for every loaded hook, including old and new threads that have the hook.
If a thread never loaded the hook, the plugin code is not being called and the
Codex app must reload the plugin list first.

Examples from the plugin root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 kortoeng_control.py off
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 kortoeng_control.py on
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 kortoeng_control.py model mini
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 kortoeng_control.py codex-bin
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_model.ps1 -Model mini
```

On Apple Silicon macOS, use `sh ./scripts/bootstrap.sh ...` instead:

```sh
sh ./scripts/bootstrap.sh kortoeng_control.py on
sh ./scripts/bootstrap.sh kortoeng_control.py model mini
```

Useful environment variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `CODEX_KOR_TO_ENG_MODEL` | `gpt-5.4-mini` | Fallback model used only when no model is stored in the settings file. |
| `CODEX_KOR_TO_ENG_EFFORT` | `medium` | Fallback reasoning effort used only when no effort is stored in the settings file. |
| `CODEX_KOR_TO_ENG_CODEX_BIN` | auto-detected | Optional manual override for unusual Codex CLI installs. Missing stale paths are ignored. |
| `CODEX_KOR_TO_ENG_RUNTIME_DIR` | `$CODEX_HOME/codex-kor-to-eng/runtime` | Local cache root for portable Python. |
| `CODEX_KOR_TO_ENG_PYTHON_DOWNLOAD_ROOT` | Python standalone release URL | Download root for portable Python archives. |
| `CODEX_KOR_TO_ENG_PYTHON_BIN` | auto-detected | Optional Python executable override for managed environments. |
| `CODEX_KOR_TO_ENG_TIMEOUT_SECONDS` | `45` | Fallback maximum wait time used only when no timeout is stored in the settings file. |
| `CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND` | empty | Custom translator command. Receives the translation prompt on stdin and must print English to stdout. |

The hook sets `CODEX_KOR_TO_ENG_DISABLED=1` when it calls a child Codex process.
That prevents an endless loop where the translation Codex run triggers this same
translation hook again.

## Correction Scope

`$gram` is explicit, so it asks the rewrite model to improve the remaining
English request even when the original is understandable. "Understandable" only
means the rough meaning can be guessed; it can still be corrected if it is
awkward, typo-prone, or vague.

`$gram` may correct:

- spelling and typos, such as `implimented` to `implemented`
- capitalization and terms, such as `readme` to `README`
- spacing and numbering, such as `number2` to `number 2`
- grammar, punctuation, and word order
- unnatural wording that a fluent English speaker would not normally use
- vague but understandable phrasing, when it can be improved without inventing
  missing details

The correction must preserve the user's intent, file paths, commands, code,
URLs, IDs, and @mentions. If a sentence is already fluent and clear, the rewrite
may be identical or only minimally changed. Automatic English polishing without
`$gram` is more conservative and only catches obvious awkward markers.

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

For fluent English-only input, the hook outputs nothing. For explicit grammar
study:

```text
$gram is number2 implimented now?
```

The visible correction is:

```text
교정: Is number 2 implemented now?
```

Codex then treats `Is number 2 implemented now?` as the request to answer.

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
{"hook_event_name":"UserPromptSubmit","prompt":"\ud14c\uc2a4\ud2b8 \uc2a4\ub808\ub4dc \uc0c1\ud0dc \ud655\uc778\ud574\uc918","cwd":"C:\\repos\\simdorei\\lazy-eng-study-codex","session_id":"manual"}
'@ | powershell -NoProfile -ExecutionPolicy Bypass -File .\plugins\codex-kor-to-eng\scripts\bootstrap.ps1
```

The output should be JSON with `systemMessage` and
`hookSpecificOutput.additionalContext`.

## Non-Goals

- No Discord dependency.
- No automatic rewrite of your original prompt text inside Codex.
- No silent fallback when translation fails.
