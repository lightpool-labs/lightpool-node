#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from lib.bin_utils import require_binary
from lib.config import BURST_CLIENT_BIN, BURST_FRONT


def main() -> None:
    require_binary(
        BURST_CLIENT_BIN,
        "Place burst_client at bin/burst_client or set BURST_CLIENT_BIN",
    )

    print("Burst stage 1 (fast): stop when committed_block_num >= 1000")
    argv = [
        BURST_CLIENT_BIN,
        "--address",
        BURST_FRONT,
        "--senders",
        "128",
        "--tasks",
        "2",
        "--rate-per-task",
        "200",
        "--duration",
        "800",
        "--transfer-amount",
        "2048",
    ]
    os.execv(BURST_CLIENT_BIN, argv)


if __name__ == "__main__":
    main()
