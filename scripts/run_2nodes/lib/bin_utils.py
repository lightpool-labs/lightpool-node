from __future__ import annotations

import sys
from pathlib import Path


def require_binary(path: str, build_hint: str) -> None:
    if not Path(path).is_file():
        print(f"Missing binary: {path}", file=sys.stderr)
        print(build_hint, file=sys.stderr)
        raise SystemExit(1)
