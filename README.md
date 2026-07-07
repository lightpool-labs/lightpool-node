# lightpool-node

High-Frequency Trading Infrastructure Powered by a Layer 1 Blockchain

This project is intended for educational and research purposes only. It is not intended for production deployment, live trading, or commercial use.

## Setup

Place release archives in `bin/`:

- `lightpool-v*.tar.gz`
- `lightpool-cli-v*.tar.gz`

Build the launcher and extract binaries:

```shell
cargo build --release
export PATH="$(pwd)/target/release:$(pwd)/bin:$PATH"
```

For the two-node local network you also need `burst_client` at `bin/burst_client` (or set `BURST_CLIENT_BIN`). Build it from the LightPool SDK repo:

```shell
cargo build --release -p lightpool-sdk --example burst_client
cp /path/to/lightpool/target/release/examples/burst_client bin/burst_client
```

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
cargo run --release
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

### Prerequisites

```shell
cargo build --release
chmod +x scripts/*.sh
```

### Listening addresses

| | node0 | node1 |
| --- | --- | --- |
| front | 127.0.0.1:26000 | 127.0.0.1:27000 |
| rpc | 127.0.0.1:26300 | 127.0.0.1:27300 |
| ws | 127.0.0.1:26400 | 127.0.0.1:27400 |

### Step-by-step

**Terminal 1** — init wallets and validator config (cleans old `scripts/.local-network`):

```shell
cd scripts
./init.sh
```

**Terminal 2** — start node0:

```shell
cd scripts
./run_node0.sh
```

Wait until you see `Node is running; press Ctrl+C to stop`.

**Terminal 1** — burst transactions on node0 until the first checkpoint:

```shell
cd scripts
./burst_stage1.sh
```

Watch node0 logs until `committed_block_num` reaches **1000** (first checkpoint epoch). Press **Ctrl+C** to stop the burst client.

**Terminal 3** — start node1 (syncs from node0):

```shell
cd scripts
./run_node1.sh
```

Wait until node1 finishes boot sync and shows `Node is running`.

**Terminal 1** — staking setup (LPL token, bonds for both validators):

```shell
cd scripts
./staking.sh
```

**Terminal 1** — burst again to advance the chain:

```shell
cd scripts
./burst_stage1.sh
```

Press Ctrl+C in any node terminal to stop that node.

### Optional: log to file

```shell
./run_node0.sh .local-network/node0/lightpool.log
./run_node1.sh .local-network/node1/lightpool.log
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
