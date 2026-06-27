from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "lazy-eng-study-codex"
SCRIPT_DIR = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import install_plugin

LEGACY_MARKETPLACE_HEADER = "[marketplaces.codex-kor-to-eng-local]"
LEGACY_PLUGIN_KEY = "codex-kor-to-eng@codex-kor-to-eng-local"
LEGACY_HOOK_KEY = f"{LEGACY_PLUGIN_KEY}:hooks/hooks.json:user_prompt_submit:0:0"
PLUGIN_KEY = "lazy-eng-study-codex@lazy-eng-study-codex-local"


class InstallPluginMigrationTest(unittest.TestCase):
    def test_install_removes_legacy_kor_to_eng_plugin_registration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            codex_home = Path(temp_dir) / "codex-home"
            config_path = codex_home / "config.toml"
            config_path.parent.mkdir(parents=True)
            _ = config_path.write_text(
                (
                    "[features]\n"
                    "existing = true\n\n"
                    f"{LEGACY_MARKETPLACE_HEADER}\n"
                    'source = "C:\\repos\\simdorei\\codex-kor-to-eng\\plugins"\n\n'
                    f'[plugins."{LEGACY_PLUGIN_KEY}"]\n'
                    "enabled = true\n\n"
                    f'[hooks.state."{LEGACY_HOOK_KEY}"]\n'
                    "enabled = true\n"
                    'trusted_hash = "sha256:legacy"\n'
                ),
                encoding="utf-8",
            )

            result = install_plugin.install({"CODEX_HOME": str(codex_home)})
            config = result.config_path.read_text(encoding="utf-8")

        self.assertNotIn(LEGACY_MARKETPLACE_HEADER, config)
        self.assertNotIn(LEGACY_PLUGIN_KEY, config)
        self.assertNotIn(LEGACY_HOOK_KEY, config)
        self.assertIn(f'[plugins."{PLUGIN_KEY}"]', config)


if __name__ == "__main__":
    _ = unittest.main()
