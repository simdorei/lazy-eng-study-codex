from __future__ import annotations

import json
from typing import Final, assert_never

from hook_types import (
    JsonObject,
    PromptPayload,
    TranslationFailure,
    TranslationResult,
    TranslationSuccess,
)
from prompt_rewrite import contains_korean, is_gram_command, rewrite_source

MAX_VISIBLE_CHARS: Final = 700
PLUGIN_NAME: Final = "lazy-eng-study-codex"
CONTRACT_VERSION: Final = "1"


def format_hook_output(payload: PromptPayload, result: TranslationResult) -> str:
    source_prompt = rewrite_source(payload.prompt)
    grammar_command = is_gram_command(payload.prompt)
    mode = output_mode(source_prompt, grammar_command=grammar_command)
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
                "$gram understood-request display is active."
                if grammar_command
                else "Prompt translation/correction hook is active."
            )
            action_note = (
                "Treat the visible correction line as the primary user request."
                if grammar_command
                else "Treat the rewritten English prompt as the primary user request."
            )
            context_lines = [
                command_note,
                f"Rewrite engine: {engine}",
                "Show the rewritten prompt in the Codex app itself.",
                f"First visible assistant message line: {visible_notice}",
                "Do not repeat that line in the final answer if it was already shown.",
                action_note,
            ]
            if not grammar_command:
                context_lines.append(f"Assistant-understood request: {english}")
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
            context = "\n".join(context_lines)
            system_message = f"{visible_notice} ({engine})"
            metadata = success_metadata(
                mode=mode,
                visible_notice=visible_notice,
                assistant_understood_request=english,
            )
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
            metadata = failure_metadata(mode=mode, reason=reason)
        case _ as unreachable:
            assert_never(unreachable)
    output = {
        "systemMessage": system_message,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
            "lazyEngStudyCodex": metadata,
        },
    }
    return json.dumps(output, ensure_ascii=True) + "\n"


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
            "lazyEngStudyCodex": failure_metadata(mode="preflight", reason=reason),
        },
    }
    return json.dumps(output, ensure_ascii=True) + "\n"


def output_mode(source_prompt: str, *, grammar_command: bool) -> str:
    if grammar_command:
        return "grammar-correction"
    if contains_korean(source_prompt):
        return "translation"
    return "english-correction"


def base_metadata(*, status: str, mode: str) -> JsonObject:
    return {
        "pluginName": PLUGIN_NAME,
        "contractVersion": CONTRACT_VERSION,
        "status": status,
        "mode": mode,
    }


def success_metadata(
    *,
    mode: str,
    visible_notice: str,
    assistant_understood_request: str,
) -> JsonObject:
    metadata = base_metadata(status="success", mode=mode)
    metadata["visibleLine"] = visible_notice
    metadata["assistantUnderstoodRequest"] = assistant_understood_request
    return metadata


def failure_metadata(*, mode: str, reason: str) -> JsonObject:
    metadata = base_metadata(status="failure", mode=mode)
    metadata["failureReason"] = reason
    return metadata


def limit_visible(text: str) -> str:
    one_line = " ".join(text.split())
    if len(one_line) <= MAX_VISIBLE_CHARS:
        return one_line
    return f"{one_line[:MAX_VISIBLE_CHARS - 3]}..."
