# Frontend flow: Bridge deposit & withdraw

Manual Cash deposit / withdraw in `event-contract-app`.

**Accounts**

| Role | Address |
|------|---------|
| User (MetaMask) | `0xC019cECd52FE1f68b53daf766c4aF0Dea667A2c7` |
| Validator / maker | `lightpool-cli address` (node wallet eth) |
| Deployer | `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` |

Deploy mints **1e12 USDT** to deployer + validator, **10,000 USDT** to user, plus ETH for gas.

---

## 0) Env

```bash
cd ~/work/lightpool-labs
export PATH="$HOME/.foundry/bin:$PWD/tools/reth/bin:$PATH"
export RETH_RPC=http://127.0.0.1:8545
export LP_RPC=http://127.0.0.1:26300
export LP_CLI=$PWD/lightpool/target/release/lightpool-cli
export NODE_WALLET=$HOME/.lightpool/wallet.json
export EVM_CHAIN_ID=1337
export PK=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
export USER_ETH=0xC019cECd52FE1f68b53daf766c4aF0Dea667A2c7
```

```bash
cd ~/work/lightpool-labs/lightpool
#cargo build --release -p lightpool -p lightpool-cli
#$LP_CLI --rpc-url $LP_RPC create-wallet || true
export VALIDATOR_ETH=$($LP_CLI --rpc-url $LP_RPC address | grep -oE '0x[0-9a-fA-F]{40}' | head -1)
echo "VALIDATOR_ETH=$VALIDATOR_ETH"
```

Set backend `DEV_SECRET_KEY` to the node wallet hex secret when maker/admin must match the validator address.

---

## 1) Infrastructure (one terminal each)

**A — Reth**

```bash
cd ~/work/lightpool-labs
./tools/reth/run-dev.sh
```

**B — Deploy EVM USDT + Bridge** (node not running yet)

```bash
cd ~/work/lightpool-labs/lightpool-node/scripts/event-contract-setup
USER_ETH=0xC019cECd52FE1f68b53daf766c4aF0Dea667A2c7 \
  python3 00_bridge_bootstrap.py --phase deploy
```

**C — LightPool once (with Link)**

```bash
cd ~/work/lightpool-labs/lightpool
./target/release/lightpool --role validator \
  --bridge-config ~/work/lightpool-labs/tools/bridge-local/bridge-config.json
```

Until init finishes, Link may log `bridge config not initialized`. Keep this process running.

**B — Init bridge (LP USDT)**

```bash
cd ~/work/lightpool-labs/lightpool-node/scripts/event-contract-setup
python3 00_bridge_bootstrap.py --phase init
```

**D — clob-index**

```bash
cd ~/work/lightpool-labs/lightpool-clob-index
cp -n .env.example .env
cargo run --release
```

**E — Backend**

```bash
cd ~/work/lightpool-labs/event-contract-app/backend
# .env: CLOB_INDEX_URL, CASH_TOKEN_ADDRESS, ETH_USDT, BRIDGE, EVM_RPC_URL, EVM_CHAIN_ID, DEV_SECRET_KEY
cargo run
```

**F — Frontend**

```bash
cd ~/work/lightpool-labs/event-contract-app/frontend
cp -n .env.example .env.local
# NEXT_PUBLIC_API_URL=http://127.0.0.1:3001/api
# NEXT_PUBLIC_EVM_RPC_URL=http://127.0.0.1:8545
# NEXT_PUBLIC_EVM_CHAIN_ID=1337
# npm install
npm run dev
```

---

## 2) MetaMask

1. Network: RPC `http://127.0.0.1:8545`, chain id `1337`
2. Import key for `0xC019cECd52FE1f68b53daf766c4aF0Dea667A2c7`

Connect MetaMask for SIWE login. `set_agent` and bridge withdraw use MetaMask **EIP-712** (`LightPoolTx`); no `NEXT_PUBLIC_LP_PRIVATE_KEY` needed.

---

## 3) Deposit

1. Open `http://127.0.0.1:3000` → **Connect MetaMask** (`0xC019…`) — sign-in, then approve EIP-712 `set_agent` when prompted
2. **Cash** → enter amount → **Deposit**
3. Approve MetaMask `approve` + `Bridge.deposit`
4. Wait for Link `confirm_dep` → LP USDT balance updates

---

## 4) Withdraw

1. **Cash** → enter amount → **Withdraw**
2. Approve MetaMask EIP-712 LightPool withdraw
3. Wait for Link `requestWithdraw` / `finalizeWithdraw` (~5s dispute) → EVM USDT returns to `0xC019…`

---

## Path

```text
deploy (Reth) → lightpool --bridge-config → init-bridge
  → clob-index → backend → frontend
  → MetaMask deposit → Link mint LP
  → MetaMask-signed withdraw → Link unlock EVM
```
