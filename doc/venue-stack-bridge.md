# Venue stack + bridge

**Terminals: 4** (1 reused for sequential setup; 2/3/4 keep open)

## Accounts

| Role | Address | Private key | Where used |
|------|---------|-------------|------------|
| **Deployer** (Reth `--dev` #0) | `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` | `$DEV_KEY` below | forge DeployLocal; pays gas; mints EVM MockUSDT |
| **Maker / validator** | same as Deployer after `import-wallet --private-key $DEV_KEY` → `~/.lightpool/wallet.json` | `$DEV_KEY` | LightPool node signer; `liquidity-maker`; Bridge.deposit in **init** to get LP USDT |
| **User** (MetaMask) | `0xC019cECd52FE1f68b53daf766c4aF0Dea667A2c7` | import in MetaMask (see Cash UI / team notes) | frontend Cash deposit / withdraw / trade |

In this flow **Deployer ≡ Maker/validator** (one key). Fresh clear → first LP USDT is `0x0200000000000001`.

| Token | Chain | Meaning |
|-------|-------|---------|
| **ETH_USDT** | Reth `:8545` | EVM MockUSDT (`ETH_USDT=…` in `.env.bridge`) |
| **LP USDT / CASH** | LightPool | Bridge LP token (`CASH_TOKEN_ADDRESS`, expect `0x0200…0001` after wipe) |
| **BRIDGE** | Reth | EVM Bridge contract |

Paste once per shell: workspace paths, RPC endpoints, maker deposit size, and market bootstrap knobs.

```bash
export LABS=~/work/lightpool-labs
export DEV_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
export PATH="$HOME/.foundry/bin:$LABS/lightpool-node/tools/reth/bin:$LABS/lightpool-node/bin:$PATH"
export RETH_RPC=http://127.0.0.1:8545
export LP_RPC=http://127.0.0.1:26300
export LIGHTPOOL_CLOB_INDEX_HTTP=http://127.0.0.1:3002
export LIGHTPOOL_CLOB_INDEX_WS=ws://127.0.0.1:3002
export USER_ETH=0xC019cECd52FE1f68b53daf766c4aF0Dea667A2c7
export MAX_MARKETS=4
export MINT_AMOUNT=1000000000000000
export MAKER_LP_DEPOSIT_WHOLE=20000000000
```

## Terminal 1 — build

Build the LightPool node CLI, put it on PATH, and import the shared Deployer/Maker wallet.

```bash
cd "$LABS/lightpool-node"
cargo build --release
source ./env.sh
lightpool import-wallet --private-key "$DEV_KEY" --force
lightpool address
```

Build the CLOB indexer binary and install it into `lightpool-node/bin/`.

```bash
cd "$LABS/lightpool-clob-indexer"
cargo build --release --bin lightpool-clob-indexer
cp -f target/release/lightpool-clob-indexer "$LABS/lightpool-node/bin/"
```

Build the off-chain `lightpool-bridge` binary (Admin UI + route watcher).

```bash
cd "$LABS/lightpool-bridge"
cargo build --release
```

## Terminal 2 — Reth (keep open)

Download the Reth binary if needed, then start local EVM (`:8545` / `:8546`). Keep this terminal open.

```bash
cd "$LABS/lightpool-node"
./tools/reth/download.sh
./tools/reth/run-dev.sh
```

## Terminal 1 — venue + deploy

Start the LightPool venue stack in Docker (validator + related services). Drop `--no-cache` on rebuild if nothing changed.

```bash
cd "$LABS/lightpool-node/docker"
[ -f .env ] || cp .env.example .env
./prepare-binaries.sh
docker compose down
docker compose build --no-cache
docker compose up -d
```

Deploy MockUSDT + EVM Bridge on Reth; write `.env.bridge` and empty `lightpool-bridge/bridge-config.json`.

```bash
cd "$LABS/lightpool-node/scripts/event-contract-setup"
USER_ETH="$USER_ETH" python3 00_bridge_bootstrap.py --phase deploy
```

## Terminal 3 — lightpool-bridge (keep open)

Start the bridge process against `bridge-config.json` (Admin UI `:8787`). Keep this terminal open.

```bash
cd "$LABS/lightpool-bridge"
./target/release/lightpool-bridge --config "$LABS/lightpool-bridge/bridge-config.json"
```

## Terminal 1 — create + fund + app

Create the local inbound bridge + LP USDT, auto-upsert `reth-usdt` route, then fund maker LP via EVM `deposit`.

```bash
cd "$LABS/lightpool-node"
source ./env.sh
cd "$LABS/lightpool-node/scripts/event-contract-setup"
python3 00_bridge_bootstrap.py --phase create
MAKER_LP_DEPOSIT_WHOLE="$MAKER_LP_DEPOSIT_WHOLE" python3 00_bridge_bootstrap.py --phase fund
```

Copy bridge env into the app Docker `.env`, then build and start the event-contract frontend/backend stack.

```bash
cd "$LABS/event-contract-app/docker"
[ -f .env ] || cp .env.example .env
for k in ETH_USDT BRIDGE CASH_TOKEN_ADDRESS CASH_TOKEN_SYMBOL; do
  v="$(grep -E "^${k}=" "$LABS/lightpool-node/scripts/event-contract-setup/.env.bridge" | cut -d= -f2- | tr -d '[:space:]')"
  test -n "$v" || continue
  if grep -qE "^${k}=" .env; then
    sed -i "s|^${k}=.*|${k}=${v}|" .env
  else
    echo "${k}=${v}" >> .env
  fi
done
./prepare-binaries.sh
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Terminal 4 — maker (keep open)

Run the liquidity maker (needs proxy for Polymarket). Replace `<live-polymarket-event-slug>` with a live event. Keep this terminal open.

```bash
cd "$LABS/lightpool-bot"
export HTTPS_PROXY=http://127.0.0.1:8118
export HTTP_PROXY=http://127.0.0.1:8118
export LIGHTPOOL_CLOB_INDEX_HTTP=http://127.0.0.1:3002
export LIGHTPOOL_CLOB_INDEX_WS=ws://127.0.0.1:3002
export LIGHTPOOL_COLLATERAL_TOKEN="$(grep -E '^CASH_TOKEN_ADDRESS=' "$LABS/event-contract-app/backend/.env" | cut -d= -f2 | tr -d '[:space:]')"
echo "LIGHTPOOL_COLLATERAL_TOKEN=$LIGHTPOOL_COLLATERAL_TOKEN"
cargo run -p lightpool-strategies --bin liquidity-maker -- \
  --polymarket-slug <live-polymarket-event-slug> \
  --bootstrap-markets \
  --max-markets "$MAX_MARKETS" \
  --mint-amount "$MINT_AMOUNT"
```

## User — MetaMask

Point MetaMask at local Reth, import the User account, then use the Cash UI.

```text
RPC http://127.0.0.1:8545
chainId 1337
import 0xC019cECd52FE1f68b53daf766c4aF0Dea667A2c7
UI http://127.0.0.1:3000 → Cash → Deposit → Markets buy/sell
```

## Terminal 1 — stop + clear all data

Ctrl+C: Terminal 4, 3, 2 first.

Tear down Docker stacks and wipe Reth/venue data, bridge env, bridge config, and bridge events DB so the next run starts from LP USDT `0x0200…0001`.

```bash
cd "$LABS/event-contract-app/docker" && docker compose down
cd "$LABS/lightpool-node/docker" && docker compose down
sudo rm -rf "$LABS/lightpool-node/docker/data"
sudo rm -rf "$LABS/lightpool-node/tools/reth/data/dev"
rm -f "$LABS/lightpool-node/scripts/event-contract-setup/.env.bridge"
rm -f "$LABS/lightpool-bridge/bridge-config.json"
rm -f "$LABS/lightpool-bridge/bridge-config-events.db" \
  "$LABS/lightpool-bridge/bridge-config-events.db-wal" \
  "$LABS/lightpool-bridge/bridge-config-events.db-shm"
```

Fresh retest → LP USDT is `0x0200000000000001` (not `…0019`).
