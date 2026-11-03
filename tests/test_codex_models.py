from __future__ import annotations

# ruff: noqa: PT027 -- This repository uses unittest without a pytest dependency.
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "plugins" / "lazy-eng-study-codex" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import kor_to_eng_hook as hook
from codex_models import ModelDiscoveryError, list_codex_models, oldest_medium_model
from hook_types import JsonObject


def model(name: str, *, hidden: bool = False, effort: str = "medium") -> JsonObject:
    return {
        "model": name,
        "hidden": hidden,
        "supportedReasoningEfforts": [{"reasoningEffort": effort}],
    }


class OldestModelTest(unittest.TestCase):
    def test_compares_versions_numerically_and_keeps_codex_order_on_ties(self) -> None:
        self.assertEqual(
            oldest_medium_model(
                [
                    model("gpt-10-sol"),
                    model("gpt-9.10-sol"),
                    model("gpt-9.2-sol"),
                    model("gpt-9.2-luna"),
                ]
            ),
            "gpt-9.2-sol",
        )

    def test_excludes_hidden_non_gpt_and_incompatible_models(self) -> None:
        audio = model("gpt-3-audio")
        audio["inputModalities"] = ["audio"]
        self.assertEqual(
            oldest_medium_model(
                [
                    model("gpt-1-hidden", hidden=True),
                    model("gpt-2-low", effort="low"),
                    model("codex-auto-review"),
                    audio,
                    model("gpt-4-text"),
                ]
            ),
            "gpt-4-text",
        )

    def test_removed_old_model_automatically_moves_to_next_supported_generation(self) -> None:
        newer = model("gpt-12-new")
        older = model("gpt-11-old")
        self.assertEqual(oldest_medium_model([newer, older]), "gpt-11-old")
        self.assertEqual(oldest_medium_model([newer]), "gpt-12-new")

    def test_empty_or_unsupported_catalog_fails_without_guessing(self) -> None:
        catalogs: list[list[JsonObject]] = [
            [],
            [model("gpt-1-low", effort="low")],
            [{"model": "gpt-1"}],
        ]
        for models in catalogs:
            with self.subTest(models=models), self.assertRaises(ModelDiscoveryError):
                _ = oldest_medium_model(models)

    def test_discovery_failure_is_visible_and_never_starts_translation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = {"CODEX_KOR_TO_ENG_SETTINGS_FILE": str(Path(temp_dir) / "settings.json")}
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "\ud14c\uc2a4\ud2b8",
                "cwd": temp_dir,
            }
            with (
                patch.object(
                    hook,
                    "list_codex_models",
                    side_effect=ModelDiscoveryError("catalog unavailable"),
                ),
                patch.object(subprocess, "run") as translate,
            ):
                output = hook.run_hook(json.dumps(payload), env)
            translate.assert_not_called()

        self.assertIn("translation failed", output)
        self.assertIn("catalog unavailable", output)


class ModelListProtocolTest(unittest.TestCase):
    def run_catalog(self, mode: str = "pages", *, timeout: float = 5) -> list[JsonObject]:
        fixture = REPO_ROOT / "tests" / "fixtures" / "fake_codex_models.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            _ = (Path(temp_dir) / "app-server").write_text(
                fixture.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            return list_codex_models(
                sys.executable,
                {**os.environ, "FAKE_MODEL_MODE": mode},
                temp_dir,
                timeout=timeout,
            )

    def test_handshake_notifications_and_pagination_through_real_child_process(self) -> None:
        models = self.run_catalog()
        self.assertEqual([item["model"] for item in models], ["gpt-10.1-new", "gpt-8.2-old"])
        self.assertEqual(oldest_medium_model(models), "gpt-8.2-old")

    def test_protocol_failures_are_reported(self) -> None:
        for mode, message in (
            ("exit", "catalog unavailable"),
            ("invalid", "invalid JSON"),
            ("error", "sign in required"),
            ("repeat", "repeated cursor"),
        ):
            with self.subTest(mode=mode), self.assertRaisesRegex(ModelDiscoveryError, message):
                _ = self.run_catalog(mode)

    def test_timeout_stops_child_process_promptly(self) -> None:
        started = time.monotonic()
        with self.assertRaisesRegex(ModelDiscoveryError, "timed out"):
            _ = self.run_catalog("timeout", timeout=0.3)
        self.assertLess(time.monotonic() - started, 5)

    def test_missing_executable_is_reported(self) -> None:
        with self.assertRaisesRegex(ModelDiscoveryError, "codex executable"):
            _ = list_codex_models("__missing_codex__", os.environ, str(REPO_ROOT))
