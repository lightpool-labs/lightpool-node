#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
require_binary "$LIGHTPOOL_CLI" "cargo build --release (extracts bin/lightpool-cli from bin/lightpool-cli-v*.tar.gz)"

if [[ -d "$DATA_DIR" ]]; then
    echo "Removing old data dir: $DATA_DIR"
    rm -rf "$DATA_DIR"
fi
mkdir -p "$DATA_DIR"

cd "$SCRIPTS_DIR"
python3 <<PY
from pathlib import Path
import json

from node_utils import build_node_spec
from wallet_utils import create_wallet, wallet_identity

data_dir = Path("${DATA_DIR}")
node0 = build_node_spec(0, data_dir)
node1 = build_node_spec(1, data_dir, boot_peer="${NODE0_BOOT_PEER}")

for spec in (node0, node1):
    create_wallet(spec.wallet_path, force=True)
    _, consensus_pubkey = wallet_identity(spec.wallet_path)
    payload = {
        "consensus_pubkey": consensus_pubkey,
        "mempool_address": f"127.0.0.1:{spec.mempool_port}",
        "consensus_address": f"127.0.0.1:{spec.consensus_port}",
    }
    spec.validator_path.parent.mkdir(parents=True, exist_ok=True)
    spec.validator_path.write_text(json.dumps(payload, indent=2) + "\\n", encoding="utf-8")
    print(f"Wrote {spec.validator_path}")

print(f"Data dir: {data_dir}")
PY

echo "Init done."
