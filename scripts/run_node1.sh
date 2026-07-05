#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
require_binary "$LIGHTPOOL" "cargo build --release (extracts bin/lightpool from bin/lightpool-v*.tar.gz)"

[[ -f "$NODE1_WALLET" ]] || { echo "Run ./init.sh first" >&2; exit 1; }
[[ -f "$NODE1_VALIDATOR" ]] || { echo "Run ./init.sh first" >&2; exit 1; }

LOG_FILE="${1:-}"

if [[ -d "$NODE1_STORE" ]]; then
    echo "Removing stale node1 store: $NODE1_STORE"
    rm -rf "$NODE1_STORE"
fi
mkdir -p "$NODE1_STORE"
if [[ -n "$LOG_FILE" ]]; then
    mkdir -p "$(dirname "$LOG_FILE")"
fi

CMD=(
  "$LIGHTPOOL"
  --wallet "$NODE1_WALLET"
  --store "$NODE1_STORE"
  --validator "$NODE1_VALIDATOR"
  --boot-peer "$NODE0_BOOT_PEER"
  --front-listen-addr "0.0.0.0:27000"
  --rpc-listen-addr "0.0.0.0:27300"
  --ws-listen-addr "0.0.0.0:27400"
)

if [[ -n "$LOG_FILE" ]]; then
    echo "Starting node1 (boot-peer $NODE0_BOOT_PEER, log $LOG_FILE)"
    exec "${CMD[@]}" >> "$LOG_FILE" 2>&1
else
    echo "Starting node1 (boot-peer $NODE0_BOOT_PEER)"
    exec "${CMD[@]}"
fi
