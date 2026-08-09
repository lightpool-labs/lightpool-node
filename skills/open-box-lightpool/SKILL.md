---
name: open-box-lightpool
description: >-
  UC2: integrate an external app with a local LightPool spot orderbook via
  lightpool-clob-index HTTP/WS APIs and lightpool-sdk signing. Use when an AI
  agent builds or wires an app against local node + clob-index for spot markets
  (tokens + CLOB such as AAPL/USDT): discover markets, read books, submit signed
  txs, subscribe to orderbook feeds.
---

# UC2 — Integrate an app with LightPool (spot)

This skill is for **AI agents** wiring an **application** to LightPool.

**UC2 open-box context:** a local LightPool stack is available (`lightpool-node`
Docker: node + clob-index). The chain supports **spot** markets (base/quote CLOB,
e.g. AAPL/USDT) after tokens and a spot market exist on that venue.

LightPool is still in development; there is **no production** hosted endpoint.
The app talks only to **local clob-index**. Do not call node RPC/WS from the app.

Human ops for unpacking binaries / starting Docker / seeding tokens and markets
live in `lightpool-node/README.md` and `doc/`. This skill does **not** teach CLI
workflows.

## Integration path

```
App ──HTTP/WS──► lightpool-clob-index (:3002)
                      │
                      ▼
                 lightpool node (:26300 / :26400)
```

1. Assume local venue is up: clob-index `http://127.0.0.1:3002`, WS
   `ws://127.0.0.1:3002/api/ws`.
2. App holds a user `Signer` (offline). Derive user `Address`.
3. Discover spot markets / instruments via clob-index HTTP.
4. Read books: `GET /api/spot/:spot_market/book` or WS `orderbook_delta`.
5. Build actions with `lightpool-sdk` (`ActionBuilder` / `TransactionBuilder`),
   sign offline, `POST /api/tx/submit`.
6. Track fills / user updates via WS `user` and order/balance HTTP as needed.

## Critical types

| Type | Meaning |
|------|---------|
| `Address` | User account (20 bytes, Ethereum-style `0x…`) |
| `ContractAddress` | Token, spot market, … (8 bytes, module-prefixed `0x…`) |

Spot markets are typically `0x03…`; tokens `0x02…`. Never treat them as
interchangeable.

## App must use clob-index

| Concern | App uses |
|---------|----------|
| Market list / metadata | `GET /api/markets`, `/api/markets/slug/:slug`, `/api/spot/:spot_market/info` |
| Order book snapshot | `GET /api/spot/:spot_market/book` |
| Live book / quotes | WS `orderbook_delta`, `quote` |
| User-scoped updates | WS `user` |
| Balances | `POST /api/accounts/:address/balances` |
| Orders index | `GET /api/orders`, `/api/orders/query` |
| Execution | Sign with SDK → `POST /api/tx/submit` |

Do **not** point the app at node `submitTransaction` / node WS.

## Sign then submit

Crate: `lightpool-sdk` (package `lightpool-sdk-rust`).

```rust
use lightpool_sdk::{
    ActionBuilder, OrderParamsType, OrderSide, PlaceOrderParams,
    Signer, TimeInForce, TransactionBuilder,
};

let signer = /* load app user key */;
let action = ActionBuilder::place_order(
    spot_market, // ContractAddress of the spot market
    PlaceOrderParams {
        side: OrderSide::Buy, // or Sell
        amount: /* scaled size */,
        order_type: OrderParamsType::Limit {
            tif: TimeInForce::GTC,
        },
        limit_price: /* scaled price */,
        // Sell locks base token; Buy locks quote token
        token_address: quote_or_base_token,
    },
)?;

let tx = TransactionBuilder::new()
    .sender(signer.address())
    .expiration(u64::MAX)
    .add_action(action)
    .build_and_sign_only(&signer)?;

// POST JSON { "tx": <SignedTransaction> } to
// http://127.0.0.1:3002/api/tx/submit
```

Other common writes the app may sign the same way: `cancel_order`,
`update_order`, `place_order_group`, token `transfer` / `mint` when the product
requires it. Prefer market metadata from clob-index when sizing amounts/prices
(on-chain integer scale).

## Agent rules

When implementing or reviewing app integration:

1. Default base URL: `http://127.0.0.1:3002` (routes under `/api`).
2. Wire market data and execution through clob-index only.
3. Keep signing offline with `lightpool-sdk`; never embed node RPC clients in the app path.
4. Model spot instruments with separate `ContractAddress` for base, quote, and spot market.
5. For UC2 spot demos, assume tokens + spot market already exist on the local venue (seeded by operators); the app discovers them via `/api/markets` or known addresses.
6. No production LightPool URL — local / self-hosted only.

## Package map

| Package | Role for the app |
|---------|------------------|
| `lightpool-node` | Local venue (node + Docker); ops docs for humans |
| `lightpool-clob-index` | App-facing HTTP/WS (`:3002`) |
| `lightpool-sdk-rust` | Offline tx signing |

## Additional resources

- Endpoint table: [api-reference.md](api-reference.md)
- Signing / submit patterns: [examples.md](examples.md)
