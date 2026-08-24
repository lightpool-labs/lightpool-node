# Run one node on Docker

Runs **one LightPool node + clob-index** via Compose under `docker/`. Finish [Setup](../README.md#setup-binaries-on-path) first (`bin/lightpool` and `bin/lightpool-clob-indexer` present).

```shell
# same key as docker/.env LIGHTPOOL_PRIVATE_KEY
export DEV_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
lightpool import-wallet --private-key "$DEV_KEY" --force

cd docker
[ -f .env ] || cp .env.example .env
# set LIGHTPOOL_PRIVATE_KEY (same as DEV_KEY)
./prepare-binaries.sh
docker compose down
# sudo rm -rf ./data/node ./data/clob-index
# --no-cache rebuilds base layers; apt download can be slow the first time
docker compose build --no-cache
docker compose up -d
```

Ports: RPC `26300`, WS `26400`, mempool `26000`, clob-index `3002`.

`--no-cache` may download slowly (Ubuntu packages). Builds use host proxy `http://127.0.0.1:8118` by default (`HTTP_PROXY` in `docker/.env`); start the proxy first if you need it. For a faster rebuild when images already exist, omit `--no-cache`.

When the stack is up, load-test transfers and spot CLOB with the SDK burst examples — see [Run one node](../README.md#run-one-node) in the README.

Manual CLI flows (single token transfer or step-by-step spot) remain in [`create-token-and-transfer.md`](create-token-and-transfer.md) and [`spot-create-place-fill.md`](spot-create-place-fill.md).
