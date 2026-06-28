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
from hook_types import HookSettings, JsonObject, JsonValue


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


def get_text(value: Mapping[str, JsonValue], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise AssertionError(f"expected text key: {key}")
    return item


def get_object_map(value: Mapping[str, JsonValue], key: str) -> JsonObject:
    item = value.get(key)
    if not isinstance(item, dict):
        raise AssertionError(f"expected object key: {key}")
    normalized: JsonObject = {}
    for nested_key, nested_item in item.items():
        normalized[nested_key] = nested_item
    return normalized


class CodexTranslatorTest(unittest.TestCase):
    def test_default_codex_command_uses_mini_model_and_medium_effort(self) -> None:
        settings = HookSettings(
            enabled=True,
            custom_command=None,
            codex_bin="codex",
            model=hook.DEFAULT_MODEL,
            effort=hook.DEFAULT_EFFORT,
            timeout_seconds=45,
        )

        command = hook.build_codex_command(settings, "테스트해줘")

        self.assertIn("gpt-5.4-mini", command)
        self.assertIn('model_reasoning_effort="medium"', command)
        self.assertIn("--ephemeral", command)
        self.assertEqual(command[1:4], ["--ask-for-approval", "never", "exec"])
        self.assertEqual(command[-1].splitlines()[-1], "테스트해줘")

    def test_default_codex_fallback_can_translate_through_run_hook(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_codex = Path(temp_dir) / "codex.cmd"
            cleanup_line = "echo SUCCESS: The process with PID 1 ({}) has been terminated.".format(
                "child process of PID 2",
            )
            script_lines = [
                "@echo off",
                cleanup_line,
                "echo Check the test thread status through default codex.",
                "",
            ]
            _ = fake_codex.write_text("\r\n".join(script_lines), encoding="utf-8")
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "테스트 스레드 상태 확인해줘",
                "cwd": temp_dir,
                "session_id": "session-1",
            }
            env = isolated_env(
                Path(temp_dir) / "settings.json",
                {"CODEX_KOR_TO_ENG_CODEX_BIN": str(fake_codex)},
            )

            output = hook.run_hook(json.dumps(payload), env)

        parsed = parse_json_object(output)
        context = get_text(get_object_map(parsed, "hookSpecificOutput"), "additionalContext")
        system_message = get_text(parsed, "systemMessage")
        self.assertIn("gpt-5.4-mini/medium", system_message)
        self.assertNotIn("SUCCESS: The process", system_message)
        self.assertIn("Check the test thread status through default codex.", system_message)
        self.assertIn(
            "Assistant-understood request: Check the test thread status through default codex.",
            context,
        )
        self.assertIn("Treat the rewritten English prompt as the primary user request.", context)


if __name__ == "__main__":
    _ = unittest.main()
