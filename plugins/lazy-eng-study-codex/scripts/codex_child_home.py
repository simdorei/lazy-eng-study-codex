from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

CHILD_HOME_DIR: Final = "lazy-eng-study-codex"
CHILD_CODEX_HOME_DIR: Final = "codex-home"
PASSTHROUGH_ENV_KEYS: Final[frozenset[str]] = frozenset(
    {
        "ALL_PROXY",
        "APPDATA",
        "COMSPEC",
        "CURL_CA_BUNDLE",
        "GIT_SSL_CAINFO",
        "HOME",
        "HOMEDRIVE",
        "HOMEPATH",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "LOCALAPPDATA",
        "NO_PROXY",
        "OS",
        "PATH",
        "PATHEXT",
        "PROGRAMDATA",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "PROGRAMW6432",
        "PYTHONHOME",
        "PYTHONIOENCODING",
        "PYTHONPATH",
        "PYTHONUTF8",
        "REQUESTS_CA_BUNDLE",
        "SHELL",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USERDOMAIN",
        "USERNAME",
        "USERPROFILE",
        "VIRTUAL_ENV",
        "WINDIR",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
    },
)
PASSTHROUGH_ENV_PREFIXES: Final[tuple[str, ...]] = (
    "ANTHROPIC_",
    "AZURE_OPENAI_",
    "OPENAI_",
)


def child_codex_env(env: Mapping[str, str]) -> dict[str, str]:
    prepared = passthrough_env(env)
    prepared["CODEX_KOR_TO_ENG_DISABLED"] = "1"
    prepared["CODEX_HOME"] = str(prepare_child_codex_home(env))
    return prepared


def passthrough_env(env: Mapping[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in env.items()
        if should_passthrough_env_key(key)
    }


def should_passthrough_env_key(key: str) -> bool:
    normalized = key.upper()
    if normalized in PASSTHROUGH_ENV_KEYS:
        return True
    return normalized.startswith(PASSTHROUGH_ENV_PREFIXES)


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
