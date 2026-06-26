from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "codex-kor-to-eng"
SCRIPT_DIR = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import install_plugin
from hook_trust import trusted_hook_states_for_plugin
from hook_types import JsonObject
from install_errors import InstallPluginError


def read_json_object(path: Path) -> JsonObject:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise AssertionError("expected JSON object")
    return parsed


def first_hook_handler(hooks_file: Path) -> JsonObject:
    hooks_manifest = read_json_object(hooks_file)
    hooks = hooks_manifest["hooks"]
    if not isinstance(hooks, dict):
        raise AssertionError("expected hooks object")
    groups = hooks["UserPromptSubmit"]
    if not isinstance(groups, list):
        raise AssertionError("expected UserPromptSubmit hook groups")
    group = groups[0]
    if not isinstance(group, dict):
        raise AssertionError("expected hook group object")
    handlers = group["hooks"]
    if not isinstance(handlers, list):
        raise AssertionError("expected hook handlers")
    handler = handlers[0]
    if not isinstance(handler, dict):
        raise AssertionError("expected hook handler object")
    return handler


def decode_encoded_command(command: str) -> str:
    parts = command.split()
    marker = "-EncodedCommand"
    if marker not in parts:
        raise AssertionError("missing -EncodedCommand")
    encoded = parts[parts.index(marker) + 1]
    return base64.b64decode(encoded).decode("utf-16le")


