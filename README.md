# lightpool-node

High-Frequency Trading Infrastructure Powered by a Layer 1 Blockchain

This project is intended for educational and research purposes only. It is not intended for production deployment, live trading, or commercial use.

## Setup

Build the launcher:

```shell
cargo build --release
export PATH="$(pwd)/target/release:$(pwd)/bin:$PATH"
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

Use `scripts/run_two_nodes.py` to start two validators that share one bootstrap committee.

### 1. Start the network

```shell
python3 scripts/run_two_nodes.py --clean
```

Listening addresses:

| | node0 | node1 |
| --- | --- | --- |
| front | localhost:26000 | localhost:27000 |
| mempool | localhost:26100 | localhost:27100 |
| consensus | localhost:26200 | localhost:27200 |
| rpc | localhost:26300 | localhost:27300 |
| ws | localhost:26400 | localhost:27400 |

Useful options:

```shell
python3 scripts/run_two_nodes.py --clean --verbose
python3 scripts/run_two_nodes.py --data-dir ./scripts/.local-network
```

Press Ctrl+C to stop all nodes.

### 2. Send transactions through either node

```shell
lightpool-cli create-token \
  --name "Network Token" \
  --symbol "NET" \
  --total-supply "1000000" \
  --mintable
```
