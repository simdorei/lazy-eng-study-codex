from __future__ import annotations

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "plugins" / "codex-kor-to-eng" / "scripts"


class PythonCompatibilityTest(unittest.TestCase):
    def test_hook_scripts_parse_as_python_311(self) -> None:
        for path in SCRIPT_DIR.glob("*.py"):
            with self.subTest(path=path.name):
                _ = ast.parse(
                    path.read_text(encoding="utf-8"),
                    filename=str(path),
                    feature_version=(3, 11),
                )


if __name__ == "__main__":
    _ = unittest.main()
