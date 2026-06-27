from __future__ import annotations

from typing import Final

HANGUL_START: Final = ord("\uac00")
HANGUL_END: Final = ord("\ud7a3")
WORD_EDGE_CHARS: Final = ".,!?;:\"'`()[]{}<>"
GRAM_COMMAND: Final = "$gram"
ENGLISH_POLISH_MARKERS: Final[tuple[str, ...]] = (
    "already installed already",
    "can repo install",
    "people use level",
    "awkward sentence fixing is okay",
    "with kor plz",
    "plz",
    "pls",
    "wanna",
    "gonna",
)


def contains_korean(text: str) -> bool:
    return any(HANGUL_START <= ord(char) <= HANGUL_END for char in text)


def gram_command_text(text: str) -> str | None:
    stripped = text.strip()
    lowered = stripped.lower()
    if lowered == GRAM_COMMAND:
        return ""
    if not lowered.startswith(f"{GRAM_COMMAND} "):
        return None
    return stripped[len(GRAM_COMMAND) :].strip()


def is_gram_command(text: str) -> bool:
    return gram_command_text(text) is not None


def rewrite_source(text: str) -> str:
    command_text = gram_command_text(text)
    if command_text is not None:
        return command_text
    return text


def should_polish_english(text: str) -> bool:
    command_text = gram_command_text(text)
    if command_text is not None:
        return command_text != ""
    if not contains_ascii_letter(text):
        return False
    normalized = " ".join(text.lower().split())
    if any(marker in normalized for marker in ENGLISH_POLISH_MARKERS):
        return True
    return has_repeated_adjacent_word(text)


def contains_ascii_letter(text: str) -> bool:
    return any("a" <= char.lower() <= "z" for char in text)


def has_repeated_adjacent_word(text: str) -> bool:
    previous = ""
    for word in normalized_english_words(text):
        if word == previous:
            return True
        previous = word
    return False


def normalized_english_words(text: str) -> list[str]:
    words: list[str] = []
    for raw_word in text.split():
        word = raw_word.strip(WORD_EDGE_CHARS).lower()
        if word != "" and contains_ascii_letter(word):
            words.append(word)
    return words


def build_rewrite_prompt(prompt: str) -> str:
    source = rewrite_source(prompt)
    if contains_korean(source):
        return build_translation_prompt(source)
    return build_english_polish_prompt(source)


def build_translation_prompt(prompt: str) -> str:
    return f"""Translate the following Korean Codex user request into natural English.
Output only the English translation. Do not add markdown or commentary.
Preserve file paths, commands, code, URLs, IDs, and @mentions exactly.

Korean request:
{prompt}"""


def build_english_polish_prompt(prompt: str) -> str:
    return f"""Rewrite the following English Codex user request into natural English.
Output only the corrected English request. Do not add markdown or commentary.
Preserve file paths, commands, code, URLs, IDs, and @mentions exactly.
Do not change the user's intent.

English request:
{prompt}"""
