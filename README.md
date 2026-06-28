# lightpool-node

High-Frequency Trading Infrastructure Powered by a Layer 1 Blockchain

This project is intended for educational and research purposes only. It is not intended for production deployment, live trading, or commercial use.

## Setup

Place the prebuilt release archive in `bin/`. The archive name changes on each release, for example:

```text
bin/lightpool-v0.1.1-linux-amd64-9810608.tar.gz
```

Build the launcher from this directory:

```shell
cargo build --release
```

On release builds, if `bin/lightpool` is missing, the build script automatically picks the newest `bin/lightpool-v*.tar.gz`, unpacks it, and installs the binary as `bin/lightpool`.

The launcher binary is also named `lightpool`. It forwards all arguments to `bin/lightpool`.

CLI commands (`create-wallet`, `create-token`, `transfer`, and so on) use `lightpool-cli` from the [lightpool](https://github.com/lightpool-labs/lightpool) source tree. Build it once from a sibling checkout:

```shell
cargo build --release -p lightpool-cli --manifest-path ../lightpool/Cargo.toml
```

Set `LIGHTPOOL_SOURCE_ROOT` if your lightpool checkout is not at `../lightpool`.

## Single Node: Wallet, Token, and Transfer

This example runs one validator locally, creates a token, and transfers tokens to a second wallet.

### 1. Prepare binaries

```shell
cargo build --release
cargo build --release -p lightpool-cli --manifest-path ../lightpool/Cargo.toml
```

Add the CLI to your `PATH` for the rest of this example:

```shell
export PATH="$(pwd)/../lightpool/target/release:$PATH"
```

### 2. Create wallets

```shell
mkdir -p data/node0 data/recipient

lightpool-cli create-wallet --force --wallet-path data/node0/wallet.json
lightpool-cli create-wallet --force --wallet-path data/recipient/wallet.json

lightpool-cli address --wallet-path data/node0/wallet.json
lightpool-cli address --wallet-path data/recipient/wallet.json
```

Save the validator `Address` and `Public Key` from the node0 output. Save the recipient `Address` for the transfer step.

### 3. Create validators.json

Replace `OWNER_ADDRESS` and `CONSENSUS_PUBKEY` with the values from step 2:

```shell
cat > data/node0/validators.json <<'EOF'
{
  "validators": [
    {
      "owner": "OWNER_ADDRESS",
      "consensus_pubkey": "CONSENSUS_PUBKEY",
      "mempool_address": "127.0.0.1:26100",
      "consensus_address": "127.0.0.1:26200",
      "stake": 1
    }
  ]
}
EOF
```

### 4. Run the node

In one terminal:

```shell
cargo run --release -- \
  --wallet data/node0/wallet.json \
  --store data/node0/store \
  --validators data/node0/validators.json \
  --front-listen-addr 0.0.0.0:26000 \
  --rpc-listen-addr 0.0.0.0:26300 \
  --ws-listen-addr 0.0.0.0:26400
```

RPC listens on `http://127.0.0.1:26300`. Press Ctrl+C to stop the node.

### 5. Create a token

In another terminal:

```shell
lightpool-cli create-token \
  --wallet-path data/node0/wallet.json \
  --rpc-url http://127.0.0.1:26300 \
  --name "Example Token" \
  --symbol "EXT" \
  --total-supply "1000000" \
  --mintable
```

Copy the token contract address from the command output.

### 6. Transfer tokens

Replace `TOKEN_ADDRESS` and `RECIPIENT_ADDRESS`:

```shell
lightpool-cli transfer \
  --wallet-path data/node0/wallet.json \
  --rpc-url http://127.0.0.1:26300 \
  --token-address "TOKEN_ADDRESS" \
  --to "RECIPIENT_ADDRESS" \
  --amount "100"
```

Check balances:

```shell
lightpool-cli balance \
  --wallet-path data/node0/wallet.json \
  --rpc-url http://127.0.0.1:26300 \
  --token-address "TOKEN_ADDRESS"

lightpool-cli balance \
  --wallet-path data/recipient/wallet.json \
  --rpc-url http://127.0.0.1:26300 \
  --token-address "TOKEN_ADDRESS" \
  --account "RECIPIENT_ADDRESS"
```

## Two Nodes: Local Network

Use `scripts/run_two_nodes.py` to start two validators that share one bootstrap committee.

### 1. Prepare binaries

Build the launcher and CLI:

```shell
cargo build --release
python3 scripts/run_two_nodes.py --build --no-wait
```

The `--build` flag builds `lightpool-cli` from the lightpool source tree and runs `cargo build --release` here to install `bin/lightpool`.

### 2. Start the network

```shell
python3 scripts/run_two_nodes.py --clean
```

This creates wallets, writes `validators.json`, starts node0 and node1, and waits until both RPC endpoints are ready:

- node0 RPC: `http://127.0.0.1:26300`
- node1 RPC: `http://127.0.0.1:27300`

Useful options:

```shell
python3 scripts/run_two_nodes.py --clean --verbose
python3 scripts/run_two_nodes.py --data-dir ./scripts/.local-network
python3 scripts/run_two_nodes.py --no-wait
```

Press Ctrl+C to stop all nodes.

### 3. Send transactions through either node

```shell
export PATH="$(pwd)/../lightpool/target/release:$PATH"

lightpool-cli create-token \
  --wallet-path scripts/.local-network/node0/wallet.json \
  --rpc-url http://127.0.0.1:26300 \
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
