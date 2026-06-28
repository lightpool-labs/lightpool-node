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

Save a recipient `Address` for the transfer step.

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

Replace `TOKEN_ADDRESS` and `RECIPIENT_ADDRESS`:

```shell
lightpool-cli transfer \
  --token-address "TOKEN_ADDRESS" \
  --to "RECIPIENT_ADDRESS" \
  --amount "100"
```

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

Useful options:

```shell
python3 scripts/run_two_nodes.py --clean --verbose
python3 scripts/run_two_nodes.py --data-dir ./scripts/.local-network
python3 scripts/run_two_nodes.py --no-wait
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

## Scripts

| Path | Purpose |
|------|---------|
| `scripts/run_two_nodes.py` | Start a local two-validator network |
| `scripts/config.py` | Shared ports, paths, and binary locations |
| `scripts/node_utils.py` | Node startup and health checks |
| `scripts/wallet_utils.py` | Wallet creation helpers for local scripts |

Local network data is written under `scripts/.local-network/` by default.
