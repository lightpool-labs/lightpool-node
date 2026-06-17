# lightpool-node

High-Frequency Trading Infrastructure Powered by a Layer 1 Blockchain

This project is intended for educational and research purposes only. It is not intended for production deployment, live trading, or commercial use.

## Setup

Place the prebuilt release archive in `bin/`. The archive name changes on each release, for example:

```text
bin/lightpool-v0.1.1-linux-amd64-9810608.tar.gz
```

Extract the `lightpool` binary before building:

```shell
bash scripts/extract-binary.sh
```

This picks the newest `bin/lightpool-v*.tar.gz`, unpacks it, and installs the binary as `bin/lightpool`.

## Build

From this directory:

```shell
cargo build --release
```

The binary is installed as `lightpool`.

## Create Node

```shell
cargo run -- create --datadir ./data/node1
```

## Run Node

```shell
cargo run -- -vv run --keys data/node1/node.json --committee data/node1/committee.json --store data/node1/store
```

RPC listens on `0.0.0.0:26300` by default. Press Ctrl+C to stop the node.
