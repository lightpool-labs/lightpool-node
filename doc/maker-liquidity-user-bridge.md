# Maker liquidity + user bridge deposit / withdraw

End-to-end **local** flow under a `lightpool-labs` workspace:

1. Download repos + install tools (Reth, Foundry)
2. Infrastructure (Reth, LightPool + Link, clob-index, app)
3. **Maker** runs `liquidity-maker` (Polymarket → LightPool book mirror)
4. **User** deposits / withdraws USDT via MetaMask + Cash UI

---

## Workspace layout

Create a root folder and put the downloaded packages side by side:

```text
lightpool-labs/
  tools/                 # optional (e.g. bridge-local config written by bootstrap)
  lightpool-node/        # node release package
    bin/                 # lightpool (node + client subcommands)
    tools/reth/          # download.sh + run-dev.sh
  lightpool-bridge/      # EVM MockUSDT + Bridge (Foundry)
  lightpool-clob-indexer/  # CLOB index HTTP/WS
  lightpool-bot/         # liquidity-maker
  event-contract-app/    # frontend + backend
```

You download / clone at least:

| Package | Role |
|---------|------|
| `lightpool-node` | Prebuilt `lightpool` under `bin/` |
| `lightpool-bridge` | Deploy MockUSDT + Bridge on Reth |
| `lightpool-clob-indexer` | Index books / orders for app + maker |
| `lightpool-bot` | Polymarket → LightPool liquidity maker |
| `event-contract-app` | Markets UI + Cash deposit/withdraw |

**Accounts**

