from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "plugins" / "lazy-eng-study-codex" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import kor_to_eng_hook as hook


def isolated_env(settings_path: Path) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("CODEX_KOR_TO_ENG_")
    }
    env["CODEX_KOR_TO_ENG_SETTINGS_FILE"] = str(settings_path)
    return env


class GramHookTest(unittest.TestCase):
    def test_malformed_hook_json_returns_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = hook.run_hook(
                '{"hook_event_name":"UserPromptSubmit","prompt":',
                isolated_env(Path(temp_dir) / "settings.json"),
            )

        self.assertNotEqual(output, "", "malformed JSON should return structured failure output")
        parsed = json.loads(output)
        hook_output = parsed["hookSpecificOutput"]
        context = hook_output["additionalContext"]
        self.assertIn("hook input JSON is invalid", parsed["systemMessage"])
        self.assertIn("hook input JSON is invalid", context)

    def test_gram_command_shows_understood_request_in_visible_correction_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_translator = Path(temp_dir) / "fake_translator.py"
            fake_script_lines = (
                "import sys",
                "text = sys.stdin.read()",
                "if '$gram' in text:",
                "    raise SystemExit(7)",
                "print('Is number 2 implemented now?')",
            )
            fake_script = "\n".join(fake_script_lines) + "\n"
            _ = fake_translator.write_text(
                fake_script,
                encoding="utf-8",
            )
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "$gram is number2 implimented now?",
                "cwd": temp_dir,
            }
            env = isolated_env(Path(temp_dir) / "settings.json")
            env["CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND"] = f'py -3 "{fake_translator}"'

            output = hook.run_hook(json.dumps(payload), env)

        parsed = json.loads(output)
        hook_output = parsed["hookSpecificOutput"]
        context = hook_output["additionalContext"]
        self.assertEqual(hook_output["hookEventName"], "UserPromptSubmit")
        self.assertTrue(
            parsed["systemMessage"].startswith("\uad50\uc815: Is number 2 implemented now?"),
        )
        visible_line = "교정: Is number 2 implemented now?"
        expected_visible_line = (
            "Start only the first visible assistant message in this turn "
            f"with this exact line: {visible_line}"
        )
        self.assertIn(expected_visible_line, context)
        self.assertIn("Do not repeat that exact line in later assistant messages for this turn.", context)
        self.assertIn("Treat the visible correction line as the primary user request.", context)
        self.assertIn("Original English:", context)

    def test_gram_command_runs_when_translation_setting_is_off(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_translator = Path(temp_dir) / "fake_translator.py"
            fake_script = "import sys\n_ = sys.stdin.read()\nprint('Show what you understand.')\n"
            _ = fake_translator.write_text(fake_script, encoding="utf-8")
            settings_path = Path(temp_dir) / "settings.json"
            _ = settings_path.write_text('{"enabled": false}\n', encoding="utf-8")
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "$gram show what u understand",
                "cwd": temp_dir,
            }
            env = isolated_env(settings_path)
            env["CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND"] = f'py -3 "{fake_translator}"'

            output = hook.run_hook(json.dumps(payload), env)

        parsed = json.loads(output)
        self.assertTrue(
            parsed["systemMessage"].startswith("\uad50\uc815: Show what you understand."),
        )


if __name__ == "__main__":
    _ = unittest.main()
