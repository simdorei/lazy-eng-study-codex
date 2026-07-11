from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Final

from codex_bin_discovery import empty_to_none, read_codex_bin
from hook_types import HookSettings, JsonObject, JsonValue

DEFAULT_MODEL: Final = "gpt-5.5"
DEFAULT_EFFORT: Final = "medium"
DEFAULT_TIMEOUT_SECONDS: Final = 90
SETTINGS_FILE_ENV: Final = "CODEX_KOR_TO_ENG_SETTINGS_FILE"


class SettingsError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ModelChoice:
    model: str
    timeout_seconds: int


MODEL_CHOICES: Final[dict[str, ModelChoice]] = {
    "gpt-5.3-codex-spark": ModelChoice(model="gpt-5.3-codex-spark", timeout_seconds=90),
    "gpt-5.5": ModelChoice(model="gpt-5.5", timeout_seconds=90),
}
MODEL_ALIASES: Final[dict[str, str]] = {
    "spark": "gpt-5.3-codex-spark",
    "gpt55": "gpt-5.5",
}


def read_hook_settings(env: Mapping[str, str]) -> HookSettings:
    stored = load_settings_map(env)
    codex_env = dict(env)
    stored_codex_bin = read_text(stored, "codex_bin")
    if stored_codex_bin is not None:
        codex_env["CODEX_KOR_TO_ENG_CODEX_BIN"] = stored_codex_bin

    return HookSettings(
        enabled=read_bool(stored, "enabled", default=True),
        custom_command=empty_to_none(env.get("CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND")),
        codex_bin=read_codex_bin(codex_env),
        model=resolve_model_choice(
            read_text(stored, "model") or env.get("CODEX_KOR_TO_ENG_MODEL", DEFAULT_MODEL),
        ).model,
        effort=read_text(stored, "effort") or env.get("CODEX_KOR_TO_ENG_EFFORT", DEFAULT_EFFORT),
        timeout_seconds=read_timeout_seconds(stored, env),
    )


def read_timeout_seconds(stored: Mapping[str, JsonValue], env: Mapping[str, str]) -> int:
    stored_value = read_int(stored, "timeout_seconds")
    if stored_value is not None:
        if stored_value < 1:
            raise SettingsError("timeout_seconds must be at least 1")
        return stored_value

    raw = env.get("CODEX_KOR_TO_ENG_TIMEOUT_SECONDS")
    if raw is None:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        parsed = int(raw)
    except ValueError:
        raise SettingsError(
            "CODEX_KOR_TO_ENG_TIMEOUT_SECONDS must be a positive integer",
        ) from None
    if parsed < 1:
        raise SettingsError("CODEX_KOR_TO_ENG_TIMEOUT_SECONDS must be a positive integer")
    return parsed


def load_settings_map(env: Mapping[str, str]) -> JsonObject:
    path = settings_file_path(env)
    if not path.is_file():
        return {}

    try:
        parsed = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=json_object_pairs)
    except JSONDecodeError as exc:
        raise SettingsError(f"settings file is invalid JSON: {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SettingsError(f"settings file must contain a JSON object: {path}")
    normalized: JsonObject = {}
    for key, item in parsed.items():
        if isinstance(key, str):
            normalized[key] = item
    return normalized


def save_settings_map(env: Mapping[str, str], settings: Mapping[str, JsonValue]) -> Path:
    path = settings_file_path(env)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(settings, ensure_ascii=False, indent=2, sort_keys=True)
    _ = path.write_text(f"{payload}\n", encoding="utf-8")
    return path


def settings_file_path(env: Mapping[str, str]) -> Path:
    configured = empty_to_none(env.get(SETTINGS_FILE_ENV))
    if configured is not None:
        return Path(configured)

    codex_home = empty_to_none(env.get("CODEX_HOME"))
    if codex_home is not None:
        return Path(codex_home) / "lazy-eng-study-codex-settings.json"

    home = empty_to_none(env.get("USERPROFILE")) or empty_to_none(env.get("HOME"))
    if home is not None:
        return Path(home) / ".codex" / "lazy-eng-study-codex-settings.json"

    return Path.home() / ".codex" / "lazy-eng-study-codex-settings.json"


def resolve_model_choice(raw: str) -> ModelChoice:
    key = raw.strip()
    model = MODEL_ALIASES.get(key, key)
    choice = MODEL_CHOICES.get(model)
    if choice is None:
        supported = ", ".join([*MODEL_ALIASES, *MODEL_CHOICES])
        raise SettingsError(f"unknown model '{raw}'. Supported values: {supported}")
    return choice


def read_bool(settings: Mapping[str, JsonValue], key: str, *, default: bool) -> bool:
    value = settings.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise SettingsError(f"{key} must be true or false")


def read_text(settings: Mapping[str, JsonValue], key: str) -> str | None:
    value = settings.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return empty_to_none(value)
    raise SettingsError(f"{key} must be a string")


def read_int(settings: Mapping[str, JsonValue], key: str) -> int | None:
    value = settings.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        raise SettingsError(f"{key} must be a number")
    if isinstance(value, int):
        return value
    raise SettingsError(f"{key} must be a number")


def json_object_pairs(pairs: list[tuple[str, JsonValue]]) -> JsonObject:
    return dict(pairs)
