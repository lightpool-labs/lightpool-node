# Examples and reference code

LightPool is a blockchain orderbook; prediction markets use the same CLOB
via event contracts. Integrate through **clob-index**. Prefer reading these
files over inventing new call patterns.

## clob-index

Primary surface for app developers:

| Piece | Path |
|-------|------|
| Service | `lightpool-clob-index/` |
| HTTP routes | `lightpool-clob-index/src/http/` |
| WS channels | `lightpool-clob-index/src/ws/` |

Default endpoints:

- HTTP: `http://127.0.0.1:3002` (routes under `/api`)
- WS: `ws://127.0.0.1:3002/api/ws`

## Local stack for apps

Typical packages side by side: `lightpool-node`, `lightpool-bridge`,
`lightpool-clob-index`, `lightpool-sdk-rust`.

## SDK (signing only)

Crate: `lightpool-sdk` in `lightpool-sdk-rust/`.

Use for offline sign of `place_order` / `cancel_order` / etc., then POST to
`/api/tx/submit`. Do not use SDK clients against node RPC/WS from an app.

| Type | Role |
|------|------|
| `Signer` | Keys / user `Address` |
| `TransactionBuilder`, `ActionBuilder` | Build and sign txs |
| `Address`, `ContractAddress`, order params | Types for signed payloads |
