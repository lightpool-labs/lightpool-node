#!/bin/sh
set -e

WALLET_PATH="${WALLET_PATH:-/data/wallet.json}"
STORE_PATH="${STORE_PATH:-/data/store}"
VALIDATOR_PATH="${VALIDATOR_PATH:-/data/validator.json}"

mkdir -p "$STORE_PATH" "$(dirname "$WALLET_PATH")" "$(dirname "$VALIDATOR_PATH")"

normalize_key() {
  printf '%s' "$1" | sed 's/^0x//;s/^0X//' | tr 'A-F' 'a-f'
}

if [ -n "${LIGHTPOOL_PRIVATE_KEY:-}" ]; then
  KEY_HEX="$(normalize_key "$LIGHTPOOL_PRIVATE_KEY")"
  if [ "${#KEY_HEX}" -ne 64 ]; then
    echo "LIGHTPOOL_PRIVATE_KEY must be 32 bytes hex (64 chars), got ${#KEY_HEX} chars" >&2
    exit 1
  fi

  if [ -f "$WALLET_PATH" ]; then
    EXISTING_HEX="$(normalize_key "$(sed -n 's/.*"private_key"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$WALLET_PATH" | head -1)")"
    if [ -n "$EXISTING_HEX" ] && [ "$EXISTING_HEX" != "$KEY_HEX" ]; then
      echo "Refusing to start: $WALLET_PATH already exists with a different private key." >&2
      echo "Use a matching LIGHTPOOL_PRIVATE_KEY, or remove ./data/node and start fresh." >&2
      exit 1
    fi
  fi

  if [ ! -f "$WALLET_PATH" ] || [ -z "${EXISTING_HEX:-}" ]; then
    lightpool import-wallet \
      --private-key "$KEY_HEX" \
      --wallet-path "$WALLET_PATH" \
      --force
    rm -f "$VALIDATOR_PATH"
  fi
elif [ -f "$WALLET_PATH" ]; then
  :
else
  echo "Missing validator credentials." >&2
  echo "Set LIGHTPOOL_PRIVATE_KEY in .env (like a database password), or mount wallet.json at $WALLET_PATH." >&2
  echo "Example:" >&2
  echo "  cp .env.example .env" >&2
  echo "  # edit LIGHTPOOL_PRIVATE_KEY, then: docker compose up -d" >&2
  exit 1
fi

lightpool --wallet-path "$WALLET_PATH" address || true

exec lightpool node \
  --wallet "$WALLET_PATH" \
  --store "$STORE_PATH" \
  --validator "$VALIDATOR_PATH" \
  --role validator \
  --rpc-listen-addr 0.0.0.0:26300 \
  --ws-listen-addr 0.0.0.0:26400 \
  --front-listen-addr 0.0.0.0:26000 \
  "$@"
