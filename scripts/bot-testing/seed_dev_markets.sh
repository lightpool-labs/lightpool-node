#!/usr/bin/env bash
# Seed local LightPool for lightpool-bot adapter smoke tests.
#
# Creates sample event markets via clob-index so bins like
# lightpool-http-public / http-exec / ws-data see instruments.
#
# Uses the default lightpool wallet: ~/.lightpool/wallet.json
# (creates it if missing). Does not require LIGHTPOOL_PRIVATE_KEY.
#
# Collateral defaults to 0x0200000000000001 (same as nautilus-lightpool).
# If that token is missing on chain, this script creates it (first create-token
# on a fresh chain is 0x0200000000000001). Override with LIGHTPOOL_COLLATERAL_TOKEN.
# Wallet is funded with billions of USDT (create total-supply and/or mint top-up)
# for full-process tests (e.g. liquidity-maker --bootstrap-markets).
#
# Prerequisites (already running):
#   - lightpool node  (RPC http://127.0.0.1:26300)
#   - lightpool-clob-index  (http://127.0.0.1:3002)
#
# Usage (from lightpool-node):
#   source ./env.sh
#   ./scripts/bot-testing/seed_dev_markets.sh
set -euo pipefail

NODE_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
BOT_DIR="$(cd "$NODE_DIR/../lightpool-bot" && pwd)"
CLOB_HTTP="${LIGHTPOOL_CLOB_INDEX_HTTP:-http://127.0.0.1:3002}"
WALLET_PATH="${HOME}/.lightpool/wallet.json"
# Match nautilus-lightpool DEFAULT_COLLATERAL_TOKEN.
DEFAULT_COLLATERAL_TOKEN="0x0200000000000001"
export LIGHTPOOL_COLLATERAL_TOKEN="${LIGHTPOOL_COLLATERAL_TOKEN:-$DEFAULT_COLLATERAL_TOKEN}"
# Human-unit USDT (6 decimals). Default 10 billion — enough for liquidity-maker
# default mint (~1e9/market × 5) plus headroom.
SEED_USDT_AMOUNT="${SEED_USDT_AMOUNT:-10000000000}"

parse_contract_address() {
  local text="$1"
  printf '%s\n' "$text" | grep -oE '0x02[0-9a-fA-F]{14}' | head -n1 || true
}

for arg in "$@"; do
  case "$arg" in
    --skip-token)
      # Kept for compatibility; ignored (token is ensured below).
      ;;
    -h|--help)
      sed -n '2,22p' "$0"
      exit 0
      ;;
  esac
done

if [[ ! -d "$BOT_DIR" ]]; then
  echo "lightpool-bot not found next to lightpool-node: $BOT_DIR" >&2
  exit 1
fi

if [[ -f "$NODE_DIR/env.sh" ]]; then
  # shellcheck disable=SC1091
  source "$NODE_DIR/env.sh"
fi

if ! command -v lightpool >/dev/null 2>&1; then
  echo "lightpool not on PATH. Run: cd $NODE_DIR && cargo build --release && source ./env.sh" >&2
  exit 1
fi

# Prefer default wallet.json for adapter bins (resolve_private_key reads it).
unset LIGHTPOOL_PRIVATE_KEY || true

if [[ ! -f "$WALLET_PATH" ]]; then
  echo "Creating default wallet at $WALLET_PATH ..."
  lightpool create-wallet --force
fi

echo "Using default wallet: $WALLET_PATH"
lightpool address || true

echo "Checking clob-index at $CLOB_HTTP ..."
if ! curl -sf "$CLOB_HTTP/api/health/health" >/dev/null && ! curl -sf "$CLOB_HTTP/api/markets?limit=1" >/dev/null; then
  echo "clob-index not healthy. Start it with:" >&2
  echo "  cd ../lightpool-clob-index && cargo run --release --bin lightpool-clob-index" >&2
  exit 1
fi

echo "Ensuring collateral token $LIGHTPOOL_COLLATERAL_TOKEN (fund ${SEED_USDT_AMOUNT} USDT) ..."
# lightpool balance prints Available: 0 even when the token does not exist, so key off Total.
BALANCE_OUT="$(lightpool balance --token-address "$LIGHTPOOL_COLLATERAL_TOKEN" 2>&1 || true)"
TOTAL="$(printf '%s\n' "$BALANCE_OUT" | sed -n 's/^Total:[[:space:]]*//p' | head -1 | tr -d '[:space:]')"
if [[ -z "$TOTAL" || "$TOTAL" == "0" ]]; then
  echo "Collateral token missing or zero supply; creating USDT via lightpool create-token ..."
  CREATE_OUT="$(lightpool create-token \
    --name USDT \
    --symbol USDT \
    --total-supply "$SEED_USDT_AMOUNT" \
    --mintable 2>&1)" || true
  printf '%s\n' "$CREATE_OUT"
  CREATED="$(parse_contract_address "$CREATE_OUT")"
  if [[ -n "$CREATED" ]]; then
    if [[ "$CREATED" != "$LIGHTPOOL_COLLATERAL_TOKEN" ]]; then
      echo "create-token produced $CREATED, but script expects $LIGHTPOOL_COLLATERAL_TOKEN." >&2
      echo "On a fresh chain the first token is $DEFAULT_COLLATERAL_TOKEN." >&2
      echo "Reset local chain state, or: export LIGHTPOOL_COLLATERAL_TOKEN=$CREATED" >&2
      exit 1
    fi
    echo "Created collateral token: $LIGHTPOOL_COLLATERAL_TOKEN (supply=$SEED_USDT_AMOUNT)"
  else
    echo "create-token did not yield an address (token may already exist); minting instead ..."
    lightpool mint \
      --token-address "$LIGHTPOOL_COLLATERAL_TOKEN" \
      --amount "$SEED_USDT_AMOUNT"
  fi
else
  echo "Collateral token already exists; minting ${SEED_USDT_AMOUNT} USDT to wallet ..."
  lightpool mint \
    --token-address "$LIGHTPOOL_COLLATERAL_TOKEN" \
    --amount "$SEED_USDT_AMOUNT"
fi

echo "Collateral balance after fund:"
lightpool balance --token-address "$LIGHTPOOL_COLLATERAL_TOKEN" || true

# Dev sample markets are optional (liquidity-maker --bootstrap-markets is preferred).
if [[ "${SEED_BOOTSTRAP_MARKETS:-0}" != "1" ]]; then
  echo "Skipping http-bootstrap markets (set SEED_BOOTSTRAP_MARKETS=1 to create them)."
  echo "Verify: curl -s '$CLOB_HTTP/api/markets?limit=10'"
  exit 0
fi

export LIGHTPOOL_CLOB_INDEX_HTTP="$CLOB_HTTP"
export LIGHTPOOL_BOOTSTRAP_COUNT="${LIGHTPOOL_BOOTSTRAP_COUNT:-2}"
export LIGHTPOOL_BOOTSTRAP_MINT="${LIGHTPOOL_BOOTSTRAP_MINT:-1000000000}"

echo "Bootstrapping markets via clob-index (collateral=$LIGHTPOOL_COLLATERAL_TOKEN) ..."
cd "$BOT_DIR"
env -u LIGHTPOOL_PRIVATE_KEY \
  LIGHTPOOL_COLLATERAL_TOKEN="$LIGHTPOOL_COLLATERAL_TOKEN" \
  cargo run -p nautilus-lightpool --bin lightpool-http-bootstrap

echo
echo "Verify:"
echo "  curl -s '$CLOB_HTTP/api/markets?limit=10' | head"
