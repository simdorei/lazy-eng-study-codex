from __future__ import annotations

import json
from typing import Final, assert_never

from hook_types import (
    PromptPayload,
    TranslationFailure,
    TranslationResult,
    TranslationSuccess,
)
from prompt_rewrite import contains_korean, is_gram_command, rewrite_source

MAX_VISIBLE_CHARS: Final = 700
GRAM_ANSWER_INSTRUCTION_START: Final = (
    "After printing the exact visible correction line, answer the understood request normally"
)
GRAM_ANSWER_INSTRUCTION_MIDDLE: Final = "in the same assistant message."
GRAM_ANSWER_INSTRUCTION_END: Final = (
    "Do not stop after only the correction line unless the understood request itself asks only "
    "for correction."
)
GRAM_ANSWER_INSTRUCTION_PARTS: Final[tuple[str, str, str]] = (
    GRAM_ANSWER_INSTRUCTION_START,
    GRAM_ANSWER_INSTRUCTION_MIDDLE,
    GRAM_ANSWER_INSTRUCTION_END,
)
GRAM_ANSWER_INSTRUCTION: Final = " ".join(GRAM_ANSWER_INSTRUCTION_PARTS)


def format_hook_output(payload: PromptPayload, result: TranslationResult) -> str:
    source_prompt = rewrite_source(payload.prompt)
    grammar_command = is_gram_command(payload.prompt)
    match result:
        case TranslationSuccess(english=english, engine=engine):
            visible_label = "\uad50\uc815" if grammar_command else "\ubc88\uc5ed"
            visible_notice = f"{visible_label}: {limit_visible(english)}"
            context = success_context(
                source_prompt,
                english,
                engine=engine,
                visible_notice=visible_notice,
                grammar_command=grammar_command,
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
            system_message = f"Lazy Eng Study Codex translation failed: {limit_visible(reason)}"
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


def success_context(
    source_prompt: str,
    english: str,
    *,
    engine: str,
    visible_notice: str,
    grammar_command: bool,
) -> str:
    original_label = "Korean original:" if contains_korean(source_prompt) else "Original English:"
    rewritten_label = (
        "English translation:"
        if contains_korean(source_prompt) and not grammar_command
        else "Corrected English:"
    )
    command_note = (
        "$gram understood-request display is active."
        if grammar_command
        else "Prompt translation/correction hook is active."
    )
    action_note = (
        GRAM_ANSWER_INSTRUCTION
        if grammar_command
        else "Treat the rewritten English prompt as the primary user request."
    )
    visible_instruction = (
        f"Start only the first visible assistant message in this turn "
        f"with this exact line: {visible_notice}"
    )
    context_lines = [
        command_note,
        f"Rewrite engine: {engine}",
        visible_instruction,
        "Do not repeat that exact line in later assistant messages for this turn.",
        action_note,
        f"Assistant-understood request: {english}",
    ]
    context_lines.extend(
        [
            "Use the original prompt only to resolve ambiguity.",
            "",
            original_label,
            source_prompt,
        ],
    )
    if not grammar_command:
        context_lines.extend(["", rewritten_label, english])
    return "\n".join(context_lines)


def format_preflight_failure(reason: str) -> str:
    context = "\n".join(
        [
            "Lazy Eng Study Codex hook could not read the submitted prompt.",
            "Do not assume a rewritten English prompt was available.",
            f"Failure: {reason}",
        ],
    )
    output = {
        "systemMessage": f"Lazy Eng Study Codex hook failed: {limit_visible(reason)}",
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
