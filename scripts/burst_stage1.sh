#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
require_binary "$BURST_CLIENT" "Place burst_client at bin/burst_client or set BURST_CLIENT_BIN"

echo "Burst stage 1 (fast): stop when committed_block_num >= 1000"
exec "$BURST_CLIENT" \
  --address "$BURST_FRONT" \
  --senders 128 \
  --recipients 128 \
  --tasks 2 \
  --rate-per-task 200 \
  --duration 800 \
  --transfer-amount 2048
