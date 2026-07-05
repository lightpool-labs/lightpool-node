#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
require_binary "$LIGHTPOOL" "cargo build --release (extracts bin/lightpool from bin/lightpool-v*.tar.gz)"

[[ -f "$NODE0_WALLET" ]] || { echo "Run ./init.sh first" >&2; exit 1; }
[[ -f "$NODE0_VALIDATOR" ]] || { echo "Run ./init.sh first" >&2; exit 1; }

LOG_FILE="${1:-}"

mkdir -p "$NODE0_STORE"
if [[ -n "$LOG_FILE" ]]; then
    mkdir -p "$(dirname "$LOG_FILE")"
fi

CMD=(
  "$LIGHTPOOL"
  --wallet "$NODE0_WALLET"
  --store "$NODE0_STORE"
  --validator "$NODE0_VALIDATOR"
  --front-listen-addr "0.0.0.0:26000"
  --rpc-listen-addr "0.0.0.0:26300"
  --ws-listen-addr "0.0.0.0:26400"
)

if [[ -n "$LOG_FILE" ]]; then
    echo "Starting node0 (RPC $NODE0_RPC, log $LOG_FILE)"
    exec "${CMD[@]}" >> "$LOG_FILE" 2>&1
else
    echo "Starting node0 (RPC $NODE0_RPC)"
    exec "${CMD[@]}"
fi
