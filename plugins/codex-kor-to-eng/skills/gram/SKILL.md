---
name: gram
description: Use when the user invokes $gram to correct one English sentence while studying English in Codex.
---

# Gram

`$gram <English sentence>` is a code-backed grammar correction command.

The hook strips `$gram`, sends the remaining sentence to the configured rewrite
model, and returns a visible `교정: ...` line. When this skill is active and the
hook context contains `First visible assistant message line: 교정: ...`, answer
with that exact correction line.

If the user asks about the correction, explain briefly why the corrected
sentence is more natural.
