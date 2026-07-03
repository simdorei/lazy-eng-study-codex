from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

CHILD_HOME_DIR: Final = "lazy-eng-study-codex"
CHILD_CODEX_HOME_DIR: Final = "codex-home"


def child_codex_env(env: Mapping[str, str]) -> dict[str, str]:
    prepared = dict(env)
    prepared["CODEX_KOR_TO_ENG_DISABLED"] = "1"
    prepared["CODEX_HOME"] = str(prepare_child_codex_home(env))
    return prepared


def prepare_child_codex_home(env: Mapping[str, str]) -> Path:
    parent = parent_codex_home(env)
    child = parent / CHILD_HOME_DIR / CHILD_CODEX_HOME_DIR
    child.mkdir(parents=True, exist_ok=True)
    _ = (child / "config.toml").write_text("", encoding="utf-8")

    auth_source = parent / "auth.json"
    if auth_source.is_file():
        _ = shutil.copy2(auth_source, child / "auth.json")
    return child


def parent_codex_home(env: Mapping[str, str]) -> Path:
    codex_home = non_empty_env(env, "CODEX_HOME")
    if codex_home is not None:
        return Path(codex_home)

    home = non_empty_env(env, "USERPROFILE") or non_empty_env(env, "HOME")
    if home is not None:
        return Path(home) / ".codex"

    return Path.home() / ".codex"


def non_empty_env(env: Mapping[str, str], key: str) -> str | None:
    value = env.get(key)
    if value is None or value.strip() == "":
        return None
    return value