| Role | Address / key |
|------|----------------|
| User (MetaMask) | `0xC019cECd52FE1f68b53daf766c4aF0Dea667A2c7` |
| Maker / validator | `lightpool address` (`~/.lightpool/wallet.json`) |
| Deployer (Reth `--dev` #0) | `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` |

**Funding rule:** bridge LP USDT (`0x0200…`) is **not** mintable by the maker wallet. Only Link `confirm_dep` after `Bridge.deposit` credits LP USDT. Maker funding is part of **init** (below).

---

## 0) Bootstrap workspace

```bash
mkdir -p ~/work/lightpool-labs
cd ~/work/lightpool-labs

# Place / clone the packages listed above into this folder, e.g.:
#   lightpool-node  lightpool-bridge  lightpool-clob-indexer
#   lightpool-bot   event-contract-app
```

### 0.1 Download Reth (`lightpool-node/tools/reth`)

```bash
cd ~/work/lightpool-labs/lightpool-node
./tools/reth/download.sh
```

Binary lands at `lightpool-node/tools/reth/bin/reth`.

### 0.2 Install Foundry (`forge` / `cast`)

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
# ensure on PATH for later terminals
export PATH="$HOME/.foundry/bin:$PATH"
forge --version
cast --version
```

### 0.3 Unpack LightPool binaries into `lightpool-node/bin`

`lightpool-node` does **not** need LightPool source. Put release archives in `lightpool-node/bin/` (or follow that package’s README), then:

```bash
cd ~/work/lightpool-labs/lightpool-node
# Place lightpool-v*.tar.gz under bin/ if not already there
cargo build --release
source ./env.sh
```

After that you should have:

```text
lightpool-node/bin/lightpool
```

### 0.4 Env (every new terminal)

```bash
cd ~/work/lightpool-labs
export PATH="$HOME/.foundry/bin:$PWD/lightpool-node/tools/reth/bin:$PWD/lightpool-node/bin:$PATH"
export RETH_RPC=http://127.0.0.1:8545
export LP_RPC=http://127.0.0.1:26300
export LP_CLI=$PWD/lightpool-node/bin/lightpool
export LIGHTPOOL_BIN=$LP_CLI
export NODE_WALLET=$HOME/.lightpool/wallet.json
export EVM_CHAIN_ID=1337
export PK=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
export USER_ETH=0xC019cECd52FE1f68b53daf766c4aF0Dea667A2c7

# Maker → clob-index
export LIGHTPOOL_CLOB_INDEX_HTTP=http://127.0.0.1:3002
export LIGHTPOOL_CLOB_INDEX_WS=ws://127.0.0.1:3002
```

Create / reuse the node wallet:

```bash
$LP_CLI --rpc-url $LP_RPC create-wallet || true
export VALIDATOR_ETH=$($LP_CLI --rpc-url $LP_RPC address | grep -oE '0x[0-9a-fA-F]{40}' | head -1)
echo "VALIDATOR_ETH=$VALIDATOR_ETH"
```

Maker signing key: prefer `~/.lightpool/wallet.json` (default for `liquidity-maker`), or set `LIGHTPOOL_PRIVATE_KEY`.

---

## 1) Infrastructure (one terminal each)

Keep each process running.

**A — Reth**

```bash
cd ~/work/lightpool-labs/lightpool-node
./tools/reth/run-dev.sh
```

**B — Deploy EVM USDT + Bridge** (before LightPool)

```bash
cd ~/work/lightpool-labs/lightpool-node/scripts/event-contract-setup
USER_ETH=0xC019cECd52FE1f68b53daf766c4aF0Dea667A2c7 \
  python3 00_bridge_bootstrap.py --phase deploy
```

This mints a large EVM USDT balance to the validator/maker on Reth (and a smaller amount to `USER_ETH`). It does **not** create LP USDT yet. It writes:

- `lightpool-node/scripts/event-contract-setup/.env.bridge`
- `tools/bridge-local/bridge-config.json`

**C — LightPool + Link**

```bash
cd ~/work/lightpool-labs
lightpool node --role validator \
  --bridge-config $PWD/tools/bridge-local/bridge-config.json
```

Or explicitly:

```bash
~/work/lightpool-labs/lightpool-node/bin/lightpool node --role validator \
  --bridge-config ~/work/lightpool-labs/tools/bridge-local/bridge-config.json
```

Log should show Link started. Init (next) needs Link to credit LP after deposit.

**D — Init bridge (LP USDT) + maker funding**

Run only after LightPool + Link are up:

```bash
cd ~/work/lightpool-labs/lightpool-node/scripts/event-contract-setup
python3 00_bridge_bootstrap.py --phase init
```

This command:

1. `init-bridge` → creates bridge LP USDT (`CASH_TOKEN_ADDRESS` / `LP_USDT`)
2. Writes app env (`event-contract-app/backend/.env`)
3. **Funds the maker:** `approve` + `Bridge.deposit` from the node wallet eth key
4. Waits for Link `confirm_dep` until maker LP `Available` covers the deposit

Default deposit: `MAKER_LP_DEPOSIT_WHOLE=10000000000` (override if needed).

Confirm:

```bash
grep CASH_TOKEN_ADDRESS ~/work/lightpool-labs/event-contract-app/backend/.env
# must be a full 8-byte LP token, e.g. 0x0200000000000001

$LP_CLI --rpc-url $LP_RPC balance \
  --token-address 0x0200000000000001 \
  --account "$VALIDATOR_ETH"
```

`Available` must be **> 0**. Do **not** use `lightpool mint` on bridge LP USDT.

**E — clob-index**

```bash
cd ~/work/lightpool-labs/lightpool-clob-indexer
cp -n .env.example .env
cargo run --release
```

**F — Backend**

```bash
cd ~/work/lightpool-labs/event-contract-app/backend
cargo run
```

**G — Frontend**

```bash
cd ~/work/lightpool-labs/event-contract-app/frontend
cp -n .env.example .env.local
npm install
npm run dev
```

---

## 2) Maker: run `liquidity-maker`

Requires maker LP USDT from init (above).

```bash
cd ~/work/lightpool-labs/lightpool-bot
# Required if Polymarket is blocked from your network (also ok in lightpool-bot/.env)
export HTTPS_PROXY=http://127.0.0.1:8118
cargo run -p lightpool-strategies --bin liquidity-maker -- \
  --polymarket-slug us-announces-end-of-iranian-blockade-byptptpt-20260713152715080 \
  --bootstrap-markets \
  --max-markets 5
```

Use a **live** Polymarket event slug (`closed=false`).

Optional smaller mint:

```bash
cargo run -p lightpool-strategies --bin liquidity-maker -- \
  --polymarket-slug us-announces-end-of-iranian-blockade-byptptpt-20260713152715080 \
  --bootstrap-markets \
  --max-markets 5 \
  --mint-amount 1000000000
```

Or attach to an existing LightPool market slug:

```bash
cargo run -p lightpool-strategies --bin liquidity-maker -- \
  --polymarket-slug <event-slug> \
  --lightpool-slug <existing-lp-market-slug>
```

| Flag | Default | Description |
|------|---------|-------------|
| `--polymarket-slug` | required | Polymarket event slug |
| `--lightpool-slug` | | Required unless `--bootstrap-markets` or `--polymarket-only` |
| `--bootstrap-markets` | false | Create + mint top-N LightPool markets from Polymarket |
| `--max-markets` | 5 | Max markets to bootstrap / subscribe |
| `--mint-amount` | `1e15` raw | Collateral burned per market mint (~1e9 USDT @ 6dp) |
| `--depth` | 10 | Book levels per side |
| `--no-trading` | false | Data/logging only (no LightPool orders) |
| `--polymarket-only` | false | Disable LightPool data client |

Maker talks to LightPool **only via clob-index** (HTTP + WS).

Useful checks:

- Maker logs show `pm_to_lp N:N` / market pairs and `trading_enabled=true`
- Frontend **Markets** lists bootstrapped slugs and shows book depth
- Maker has LP USDT before bootstrap; YES/NO inventory after mint

---

## 3) User: MetaMask

1. Network: RPC `http://127.0.0.1:8545`, chain id `1337`
2. Import key for `0xC019cECd52FE1f68b53daf766c4aF0Dea667A2c7`
3. Keep **proxy on** if MetaMask cannot reach MetaMask cloud (otherwise approve/transfer can hang)

Connect MetaMask → SIWE login → EIP-712 `set_agent` / **Authorize agent** when prompted.

---

## 4) User: Deposit

1. Open `http://127.0.0.1:3000` → Connect MetaMask (`0xC019…`)
2. Nav **Cash $…** → **Deposit**
3. MetaMask: ERC-20 `approve` then `Bridge.deposit`
4. Wait for Link `confirm_dep` → LP USDT balance updates

---

## 5) User: Withdraw

1. **Cash** → **Withdraw**
2. MetaMask: EIP-712 LightPool `bridge_withdraw`
3. Wait for Link `requestWithdraw` / `finalizeWithdraw` (~5s dispute) → EVM USDT back to `0xC019…`

---

## Path

```text
download repos → lightpool-node/tools/reth + foundry → lightpool-node/bin
  → Reth → deploy bridge → lightpool+Link → init (LP USDT + maker deposit)
  → clob-index → backend → frontend
  → maker: liquidity-maker (--bootstrap-markets)
  → user: MetaMask deposit / trade / withdraw
```

## Roles

| Actor | What they do |
|-------|----------------|
| Maker (`liquidity-maker`) | Bootstrap markets, mint, place/cancel spot orders from Polymarket books |
| Init (`00_bridge_bootstrap.py --phase init`) | Create LP USDT + fund maker via Bridge.deposit |
| User (MetaMask + Cash UI) | Bridge deposit / withdraw; SIWE + agent; trade on frontend |
| Link (in validator process) | `confirm_dep` mint LP; withdraw unlock on Reth |
