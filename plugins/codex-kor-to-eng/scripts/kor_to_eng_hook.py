from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from json import JSONDecodeError
from pathlib import Path
from typing import Final, assert_never

from hook_types import (
    HookSettings,
    JsonObject,
    JsonValue,
    PromptPayload,
    TranslationFailure,
    TranslationRequest,
    TranslationResult,
    TranslationSuccess,
)
from plugin_settings import DEFAULT_EFFORT as _DEFAULT_EFFORT
from plugin_settings import DEFAULT_MODEL as _DEFAULT_MODEL
from plugin_settings import SettingsError, read_hook_settings

HANGUL_START: Final = ord("\uac00")
HANGUL_END: Final = ord("\ud7a3")
DEFAULT_MODEL: Final = _DEFAULT_MODEL
DEFAULT_EFFORT: Final = _DEFAULT_EFFORT
MAX_VISIBLE_CHARS: Final = 700


def contains_korean(text: str) -> bool:
    return any(HANGUL_START <= ord(char) <= HANGUL_END for char in text)


def resolve_cwd(raw_cwd: str) -> str | None:
    if Path(raw_cwd).is_dir():
        return raw_cwd
    return None


def parse_payload(raw: str) -> PromptPayload | None:
    if raw.strip() == "":
        return None
    try:
        parsed = json.loads(raw, object_pairs_hook=json_object_pairs)
    except JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    payload: JsonObject = {}
    for key, item in parsed.items():
        if isinstance(key, str):
            payload[key] = item

    event = payload.get("hook_event_name")
    prompt = payload.get("prompt")
    cwd = payload.get("cwd")
    if event != "UserPromptSubmit":
        return None
    if not isinstance(prompt, str):
        return None
    if not isinstance(cwd, str):
        return None
    return PromptPayload(prompt=prompt, cwd=cwd)


def json_object_pairs(pairs: list[tuple[str, JsonValue]]) -> JsonObject:
    return dict(pairs)


def read_settings(env: Mapping[str, str]) -> HookSettings:
    return read_hook_settings(env)


def translate_prompt(request: TranslationRequest) -> TranslationResult:
    command = request.settings.custom_command
    if command is not None:
        return run_custom_translator(request)
    return run_codex_translator(request)


def run_custom_translator(request: TranslationRequest) -> TranslationResult:
    command = request.settings.custom_command
    if command is None:
        return TranslationFailure(reason="custom translator command is missing")
    translation_prompt = build_translation_prompt(request.prompt)
    env = translator_env(os.environ)
    try:
        completed = subprocess.run(
            command,
            input=translation_prompt,
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=request.cwd,
            env=env,
            shell=True,
            timeout=request.settings.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return TranslationFailure(
            reason=f"translator timed out after {request.settings.timeout_seconds}s",
        )

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        return TranslationFailure(reason=f"translator exited {completed.returncode}: {detail}")
    english = completed.stdout.strip()
    if english == "":
        return TranslationFailure(reason="translator returned empty output")
    return TranslationSuccess(english=english, engine="custom command")


def run_codex_translator(request: TranslationRequest) -> TranslationResult:
    command = build_codex_command(request.settings, request.prompt)
    env = translator_env(os.environ)
    try:
        completed = subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=request.cwd,
            env=env,
            shell=False,
            timeout=request.settings.timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return TranslationFailure(
            reason=f"codex executable not found: {request.settings.codex_bin}",
        )
    except subprocess.TimeoutExpired:
        return TranslationFailure(
            reason=f"codex translation timed out after {request.settings.timeout_seconds}s",
        )

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        return TranslationFailure(reason=f"codex exited {completed.returncode}: {detail}")
    english = completed.stdout.strip()
    if english == "":
        return TranslationFailure(reason="codex returned empty translation")
    return TranslationSuccess(
        english=english,
        engine=f"{request.settings.model}/{request.settings.effort}",
    )


def build_codex_command(settings: HookSettings, prompt: str) -> list[str]:
    return [
        settings.codex_bin,
        "--ask-for-approval",
        "never",
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--model",
        settings.model,
        "--config",
        f'model_reasoning_effort="{settings.effort}"',
        "--config",
        'model_verbosity="low"',
        build_translation_prompt(prompt),
    ]


def build_translation_prompt(prompt: str) -> str:
    return f"""Translate the following Korean Codex user request into natural English.
Output only the English translation. Do not add markdown or commentary.
Preserve file paths, commands, code, URLs, IDs, and @mentions exactly.

Korean request:
{prompt}"""


def translator_env(env: Mapping[str, str]) -> dict[str, str]:
    prepared = dict(env)
    prepared["CODEX_KOR_TO_ENG_DISABLED"] = "1"
    return prepared


def format_hook_output(payload: PromptPayload, result: TranslationResult) -> str:
    match result:
        case TranslationSuccess(english=english, engine=engine):
            visible_translation_notice = f"\ubc88\uc5ed: {limit_visible(english)}"
            context = "\n".join(
                [
                    "Korean-to-English prompt translation is active.",
                    f"Translation engine: {engine}",
                    "Show the translation in the Codex app itself.",
                    f"Start the assistant reply with this exact line: {visible_translation_notice}",
                    "Treat the English translation as the primary user request.",
                    "Use the Korean original only to resolve translation ambiguity.",
                    "",
                    "Korean original:",
                    payload.prompt,
                    "",
                    "English translation:",
                    english,
                ],
            )
            system_message = f"KOR->ENG ({engine}): {limit_visible(english)}"
        case TranslationFailure(reason=reason):
            context = "\n".join(
                [
                    "Korean prompt was detected, but translation failed.",
                    "Do not assume an English translation was available.",
                    f"Failure: {reason}",
                    "",
                    "Korean original:",
                    payload.prompt,
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


def run_hook(raw: str, env: Mapping[str, str]) -> str:
    if env.get("CODEX_KOR_TO_ENG_DISABLED") == "1":
        return ""
    payload = parse_payload(raw)
    if payload is None:
        return ""
    if not contains_korean(payload.prompt):
        return ""
    try:
        settings = read_settings(env)
    except SettingsError as exc:
        settings_failure: TranslationResult = TranslationFailure(reason=str(exc))
        return format_hook_output(payload, settings_failure)
    if not settings.enabled:
        return ""
    cwd = resolve_cwd(payload.cwd)
    if cwd is None:
        cwd_failure: TranslationResult = TranslationFailure(
            reason=f"cwd is not a directory: {payload.cwd}",
        )
        return format_hook_output(payload, cwd_failure)
    result = translate_prompt(TranslationRequest(prompt=payload.prompt, settings=settings, cwd=cwd))
    return format_hook_output(payload, result)


def main() -> int:
    _ = sys.stdout.write(run_hook(sys.stdin.buffer.read().decode("utf-8"), os.environ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
