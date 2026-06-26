from __future__ import annotations

import sys


def main() -> int:
    _ = sys.stdin.read()
    _ = sys.stdout.write("Check the test thread status.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
