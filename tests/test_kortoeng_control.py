from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from collections.abc import Mapping, Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "plugins" / "codex-kor-to-eng" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import kor_to_eng_hook as hook
import kortoeng_control as control
from hook_types import JsonObject


def parse_json_object(raw: str) -> JsonObject:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise AssertionError("expected JSON object")
    return parsed


def run_control(args: Sequence[str], env: Mapping[str, str]) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exit_code = control.main(args, env)
    return exit_code, output.getvalue()


def read_settings(path: Path) -> JsonObject:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise AssertionError("expected JSON object")
    return parsed


class KortoengControlTest(unittest.TestCase):
    def test_control_commands_write_settings_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings_path = root / "settings.json"
            fake_codex = root / ("codex.exe" if os.name == "nt" else "codex")
            _ = fake_codex.write_text("", encoding="utf-8")
            fake_codex.chmod(0o755)
            env = {
                "CODEX_KOR_TO_ENG_SETTINGS_FILE": str(settings_path),
                "PATH": str(root),
            }

            off_exit, off_output = run_control(["off"], env)
            on_exit, on_output = run_control(["on"], env)
            model_exit, model_output = run_control(["model", "mini"], env)
            bin_exit, bin_output = run_control(["codex-bin"], env)
            settings = read_settings(settings_path)
        self.assertEqual(off_exit, 0)
        self.assertEqual(on_exit, 0)
        self.assertEqual(model_exit, 0)
        self.assertEqual(bin_exit, 0)
        self.assertIn("translation=off", off_output)
        self.assertIn("translation=on", on_output)
        self.assertIn("model=gpt-5.4-mini", model_output)
        self.assertIn("codex_bin=", bin_output)
        self.assertEqual(settings["enabled"], True)
        self.assertEqual(settings["model"], "gpt-5.4-mini")
        self.assertEqual(settings["timeout_seconds"], 45)
        self.assertIn("codex", str(settings["codex_bin"]).lower())

    def test_status_reports_when_codex_is_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            env = {
                "CODEX_KOR_TO_ENG_SETTINGS_FILE": str(settings_path),
                "PATH": "",
            }

            exit_code, output = run_control(["status"], env)

        self.assertEqual(exit_code, 0)
        self.assertIn("codex_bin_source=fallback", output)
        self.assertIn("codex_found=false", output)
        self.assertIn("codex executable was not found.", output)

    def test_codex_bin_saves_absolute_configured_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings_path = root / "settings.json"
            bin_dir = root / "bin"
            bin_dir.mkdir()
            fake_codex = bin_dir / "codex.exe"
            _ = fake_codex.write_text("", encoding="utf-8")
            env = {
                "CODEX_KOR_TO_ENG_SETTINGS_FILE": str(settings_path),
                "CODEX_KOR_TO_ENG_CODEX_BIN": str(fake_codex.relative_to(root)),
                "PATH": "",
            }
            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                exit_code, output = run_control(["codex-bin"], env)
            finally:
                os.chdir(old_cwd)
            settings = read_settings(settings_path)

        self.assertEqual(exit_code, 0)
        self.assertIn("source=configured", output)
        self.assertEqual(settings["codex_bin"], str(fake_codex.resolve()))

    def test_status_uses_saved_codex_bin_when_live_lookup_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings_path = root / "settings.json"
            fake_codex = root / "saved" / "codex.exe"
            fake_codex.parent.mkdir()
            _ = fake_codex.write_text("", encoding="utf-8")
            _ = settings_path.write_text(
                json.dumps({"codex_bin": str(fake_codex)}),
                encoding="utf-8",
            )
            env = {
                "CODEX_KOR_TO_ENG_SETTINGS_FILE": str(settings_path),
                "LOCALAPPDATA": str(root / "empty-localappdata"),
                "PATH": "",
            }

            exit_code, output = run_control(["status"], env)

        self.assertEqual(exit_code, 0)
        self.assertIn("codex_bin_source=configured", output)
        self.assertIn("codex_found=true", output)
        self.assertNotIn("codex executable was not found.", output)

    def test_invalid_model_does_not_corrupt_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            _ = settings_path.write_text('{"enabled": true}\n', encoding="utf-8")
            env = {"CODEX_KOR_TO_ENG_SETTINGS_FILE": str(settings_path)}

            exit_code, output = run_control(["model", "unknown"], env)
            settings = read_settings(settings_path)

        self.assertEqual(exit_code, 2)
        self.assertIn("unknown model", output)
        self.assertEqual(settings, {"enabled": True})

    def test_disabled_settings_make_hook_output_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            _ = settings_path.write_text('{"enabled": false}\n', encoding="utf-8")
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "테스트 스레드 상태 확인해줘",
                "cwd": temp_dir,
            }
            env = {"CODEX_KOR_TO_ENG_SETTINGS_FILE": str(settings_path)}

            output = hook.run_hook(json.dumps(payload), env)

        self.assertEqual(output, "")

    def test_invalid_settings_json_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            _ = settings_path.write_text("{not json", encoding="utf-8")
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "테스트 스레드 상태 확인해줘",
                "cwd": temp_dir,
            }
            env = {"CODEX_KOR_TO_ENG_SETTINGS_FILE": str(settings_path)}

            output = hook.run_hook(json.dumps(payload), env)

        parsed = parse_json_object(output)
        self.assertIn("translation failed", str(parsed["systemMessage"]))
        self.assertIn("settings file is invalid JSON", output)


if __name__ == "__main__":
    _ = unittest.main()
