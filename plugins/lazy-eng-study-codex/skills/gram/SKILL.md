---
name: gram
description: Use when the user invokes $gram to show the English request context Codex should answer.
---

# Gram

`$gram <English request>` is a code-backed understood-request display command.

The hook strips `$gram`, sends the remaining sentence to the configured rewrite
model, and returns a visible `교정: ...` line. That visible line is the request
context Codex should answer. When this skill is active, show that correction
line if it was not already shown, then handle that request normally.

Do not run a second grammar-correction pass in the assistant response. The hook
has already produced the understood request.

If the user asks about the correction, explain briefly why the corrected
sentence is more natural.
