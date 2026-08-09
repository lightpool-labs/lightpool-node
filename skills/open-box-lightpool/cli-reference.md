# lightpool CLI — UC2 quick reference

Default RPC: `http://localhost:26300` (`--rpc-url`).  
Default wallet: `~/.lightpool/wallet.json` (`--wallet-path`).

## Wallet

| Command | Purpose |
|---------|---------|
| `lightpool create-wallet --force` | New wallet |
| `lightpool import-wallet --private-key 0x… --force` | Import key (match Docker `LIGHTPOOL_PRIVATE_KEY`) |
| `lightpool address` | Print `Address` |

## Token

| Command | Purpose |
|---------|---------|
| `lightpool create-token --name … --symbol … --total-supply … [--mintable]` | Create token (`ContractAddress` `0x02…`) |
| `lightpool mint --token-address … --amount … [--to …]` | Mint (if mintable) |
| `lightpool transfer --token-address … --to … --amount …` | Transfer |
| `lightpool balance --token-address … [--account …]` | Balance |

## Spot

| Command | Purpose |
|---------|---------|
| `lightpool create-spot-market --name … --base-token … --quote-token …` | Spot CLOB (`0x03…`) |
| `lightpool place-order --spot-market … --side buy\|sell --amount … --price … --token-address …` | Place order |
| `lightpool get-book --spot-market … [--depth N]` | Order book |

### `place-order` notes

- **Sell** locks **base** (`--token-address` = base token)
- **Buy** locks **quote** (`--token-address` = quote token)
- `--tif gtc|ioc|fok` (default `gtc`); `--market` for market order
- Amounts/prices are human decimal strings (CLI scales them)

## Not UC2 (avoid here)

| Command | What it actually is |
|---------|---------------------|
| `lightpool create-market` | **Event contract** (prediction), not spot |
| `init-bridge` / `bridge-withdraw` | Bridge path — out of UC2 scope |
