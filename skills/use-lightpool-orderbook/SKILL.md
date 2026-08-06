---
name: use-lightpool-orderbook
description: >-
  Integrate an external app with LightPool, a local blockchain orderbook that
  also supports prediction markets. Use when downloading and running
  lightpool-node plus lightpool-clob-index, or when placing/canceling orders,
  reading orderbook feeds, or submitting signed txs via clob-index.
  LightPool is not an online hosted service.
---

# Use LightPool as an Orderbook

LightPool is a **blockchain orderbook**. It provides on-chain CLOB matching and
settlement, and integrates **prediction markets** (event contracts with YES/NO
books) on top of that same orderbook model.

**Not an online service.** There is no hosted LightPool / clob-index endpoint.
You must **download and run** `lightpool-node` and `lightpool-clob-index`
locally (or on your own machines). LightPool is still in development; there is
no production network.

External apps integrate through the **local** `lightpool-clob-index`
(HTTP + WS). Do not talk to the node RPC/WS from the app.

This skill is for external app developers, not node developers.

## What you get

| Capability | How |
|------------|-----|
| Blockchain orderbook (spot CLOB) | Sign orders with SDK → submit via local clob-index |
| Prediction markets | Event contract + YES/NO outcome tokens traded on spot books |
| Balances | Bridge deposit (user cash) or indexed account balances API |
| Live book feeds | Local clob-index WS `orderbook_delta` |

## Download packages

Create a workspace and clone the release packages (side by side):

```bash
mkdir -p ~/work/lightpool-labs
cd ~/work/lightpool-labs

git clone git@github.com:lightpool-labs/lightpool-node.git
git clone git@github.com:lightpool-labs/lightpool-clob-index.git
# Optional: signing SDK for the app
git clone git@github.com:lightpool-labs/lightpool-sdk-rust.git
```

HTTPS alternative: `https://github.com/lightpool-labs/<repo>.git`.

| Package | Role |
|---------|------|
| `lightpool-node` | Local validator binary + CLI (not a cloud API) |
| `lightpool-clob-index` | Local CLOB HTTP/WS indexer (not a cloud API) |
| `lightpool-sdk-rust` | Offline tx signing for your app |

## Run LightPool node (local)

`lightpool-node` does **not** need LightPool source. Put prebuilt release
archives under `lightpool-node/bin/`:

- `lightpool-v*.tar.gz`
- `lightpool-cli-v*.tar.gz`

Then unpack and put binaries on `PATH`:

```bash
cd ~/work/lightpool-labs/lightpool-node
# Place the release archives in bin/ first
cargo build --release
source ./env.sh
```

You should have `lightpool` and `lightpool-cli` available.

Create a wallet (once), then start the node in its own terminal:

```bash
lightpool-cli create-wallet --force
lightpool-cli address

lightpool
```

Default local node0 ports (keep the process running):

| Service | URL |
|---------|-----|
| Mempool / front | `127.0.0.1:26000` |
| HTTP RPC | `http://127.0.0.1:26300` |
| WebSocket | `ws://127.0.0.1:26400` |

Press Ctrl+C to stop the node. Details: `lightpool-node/README.md`.

## Run lightpool-clob-index (local)

Start **after** the node is up. clob-index talks to the local node; your app
talks only to clob-index.

```bash
cd ~/work/lightpool-labs/lightpool-clob-index
cp -n .env.example .env
cargo run --release
```

`.env.example` defaults (local only):

| Env | Default |
|-----|---------|
| `HOST` / `PORT` | `0.0.0.0` / `3002` |
| `LIGHTPOOL_RPC_URL` | `http://127.0.0.1:26300` |
| `LIGHTPOOL_WS_URL` | `ws://127.0.0.1:26400` |
| `ENABLE_INDEXER` | `true` |

App-facing endpoints (local):

- HTTP: `http://127.0.0.1:3002` (routes under `/api`)
- WS: `ws://127.0.0.1:3002/api/ws`

## Integration path

Your app connects **only** to the local clob-index.

- Market data: HTTP books + WS `orderbook_delta` / `quote` / `user`
- Execution: build and sign txs with `lightpool-sdk` → `POST /api/tx/submit`

## Integrator workflow

1. Download and run `lightpool-node`, then `lightpool-clob-index` (sections above).
2. Create or load a `Signer` → user `Address` (SDK, offline signing only).
3. Fund balances (typically EVM bridge deposit → LP token).
4. Discover markets: `GET /api/markets` or `/api/markets/slug/:slug`.
5. Trade: sign `place_order` / `cancel_order` / `update_order` → `POST /api/tx/submit`.
6. Read the book: `GET /api/spot/:spot_market/book` or WS `orderbook_delta`.

### Sign then submit via clob-index

```rust
use lightpool_sdk::{
    ActionBuilder, OrderParamsType, OrderSide, PlaceOrderParams,
    Signer, TimeInForce, TransactionBuilder,
};

let signer = Signer::new(); // or load existing key

let action = ActionBuilder::place_order(
    market_address, // ContractAddress of the spot market
    PlaceOrderParams {
        side: OrderSide::Buy,
        amount: 2_000_000,
        order_type: OrderParamsType::Limit {
            tif: TimeInForce::GTC,
        },
        limit_price: 50_000_000_000,
        token_address: quote_or_base_token, // ContractAddress
    },
)?;

let tx = TransactionBuilder::new()
    .sender(signer.address())
    .expiration(u64::MAX)
    .add_action(action)
    .build_and_sign_only(&signer)?;

// POST signed tx to http://127.0.0.1:3002/api/tx/submit
```

## Critical types

| Type | Meaning |
|------|---------|
| `Address` | User account (20 bytes, Ethereum-style) |
| `ContractAddress` | Token, spot market, event contract, vault (8 bytes, module-prefixed) |

Do **not** treat user addresses and contract addresses as interchangeable.

## Do not confuse

- **Bridge deposit** (EVM → LightPool LP token) ≠ **vault** `deposit_vault` ≠ **token** mint
- Connect to **local clob-index** for books, quotes, user events, and tx submit — not the node
- `lightpool-node` and `lightpool-clob-index` are **local processes**, not hosted SaaS
- LightPool has **no production** network yet — local / test only

## Repo map

| Path | Role |
|------|------|
| `lightpool-node/` | Download, unpack binaries, run local validator |
| `lightpool-clob-index/` | Download, run local CLOB HTTP/WS (`:3002`) |
| `lightpool-sdk-rust/` | Sign transactions offline (submit via clob-index) |
| `lightpool-bridge/` | Optional EVM deposit/withdraw |

## Additional resources

- HTTP/WS endpoint table: [api-reference.md](api-reference.md)
- Setup / examples index: [examples.md](examples.md)
