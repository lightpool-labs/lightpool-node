from __future__ import annotations

import os
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
CRATE_DIR = SCRIPTS_DIR.parent
WORKSPACE_ROOT = CRATE_DIR.parent.parent

NODE_COUNT = 2
PORT_STEP = 1000
VALIDATOR_STAKE = 1

BASE_FRONT_PORT = 26000
BASE_MEMPOOL_PORT = 26100
BASE_CONSENSUS_PORT = 26200
BASE_RPC_PORT = 26300
BASE_WS_PORT = 26400

DATA_DIR = Path(
    os.environ.get("LIGHTPOOL_NETWORK_DATA_DIR", SCRIPTS_DIR / ".local-network")
)

LIGHTPOOL_BIN = os.environ.get(
    "LIGHTPOOL_BIN",
    str(WORKSPACE_ROOT / "target" / "release" / "lightpool"),
)

LIGHTPOOL_CLI = os.environ.get(
    "LIGHTPOOL_CLI",
    str(WORKSPACE_ROOT / "target" / "release" / "lightpool-cli"),
)
