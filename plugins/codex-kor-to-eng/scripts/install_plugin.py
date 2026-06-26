from __future__ import annotations

import base64
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from codex_config import update_codex_config
from hook_trust import (
    hook_manifest_paths,
    read_json_object,
    resolve_hook_manifest_path,
    trusted_hook_states_for_plugin,
)
from install_errors import InstallPluginError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from hook_trust import TrustedHookState
    from hook_types import JsonObject, JsonValue

MARKETPLACE_NAME: Final = "codex-kor-to-eng-local"


@dataclass(frozen=True, slots=True)
class InstallResult:
    marketplace_name: str
    plugin_name: str
    version: str
    cache_path: Path
    config_path: Path
    trusted_hooks: tuple[TrustedHookState, ...]


def main(env: Mapping[str, str] | None = None) -> int:
    active_env = os.environ if env is None else env
    try:
        result = install(active_env)
    except InstallPluginError as exc:
        _ = sys.stderr.write(f"error: {exc}\n")
        return 2

    _ = sys.stdout.write(f"marketplace={result.marketplace_name}\n")
    _ = sys.stdout.write(f"plugin={result.plugin_name}\n")
    _ = sys.stdout.write(f"version={result.version}\n")
    _ = sys.stdout.write(f"cache_path={result.cache_path}\n")
    _ = sys.stdout.write(f"config_path={result.config_path}\n")
    for state in result.trusted_hooks:
        _ = sys.stdout.write(f"trusted_hook={state.key}\n")
        _ = sys.stdout.write(f"trusted_hash={state.trusted_hash}\n")
    _ = sys.stdout.write("plugin_cache=ok\n")
    return 0


def install(env: Mapping[str, str]) -> InstallResult:
    script_dir = Path(__file__).resolve().parent
    plugin_root = script_dir.parent
    manifest = read_json_object(plugin_root / ".codex-plugin" / "plugin.json")
    plugin_name = required_string(manifest, "name")
    version = required_string(manifest, "version")
    source_root = marketplace_source_root(plugin_root)
    codex_home = codex_home_path(env)
    cache_path = copy_plugin_to_cache(
        plugin_root=plugin_root,
        codex_home=codex_home,
        plugin_name=plugin_name,
        version=version,
    )
    prepare_cached_hooks(cache_path=cache_path, manifest=manifest)
    cached_manifest = read_json_object(cache_path / ".codex-plugin" / "plugin.json")
    trusted_hooks = tuple(
        trusted_hook_states_for_plugin(
            plugin_root=cache_path,
            plugin_name=plugin_name,
            marketplace_name=MARKETPLACE_NAME,
            manifest=cached_manifest,
        ),
    )
    config_path = codex_home / "config.toml"
    update_codex_config(
        config_path=config_path,
        source_root=source_root,
        marketplace_name=MARKETPLACE_NAME,
        plugin_name=plugin_name,
        trusted_hooks=trusted_hooks,
    )
    return InstallResult(
        marketplace_name=MARKETPLACE_NAME,
        plugin_name=plugin_name,
        version=version,
        cache_path=cache_path,
        config_path=config_path,
        trusted_hooks=trusted_hooks,
    )


def prepare_cached_hooks(*, cache_path: Path, manifest: JsonObject) -> None:
    if os.name != "nt":
        return
    command = windows_powershell_file_command(cache_path / "scripts" / "bootstrap.ps1")
    for hook_path in hook_manifest_paths(manifest.get("hooks")):
        rewrite_cached_hook_file(resolve_hook_manifest_path(cache_path, hook_path), command)


