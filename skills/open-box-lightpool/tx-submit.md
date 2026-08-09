# Transaction submit API

Endpoint: `POST /api/tx/submit`  
Base URL (local): `http://127.0.0.1:3002`

The app **builds and signs** the transaction with **`lightpool-sdk`**
(`lightpool-sdk-rust`), then POSTs the signed payload here. Do not invent the
`tx` JSON by hand.

---

## HTTP input

```json
{
  "tx": { /* SignedTransaction — see SDK below */ }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `tx` | `SignedTransaction` | Full signed tx from SDK (`serde` JSON) |

---

## HTTP output (success)

```json
{
  "digest": "<hex string>",
  "receipt": {
    "transaction_digest": "<Digest>",
    "status": "Success",
    "events": [ /* TransactionEvent[] */ ],
    "block_num": 0
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `digest` | string | Transaction digest hex |
| `receipt` | `TransactionReceipt` | SDK receipt (status, events, block) |

On execution failure the API returns an error (HTTP error body); do not treat
failed receipts as success.

---

## Build `tx` with lightpool-sdk (required)

Package: **`lightpool-sdk-rust`** (crate `lightpool_sdk`).

### Types

| SDK type | Role |
|----------|------|
| `Signer` | User key; produces `Address` |
| `ActionBuilder` | Build module actions (`place_order`, `cancel_order`, …) |
| `TransactionBuilder` | Assemble + sign → `SignedTransaction` |
| `PlaceOrderParams` | Spot order fields |
| `SignedTransaction` | Value of request field `tx` |
| `TransactionReceipt` | Inside submit response |

### Spot place-order example

```rust
use lightpool_sdk::{
    ActionBuilder, OrderParamsType, OrderSide, PlaceOrderParams,
    Signer, TimeInForce, TransactionBuilder,
};

let signer: Signer = /* load app user key */;

let action = ActionBuilder::place_order(
    spot_market, // ContractAddress
    PlaceOrderParams {
        side: OrderSide::Buy, // or Sell
        amount: /* u64 on-chain scale */,
        order_type: OrderParamsType::Limit {
            tif: TimeInForce::GTC,
        },
        limit_price: /* u64 on-chain scale */,
        // Sell → base token; Buy → quote token
        token_address: quote_or_base_token,
    },
)?;

let signed: lightpool_sdk::lightpool_types::SignedTransaction =
    TransactionBuilder::new()
        .sender(signer.address())
        .expiration(u64::MAX)
        .add_action(action)
        .build_and_sign_only(&signer)?;

// Serialize `signed` as JSON field `tx` and POST /api/tx/submit
```

### `PlaceOrderParams`

| Field | Type | Notes |
|-------|------|--------|
| `side` | `OrderSide` | `Buy` / `Sell` |
| `amount` | u64 | Size in on-chain scale |
| `order_type` | `OrderParamsType` | `Limit { tif }` or `Market { slippage }` |
| `limit_price` | u64 | Limit / bound price in on-chain scale |
| `token_address` | `ContractAddress` | Token locked for this side |

### Other actions (same submit path)

Build with `ActionBuilder`, sign with `TransactionBuilder`, POST the same
`{ "tx": … }`:

- `cancel_order` / `update_order`
- `place_order_group`
- token `transfer` / `mint` when the product needs funding txs

### `SignedTransaction` shape (conceptual)

Produced by the SDK; fields include:

```text
SignedTransaction {
  transaction: {
    sender: Address,
    account: Option<Address>,   // agent txs
    expiration: u64,
    actions: [{ contract, action, params }],
  },
  signature: Signature,
  scheme: AuthScheme,           // default LightPoolNative
}
```

Serialize with the SDK’s serde (same types the indexer deserializes). Prefer
posting the value returned by `build_and_sign_only` rather than hand-writing
JSON.

---

## Agent checklist

1. Create `Signer` for the app user.  
2. Build action(s) via `ActionBuilder`.  
3. `TransactionBuilder` → `build_and_sign_only` → `SignedTransaction`.  
4. `POST /api/tx/submit` with body `{ "tx": <SignedTransaction> }`.  
5. On success read `digest` + `receipt`; optionally confirm via WS `user` / HTTP orders.
