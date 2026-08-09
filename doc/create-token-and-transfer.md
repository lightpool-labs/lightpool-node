# Create token and transfer

Requires a running node (Docker venue in `docker/`, or `lightpool node` in another terminal).

Run from the **`lightpool-node` package root** (parent of `docker/`), not from `docker/`:

```shell
cd ~/work/lightpool-labs/lightpool-node   # or your clone path
source ./env.sh
```

## 1. Create a token

```shell
lightpool create-token \
  --name "USDT" \
  --symbol "USDT" \
  --total-supply "10000000000" \
  --mintable
```

Copy the token address from the output (on a fresh chain the first token is usually `0x0200000000000001`).

## 2. Check balance

```shell
lightpool balance --token-address "0x0200000000000001"
```

## 3. Create a recipient wallet and transfer

```shell
mkdir -p data/recipient

lightpool create-wallet --force --wallet-path data/recipient/wallet.json
export RECIPIENT=$(lightpool address --wallet-path data/recipient/wallet.json | grep -oE '0x[0-9a-fA-F]{40}' | head -1)

lightpool transfer \
  --token-address "0x0200000000000001" \
  --to "$RECIPIENT" \
  --amount "100"
```

```shell
lightpool balance --token-address "0x0200000000000001"
lightpool balance \
  --token-address "0x0200000000000001" \
  --account "$RECIPIENT"
```

## 4. Optional mint

```shell
lightpool mint \
  --token-address "0x0200000000000001" \
  --amount "1000"
```

Next: spot market (create, place, fill) — see [`spot-create-place-fill.md`](spot-create-place-fill.md).
