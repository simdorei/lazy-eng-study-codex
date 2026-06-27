from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "plugins" / "codex-kor-to-eng" / "scripts"
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
    def test_gram_command_corrects_sentence_and_strips_command_prefix(self) -> None:
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
        self.assertTrue(parsed["systemMessage"].startswith("\uad50\uc815: Is number 2"))
        self.assertIn("$gram grammar correction command is active.", context)
        self.assertIn("Treat the corrected English prompt as the primary user request.", context)
        self.assertNotIn("Answer with that exact correction line.", context)
        self.assertIn("is number2 implimented now?", context)
        self.assertNotIn("$gram is number2", context)


if __name__ == "__main__":
    _ = unittest.main()
