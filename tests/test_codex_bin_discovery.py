from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "plugins" / "lazy-eng-study-codex" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from codex_bin_discovery import read_codex_bin


class CodexBinDiscoveryTest(unittest.TestCase):
    def test_uses_openai_install_when_path_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_codex = Path(temp_dir) / "OpenAI" / "Codex" / "bin" / "version" / "codex.exe"
            fake_codex.parent.mkdir(parents=True)
            _ = fake_codex.write_text("", encoding="utf-8")

            codex_bin = read_codex_bin({"LOCALAPPDATA": temp_dir, "PATH": ""})

        self.assertEqual(codex_bin, str(fake_codex))

    def test_prefers_newest_installed_app_binary_over_stale_stable_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            install_root = Path(temp_dir) / "OpenAI" / "Codex" / "bin"
            stable_codex = install_root / "codex.exe"
            version_codex = install_root / "version" / "codex.exe"
            version_codex.parent.mkdir(parents=True)
            _ = stable_codex.write_text("", encoding="utf-8")
            _ = version_codex.write_text("", encoding="utf-8")
            os.utime(stable_codex, (100, 100))
            os.utime(version_codex, (200, 200))

            codex_bin = read_codex_bin({"LOCALAPPDATA": temp_dir, "PATH": ""})

        self.assertEqual(codex_bin, str(version_codex))

    def test_saved_app_path_tracks_newest_install_without_changing_custom_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            install_root = Path(temp_dir) / "OpenAI" / "Codex" / "bin"
            older = install_root / "zz-old" / "codex.exe"
            newer = install_root / "aa-new" / "codex.exe"
            custom = Path(temp_dir) / "custom" / "codex.exe"
            for path, modified in ((older, 100), (newer, 200), (custom, 50)):
                path.parent.mkdir(parents=True, exist_ok=True)
                _ = path.write_text("", encoding="utf-8")
                os.utime(path, (modified, modified))
            env = {"LOCALAPPDATA": temp_dir, "PATH": ""}
            selected_app = read_codex_bin({**env, "CODEX_KOR_TO_ENG_CODEX_BIN": str(older)})
            selected_custom = read_codex_bin({**env, "CODEX_KOR_TO_ENG_CODEX_BIN": str(custom)})

        self.assertEqual(selected_app, str(newer))
        self.assertEqual(selected_custom, str(custom))

    def test_ignores_missing_configured_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            install_root = Path(temp_dir) / "OpenAI" / "Codex" / "bin"
            stable_codex = install_root / "codex.exe"
            install_root.mkdir(parents=True)
            _ = stable_codex.write_text("", encoding="utf-8")
            env = {
                "CODEX_KOR_TO_ENG_CODEX_BIN": str(Path(temp_dir) / "missing" / "codex.exe"),
                "LOCALAPPDATA": temp_dir,
                "PATH": "",
            }

            codex_bin = read_codex_bin(env)

        self.assertEqual(codex_bin, str(stable_codex))

    def test_ignores_windowsapps_configured_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            install_root = Path(temp_dir) / "OpenAI" / "Codex" / "bin"
            stable_codex = install_root / "codex.exe"
            windowsapps_codex = (
                Path(temp_dir)
                / "WindowsApps"
                / "OpenAI.Codex"
                / "app"
                / "resources"
                / "codex.exe"
            )
            stable_codex.parent.mkdir(parents=True)
            windowsapps_codex.parent.mkdir(parents=True)
            _ = stable_codex.write_text("", encoding="utf-8")
            _ = windowsapps_codex.write_text("", encoding="utf-8")
            env = {
                "CODEX_KOR_TO_ENG_CODEX_BIN": str(windowsapps_codex),
                "LOCALAPPDATA": temp_dir,
                "PATH": "",
            }

            codex_bin = read_codex_bin(env)

        self.assertEqual(codex_bin, str(stable_codex))

    def test_uses_macos_app_support_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_codex = (
                Path(temp_dir)
                / "Library"
                / "Application Support"
                / "OpenAI"
                / "Codex"
                / "bin"
                / "codex"
            )
            fake_codex.parent.mkdir(parents=True)
            _ = fake_codex.write_text("", encoding="utf-8")

            codex_bin = read_codex_bin({"HOME": temp_dir, "PATH": ""})

        self.assertEqual(codex_bin, str(fake_codex))


if __name__ == "__main__":
    _ = unittest.main()
