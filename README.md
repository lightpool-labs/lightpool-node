# lightpool-node

High-Frequency Trading Infrastructure Powered by a Layer 1 Blockchain

This project is intended for educational and research purposes only. It is not intended for production deployment, live trading, or commercial use.

## Setup

This package does **not** need LightPool source code. Put prebuilt release artifacts in `bin/`:

- `lightpool-v*.tar.gz` — extracted to `bin/lightpool` on build
- `lightpool-cli-v*.tar.gz` — extracted to `bin/lightpool-cli` on build
- `burst_client` — prebuilt binary placed directly at `bin/burst_client`

  You can build `burst_client` from
  [`lightpool-sdk-rust/examples/burst_client.rs`](../lightpool-sdk-rust/examples/burst_client.rs):

  ```shell
  # in lightpool-sdk-rust
  cargo build --release --example burst_client
  cp target/release/examples/burst_client /path/to/lightpool-node/bin/burst_client
  ```

Extract packages and generate `env.sh` (adds `bin/` to `PATH`):

```shell
cargo build --release
source ./env.sh
```

After that, these commands are available on `PATH`:

- `lightpool`
- `lightpool-cli`
- `burst_client`

Local network scripts also resolve these binaries under `bin/` directly. You can override with `LIGHTPOOL_BIN`, `LIGHTPOOL_CLI`, or `BURST_CLIENT_BIN`.

## Single Node: Wallet, Token, and Transfer

This example runs one validator locally, creates a token, and transfers tokens to a second wallet.

### 1. Create wallet

```shell
lightpool-cli create-wallet --force
lightpool-cli address
```

### 2. Run the node

In one terminal:

```shell
lightpool
```

Press Ctrl+C to stop the node.

### 3. Create a token

In another terminal:

```shell
lightpool-cli create-token \
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

lightpool-cli create-wallet --force --wallet-path data/recipient/wallet.json
lightpool-cli address --wallet-path data/recipient/wallet.json

lightpool-cli transfer \
  --token-address "TOKEN_ADDRESS" \
  --to "RECIPIENT_ADDRESS" \
  --amount "100"
```

Replace `TOKEN_ADDRESS` and `RECIPIENT_ADDRESS` from the command output.

Check balances:

```shell
lightpool-cli balance \
  --token-address "TOKEN_ADDRESS"

lightpool-cli balance \
  --token-address "TOKEN_ADDRESS" \
  --account "RECIPIENT_ADDRESS"
```

## Two Nodes: Local Network

Run two validators manually across three terminals. node0 starts alone and produces the first checkpoint at block 1000; node1 joins afterward via state sync and staking.

### Listening addresses

| | node0 | node1 |
| --- | --- | --- |
| front | 127.0.0.1:26000 | 127.0.0.1:27000 |
| rpc | 127.0.0.1:26300 | 127.0.0.1:27300 |
| ws | 127.0.0.1:26400 | 127.0.0.1:27400 |

### Step-by-step

**Terminal 1** — init wallets and validator config (cleans old `scripts/.local-network`):

```shell
python3 scripts/init.py
```

**Terminal 2** — start node0:

```shell
python3 scripts/run_node0.py
```

Wait until you see `Node is running; press Ctrl+C to stop`.

**Terminal 1** — burst transactions on node0 until the first checkpoint:

```shell
python3 scripts/burst_stage1.py
```

Watch node0 logs until `committed_block_num` reaches **1000** (first checkpoint epoch). Press **Ctrl+C** to stop the burst client.

**Terminal 3** — start node1 (syncs from node0):

```shell
python3 scripts/run_node1.py
```

Wait until node1 finishes boot sync and shows `Node is running`.

**Terminal 1** — staking setup (LPL token, bonds for both validators):

```shell
python3 scripts/staking.py
```

**Terminal 1** — burst again to advance the chain:

```shell
python3 scripts/burst_stage1.py
```

Press Ctrl+C in any node terminal to stop the burst.

### Optional: log to file

```shell
python3 scripts/run_node0.py scripts/.local-network/node0/lightpool.log
python3 scripts/run_node1.py scripts/.local-network/node1/lightpool.log
```

### Send transactions through either node

```shell
lightpool-cli create-token \
  --rpc-url http://127.0.0.1:26300 \
  --name "Network Token" \
  --symbol "NET" \
  --total-supply "1000000" \
  --mintable
```
