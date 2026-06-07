# lightpool-node

High-Frequency Trading Infrastructure Powered by a Layer 1 Blockchain

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

Or after building:

```shell
./target/release/lightpool create --datadir ./data/node1
```

## Run Node

```shell
cargo run -- -vv run --keys data/node1/node.json --committee data/node1/committee.json --store data/node1/store
```

Or after building:

```shell
./target/release/lightpool -vv run --keys data/node1/node.json --committee data/node1/committee.json --store data/node1/store
```

RPC listens on `0.0.0.0:26300` by default. Press Ctrl+C to stop the node.
