#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
require_binary "$LIGHTPOOL_CLI" "cargo build --release (extracts bin/lightpool-cli from bin/lightpool-cli-v*.tar.gz)"

cd "$SCRIPTS_DIR"
python3 <<PY
import sys
from pathlib import Path

from node_utils import build_node_spec, rpc_ready
from staking_utils import run_staking_setup

data_dir = Path("${DATA_DIR}")
leader = build_node_spec(0, data_dir)
follower = build_node_spec(1, data_dir, boot_peer="${NODE0_BOOT_PEER}")

print(f"Waiting for node0 RPC on http://127.0.0.1:{leader.rpc_port}...", flush=True)
if not rpc_ready(leader.rpc_port, timeout_sec=30.0):
    print(
        f"node0 RPC is not ready on port {leader.rpc_port}.\\n"
        "Start node0 first and wait until you see:\\n"
        "  JSON-RPC HTTP server listening on 0.0.0.0:26300\\n"
        "  Node is running; press Ctrl+C to stop",
        file=sys.stderr,
        flush=True,
    )
    raise SystemExit(1)

run_staking_setup(leader, follower, data_dir)
print("Staking setup done.")
PY
