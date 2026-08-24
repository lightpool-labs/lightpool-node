# lightpool-node

High-Frequency Trading Infrastructure Powered by a Layer 1 Blockchain with 200ktps orderbook

This project is intended for educational and research purposes only. It is not intended for production deployment, live trading, or commercial use.

## Setup (binaries on PATH)

This package does **not** need LightPool source code. Put prebuilt release artifacts in `bin/`:

- `lightpool-v*.tar.gz` — extracted to `bin/lightpool` on build
- `lightpool-clob-indexer-v*.tar.gz` — extracted to `bin/lightpool-clob-indexer` on build
- `burst_client` — prebuilt binary placed directly at `bin/burst_client`

Extract packages and generate `env.sh` (adds `bin/` to `PATH`; gitignored):

```shell
cargo build --release
source ./env.sh
```

After that, these commands are available on `PATH`:

- `lightpool` (node + client subcommands)
- `lightpool-clob-indexer`
- `burst_client`

Or call `./bin/lightpool` without sourcing. Override paths with `LIGHTPOOL_BIN` / `BURST_CLIENT_BIN` if needed.

## Run one node

### Docker

See [`doc/run-one-node-in-docker.md`](doc/run-one-node-in-docker.md) for one LightPool node + clob-index via Compose (`docker/`).

### Transfer and CLOB burst (SDK)

With the node reachable at RPC `26300` and mempool `26000` (Docker defaults on `127.0.0.1`), build and run the examples from **`lightpool-sdk-rust`**:

```shell
export LABS=~/work/lightpool-labs   # or your clone root
cd "$LABS/lightpool-sdk-rust"
```

**Token transfer burst** — [`examples/burst_client.rs`](../lightpool-sdk-rust/examples/burst_client.rs): creates a token, funds many senders, then pushes parallel transfers through the mempool.

```shell
cargo run --release --example burst_client -- \
  --address 127.0.0.1 \
  --senders 64 --recipients 64 --tasks 4 --rate-per-task 100 --duration 5
```

Omit the extra flags to use the example defaults (high-throughput benchmark: 2048 senders, 8 tasks, 1000 tx/s per task, 10s).

**Multi-market spot CLOB burst** — [`examples/burst_spot_multi_market_client.rs`](../lightpool-sdk-rust/examples/burst_spot_multi_market_client.rs): creates tokens and spot markets, funds senders, then bursts `place_order` traffic (mostly resting limits; ~1% market sells for fills).

```shell
cargo run --release --example burst_spot_multi_market_client -- \
  --address 127.0.0.1 \
  --num-markets 4 --senders 32 --tasks 4 --rate-per-task 50 --duration 5
```

Omit the extra flags for the full benchmark profile (500 markets, 1024 senders, 8 tasks, 500 orders/s per task, 10s).

Both examples use ephemeral SDK signers (no `lightpool import-wallet` required). Point `--address` at the node host if it is not local.

Optional: copy release binaries into this package for scripts that expect `bin/burst_client`:

```shell
cargo build --release --example burst_client --example burst_spot_multi_market_client
cp target/release/examples/burst_client "$LABS/lightpool-node/bin/"
cp target/release/examples/burst_spot_multi_market_client "$LABS/lightpool-node/bin/"
```

Step-by-step CLI token transfer and spot place/fill (no burst): [`doc/create-token-and-transfer.md`](doc/create-token-and-transfer.md), [`doc/spot-create-place-fill.md`](doc/spot-create-place-fill.md).

## Run two nodes

See [`doc/two-nodes.md`](doc/two-nodes.md).
