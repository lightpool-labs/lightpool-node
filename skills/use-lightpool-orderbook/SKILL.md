---
name: use-lightpool-orderbook
description: >-
  Integrate an external system with LightPool, a blockchain orderbook that
  also supports prediction markets. Use when another product needs on-chain
  CLOB matching, spot or event/prediction books, place/cancel/update orders,
  orderbook feeds, or lightpool-clob-index integration.
---

# Use LightPool as an Orderbook

LightPool is a **blockchain orderbook**. It provides on-chain CLOB matching and
settlement, and integrates **prediction markets** (event contracts with YES/NO
books) on top of that same orderbook model.

External apps integrate through **`lightpool-clob-index`** (HTTP + WS).
Do not talk to the node RPC/WS directly.

This skill is for external app developers, not node developers.
LightPool is still in development; there is no production network yet.

## What you get

| Capability | How |
|------------|-----|
| Blockchain orderbook (spot CLOB) | Sign orders with SDK → submit via clob-index |
| Prediction markets | Event contract + YES/NO outcome tokens traded on spot books |
| Balances | Bridge deposit (user cash) or indexed account balances API |
| Live book feeds | clob-index WS `orderbook_delta` |

## Integration path

Run **LightPool node** + **`lightpool-clob-index`** (default `:3002`).
Your app connects **only** to clob-index.

- Market data: HTTP books + WS `orderbook_delta` / `quote` / `user`
- Execution: build and sign txs with `lightpool-sdk` → `POST /api/tx/submit`

Default clob-index endpoints:

- HTTP: `http://127.0.0.1:3002`
- WS: `ws://127.0.0.1:3002/api/ws`

## Integrator workflow

1. Start LightPool node and `lightpool-clob-index`.
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
- Connect to **clob-index** for books, quotes, user events, and tx submit — not the node
- LightPool has **no production** network yet — local / test only

## Repo map (workspace root)

| Path | Role |
|------|------|
| `lightpool-clob-index/` | Indexer + CLOB HTTP/WS (`:3002`) — primary integration surface |
| `lightpool-sdk-rust/` | Sign transactions offline (submit via clob-index) |
| `lightpool-bridge/` | EVM deposit/withdraw |

## Additional resources

- HTTP/WS endpoint table: [api-reference.md](api-reference.md)
- Runnable examples index: [examples.md](examples.md)
