# clob-index API reference (app integration)

Local defaults: HTTP `http://127.0.0.1:3002`, WS `ws://127.0.0.1:3002/api/ws`.
All HTTP routes below are under `/api`.

Upstream node is configured on clob-index (`LIGHTPOOL_RPC_URL` /
`LIGHTPOOL_WS_URL`). The **app never calls the node**.

## HTTP

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health/health`, `/api/health/ready` | Liveness / readiness |
| GET | `/api/markets` | List / filter markets |
| GET | `/api/markets/slug/:slug` | Market by slug |
| GET | `/api/spot/:spot_market/book` | Book snapshot (`depth` query) |
| GET | `/api/spot/:spot_market/info` | Spot market info |
| GET | `/api/spot/:spot_market/bars` | Bars |
| POST | `/api/accounts/:address/balances` | Account balances |
| GET | `/api/orders`, `/api/orders/query` | Indexed orders |
| POST | `/api/tx/submit` | Submit signed transaction |
| GET | `/api/vaults`, `/api/vaults/address/:address` | Vault queries |

`:spot_market` is the spot market `ContractAddress` string used by the indexer.

### `POST /api/tx/submit`

Body: JSON with signed transaction field `tx` (`SignedTransaction` from
`lightpool-sdk`). Response includes digest + receipt on success.

## WebSocket — `ws://127.0.0.1:3002/api/ws`

```json
{
  "op": "subscribe",
  "channel": "orderbook_delta",
  "spot_market": "<spot ContractAddress>",
  "depth": 10
}
```

| Channel | Key field | Purpose |
|---------|-----------|---------|
| `orderbook_delta` | `spot_market` | Incremental book updates |
| `quote` | `spot_market` | Top-of-book quotes |
| `user` | `user_address` | User-scoped updates |
| `bars` | (see service) | Bar updates |

Unsubscribe with `op: "unsubscribe"` and the same channel/key fields.

## SDK actions (sign offline, submit via clob-index)

| `ActionBuilder` | Use |
|-----------------|-----|
| `place_order` | Limit / market orders on a spot market |
| `place_order_group` | Parent + TP/SL group |
| `cancel_order` / `update_order` | Manage resting orders |
| `transfer_token` / `mint` / … | Wallet funding flows when the product needs them |

### `PlaceOrderParams`

| Field | Notes |
|-------|-------|
| `side` | `OrderSide::Buy` / `Sell` |
| `amount` | Size in on-chain scale |
| `order_type` | `Limit { tif }` or `Market { slippage }` |
| `limit_price` | Limit / bound price in on-chain scale |
| `token_address` | Token locked for this side (base for sell, quote for buy) |

Prefer `/api/spot/:spot_market/info` and `/api/markets` when choosing scale and
tick size.
