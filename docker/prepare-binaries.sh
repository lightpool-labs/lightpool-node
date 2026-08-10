#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_ROOT="$(cd "$ROOT/.." && pwd)"
BIN_DIR="$ROOT/bin"

NODE_BIN="${LIGHTPOOL_BIN:-$NODE_ROOT/bin/lightpool}"
CLOB_BIN="${LIGHTPOOL_CLOB_INDEX_BIN:-$NODE_ROOT/bin/lightpool-clob-indexer}"

mkdir -p "$BIN_DIR"

copy_one() {
  local src="$1"
  local name="$2"
  if [[ ! -f "$src" ]]; then
    echo "missing: $src" >&2
    echo "hint: place release tarballs in $NODE_ROOT/bin and run: cd $NODE_ROOT && cargo build" >&2
    exit 1
  fi
  cp -f "$src" "$BIN_DIR/$name"
  chmod +x "$BIN_DIR/$name"
  echo "copied $name <- $src"
}

copy_one "$NODE_BIN" lightpool
copy_one "$CLOB_BIN" lightpool-clob-indexer

echo "binaries ready under $BIN_DIR"
echo "next: docker compose -f $ROOT/docker-compose.yml up --build -d"
