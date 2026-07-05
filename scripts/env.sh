#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$SCRIPT_DIR"
PROJECT_ROOT="$(cd "$SCRIPTS_DIR/.." && pwd)"
DATA_DIR="${LIGHTPOOL_NETWORK_DATA_DIR:-$SCRIPTS_DIR/.local-network}"

LIGHTPOOL="${LIGHTPOOL_BIN:-$PROJECT_ROOT/bin/lightpool}"
LIGHTPOOL_CLI="${LIGHTPOOL_CLI:-$PROJECT_ROOT/bin/lightpool-cli}"
BURST_CLIENT="${BURST_CLIENT_BIN:-$PROJECT_ROOT/bin/burst_client}"

NODE0_WALLET="$DATA_DIR/node0/wallet.json"
NODE1_WALLET="$DATA_DIR/node1/wallet.json"
NODE0_VALIDATOR="$DATA_DIR/node0/validator.json"
NODE1_VALIDATOR="$DATA_DIR/node1/validator.json"
NODE0_STORE="$DATA_DIR/node0/store"
NODE1_STORE="$DATA_DIR/node1/store"
NODE0_LOG="$DATA_DIR/node0/lightpool.log"
NODE1_LOG="$DATA_DIR/node1/lightpool.log"

NODE0_RPC="http://127.0.0.1:26300"
NODE0_BOOT_PEER="http://127.0.0.1:26300"
NODE1_RPC="http://127.0.0.1:27300"

BURST_FRONT="127.0.0.1"

require_binary() {
    local path="$1"
    local build_hint="$2"
    if [[ ! -f "$path" ]]; then
        echo "Missing binary: $path" >&2
        echo "$build_hint" >&2
        exit 1
    fi
}
