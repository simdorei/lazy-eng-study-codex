from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "plugins" / "lazy-eng-study-codex" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import kor_to_eng_hook as hook
from hook_types import JsonObject, JsonValue


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
        metadata = get_object_map(hook_output, "lazyEngStudyCodex")
        context = get_text(hook_output, "additionalContext")
        notice_prefix = "First visible assistant message line: "
        expected_notice = f"{notice_prefix}\ubc88\uc5ed: Check the test thread status."
        system_message = get_text(parsed, "systemMessage")
        self.assertEqual(get_text(hook_output, "hookEventName"), "UserPromptSubmit")
        self.assertEqual(get_text(metadata, "pluginName"), "lazy-eng-study-codex")
        self.assertEqual(get_text(metadata, "mode"), "translation")
        self.assertEqual(
            get_text(metadata, "assistantUnderstoodRequest"),
            "Check the test thread status.",
        )
        self.assertTrue(system_message.startswith("\ubc88\uc5ed: Check the test thread status."))
        self.assertIn("(custom command)", system_message)
        self.assertIn(expected_notice, context)
        self.assertIn("Do not repeat that line in the final answer", context)
        self.assertIn("테스트 스레드 상태 확인해줘", context)
        self.assertIn("Check the test thread status.", context)

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
        self.assertIn("Original English:", context)
        self.assertIn("Corrected English:", context)
        self.assertIn("Then awkward sentence fixing is okay?", context)
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
        self.assertIn("codex executable not found", context)
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
