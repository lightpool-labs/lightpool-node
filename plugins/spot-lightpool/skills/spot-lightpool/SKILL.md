---
name: spot-lightpool
description: >-
  LightPool is a blockchain L1 targeting 200k TPS with an on-chain spot
  orderbook (matching and settlement on chain). Users deploy their own node +
  clob-index; it is not an online SaaS. Integrate an external app via
  clob-index HTTP/WS and lightpool-sdk signed submit. Use when an AI agent
  wires an app for spot markets (e.g. AAPL/USDT): read books, subscribe to
  feeds, submit signed txs.
---

# Integrate an app with LightPool (spot)

This skill is for **AI agents** wiring an **application** to LightPool **spot**.

**Spot context:** LightPool is a **blockchain L1** targeting **200k TPS**, with
an **on-chain orderbook**: spot CLOB **matching and settlement** both run on
chain. Deploy the venue from
[lightpool-node](https://github.com/lightpool-labs/lightpool-node). Default
local clob-index: `http://127.0.0.1:3002` and `ws://127.0.0.1:3002/api/ws`.
The app talks **only** to clob-index (not node RPC/WS).

LightPool is **not an online SaaS**. Operators **deploy** their own L1 node +
clob-index; the app connects to that deployment’s clob-index URL.

## How the agent finds API details

Read these three docs in this skill folder (self-contained input/output):

| Doc | Contents |
|-----|----------|
| [http.md](http.md) | All HTTP routes: method, path, input, output |
| [ws.md](ws.md) | WebSocket subscribe/unsubscribe and message shapes |
| [tx-submit.md](tx-submit.md) | `POST /api/tx/submit` + how to build `tx` with **lightpool-sdk** |

Do not invent request/response fields. Prefer the JSON shapes in those docs.
For signed transactions, build with **`lightpool-sdk`**
([lightpool-sdk-rust](https://github.com/lightpool-labs/lightpool-sdk-rust))
as described in [tx-submit.md](tx-submit.md).

## Integration path

```
App ──HTTP/WS──► clob-index (:3002) ──► lightpool node
```

1. Discover markets / spot info → [http.md](http.md)  
2. Stream books / quotes / user → [ws.md](ws.md)  
3. Sign with SDK, submit → [tx-submit.md](tx-submit.md)

## Critical types

| Type | Meaning |
|------|---------|
| `Address` | User account (20-byte `0x…`) |
| `ContractAddress` | Token or spot market (8-byte module-prefixed `0x…`) |

Spot markets are typically `0x03…`; tokens `0x02…`. Do not mix them.

## Agent rules

1. Base URL `http://127.0.0.1:3002` (paths under `/api`).  
2. Market data + execution only via clob-index.  
3. Sign offline with `lightpool-sdk`; POST `{ "tx": SignedTransaction }`.  
4. Sell locks **base** token; buy locks **quote** token in `PlaceOrderParams`.  
5. Point the app at the **deployed** clob-index base URL (local default
   `http://127.0.0.1:3002`); there is no public LightPool cloud API.
