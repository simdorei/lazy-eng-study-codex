from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "plugins" / "lazy-eng-study-codex" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from codex_child_home import child_codex_env


class CodexChildHomeTest(unittest.TestCase):
    def test_child_codex_env_does_not_reuse_parent_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir) / ".codex"
            parent.mkdir()
            _ = (parent / "auth.json").write_text('{"token":"test"}\n', encoding="utf-8")
            _ = (parent / "config.toml").write_text(
                'service_tier = "anything"\n',
                encoding="utf-8",
            )

            env = child_codex_env({"CODEX_HOME": str(parent)})

            child = Path(env["CODEX_HOME"])
            self.assertNotEqual(child, parent)
            self.assertEqual((child / "config.toml").read_text(encoding="utf-8"), "")
            self.assertEqual(
                (child / "auth.json").read_text(encoding="utf-8"),
                '{"token":"test"}\n',
            )
            self.assertEqual(env["CODEX_KOR_TO_ENG_DISABLED"], "1")


if __name__ == "__main__":
    _ = unittest.main()
