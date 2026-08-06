# LightPool integrator API reference

LightPool is a blockchain orderbook with prediction-market integration.
**Not an online service** — run `lightpool-node` and `lightpool-clob-index`
locally, then integrate via **local clob-index only**.

See [SKILL.md](SKILL.md) for download and run steps.

## clob-index (local)

Default listen: `HOST`/`PORT` → `0.0.0.0:3002`.

Upstream node is owned by clob-index (your app does not call these):

| Env | Default |
|-----|---------|
| `LIGHTPOOL_RPC_URL` | `http://127.0.0.1:26300` |
| `LIGHTPOOL_WS_URL` | `ws://127.0.0.1:26400` |
| `QUERY_ACCOUNT` | zero address |
| `ENABLE_INDEXER` | `true` |

All HTTP/WS routes are under `/api`.

### HTTP

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health`, `/api/ready` | Liveness / readiness |
| GET | `/api/markets` | List / filter markets |
| GET | `/api/markets/slug/:slug` | Market by slug |
| GET | `/api/spot/:spot_market/book` | Book snapshot (`depth` query) |
| GET | `/api/spot/:spot_market/info` | Market info |
| POST | `/api/accounts/:address/balances` | Account balances |
| GET | `/api/orders`, `/api/orders/query` | Indexed orders |
| POST | `/api/tx/submit` | Submit signed transaction |
| GET | `/api/vaults`, `/api/vaults/address/:address` | Vault queries |

`:spot_market` is the spot market `ContractAddress` string form used by the indexer.

### WebSocket — `ws://127.0.0.1:3002/api/ws`

Request shape (`op` + channel fields):

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

Unsubscribe with `op: "unsubscribe"` and the same channel/key fields.

## Signing helpers (SDK, offline only)

Use `lightpool-sdk` to build and sign transactions, then submit via
`POST /api/tx/submit`. Do not call node `submitTransaction` / `call` from the
integrator.

Common `ActionBuilder` writes:

| Method | Use |
|--------|-----|
| `place_order` | Limit / market orders |
| `place_order_group` | Parent + TP/SL group |
| `cancel_order` / `update_order` | Manage resting orders |
| `create_event_contract` / `mint_event_contract` / … | Prediction markets |
| `deposit_vault` / `withdraw_vault` / … | Vault (not bridge) |

### `PlaceOrderParams` fields

| Field | Notes |
|-------|-------|
| `side` | `OrderSide::Buy` / `Sell` |
| `amount` | Size in token scale units |
| `order_type` | `Limit { tif }` or `Market { slippage }` |
| `limit_price` | Limit price (also used as market bound depending on type) |
| `token_address` | `ContractAddress` of the token being spent/locked for this side |

Amounts and prices use on-chain integer scale. Prefer market metadata from
clob-index (`/api/spot/:spot_market/info`, `/api/markets`) when sizing orders.

---

## Bridge vs vault

| Mechanism | When to use |
|-----------|-------------|
| `lightpool-bridge` deposit/withdraw | User cash from EVM (MetaMask) into LP token |
| Vault `deposit_vault` | Vault product, not the user bridge |
