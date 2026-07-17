#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from lib.bin_utils import require_binary
from lib.config import DATA_DIR, LIGHTPOOL_CLI
from lib.node_utils import boot_peer_url, build_node_spec, rpc_ready
from lib.staking_utils import run_staking_setup


def main() -> None:
    require_binary(
        LIGHTPOOL_CLI,
        "cargo build --release (extracts bin/lightpool-cli from bin/lightpool-cli-v*.tar.gz)",
    )

    leader = build_node_spec(0, DATA_DIR)
    follower = build_node_spec(1, DATA_DIR, boot_peer=boot_peer_url(0))

    print(f"Waiting for node0 RPC on http://127.0.0.1:{leader.rpc_port}...", flush=True)
    if not rpc_ready(leader.rpc_port, timeout_sec=30.0):
        print(
            f"node0 RPC is not ready on port {leader.rpc_port}.\n"
            "Start node0 first and wait until you see:\n"
            "  JSON-RPC HTTP server listening on 0.0.0.0:26300\n"
            "  Node is running; press Ctrl+C to stop",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)

    run_staking_setup(leader, follower, DATA_DIR)
    print("Staking setup done.")


if __name__ == "__main__":
    main()
