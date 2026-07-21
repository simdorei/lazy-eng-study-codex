from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "plugins" / "lazy-eng-study-codex" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import kor_to_eng_hook as hook
from hook_output import format_hook_output
from hook_types import JsonObject, JsonValue, PromptPayload, TranslationSuccess


def isolated_env(settings_path: Path, extra: Mapping[str, str] | None = None) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("CODEX_KOR_TO_ENG_")
    }
    env["CODEX_KOR_TO_ENG_SETTINGS_FILE"] = str(settings_path)
    if extra is not None:
        env.update(extra)
    return env


def parse_json_object(raw: str) -> JsonObject:
    parsed = json.loads(raw, object_pairs_hook=json_object_pairs)
    if not isinstance(parsed, dict):
        raise AssertionError("expected JSON object")
    normalized: JsonObject = {}
    for key, item in parsed.items():
        if isinstance(key, str):
            normalized[key] = item
    return normalized


def json_object_pairs(pairs: list[tuple[str, JsonValue]]) -> JsonObject:
    return dict(pairs)


def get_value(value: Mapping[str, JsonValue], key: str) -> JsonValue:
    if key not in value:
        raise AssertionError(f"missing key: {key}")
    return value[key]


def get_text(value: Mapping[str, JsonValue], key: str) -> str:
    item = get_value(value, key)
    if not isinstance(item, str):
        raise AssertionError(f"expected text key: {key}")
    return item


def get_object_map(value: Mapping[str, JsonValue], key: str) -> JsonObject:
    item = get_value(value, key)
    if not isinstance(item, dict):
        raise AssertionError(f"expected object key: {key}")
    normalized: JsonObject = {}
    for nested_key, nested_item in item.items():
        normalized[nested_key] = nested_item
    return normalized


