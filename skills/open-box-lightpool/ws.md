# WebSocket API (clob-index)

URL (local): `ws://127.0.0.1:3002/api/ws`

Client sends JSON text frames. Server replies with JSON text frames.

---

## Client → server (input)

### Subscribe / unsubscribe envelope

```json
{
  "op": "subscribe",
  "channel": "<channel>",
  "spot_market": "<optional ContractAddress hex>",
  "user_address": "<optional Address hex>",
  "depth": 10,
  "interval": "1m"
}
```

| Field | Type | Required when |
|-------|------|----------------|
| `op` | string | always: `subscribe` or `unsubscribe` |
| `channel` | string | always for subscribe; one of below |
| `spot_market` | string | `orderbook_delta`, `quote`, `bars` |
| `user_address` | string | `user` |
| `depth` | u32 | optional for `orderbook_delta` (default 10, clamp 1…50) |
| `interval` | string | optional for `bars` (default `1m`) |

### Channels

| `channel` | Key field | Purpose |
|-----------|-----------|---------|
| `orderbook_delta` | `spot_market` | Book snapshot then deltas |
| `quote` | `spot_market` | Best bid/ask |
| `user` | `user_address` | User orders / trades |
| `bars` | `spot_market` (+ `interval`) | OHLC bars |

Unsubscribe: same shape with `"op": "unsubscribe"` and the same channel/key.

---

## Server → client (output)

### Control / errors

**Subscribed:**

```json
{ "type": "subscribed", "channel": "orderbook_delta", "key": "<spot_market or user>" }
```

**Unsubscribed:**

```json
{ "type": "unsubscribed", "channel": "orderbook_delta", "key": "<…>" }
```

**Error:**

```json
{ "type": "error", "error": "<message>" }
```

---

### `orderbook_delta`

After subscribe, server typically sends a snapshot then incremental deltas.

**Snapshot** (`type` = `"snapshot"` or service-defined snapshot type string):

```json
{
  "type": "<string>",
  "spot_market": "<string>",
  "sequence": 0,
  "bids": [{ "price": "<string>", "size": "<string>" }],
  "asks": [{ "price": "<string>", "size": "<string>" }],
  "last_trade_price": "<string|omit>"
}
```

**Delta:**

```json
{
  "type": "<string>",
  "spot_market": "<string>",
  "sequence": 0,
  "block_num": 0,
  "bids": [{ "price": "<string>", "size": "<string>" }],
  "asks": [{ "price": "<string>", "size": "<string>" }],
  "last_trade_price": "<string|omit>"
}
```

Size `"0"` on a delta level means remove that price level.

---

### `quote`

**Snapshot / delta:**

```json
{
  "type": "<string>",
  "spot_market": "<string>",
  "sequence": 0,
  "block_num": 0,
  "best_bid": { "price": "<string>", "size": "<string>" },
  "best_ask": { "price": "<string>", "size": "<string>" },
  "last_trade_price": "<string|omit>"
}
```

`best_bid` / `best_ask` / `last_trade_price` may be omitted. Snapshot messages may omit `block_num`.

---

### `user`

**Order event:**

```json
{
  "type": "<string>",
  "event": "<string>",
  "user_address": "<Address hex>",
  "chain_order_id": "<string>",
  "block_num": 0,
  "id": "<uuid>",
  "market_id": "<uuid>",
  "market_slug": "<string>",
  "question": "<string>",
  "outcome": "<string>",
  "side": "<string>",
  "price": "<string>",
  "size": "<string>",
  "status": "<string>"
}
```

**Trade / fill:**

```json
{
  "type": "<string>",
  "user_address": "<Address hex>",
  "chain_order_id": "<string>",
  "order_id": "<uuid>",
  "market_slug": "<string>",
  "outcome": "<string>",
  "side": "<string>",
  "price": "<string>",
  "fill_amount": "<string>",
  "remaining_amount": "<string>",
  "is_fully_filled": false,
  "spot_market": "<string>",
  "block_num": 0
}
```

---

### `bars`

**History snapshot on subscribe:**

```json
{
  "type": "<string>",
  "spot_market": "<string>",
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

Live updates reuse the bar message shape (`type` often `bar` / `bar_closed`).
