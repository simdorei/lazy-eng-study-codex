from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from json import JSONDecodeError
from pathlib import Path
from typing import Final, assert_never

from codex_child_home import child_codex_env
from hook_output import format_hook_output, format_preflight_failure
from hook_types import (
    HookSettings,
    JsonObject,
    JsonValue,
    PromptParseFailure,
    PromptParseResult,
    PromptPayload,
    TranslationFailure,
    TranslationRequest,
    TranslationResult,
    TranslationSuccess,
)
from plugin_settings import DEFAULT_EFFORT as _DEFAULT_EFFORT
from plugin_settings import DEFAULT_MODEL as _DEFAULT_MODEL
from plugin_settings import SettingsError, read_hook_settings
from prompt_rewrite import (
    build_rewrite_prompt,
    contains_korean,
    is_gram_command,
    is_kor_command,
    rewrite_source,
    should_polish_english,
)

DEFAULT_MODEL: Final = _DEFAULT_MODEL
DEFAULT_EFFORT: Final = _DEFAULT_EFFORT


def resolve_cwd(raw_cwd: str) -> str | None:
    if Path(raw_cwd).is_dir():
        return raw_cwd
    return None


def parse_payload(raw: str) -> PromptParseResult:
    raw = raw.removeprefix("\ufeff")
    if raw.strip() == "":
        return PromptParseFailure(reason="hook input is empty")
    try:
        parsed = json.loads(raw, object_pairs_hook=json_object_pairs)
    except JSONDecodeError as exc:
        return PromptParseFailure(reason=f"hook input JSON is invalid: {exc}")
    if not isinstance(parsed, dict):
        return PromptParseFailure(reason="hook input JSON must be an object")
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
        return PromptParseFailure(reason="hook input prompt must be a string")
    if not isinstance(cwd, str):
        return PromptParseFailure(reason="hook input cwd must be a string")
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
    translation_prompt = build_rewrite_prompt(request.prompt)
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
    try:
        env = child_codex_env(os.environ)
    except OSError as exc:
        return TranslationFailure(reason=f"codex child home could not be prepared: {exc}")
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
    except PermissionError as exc:
        return TranslationFailure(
            reason=f"codex executable could not be started: {request.settings.codex_bin}: {exc}",
        )
    except subprocess.TimeoutExpired:
        return TranslationFailure(
            reason=f"codex translation timed out after {request.settings.timeout_seconds}s",
        )

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        return TranslationFailure(reason=f"codex exited {completed.returncode}: {detail}")
    english = clean_codex_stdout(completed.stdout).strip()
    if english == "":
        return TranslationFailure(reason="codex returned empty translation")
    return TranslationSuccess(
        english=english,
        engine=f"{request.settings.model}/{request.settings.effort}",
    )


def clean_codex_stdout(stdout: str) -> str:
    lines = [
        line
        for line in stdout.splitlines()
        if not (
            line.startswith("SUCCESS: The process with PID ")
            and line.endswith(" has been terminated.")
        )
    ]
    return "\n".join(lines)


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
        build_rewrite_prompt(prompt),
    ]


def translator_env(env: Mapping[str, str]) -> dict[str, str]:
    prepared = dict(env)
    prepared["CODEX_KOR_TO_ENG_DISABLED"] = "1"
    return prepared


def run_hook(raw: str, env: Mapping[str, str]) -> str:
    if env.get("CODEX_KOR_TO_ENG_DISABLED") == "1":
        return ""
    match parse_payload(raw):
        case PromptPayload() as payload:
            pass
        case PromptParseFailure(reason=reason):
            return format_preflight_failure(reason)
        case None:
            return ""
        case unreachable:
            assert_never(unreachable)
    manual_rewrite = (
        is_kor_command(payload.prompt) or is_gram_command(payload.prompt)
    ) and rewrite_source(payload.prompt) != ""
    if not (
        manual_rewrite
        or contains_korean(payload.prompt)
        or should_polish_english(payload.prompt)
    ):
        return ""
    try:
        settings = read_settings(env)
    except SettingsError as exc:
        settings_failure: TranslationResult = TranslationFailure(reason=str(exc))
        return format_hook_output(payload, settings_failure)
    if not settings.enabled and not manual_rewrite:
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
