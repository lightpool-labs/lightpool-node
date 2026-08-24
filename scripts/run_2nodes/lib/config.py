from __future__ import annotations

import os
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SCRIPTS_DIR.parent.parent

NODE_COUNT = 2
PORT_STEP = 1000
VALIDATOR_STAKES = (100, 0)
EPOCH_LENGTH = 1000
FIRST_CHECKPOINT_EPOCH = 1
PAST_EPOCH_TARGET_BLOCK = EPOCH_LENGTH
STAKING_TARGET_EPOCH = 2
STAKING_PREPARE_BLOCK = STAKING_TARGET_EPOCH * EPOCH_LENGTH - 10
STAKING_COMMITTEE_TARGET_BLOCK = STAKING_TARGET_EPOCH * EPOCH_LENGTH
STAKING_BOND_AMOUNTS = ("90000", "10000")
STAKING_NODE1_FUNDING = "11000"

BASE_FRONT_PORT = 26000
BASE_MEMPOOL_PORT = 26100
BASE_CONSENSUS_PORT = 26200
BASE_RPC_PORT = 26300
BASE_WS_PORT = 26400

BURST_FRONT = "127.0.0.1"

DATA_DIR = Path(
    os.environ.get("LIGHTPOOL_NETWORK_DATA_DIR", SCRIPTS_DIR / ".local-network")
)

LIGHTPOOL_BIN = os.environ.get(
    "LIGHTPOOL_BIN",
    str(PROJECT_ROOT / "bin" / "lightpool"),
)

# Compat alias: client subcommands use the same unified binary.
LIGHTPOOL_CLI = os.environ.get("LIGHTPOOL_CLI", LIGHTPOOL_BIN)

BURST_CLIENT_BIN = os.environ.get(
    "BURST_CLIENT_BIN",
    str(PROJECT_ROOT / "bin" / "burst_client"),
)

BUILD_LIGHTPOOL_HINT = (
    "cargo build --release "
    f"(extracts bin/lightpool from lightpool-v*.tar.gz under {PROJECT_ROOT / 'bin'})"
)
BUILD_BURST_HINT = (
    f"Place burst_client at {PROJECT_ROOT / 'bin' / 'burst_client'} "
    "(build from lightpool-sdk-rust: cargo build --release --example burst_transfer)"
)