class InstallPluginTest(unittest.TestCase):
    def test_plugin_manifest_declares_hooks_file(self) -> None:
        manifest = read_json_object(PLUGIN_ROOT / ".codex-plugin" / "plugin.json")

        self.assertEqual(manifest["hooks"], "./hooks/hooks.json")

    def test_install_populates_cache_and_codex_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            codex_home = Path(temp_dir) / "codex-home"
            existing_config = codex_home / "config.toml"
            existing_config.parent.mkdir(parents=True)
            _ = existing_config.write_text(
                '[features]\nexisting = true\n\n[projects."keep"]\ntrusted = true\n',
                encoding="utf-8",
            )
            output = io.StringIO()
            manifest = read_json_object(PLUGIN_ROOT / ".codex-plugin" / "plugin.json")

            with contextlib.redirect_stdout(output):
                exit_code = install_plugin.main({"CODEX_HOME": str(codex_home)})

            cache_root = (
                codex_home
                / "plugins"
                / "cache"
                / "codex-kor-to-eng-local"
                / "codex-kor-to-eng"
                / str(manifest["version"])
            )
            config = existing_config.read_text(encoding="utf-8")
            cached_manifest = (cache_root / ".codex-plugin" / "plugin.json").is_file()
            cached_hooks = (cache_root / "hooks" / "hooks.json").is_file()
            installed_manifest = read_json_object(cache_root / ".codex-plugin" / "plugin.json")
            trusted_states = tuple(
                trusted_hook_states_for_plugin(
                    plugin_root=cache_root,
                    plugin_name=str(manifest["name"]),
                    marketplace_name=install_plugin.MARKETPLACE_NAME,
                    manifest=installed_manifest,
                ),
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue(cached_manifest)
        self.assertTrue(cached_hooks)
        self.assertIn("plugin_cache=ok", output.getvalue())
        self.assertEqual(len(trusted_states), 1)
        self.assertIn(f"trusted_hash={trusted_states[0].trusted_hash}", output.getvalue())
        self.assertIn("existing = true", config)
        self.assertIn('[projects."keep"]', config)
        self.assertIn("plugins = true", config)
        self.assertIn("plugin_hooks = true", config)
        self.assertIn("[marketplaces.codex-kor-to-eng-local]", config)
        self.assertIn('source_type = "local"', config)
        self.assertIn('[plugins."codex-kor-to-eng@codex-kor-to-eng-local"]', config)
        self.assertIn("enabled = true", config)
        self.assertIn(
            '[hooks.state."codex-kor-to-eng@codex-kor-to-eng-local:hooks/hooks.json:user_prompt_submit:0:0"]',
            config,
        )
        self.assertIn(f'trusted_hash = "{trusted_states[0].trusted_hash}"', config)

    def test_windows_install_rewrites_cached_hook_to_absolute_bootstrap(self) -> None:
        if os.name != "nt":
            self.skipTest("Windows cached hook rewrite only runs on Windows")

        with tempfile.TemporaryDirectory() as temp_dir:
            codex_home = Path(temp_dir) / "codex-home"

            result = install_plugin.install({"CODEX_HOME": str(codex_home)})

            cached_handler = first_hook_handler(result.cache_path / "hooks" / "hooks.json")
            expected_command = install_plugin.windows_powershell_file_command(
                result.cache_path / "scripts" / "bootstrap.ps1",
            )
            decoded_command = decode_encoded_command(expected_command)

        self.assertEqual(cached_handler["command"], expected_command)
        self.assertEqual(cached_handler["commandWindows"], expected_command)
        self.assertIn("-EncodedCommand", expected_command)
        expected_bootstrap = f"$bootstrap = '{result.cache_path}\\scripts\\bootstrap.ps1'"
        self.assertIn(expected_bootstrap, decoded_command)
        self.assertIn("[Console]::OpenStandardInput().CopyTo($inputMemory)", decoded_command)
        expected_stdin_write = (
            "$process.StandardInput.BaseStream.Write($inputBytes, 0, $inputBytes.Length)"
        )
        self.assertIn(expected_stdin_write, decoded_command)

    def test_windows_hook_command_treats_metacharacters_as_path_text(self) -> None:
        if os.name != "nt":
            self.skipTest("Windows PowerShell quoting only runs on Windows")

        with tempfile.TemporaryDirectory() as temp_dir:
            script_dir = Path(temp_dir) / "quote's $(Write-Output PWN)"
            script_dir.mkdir()
            script_path = script_dir / "safe.ps1"
            script = (
                "$memory = [System.IO.MemoryStream]::new()\n"
                "[Console]::OpenStandardInput().CopyTo($memory)\n"
                "$bytes = $memory.ToArray()\n"
                "$hasUtf8Bom = $false\n"
                "if ($bytes.Length -ge 3) {\n"
                "    $hasUtf8Bom = ($bytes[0] -eq 239)\n"
                "    $hasUtf8Bom = $hasUtf8Bom -and ($bytes[1] -eq 187)\n"
                "    $hasUtf8Bom = $hasUtf8Bom -and ($bytes[2] -eq 191)\n"
                "}\n"
                "if ($hasUtf8Bom -and $bytes.Length -gt 3) {\n"
                "    $bytes = $bytes[3..($bytes.Length - 1)]\n"
                "}\n"
                "$inputText = [System.Text.UTF8Encoding]::new($false)"
                ".GetString($bytes)\n"
                'Write-Output "SAFE:$inputText"'
            )
            _ = script_path.write_text(f"{script}\n", encoding="utf-8")
            command = install_plugin.windows_powershell_file_command(script_path)
            decoded_command = decode_encoded_command(command)

            completed = subprocess.run(  # noqa: S603 - generated command is the test subject.
                command.split(),
                check=False,
                capture_output=True,
                input="JSON:테스트".encode(),
            )

        stdout = completed.stdout.decode("utf-8")
        stderr = completed.stderr.decode("utf-8")
        self.assertEqual(completed.returncode, 0, stderr)
        self.assertEqual(stdout.strip(), "SAFE:JSON:테스트")
        self.assertNotIn("PWN", stdout)
        self.assertNotIn("PWN", stderr)
        self.assertNotIn("$(", command)
        self.assertNotIn("Write-Output", command)
        self.assertIn("quote''s", decoded_command)

    def test_rejects_hook_manifest_paths_outside_plugin_root(self) -> None:
        manifest: JsonObject = {
            "hooks": "../outside.json",
        }

        try:
            _ = trusted_hook_states_for_plugin(
                plugin_root=PLUGIN_ROOT,
                plugin_name="codex-kor-to-eng",
                marketplace_name=install_plugin.MARKETPLACE_NAME,
                manifest=manifest,
            )
        except InstallPluginError as exc:
            self.assertIn("escapes plugin root", str(exc))
        else:
            self.fail("expected InstallPluginError")

    def test_rejects_cache_root_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                _ = install_plugin.copy_plugin_to_cache(
                    plugin_root=PLUGIN_ROOT,
                    codex_home=Path(temp_dir),
                    plugin_name="codex-kor-to-eng",
                    version=".",
                )
            except InstallPluginError as exc:
                self.assertIn("outside plugin cache", str(exc))
            else:
                self.fail("expected InstallPluginError")

    def test_trusted_hash_matches_installed_cached_hook_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            codex_home = Path(temp_dir) / "codex-home"

            result = install_plugin.install({"CODEX_HOME": str(codex_home)})

            cached_manifest = read_json_object(result.cache_path / ".codex-plugin" / "plugin.json")
            cached_states = tuple(
                trusted_hook_states_for_plugin(
                    plugin_root=result.cache_path,
                    plugin_name=result.plugin_name,
                    marketplace_name=result.marketplace_name,
                    manifest=cached_manifest,
                ),
            )
            config = result.config_path.read_text(encoding="utf-8")

        self.assertEqual(result.trusted_hooks, cached_states)
        for state in cached_states:
            self.assertIn(f'trusted_hash = "{state.trusted_hash}"', config)


if __name__ == "__main__":
    _ = unittest.main()
