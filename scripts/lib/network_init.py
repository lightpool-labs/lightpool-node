from __future__ import annotations

import json
import shutil
from pathlib import Path

from lib.config import DATA_DIR
from lib.node_utils import boot_peer_url, build_node_spec
from lib.wallet_utils import create_wallet, wallet_identity


def init_network(data_dir: Path = DATA_DIR) -> None:
    if data_dir.is_dir():
        print(f"Removing old data dir: {data_dir}")
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    node0 = build_node_spec(0, data_dir)
    node1 = build_node_spec(1, data_dir, boot_peer=boot_peer_url(0))

    for spec in (node0, node1):
        create_wallet(spec.wallet_path, force=True)
        _, consensus_pubkey = wallet_identity(spec.wallet_path)
        payload = {
            "consensus_pubkey": consensus_pubkey,
            "mempool_address": f"127.0.0.1:{spec.mempool_port}",
            "consensus_address": f"127.0.0.1:{spec.consensus_port}",
        }
        spec.validator_path.parent.mkdir(parents=True, exist_ok=True)
        spec.validator_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {spec.validator_path}")

    print(f"Data dir: {data_dir}")
