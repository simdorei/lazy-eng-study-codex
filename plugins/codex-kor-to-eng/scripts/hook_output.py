from __future__ import annotations

import json
from typing import Final, assert_never

from hook_types import PromptPayload, TranslationFailure, TranslationResult, TranslationSuccess
from prompt_rewrite import contains_korean, is_gram_command, rewrite_source

MAX_VISIBLE_CHARS: Final = 700


def format_hook_output(payload: PromptPayload, result: TranslationResult) -> str:
    source_prompt = rewrite_source(payload.prompt)
    grammar_command = is_gram_command(payload.prompt)
    match result:
        case TranslationSuccess(english=english, engine=engine):
            visible_label = "\uad50\uc815" if grammar_command else "\ubc88\uc5ed"
            visible_notice = f"{visible_label}: {limit_visible(english)}"
            original_label = (
                "Korean original:" if contains_korean(source_prompt) else "Original English:"
            )
            rewritten_label = (
                "English translation:"
                if contains_korean(source_prompt) and not grammar_command
                else "Corrected English:"
            )
            command_note = (
                "$gram grammar correction command is active."
                if grammar_command
                else "Prompt translation/correction hook is active."
            )
            action_note = (
                "Answer with that exact correction line."
                if grammar_command
                else "Treat the rewritten English prompt as the primary user request."
            )
            context = "\n".join(
                [
                    command_note,
                    f"Rewrite engine: {engine}",
                    "Show the rewritten prompt in the Codex app itself.",
                    f"First visible assistant message line: {visible_notice}",
                    "Do not repeat that line in the final answer if it was already shown.",
                    action_note,
                    "Use the original prompt only to resolve ambiguity.",
                    "",
                    original_label,
                    source_prompt,
                    "",
                    rewritten_label,
                    english,
                ],
            )
            system_message = f"{visible_notice} ({engine})"
        case TranslationFailure(reason=reason):
            original_label = (
                "Korean original:" if contains_korean(source_prompt) else "Original prompt:"
            )
            context = "\n".join(
                [
                    "Prompt translation/correction was requested, but translation failed.",
                    "Do not assume a rewritten English prompt was available.",
                    f"Failure: {reason}",
                    "",
                    original_label,
                    source_prompt,
                ],
            )
            system_message = f"KOR->ENG translation failed: {limit_visible(reason)}"
        case _ as unreachable:
            assert_never(unreachable)
    output = {
        "systemMessage": system_message,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        },
    }
    return json.dumps(output, ensure_ascii=True) + "\n"


def limit_visible(text: str) -> str:
    one_line = " ".join(text.split())
    if len(one_line) <= MAX_VISIBLE_CHARS:
        return one_line
    return f"{one_line[:MAX_VISIBLE_CHARS - 3]}..."
