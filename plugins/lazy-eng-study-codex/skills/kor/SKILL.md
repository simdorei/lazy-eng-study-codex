---
name: kor
description: Use when the user invokes $kor to translate one Korean Codex prompt even while Lazy Eng Study Codex translation is off with $kortoeng-off.
---

# $kor

Use `$kor <Korean request>` for a one-shot Korean-to-English rewrite.

The hook strips `$kor`, translates the remaining text, and leaves the saved
`$kortoeng-on` or `$kortoeng-off` setting unchanged. Use this when automatic
translation is off but the current prompt should still show one translation
line.

If the raw `$kor ...` prompt reaches the assistant without a visible `번역:`
line from the hook, the hook was not loaded for this session. Do not answer the
raw Korean directly. Run the plugin hook once with the submitted prompt, show
the returned `번역: ...` line first, then answer the translated request.

Use the same hook entrypoint the plugin installs:

- Windows: pipe a `UserPromptSubmit` JSON payload into
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1`
- macOS: pipe the same payload into `sh ./scripts/bootstrap.sh`

If the hook returns a failure JSON, show the failure instead of silently falling
back to the Korean original.
