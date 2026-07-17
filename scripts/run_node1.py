#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from lib.bin_utils import require_binary
from lib.config import DATA_DIR, LIGHTPOOL_BIN
from lib.node_utils import build_node_spec, run_local_node


def main() -> None:
    default_log = build_node_spec(1, DATA_DIR).log_path
    parser = argparse.ArgumentParser(description="Run local network node1.")
    parser.add_argument(
        "log_file",
        nargs="?",
        default=None,
        help=f"Optional log file path (prints to terminal when omitted; e.g. {default_log})",
    )
    args = parser.parse_args()

    require_binary(
        LIGHTPOOL_BIN,
        "cargo build --release (extracts bin/lightpool from bin/lightpool-v*.tar.gz)",
    )
    run_local_node(1, DATA_DIR, log_file=args.log_file, reset_store=True)


if __name__ == "__main__":
    main()
