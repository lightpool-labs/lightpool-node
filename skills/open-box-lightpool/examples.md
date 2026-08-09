# App integration patterns (UC2 spot)

Venue assumed running: clob-index at `http://127.0.0.1:3002`.

## Discover markets

```http
GET /api/markets?limit=20
GET /api/markets/slug/<slug>
GET /api/spot/<spot_market>/info
```

Use returned `ContractAddress` values for base, quote, and spot market in the app.

## Read the book

```http
GET /api/spot/<spot_market>/book?depth=10
```

Live:

```json
{
  "op": "subscribe",
  "channel": "orderbook_delta",
  "spot_market": "<spot ContractAddress>",
  "depth": 10
}
```

## Submit a signed place_order

1. Build `PlaceOrderParams` + `ActionBuilder::place_order(spot_market, params)`.
2. `TransactionBuilder` → `build_and_sign_only(&signer)`.
3. `POST /api/tx/submit` with body `{ "tx": <SignedTransaction> }`.
4. On success, parse receipt / follow WS `user` for confirmation.

Sell locks **base** token; buy locks **quote** token (`token_address` field).

## Balances

```http
POST /api/accounts/<user_address>/balances
```

(Request body shape: token specs as required by clob-index accounts API.)

## SDK crate map

| Piece | Location |
|-------|----------|
| Signing SDK | `lightpool-sdk-rust` (`lightpool_sdk`) |
| Indexer HTTP/WS | `lightpool-clob-index` |
| Local venue package | `lightpool-node` (Docker node + clob-index) |
