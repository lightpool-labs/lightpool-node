#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="${ROOT}/bin/reth"
DATADIR="${RETH_DATADIR:-${ROOT}/data/dev}"
HTTP_PORT="${RETH_HTTP_PORT:-8545}"
WS_PORT="${RETH_WS_PORT:-8546}"
AUTHRPC_PORT="${RETH_AUTHRPC_PORT:-8551}"
BLOCK_TIME="${RETH_BLOCK_TIME:-1s}"

if [[ ! -x "${BIN}" ]]; then
  echo "reth not found. Run: ${ROOT}/download.sh" >&2
  exit 1
fi

mkdir -p "${DATADIR}"

exec "${BIN}" node \
  --dev \
  --dev.block-time "${BLOCK_TIME}" \
  --datadir "${DATADIR}" \
  --http \
  --http.addr 0.0.0.0 \
  --http.port "${HTTP_PORT}" \
  --http.api eth,net,web3,txpool,debug,trace \
  --http.corsdomain '*' \
  --ws \
  --ws.addr 0.0.0.0 \
  --ws.port "${WS_PORT}" \
  --ws.api eth,net,web3,txpool,debug,trace \
  --ws.origins '*' \
  --authrpc.addr 127.0.0.1 \
  --authrpc.port "${AUTHRPC_PORT}" \
  --engine.persistence-threshold 0 \
  --engine.memory-block-buffer-target 0 \
  "$@"
