from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class PromptPayload:
    prompt: str
    cwd: str


@dataclass(frozen=True, slots=True)
class PromptParseFailure:
    reason: str


@dataclass(frozen=True, slots=True)
class HookSettings:
    enabled: bool
    custom_command: str | None
    codex_bin: str
    model: str
    effort: str
    timeout_seconds: int


@dataclass(frozen=True, slots=True)
class TranslationSuccess:
    english: str
    engine: str


@dataclass(frozen=True, slots=True)
class TranslationFailure:
    reason: str


@dataclass(frozen=True, slots=True)
class TranslationRequest:
    prompt: str
    settings: HookSettings
    cwd: str


TranslationResult = TranslationSuccess | TranslationFailure
PromptParseResult = PromptPayload | PromptParseFailure | None
