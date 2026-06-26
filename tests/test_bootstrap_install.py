from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "codex-kor-to-eng"
SCRIPT_DIR = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from hook_types import JsonObject, JsonValue


def clean_env(extra: Mapping[str, str]) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("CODEX_KOR_TO_ENG_")
    }
    env.update(extra)
    return env


def powershell_exe() -> str | None:
    return shutil.which("powershell") or shutil.which("pwsh")


def shell_exe() -> str | None:
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    return shutil.which("sh") or (str(git_bash) if git_bash.is_file() else None)


def read_json_object(path: Path) -> JsonObject:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise AssertionError("expected JSON object")
    normalized: JsonObject = {}
    for key, value in parsed.items():
        if isinstance(key, str):
            normalized[key] = value
    return normalized


def parse_json_object(raw: str) -> JsonObject:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise AssertionError("expected JSON object")
    normalized: JsonObject = {}
    for key, value in parsed.items():
        if isinstance(key, str):
            normalized[key] = value
    return normalized


class BootstrapInstallTest(unittest.TestCase):
    def test_hooks_json_uses_bootstrap_entrypoints(self) -> None:
        hooks = read_json_object(PLUGIN_ROOT / "hooks" / "hooks.json")
        serialized = json.dumps(hooks)
        command_windows = serialized.replace("\\\\", "\\")

        self.assertIn("bootstrap.sh", serialized)
        self.assertIn("bootstrap.ps1", serialized)
        self.assertIn("$env:PLUGIN_ROOT\\scripts\\bootstrap.ps1", command_windows)
        self.assertNotIn("kor_to_eng_hook.py", serialized)
        self.assertNotIn("py -3", serialized)
        self.assertNotIn("python3 ", serialized)

    def test_install_ps1_configures_plugin_with_configured_python(self) -> None:
        ps = powershell_exe()
        if ps is None:
            self.skipTest("PowerShell is not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            codex_home = root / "codex-home"
            settings_path = root / "settings.json"
            bin_dir = root / "bin"
            bin_dir.mkdir()
            fake_codex = bin_dir / "codex.cmd"
            _ = fake_codex.write_text("@echo off\r\necho fake codex\r\n", encoding="utf-8")
            env = clean_env(
                {
                    "CODEX_HOME": str(codex_home),
                    "CODEX_KOR_TO_ENG_SETTINGS_FILE": str(settings_path),
                    "CODEX_KOR_TO_ENG_PYTHON_BIN": sys.executable,
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                },
            )

            completed = subprocess.run(  # noqa: S603
                [
                    ps,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(REPO_ROOT / "install.ps1"),
                ],
                text=True,
                encoding="utf-8",
                capture_output=True,
                env=env,
                check=False,
            )

            settings = read_json_object(settings_path)

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertIn("python_source=configured", completed.stdout)
        self.assertIn("install=ok", completed.stdout)
        self.assertEqual(settings["enabled"], True)
        self.assertEqual(settings["model"], "gpt-5.4-mini")
        self.assertEqual(settings["timeout_seconds"], 45)
        self.assertIn("codex", str(settings["codex_bin"]).lower())

    def test_bootstrap_ps1_runs_hook_with_configured_python(self) -> None:
        ps = powershell_exe()
        if ps is None:
            self.skipTest("PowerShell is not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            translator = root / "translator.py"
            _ = translator.write_text(
                "import sys\nsys.stdin.read()\nprint('Check the translated prompt.')\n",
                encoding="utf-8",
            )
            payload: dict[str, JsonValue] = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "\ud14c\uc2a4\ud2b8 \uc0c1\ud0dc \ud655\uc778",
                "cwd": temp_dir,
            }
            env = clean_env(
                {
                    "CODEX_KOR_TO_ENG_SETTINGS_FILE": str(root / "settings.json"),
                    "CODEX_KOR_TO_ENG_PYTHON_BIN": sys.executable,
                    "CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND": (
                        f'"{sys.executable}" "{translator}"'
                    ),
                },
            )

            completed = subprocess.run(  # noqa: S603
                [
                    ps,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(SCRIPT_DIR / "bootstrap.ps1"),
                ],
                input=json.dumps(payload),
                text=True,
                encoding="utf-8",
                capture_output=True,
                env=env,
                check=False,
            )

        parsed = parse_json_object(completed.stdout)
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertIn("Check the translated prompt.", str(parsed))

    def test_bootstrap_sh_rejects_intel_macos(self) -> None:
        sh = shell_exe()
        if sh is None:
            self.skipTest("sh is not available")

        env = clean_env(
            {
                "CODEX_KOR_TO_ENG_BOOTSTRAP_FORCE_PORTABLE": "1",
                "CODEX_KOR_TO_ENG_TEST_OS": "Darwin",
                "CODEX_KOR_TO_ENG_TEST_ARCH": "x86_64",
            },
        )

        completed = subprocess.run(  # noqa: S603
            [sh, str(SCRIPT_DIR / "bootstrap.sh"), "--ensure-python"],
            text=True,
            encoding="utf-8",
            capture_output=True,
            env=env,
            check=False,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Intel macOS is not supported", completed.stderr)


if __name__ == "__main__":
    _ = unittest.main()
