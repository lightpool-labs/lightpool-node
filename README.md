# lightpool-node

Trading and payments on a Layer 1 blockchain — target **200k TPS** on the orderbook and **400k TPS** on payments.

Still in development; not for production deployment.

## Setup

```shell
cd ~/work/lightpool-labs/lightpool-node
cargo build --release
source ./env.sh
```

## 1. Burst

Terminal 1 — node:

```shell
cd ~/work/lightpool-labs/lightpool-node
lightpool create-wallet --force
lightpool node --role validator
```

Terminal 2:

```shell
cd ~/work/lightpool-labs/lightpool-sdk-rust
cargo run --release --example burst_client -- --tasks 1 --rate-per-task 400000 --duration 10
cargo run --release --example burst_spot_client -- --tasks 1 --rate-per-task 20000 --duration 10
```

## 2. Run one node on Docker

See [`doc/run-one-node-in-docker.md`](doc/run-one-node-in-docker.md).

## 3. Run two nodes

See [`doc/two-nodes.md`](doc/two-nodes.md).
