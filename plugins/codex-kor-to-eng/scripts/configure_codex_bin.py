from __future__ import annotations

import os
import sys
from typing import assert_never

from codex_bin_discovery import resolve_codex_bin


def main() -> int:
    resolution = resolve_codex_bin(os.environ)
    if resolution.ignored_configured_path is not None:
        _ = sys.stdout.write(
            f"ignored missing CODEX_KOR_TO_ENG_CODEX_BIN={resolution.ignored_configured_path}\n",
        )

    match resolution.source:
        case "fallback":
            _ = sys.stdout.write("codex executable was not found.\n")
            guidance = (
                "Install the Codex CLI, put `codex` on PATH, "
                "or set CODEX_KOR_TO_ENG_CODEX_BIN.\n"
            )
            _ = sys.stdout.write(
                guidance,
            )
            return 1
        case "configured" | "path" | "app_install":
            _ = sys.stdout.write(f"codex_bin={resolution.path}\n")
            _ = sys.stdout.write(f"source={resolution.source}\n")
            _ = sys.stdout.write("Korean-to-English hook will use this path automatically.\n")
            return 0
        case unreachable:
            assert_never(unreachable)


if __name__ == "__main__":
    raise SystemExit(main())
