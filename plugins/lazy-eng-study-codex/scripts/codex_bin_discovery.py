from __future__ import annotations

import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

CodexBinSource: TypeAlias = Literal["configured", "path", "app_install", "fallback"]


@dataclass(frozen=True, slots=True)
class CodexBinResolution:
    path: str
    source: CodexBinSource
    ignored_configured_path: str | None


def read_codex_bin(env: Mapping[str, str]) -> str:
    return resolve_codex_bin(env).path


def resolve_codex_bin(env: Mapping[str, str]) -> CodexBinResolution:
    configured = empty_to_none(env.get("CODEX_KOR_TO_ENG_CODEX_BIN"))
    if (
        configured is not None
        and Path(configured).is_file()
        and not is_windowsapps_codex_bin(configured)
    ):
        return CodexBinResolution(
            path=str(Path(configured).resolve()),
            source="configured",
            ignored_configured_path=None,
        )
    ignored_configured_path = configured

    app_install = find_app_codex_bin(env)
    if app_install is not None:
        return CodexBinResolution(
            path=app_install,
            source="app_install",
            ignored_configured_path=ignored_configured_path,
        )

    discovered = shutil.which("codex", path=env.get("PATH"))
    if discovered is not None and not is_windowsapps_codex_bin(discovered):
        return CodexBinResolution(
            path=str(Path(discovered).resolve()),
            source="path",
            ignored_configured_path=ignored_configured_path,
        )

    return CodexBinResolution(
        path="codex",
        source="fallback",
        ignored_configured_path=ignored_configured_path,
    )


def find_app_codex_bin(env: Mapping[str, str]) -> str | None:
    windows = find_windows_codex_bin(env)
    if windows is not None:
        return windows
    return find_macos_codex_bin(env)


def find_windows_codex_bin(env: Mapping[str, str]) -> str | None:
    local_app_data = empty_to_none(env.get("LOCALAPPDATA"))
    if local_app_data is None:
        return None

    install_root = Path(local_app_data) / "OpenAI" / "Codex" / "bin"
    if not install_root.is_dir():
        return None

    stable_candidate = install_root / "codex.exe"
    if stable_candidate.is_file():
        return str(stable_candidate)

    for candidate in sorted(install_root.glob("*/codex.exe"), reverse=True):
        if candidate.is_file():
            return str(candidate)
    return None


def find_macos_codex_bin(env: Mapping[str, str]) -> str | None:
    home = empty_to_none(env.get("HOME"))
    if home is None:
        return None

    candidates = [
        Path(home)
        / "Library"
        / "Application Support"
        / "OpenAI"
        / "Codex"
        / "bin"
        / "codex",
        Path(home)
        / "Library"
        / "Application Support"
        / "Codex"
        / "bin"
        / "codex",
        Path("/Applications/Codex.app/Contents/MacOS/codex"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if stripped == "":
        return None
    return stripped


def is_windowsapps_codex_bin(path: str) -> bool:
    parts = {part.lower() for part in Path(path).parts}
    return "windowsapps" in parts and Path(path).name.lower() == "codex.exe"
