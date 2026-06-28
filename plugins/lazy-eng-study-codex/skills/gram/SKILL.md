---
name: gram
description: Use when the user invokes $gram to show the English request context Codex should answer.
---

# Gram

`$gram <English request>` is a code-backed understood-request display command.

The hook strips `$gram`, sends the remaining sentence to the configured rewrite
model, and returns a visible `교정: ...` line. That visible line is the request
context Codex should answer. It is not meant to make the sentence prettier; it
should show the request Codex understood. When this skill is active, show that
line if it was not already shown, then handle that request normally.

If the raw `$gram ...` prompt reaches the assistant without a visible `교정:`
line from the hook, the hook was not loaded for this session. Do not invent the
understood request in the assistant response. Run the plugin hook once with the
submitted prompt, show the returned `교정: ...` line first, then answer that
understood request.

Use the same hook entrypoint the plugin installs:

- Windows: pipe a `UserPromptSubmit` JSON payload into
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1`
- macOS: pipe the same payload into `sh ./scripts/bootstrap.sh`

If the hook returns a failure JSON, show the failure instead of silently
pretending the understood-request display worked.

If the user asks about the `교정:` line, explain briefly what request Codex
understood.