class KorToEngHookTest(unittest.TestCase):
    def test_success_context_omits_source_and_keeps_two_rewrite_copies(self) -> None:
        def context_for(source: str, english: str) -> str:
            output = format_hook_output(
                PromptPayload(prompt=source, cwd=str(REPO_ROOT)),
                TranslationSuccess(english=english, engine="test"),
            )
            parsed = parse_json_object(output)
            return get_text(get_object_map(parsed, "hookSpecificOutput"), "additionalContext")

        short_source_context = context_for("가", "x")
        long_source_context = context_for("가" * 200, "x")
        longer_rewrite_context = context_for("가", "xx")

        self.assertEqual(short_source_context, long_source_context)
        self.assertEqual(len(longer_rewrite_context) - len(short_source_context), 2)

    def test_adds_visible_english_context_when_korean_prompt_arrives(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_translator = Path(temp_dir) / "fake_translator.py"
            _ = fake_translator.write_text(
                "import sys\nsys.stdin.read()\nprint('Check the test thread status.')\n",
                encoding="utf-8",
            )
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "테스트 스레드 상태 확인해줘",
                "cwd": temp_dir,
                "session_id": "session-1",
            }
            env = {
                **isolated_env(Path(temp_dir) / "settings.json"),
                "CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND": f'py -3 "{fake_translator}"',
            }

            output = hook.run_hook(json.dumps(payload), env)

        parsed = parse_json_object(output)
        hook_output = get_object_map(parsed, "hookSpecificOutput")
        context = get_text(hook_output, "additionalContext")
        system_message = get_text(parsed, "systemMessage")
        self.assertEqual(get_text(hook_output, "hookEventName"), "UserPromptSubmit")
        self.assertTrue(system_message.startswith("\ubc88\uc5ed: Check the test thread status."))
        self.assertIn("(custom command)", system_message)
        visible_line = "번역: Check the test thread status."
        expected_visible_line = (
            "Start only the first visible assistant message in this turn "
            f"with this exact line: {visible_line}"
        )
        repeat_guard = "Do not repeat that exact line in later assistant messages for this turn."
        self.assertIn(expected_visible_line, context)
        self.assertIn(repeat_guard, context)
        self.assertIn("Treat the rewritten English prompt as the primary user request.", context)
        self.assertIn("Assistant-understood request: Check the test thread status.", context)

    def test_accepts_utf8_bom_prefixed_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_translator = Path(temp_dir) / "fake_translator.py"
            _ = fake_translator.write_text(
                "import sys\nsys.stdin.read()\nprint('Check the test thread status.')\n",
                encoding="utf-8",
            )
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "테스트 스레드 상태 확인해줘",
                "cwd": temp_dir,
                "session_id": "session-1",
            }
            env = {
                **isolated_env(Path(temp_dir) / "settings.json"),
                "CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND": f'py -3 "{fake_translator}"',
            }

            output = hook.run_hook(f"\ufeff{json.dumps(payload)}", env)

        parsed = parse_json_object(output)
        self.assertIn("Check the test thread status.", get_text(parsed, "systemMessage"))

    def test_custom_translator_receives_sanitized_child_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir) / ".codex"
            parent.mkdir()
            _ = (parent / "auth.json").write_text('{"token":"test"}\n', encoding="utf-8")
            _ = (parent / "config.toml").write_text(
                'service_tier = "anything"\n',
                encoding="utf-8",
            )
            fake_translator = Path(temp_dir) / "fake_translator.py"
            _ = fake_translator.write_text(
                (
                    "import os\n"
                    "import sys\n"
                    "from pathlib import Path\n"
                    "_ = sys.stdin.read()\n"
                    "if 'UNRELATED_PARENT_SETTING' in os.environ:\n"
                    "    raise SystemExit('unrelated env leaked')\n"
                    "if 'CODEX_SHOULD_NOT_LEAK' in os.environ:\n"
                    "    raise SystemExit('codex env leaked')\n"
                    "if os.environ.get('CODEX_KOR_TO_ENG_DISABLED') != '1':\n"
                    "    raise SystemExit('recursive guard missing')\n"
                    "codex_home = Path(os.environ['CODEX_HOME'])\n"
                    "if (codex_home / 'config.toml').read_text(encoding='utf-8') != '':\n"
                    "    raise SystemExit('parent config leaked')\n"
                    "print('Check the test thread status.')\n"
                ),
                encoding="utf-8",
            )
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "테스트 스레드 상태 확인해줘",
                "cwd": temp_dir,
                "session_id": "session-1",
            }
            env = {
                **isolated_env(Path(temp_dir) / "settings.json"),
                "CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND": f'py -3 "{fake_translator}"',
            }

            with patch.dict(
                os.environ,
                {
                    "CODEX_HOME": str(parent),
                    "CODEX_SHOULD_NOT_LEAK": "1",
                    "UNRELATED_PARENT_SETTING": "leak",
                },
                clear=False,
            ):
                output = hook.run_hook(json.dumps(payload), env)

        parsed = parse_json_object(output)
        self.assertIn("Check the test thread status.", get_text(parsed, "systemMessage"))

    def test_polishes_awkward_english_prompt_when_no_korean_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_translator = Path(temp_dir) / "fake_translator.py"
            _ = fake_translator.write_text(
                "import sys\nsys.stdin.read()\nprint('So sentence correction works, right?')\n",
                encoding="utf-8",
            )
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Then awkward sentence fixing is okay?",
                "cwd": temp_dir,
                "session_id": "session-1",
            }
            env = {
                **isolated_env(Path(temp_dir) / "settings.json"),
                "CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND": f'py -3 "{fake_translator}"',
            }

            output = hook.run_hook(json.dumps(payload), env)

        parsed = parse_json_object(output)
        context = get_text(get_object_map(parsed, "hookSpecificOutput"), "additionalContext")
        system_message = get_text(parsed, "systemMessage")
        self.assertTrue(system_message.startswith("\ubc88\uc5ed: So sentence correction works"))
        self.assertIn("So sentence correction works, right?", context)

    def test_returns_no_output_when_fluent_english_prompt_arrives(self) -> None:
        payload = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Check the test thread status.",
            "cwd": str(REPO_ROOT),
            "session_id": "session-1",
        }

        output = hook.run_hook(json.dumps(payload), os.environ)

        self.assertEqual(output, "")

    def test_kor_command_translates_once_when_translation_is_off(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            _ = settings_path.write_text('{"enabled": false}\n', encoding="utf-8")
            fake_translator = Path(temp_dir) / "fake_translator.py"
            _ = fake_translator.write_text(
                (
                    "import sys\n"
                    "prompt = sys.stdin.read()\n"
                    "if '$kor' in prompt:\n"
                    "    raise SystemExit(7)\n"
                    "print('Check the test thread status.')\n"
                ),
                encoding="utf-8",
            )
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": (
                    "$kor \ud14c\uc2a4\ud2b8 \uc2a4\ub808\ub4dc "
                    "\uc0c1\ud0dc \ud655\uc778\ud574\uc918"
                ),
                "cwd": temp_dir,
                "session_id": "session-1",
            }
            env = {
                **isolated_env(settings_path),
                "CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND": f'py -3 "{fake_translator}"',
            }

            output = hook.run_hook(json.dumps(payload, ensure_ascii=True), env)

        parsed = parse_json_object(output)
        hook_output = get_object_map(parsed, "hookSpecificOutput")
        self.assertEqual(get_text(hook_output, "hookEventName"), "UserPromptSubmit")
        self.assertTrue(
            get_text(parsed, "systemMessage").startswith(
                "\ubc88\uc5ed: Check the test thread status.",
            ),
        )

    def test_surfaces_translator_failure_instead_of_silent_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "테스트 스레드 상태 확인해줘",
                "cwd": temp_dir,
                "session_id": "session-1",
            }
            env = {
                **isolated_env(Path(temp_dir) / "settings.json"),
                "CODEX_KOR_TO_ENG_CODEX_BIN": "__missing_codex_binary__",
                "PATH": "",
            }
            _ = env.pop("LOCALAPPDATA", None)
            _ = env.pop("HOME", None)

            output = hook.run_hook(json.dumps(payload), env)

        parsed = parse_json_object(output)
        hook_output = get_object_map(parsed, "hookSpecificOutput")
        context = get_text(hook_output, "additionalContext")
        self.assertIn("translation failed", get_text(parsed, "systemMessage"))
        self.assertIn("codex executable", context)
        self.assertIn("테스트 스레드 상태 확인해줘", context)

    def test_surfaces_missing_cwd_instead_of_using_process_cwd(self) -> None:
        payload = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "테스트 스레드 상태 확인해줘",
            "cwd": "C:\\definitely\\missing\\lazy-eng-study-codex",
            "session_id": "session-1",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output = hook.run_hook(
                json.dumps(payload),
                isolated_env(Path(temp_dir) / "settings.json"),
            )

        parsed = parse_json_object(output)
        context = get_text(get_object_map(parsed, "hookSpecificOutput"), "additionalContext")
        self.assertIn("translation failed", get_text(parsed, "systemMessage"))
        self.assertIn("cwd is not a directory", context)

    def test_surfaces_file_cwd_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_cwd = Path(temp_dir) / "not-a-directory.txt"
            _ = file_cwd.write_text("not a directory", encoding="utf-8")
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "테스트 스레드 상태 확인해줘",
                "cwd": str(file_cwd),
                "session_id": "session-1",
            }

            output = hook.run_hook(
                json.dumps(payload),
                isolated_env(Path(temp_dir) / "settings.json"),
            )

        parsed = parse_json_object(output)
        context = get_text(get_object_map(parsed, "hookSpecificOutput"), "additionalContext")
        self.assertIn("translation failed", get_text(parsed, "systemMessage"))
        self.assertIn("cwd is not a directory", context)

    def test_disables_recursive_hook_when_child_codex_runs(self) -> None:
        payload = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "테스트 스레드 상태 확인해줘",
            "cwd": str(REPO_ROOT),
            "session_id": "session-1",
        }
        env = {**os.environ, "CODEX_KOR_TO_ENG_DISABLED": "1"}

        output = hook.run_hook(json.dumps(payload), env)

        self.assertEqual(output, "")

if __name__ == "__main__":
    _ = unittest.main()
