# HTTP API (clob-index)

Base URL (local): `http://127.0.0.1:3002`  
All paths below are under `/api`.

Amounts/prices in responses are usually **decimal strings** (human-readable scale), unless a field is named `*_raw` (integer).

---

## Health

### `GET /api/health/health`

**Input:** none  

**Output:**

```json
{ "status": "ok" }
```

### `GET /api/health/ready`

**Input:** none  

**Output:**

```json
{
  "status": "ready",
  "node": true,
  "indexer": {
    "connected": true,
    "catching_up": false,
    "block_num": 0,
    "digest": "<string>",
    "tx_count": 0,
    "market_count": 0,
    "vault_count": 0
  }
}
```

`status` is `"ready"` or `"degraded"`.

---

## Markets

### `GET /api/markets`

**Input (query):**

| Param | Type | Notes |
|-------|------|--------|
| `limit` | u32 | default 100, max 100 |
| `offset` | u32 | default 0 |
| `slug` | string | optional single slug |
| `slugs` | string | optional CSV, max 100 |
| `market_ids` | string | optional CSV of UUIDs, max 100 |
| `market_addresses` | string | optional CSV, max 100 |
| `state` | string | optional filter |
| `order` | string | `slug` \| `question` \| default resolution deadline |
| `ascending` | bool | optional |

**Output:**

```json
{
  "markets": [
    {
      "id": "<uuid>",
      "slug": "<string>",
      "question": "<string>",
      "icon_url": "<string|omit>",
      "market_address": "<ContractAddress hex>",
      "collateral_token": "<ContractAddress hex>",
      "yes_token": "<ContractAddress hex>",
      "no_token": "<ContractAddress hex>",
      "yes_spot_market": "<ContractAddress hex>",
      "no_spot_market": "<ContractAddress hex>",
      "state": "<string>",
      "resolution_deadline": 0
    }
  ],
  "total": 0,
  "limit": 100,
  "offset": 0
}
```

### `GET /api/markets/slug/:slug`

**Input:** path `slug`  

**Output:** one `Market` object (same fields as an element of `markets` above).

---

## Spot

`:spot_market` = spot market `ContractAddress` hex string (e.g. `0x03…`).

### `GET /api/spot/:spot_market/book`

**Input (query):**

| Param | Type | Notes |
|-------|------|--------|
| `depth` | u32 | default 10, clamped 1…50 |

**Output:**

```json
{
  "sequence": 0,
  "bids": [{ "price": "<string>", "size": "<string>" }],
  "asks": [{ "price": "<string>", "size": "<string>" }],
  "last_trade_price": "<string|omit>"
}
```

### `GET /api/spot/:spot_market/info`

**Input (query):**

| Param | Type | Notes |
|-------|------|--------|
| `account` | string | **required** user `Address` hex |

**Output:**

```json
{
  "last_price": "<string|null>",
  "state": "<string>",
  "min_order_size": "<string>",
  "tick_size": "<string>",
  "maker_fee_bps": 10,
  "taker_fee_bps": 20,
  "allow_market_orders": true
}
```

### `GET /api/spot/:spot_market/bars`

**Input (query):**

| Param | Type | Notes |
|-------|------|--------|
| `interval` | string | `1m` \| `5m` \| `15m` \| `1h` \| `4h` \| `1d` (default `1m`) |
| `from` | u64 | optional unix seconds |
| `to` | u64 | optional unix seconds |
| `limit` | usize | default 500, max 5000 |

**Output:**

```json
{
  "spot_market": "<normalized key>",
  "interval": "1m",
  "bars": [
    {
      "type": "bar_closed",
      "spot_market": "<string>",
      "interval": "1m",
      "start_ts": 0,
      "open": "<string>",
      "high": "<string>",
      "low": "<string>",
      "close": "<string>",
      "volume": "<string>",
      "trade_count": 0,
      "closed": true
    }
  ],
  "forming": {
    "type": "bar",
    "spot_market": "<string>",
    "interval": "1m",
    "start_ts": 0,
    "open": "<string>",
    "high": "<string>",
    "low": "<string>",
    "close": "<string>",
    "volume": "<string>",
    "trade_count": 0,
    "closed": false
  }
}
```

`forming` may be null / omitted for non-`1m` intervals.

---

## Accounts

### `POST /api/accounts/:address/balances`

**Input:**

- Path: `address` = user `Address` hex  
- Body:

```json
{
  "tokens": [
    { "symbol": "USDT", "address": "<token ContractAddress hex>" }
  ]
}
```

**Output:** array of balances (order follows request; zeros may be returned on errors for non-YES/NO symbols):

```json
[
  {
    "token": "<ContractAddress hex>",
    "symbol": "USDT",
    "total": "<string>",
    "locked": "<string>",
    "available": "<string>"
  }
]
```

---

## Orders

### `GET /api/orders`

**Input (query):**

| Param | Type | Notes |
|-------|------|--------|
| `user_address` | string | **required** |

**Output:** array of listed orders:

```json
[
  {
    "id": "<uuid>",
    "market_id": "<uuid>",
    "market_slug": "<string>",
    "question": "<string>",
    "outcome": "<string>",
    "side": "<string>",
    "price": "<string>",
    "size": "<string>",
    "status": "<string>",
    "chain_order_id": "<string>",
    "spot_market": "<ContractAddress hex>",
    "user_address": "<Address hex>",
    "size_raw": 0,
    "filled_raw": 0
  }
]
```

### `GET /api/orders/query`

**Input (query)** — one of:

1. By chain id: `spot_market` + `chain_order_id` (+ optional `user_address`)  
2. By open match: `spot_market` + `user_address` + `side` + `price` + `size_raw`

**Output:**

```json
{
  "id": "<uuid>",
  "market_id": "<uuid>",
  "market_slug": "<string>",
  "question": "<string>",
  "outcome": "<string>",
  "side": "<string>",
  "price": "<string>",
  "size": "<string>",
  "status": "<string>",
  "chain_order_id": "<string>",
  "spot_market": "<string>",
  "user_address": "<string>",
  "size_raw": 0,
  "filled_raw": 0
}
```

### `GET /api/orders/:id/cancel-context`

**Input:**

- Path: `id` = order UUID  
- Query: `user_address` (required)

**Output:**

```json
{
  "order": { /* Order fields */ },
  "chain_order_id": "<string>",
  "spot_market": "<string>"
}
```

---

## Vaults

### `GET /api/vaults`

**Input (query):** pagination similar to markets (`limit`, `offset`, … as implemented).  

**Output:**

```json
{
  "vaults": [
    {
      "id": "<uuid>",
      "name": "<string>",
      "vault_address": "<string>",
      "vault_account": "<string>",
      "manager": "<string>",
      "quote_token": "<string>",
      "share_token": "<string>",
      "equity": "<string>",
      "user_deposit": "<string>",
      "portfolio": [
        {
          "market": "<string>",
          "amount": "<string>",
          "last_price": "<string|omit>",
          "quote_value": "<string|omit>"
        }
      ],
      "allow_deposit": true,
      "is_closed": false
    }
  ],
  "total": 0,
  "limit": 100,
  "offset": 0
}
```

### `GET /api/vaults/address/:address`

**Input:** path vault address  

**Output:** one `Vault` object (same shape as an element of `vaults`).

---

## Transaction submit

See [tx-submit.md](tx-submit.md) for `POST /api/tx/submit` input/output and SDK signing.
