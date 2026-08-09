# lightpool-node

High-Frequency Trading Infrastructure Powered by a Layer 1 Blockchain with 200ktps orderbook

This project is intended for educational and research purposes only. It is not intended for production deployment, live trading, or commercial use.

## Setup (binaries on PATH)

This package does **not** need LightPool source code. Put prebuilt release artifacts in `bin/`:

- `lightpool-v*.tar.gz` — extracted to `bin/lightpool` on build
- `lightpool-clob-index-v*.tar.gz` — extracted to `bin/lightpool-clob-index` on build
- `burst_client` — prebuilt binary placed directly at `bin/burst_client`

Build clob-index tarball from `lightpool-clob-index`:

```shell
cd ../lightpool-clob-index
./build/build-release.sh
cp target/lightpool-clob-index-v*.tar.gz ../lightpool-node/bin/
```

Extract packages and generate `env.sh` (adds `bin/` to `PATH`; gitignored):

```shell
cargo build --release
source ./env.sh
```

After that, these commands are available on `PATH`:

- `lightpool` (node + client subcommands)
- `lightpool-clob-index`
- `burst_client`

Or call `./bin/lightpool` without sourcing. Override paths with `LIGHTPOOL_BIN` / `BURST_CLIENT_BIN` if needed.

## Run one node on Docker

Runs **one LightPool node + clob-index** via Compose under `docker/`. Finish [Setup](#setup-binaries-on-path) first (`bin/lightpool` and `bin/lightpool-clob-index` present).

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

Next: create a token and transfer — see [`doc/create-token-and-transfer.md`](doc/create-token-and-transfer.md).

Next: spot market (create, place, fill) — see [`doc/spot-create-place-fill.md`](doc/spot-create-place-fill.md).

App integration (Cursor Plugin + skill): [`plugins/spot-lightpool/`](plugins/spot-lightpool/) (project skill via [`.cursor/skills/spot-lightpool`](.cursor/skills/spot-lightpool)).

## Run two nodes

See [`doc/two-nodes.md`](doc/two-nodes.md).
