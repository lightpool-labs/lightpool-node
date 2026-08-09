#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from lib.bin_utils import require_binary
from lib.config import DATA_DIR, LIGHTPOOL_BIN
from lib.network_init import init_network


def main() -> None:
    require_binary(
        LIGHTPOOL_BIN,
        "cargo build --release (extracts bin/lightpool from bin/lightpool-v*.tar.gz)",
    )
    init_network(DATA_DIR)
    print("Init done.")


if __name__ == "__main__":
    main()
