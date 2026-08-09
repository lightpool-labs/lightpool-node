# lightpool-node

High-Frequency Trading Infrastructure Powered by a Layer 1 Blockchain with 200ktps orderbook

This project is intended for educational and research purposes only. It is not intended for production deployment, live trading, or commercial use.

## Run on Docker (venue)

Runs **LightPool node + clob-index** via Compose under `docker/`. No EVM / bridge.

Put release tarballs in `bin/` first:

- `lightpool-v*.tar.gz`
- `lightpool-clob-index-v*.tar.gz`

```shell
# unpack binaries into bin/ (also writes env.sh locally; not committed)
cargo build
source ./env.sh

# optional: same key as docker/.env LIGHTPOOL_PRIVATE_KEY (Anvil #0 example)
export DEV_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
lightpool import-wallet --private-key "$DEV_KEY" --force

cd docker
[ -f .env ] || cp .env.example .env
# set LIGHTPOOL_PRIVATE_KEY (same as DEV_KEY for local demo)
./prepare-binaries.sh
docker compose down
# sudo rm -rf ./data/node ./data/clob-index
docker compose build --no-cache
docker compose up -d
```

Ports: RPC `26300`, WS `26400`, mempool `26000`, clob-index `3002`.

```shell
# seed USDT for bot / app (from lightpool-node root, with env.sh sourced)
./scripts/bot-testing/seed_dev_markets.sh

docker compose -f docker/docker-compose.yml logs -f
docker compose -f docker/docker-compose.yml down
```

`--no-cache` builds use host proxy `http://127.0.0.1:8118` by default (`HTTP_PROXY` in `docker/.env`).

## Setup (binaries on PATH)

This package does **not** need LightPool source code. Put prebuilt release artifacts in `bin/`:

- `lightpool-v*.tar.gz` — extracted to `bin/lightpool` on build
- `lightpool-clob-index-v*.tar.gz` — extracted to `bin/lightpool-clob-index` on build
- `burst_client` — prebuilt binary placed directly at `bin/burst_client`

Build clob-index tarball from `lightpool-clob-index`:

```shell
cd ../lightpool-clob-index
./build/build-release.sh
cp target/lightpool-clob-index-v*.tar.gz ../lightpool-node/bin/
```

Extract packages and generate `env.sh` (adds `bin/` to `PATH`; gitignored):

```shell
cargo build --release
source ./env.sh
```

After that, these commands are available on `PATH`:

- `lightpool` (node + client subcommands)
- `lightpool-clob-index`
- `burst_client`

Or call `./bin/lightpool` without sourcing. Override paths with `LIGHTPOOL_BIN` / `BURST_CLIENT_BIN` if needed.

## Single Node: Wallet, Token, and Transfer

This example runs one validator locally, creates a token, and transfers tokens to a second wallet.

### 1. Create wallet

```shell
lightpool create-wallet --force
lightpool address
```

### 2. Run the node

In one terminal:

```shell
lightpool node
```

Press Ctrl+C to stop the node.

### 3. Create a token

In another terminal:

```shell
lightpool create-token \
  --name "Example Token" \
  --symbol "EXT" \
  --total-supply "1000000" \
  --mintable
```

Copy the token contract address from the command output.

### 4. Transfer tokens

Create a recipient wallet and transfer tokens:

```shell
mkdir -p data/recipient

lightpool create-wallet --force --wallet-path data/recipient/wallet.json
lightpool address --wallet-path data/recipient/wallet.json

lightpool transfer \
  --token-address "TOKEN_ADDRESS" \
  --to "RECIPIENT_ADDRESS" \
  --amount "100"
```

Replace `TOKEN_ADDRESS` and `RECIPIENT_ADDRESS` from the command output.

Check balances:

```shell
lightpool balance \
  --token-address "TOKEN_ADDRESS"

lightpool balance \
  --token-address "TOKEN_ADDRESS" \
  --account "RECIPIENT_ADDRESS"
```

## Two Nodes: Local Network

Run two validators locally. node0 starts alone and produces the first checkpoint at block 1000; node1 joins afterward via state sync and staking. After the second epoch (~block 2000), both nodes should propose.

### Listening addresses

| | node0 | node1 |
| --- | --- | --- |
| front | 127.0.0.1:26000 | 127.0.0.1:27000 |
| rpc | 127.0.0.1:26300 | 127.0.0.1:27300 |
| ws | 127.0.0.1:26400 | 127.0.0.1:27400 |

### Automated: `run_2nodes/run_2nodes.py`

One command drives the full flow (init → node0 → burst past 800 → node1 → first checkpoint sync → staking → burst to 3000):

```shell
python3 scripts/run_2nodes/run_2nodes.py
```

What it does:

1. `init` — reset `scripts/run_2nodes/.local-network`, create wallets/validator configs
2. Start **node0** as Validator
3. Burst until tip **> 800**, pause burst
4. Start **node1** as PendingMember (`--boot-peer` node0)
5. Burst again until tip **>= 1000**, stop burst so node1 can sync the first checkpoint
6. Run **staking** (LPL token, bonds for both nodes)
7. Burst until tip **>= 3000** (after 2000 both nodes should propose)

Logs:

- `scripts/run_2nodes/.local-network/node0/lightpool.log`
- `scripts/run_2nodes/.local-network/node1/lightpool.log`
- `scripts/run_2nodes/.local-network/burst_*.log`

Press **Ctrl+C** to stop both nodes.

### Manual step-by-step

Use separate terminals if you want to control each step yourself.

**Terminal 1** — init wallets and validator config (cleans old `scripts/run_2nodes/.local-network`):

```shell
python3 scripts/run_2nodes/init.py
```

**Terminal 2** — start node0:

```shell
python3 scripts/run_2nodes/run_node0.py
```

Wait until you see `Node is running; press Ctrl+C to stop`.

**Terminal 1** — burst transactions on node0 until near the first checkpoint, then start node1 before tip passes 1000:

```shell
python3 scripts/run_2nodes/burst_stage1.py
```

When tip is past **~800** and still before **1000**, in **Terminal 3** start node1:

```shell
python3 scripts/run_2nodes/run_node1.py
```

Continue burst until `committed_block_num` reaches **1000** (first checkpoint), then **Ctrl+C** the burst client so node1 can finish checkpoint sync.

Wait until node1 finishes boot sync, announces Join to node0, and shows `Node is running`.

**Terminal 1** — staking setup (LPL token, bonds for both validators):

```shell
python3 scripts/run_2nodes/staking.py
```

**Terminal 1** — burst again to advance the chain (past 2000 for dual proposal):

```shell
python3 scripts/run_2nodes/burst_stage1.py
```

Press Ctrl+C in any node terminal to stop.

### Optional: log to file (manual runs)

```shell
python3 scripts/run_2nodes/run_node0.py scripts/run_2nodes/.local-network/node0/lightpool.log
python3 scripts/run_2nodes/run_node1.py scripts/run_2nodes/.local-network/node1/lightpool.log
```

### Send transactions through either node

```shell
lightpool create-token \
  --rpc-url http://127.0.0.1:26300 \
  --name "Network Token" \
  --symbol "NET" \
  --total-supply "1000000" \
  --mintable
```
