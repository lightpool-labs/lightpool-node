# Examples and reference code

LightPool is a blockchain orderbook; prediction markets use the same CLOB
via event contracts. **Download and run** `lightpool-node` and
`lightpool-clob-index` locally — they are not online services.

## Download

```bash
mkdir -p ~/work/lightpool-labs && cd ~/work/lightpool-labs
git clone git@github.com:lightpool-labs/lightpool-node.git
git clone git@github.com:lightpool-labs/lightpool-clob-index.git
git clone git@github.com:lightpool-labs/lightpool-sdk-rust.git
```

## Run node

```bash
cd ~/work/lightpool-labs/lightpool-node
# Place lightpool-v*.tar.gz and lightpool-cli-v*.tar.gz under bin/
cargo build --release
source ./env.sh
lightpool-cli create-wallet --force   # once
lightpool                              # keep running (RPC :26300, WS :26400)
```

## Run clob-index

```bash
cd ~/work/lightpool-labs/lightpool-clob-index
cp -n .env.example .env
cargo run --release                    # keep running (:3002)
```

App endpoints: `http://127.0.0.1:3002/api/...`, `ws://127.0.0.1:3002/api/ws`.

## clob-index code map

| Piece | Path |
|-------|------|
| Service | `lightpool-clob-index/` |
| HTTP routes | `lightpool-clob-index/src/http/` |
| WS channels | `lightpool-clob-index/src/ws/` |

## SDK (signing only)

Crate: `lightpool-sdk` in `lightpool-sdk-rust/`.

Use for offline sign of `place_order` / `cancel_order` / etc., then POST to
local `/api/tx/submit`. Do not use SDK clients against node RPC/WS from an app.

| Type | Role |
|------|------|
| `Signer` | Keys / user `Address` |
| `TransactionBuilder`, `ActionBuilder` | Build and sign txs |
| `Address`, `ContractAddress`, order params | Types for signed payloads |