def windows_powershell_file_command(script_path: Path) -> str:
    script = "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            "$ProgressPreference = 'SilentlyContinue'",
            f"$bootstrap = {powershell_single_quoted(script_path)}",
            "$inputMemory = [System.IO.MemoryStream]::new()",
            "[Console]::OpenStandardInput().CopyTo($inputMemory)",
            (
                "$powershell = Join-Path $env:SystemRoot "
                "'System32\\WindowsPowerShell\\v1.0\\powershell.exe'"
            ),
            "if (-not (Test-Path -LiteralPath $powershell)) { $powershell = 'powershell' }",
            "$process = [System.Diagnostics.Process]::new()",
            "$process.StartInfo.FileName = $powershell",
            (
                "$process.StartInfo.Arguments = '-NoProfile -ExecutionPolicy "
                "Bypass -File \"' + $bootstrap + '\"'"
            ),
            "$process.StartInfo.UseShellExecute = $false",
            "$process.StartInfo.RedirectStandardInput = $true",
            "$process.StartInfo.RedirectStandardOutput = $true",
            "$process.StartInfo.RedirectStandardError = $true",
            "$process.StartInfo.StandardOutputEncoding = [System.Text.UTF8Encoding]::new($false)",
            "$process.StartInfo.StandardErrorEncoding = [System.Text.UTF8Encoding]::new($false)",
            "$null = $process.Start()",
            "$inputBytes = $inputMemory.ToArray()",
            "$hasUtf8Bom = $false",
            "if ($inputBytes.Length -ge 3) {",
            "    $hasUtf8Bom = ($inputBytes[0] -eq 239)",
            "    $hasUtf8Bom = $hasUtf8Bom -and ($inputBytes[1] -eq 187)",
            "    $hasUtf8Bom = $hasUtf8Bom -and ($inputBytes[2] -eq 191)",
            "}",
            "if ($hasUtf8Bom -and $inputBytes.Length -eq 3) {",
            "    $inputBytes = [byte[]]::new(0)",
            "} elseif ($hasUtf8Bom) {",
            "    $inputBytes = $inputBytes[3..($inputBytes.Length - 1)]",
            "}",
            "$process.StandardInput.BaseStream.Write($inputBytes, 0, $inputBytes.Length)",
            "$process.StandardInput.BaseStream.Close()",
            "$stdout = $process.StandardOutput.ReadToEnd()",
            "$stderr = $process.StandardError.ReadToEnd()",
            "$process.WaitForExit()",
            "[Console]::Out.Write($stdout)",
            "[Console]::Error.Write($stderr)",
            "exit $process.ExitCode",
        ],
    )
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return f"powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}"


def powershell_single_quoted(value: Path | str) -> str:
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def rewrite_cached_hook_file(hooks_file: Path, command: str) -> None:
    hooks_manifest = read_json_object(hooks_file)
    hooks = hooks_manifest.get("hooks")
    if not isinstance(hooks, dict):
        msg = f"hooks file must contain a hooks object: {hooks_file}"
        raise InstallPluginError(msg)
    for groups in hooks.values():
        rewrite_hook_groups(groups, command)
    _ = hooks_file.write_text(
        f"{json.dumps(hooks_manifest, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )


def rewrite_hook_groups(groups: JsonValue, command: str) -> None:
    if not isinstance(groups, list):
        return
    for group in groups:
        if not isinstance(group, dict):
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            continue
        for handler in handlers:
            rewrite_command_handler(handler, command)


def rewrite_command_handler(handler: JsonValue, command: str) -> None:
    if not isinstance(handler, dict) or handler.get("type") != "command":
        return
    handler["command"] = command
    handler["commandWindows"] = command


def codex_home_path(env: Mapping[str, str]) -> Path:
    configured = non_empty(env.get("CODEX_HOME"))
    if configured is not None:
        return Path(configured).expanduser()

    home = non_empty(env.get("USERPROFILE")) or non_empty(env.get("HOME"))
    if home is not None:
        return Path(home).expanduser() / ".codex"

    return Path.home() / ".codex"


def marketplace_source_root(plugin_root: Path) -> Path:
    if plugin_root.parent.name == "plugins":
        return plugin_root.parent.parent
    return plugin_root


def copy_plugin_to_cache(
    *,
    plugin_root: Path,
    codex_home: Path,
    plugin_name: str,
    version: str,
) -> Path:
    cache_base = codex_home / "plugins" / "cache" / MARKETPLACE_NAME / plugin_name
    target = cache_base / version
    ensure_path_inside(target, cache_base)
    cache_base.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    _ = shutil.copytree(
        plugin_root,
        target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )
    return target


def ensure_path_inside(target: Path, base: Path) -> None:
    resolved_target = target.resolve()
    resolved_base = base.resolve()
    if resolved_target != resolved_base and resolved_target.is_relative_to(resolved_base):
        return
    msg = f"refusing to write outside plugin cache: {resolved_target}"
    raise InstallPluginError(msg)


def required_string(settings: Mapping[str, JsonValue], key: str) -> str:
    value = settings.get(key)
    if isinstance(value, str) and value.strip() != "":
        return value
    msg = f"plugin manifest must contain a non-empty string: {key}"
    raise InstallPluginError(msg)


def non_empty(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


if __name__ == "__main__":
    raise SystemExit(main())
