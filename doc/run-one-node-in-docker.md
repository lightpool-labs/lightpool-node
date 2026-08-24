# Run one node on Docker

```shell
cd ~/work/lightpool-labs/lightpool-node
cargo build --release
source ./env.sh

cd ~/work/lightpool-labs/lightpool-clob-indexer
cargo build --release --bin lightpool-clob-indexer
cp target/release/lightpool-clob-indexer ../lightpool-node/bin/

export DEV_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
lightpool import-wallet --private-key "$DEV_KEY" --force

cd ~/work/lightpool-labs/lightpool-node/docker
[ -f .env ] || cp .env.example .env
./prepare-binaries.sh
docker compose down
docker compose build --no-cache
docker compose up -d
```

Ports: RPC `26300`, WS `26400`, mempool `26000`, clob-index `3002`.

When the stack is up:

- [`create-token-and-transfer.md`](create-token-and-transfer.md)
- [`spot-create-place-fill.md`](spot-create-place-fill.md)
