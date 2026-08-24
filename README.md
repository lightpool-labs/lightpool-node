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

## 1. Burst

Terminal 1 — node:

```shell
cd ~/work/lightpool-labs/lightpool-node
source ./env.sh
lightpool create-wallet --force
lightpool node --role validator
```

Terminal 2 — transfer burst:

```shell
cd ~/work/lightpool-labs/lightpool-sdk-rust
cargo run --release --example burst_client -- \
  --tasks 1 --rate-per-task 400000 --duration 10
```

Terminal 2 — spot CLOB burst:

```shell
cd ~/work/lightpool-labs/lightpool-sdk-rust
cargo run --release --example burst_spot_multi_market_client -- \
  --tasks 1 --rate-per-task 20000 --duration 10
```

## 2. Run one node on Docker

See [`doc/run-one-node-in-docker.md`](doc/run-one-node-in-docker.md).

## 3. Run two nodes

See [`doc/two-nodes.md`](doc/two-nodes.md).
