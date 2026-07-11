from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping, Sequence
from typing import assert_never

from codex_bin_discovery import resolve_codex_bin
from plugin_settings import (
    MODEL_CHOICES,
    SettingsError,
    load_settings_map,
    read_hook_settings,
    read_text,
    resolve_model_choice,
    save_settings_map,
    settings_file_path,
)

HOOK_SCOPE = "loaded_codex_sessions"
HOOK_RELOAD_NOTE = (
    "Loaded Codex sessions read on/off settings every time the hook runs. "
    "Changes apply after the settings file is saved; restart or reopen Codex only if "
    "the UserPromptSubmit hook itself was not loaded."
)


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    active_env = os.environ if env is None else env
    command = args[0] if args else "status"

    try:
        if command == "status":
            return show_status(active_env)
        if command in {"on", "enable"}:
            return set_enabled(active_env, enabled=True)
        if command in {"off", "disable"}:
            return set_enabled(active_env, enabled=False)
        if command == "model":
            return set_model(active_env, args[1:])
        if command in {"codex-bin", "save-codex-bin", "bin", "path"}:
            return save_codex_bin(active_env)
        if command in {"help", "--help", "-h"}:
            return show_usage()
        _ = sys.stdout.write(f"unknown command: {command}\n")
        return show_usage(exit_code=2)
    except SettingsError as exc:
        _ = sys.stdout.write(f"error: {exc}\n")
        return 2


def show_status(env: Mapping[str, str]) -> int:
    settings = read_hook_settings(env)
    resolution_env = dict(env)
    stored_codex_bin = read_text(load_settings_map(env), "codex_bin")
    if stored_codex_bin is not None:
        resolution_env["CODEX_KOR_TO_ENG_CODEX_BIN"] = stored_codex_bin
    resolution = resolve_codex_bin(resolution_env)
    codex_found = resolution.source != "fallback"
    _ = sys.stdout.write(f"settings_file={settings_file_path(env)}\n")
    _ = sys.stdout.write(f"enabled={json.dumps(settings.enabled)}\n")
    _ = sys.stdout.write(f"model={settings.model}\n")
    _ = sys.stdout.write(f"effort={settings.effort}\n")
    _ = sys.stdout.write(f"timeout_seconds={settings.timeout_seconds}\n")
    _ = sys.stdout.write(f"codex_bin={settings.codex_bin}\n")
    _ = sys.stdout.write(f"codex_bin_source={resolution.source}\n")
    _ = sys.stdout.write(f"codex_found={json.dumps(codex_found)}\n")
    _ = sys.stdout.write(f"hook_scope={HOOK_SCOPE}\n")
    _ = sys.stdout.write(f"hook_reload_note={HOOK_RELOAD_NOTE}\n")
    if not codex_found:
        _ = sys.stdout.write("codex executable was not found.\n")
    return 0


def set_enabled(env: Mapping[str, str], *, enabled: bool) -> int:
    settings = load_settings_map(env)
    settings["enabled"] = enabled
    path = save_settings_map(env, settings)
    state = "on" if enabled else "off"
    _ = sys.stdout.write(f"translation={state}\n")
    _ = sys.stdout.write(f"settings_file={path}\n")
    _ = sys.stdout.write(f"hook_scope={HOOK_SCOPE}\n")
    _ = sys.stdout.write(f"hook_reload_note={HOOK_RELOAD_NOTE}\n")
    return 0


def set_model(env: Mapping[str, str], args: Sequence[str]) -> int:
    if len(args) != 1:
        _ = sys.stdout.write("missing model. Use one of: spark, gpt55\n")
        return 2

    choice = resolve_model_choice(args[0])
    settings = load_settings_map(env)
    settings["model"] = choice.model
    settings["timeout_seconds"] = choice.timeout_seconds
    path = save_settings_map(env, settings)
    _ = sys.stdout.write(f"model={choice.model}\n")
    _ = sys.stdout.write(f"timeout_seconds={choice.timeout_seconds}\n")
    _ = sys.stdout.write(f"settings_file={path}\n")
    return 0


def save_codex_bin(env: Mapping[str, str]) -> int:
    resolution = resolve_codex_bin(env)
    if resolution.ignored_configured_path is not None:
        _ = sys.stdout.write(
            f"ignored missing CODEX_KOR_TO_ENG_CODEX_BIN={resolution.ignored_configured_path}\n",
        )

    match resolution.source:
        case "fallback":
            _ = sys.stdout.write("codex executable was not found.\n")
            return 1
        case "configured" | "path" | "app_install":
            settings = load_settings_map(env)
            settings["codex_bin"] = resolution.path
            path = save_settings_map(env, settings)
            _ = sys.stdout.write(f"codex_bin={resolution.path}\n")
            _ = sys.stdout.write(f"source={resolution.source}\n")
            _ = sys.stdout.write(f"settings_file={path}\n")
            return 0
        case unreachable:
            assert_never(unreachable)


def show_usage(*, exit_code: int = 0) -> int:
    models = ", ".join(MODEL_CHOICES)
    usage = "usage: kortoeng_control.py status|on|off|model <spark|gpt55>|codex-bin\n"
    _ = sys.stdout.write(usage)
    _ = sys.stdout.write(f"models: spark, gpt55, {models}\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
