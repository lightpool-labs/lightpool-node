# UC2 examples — open-box spot

Assumes one node is already up (Docker Compose under `docker/`) and:

```bash
cd ~/work/lightpool-labs/lightpool-node
source ./env.sh
```

## Minimal: token + spot market

```bash
lightpool create-token --name USDT --symbol USDT --total-supply 10000000000 --mintable
# copy Token Address → USDT

lightpool create-token --name Apple --symbol AAPL --total-supply 1000000 --mintable
# copy Token Address → AAPL

lightpool create-spot-market \
  --name AAPL/USDT \
  --base-token "$AAPL" \
  --quote-token "$USDT" \
  --allow-market-orders
# copy Spot Market → SPOT

lightpool get-book --spot-market "$SPOT"
```

## Transfer quote to another wallet

```bash
export TAKER_WALLET="$HOME/.lightpool/taker/wallet.json"
mkdir -p "$(dirname "$TAKER_WALLET")"
lightpool create-wallet --force --wallet-path "$TAKER_WALLET"
export TAKER=$(lightpool address --wallet-path "$TAKER_WALLET" | grep -oE '0x[0-9a-fA-F]{40}' | head -1)

lightpool transfer --token-address "$USDT" --to "$TAKER" --amount 100000
lightpool balance --token-address "$USDT" --account "$TAKER"
```

## Place sell then fill with buy

```bash
# maker (default wallet) — locks AAPL
lightpool place-order \
  --spot-market "$SPOT" --side sell --amount 10 --price 190 \
  --token-address "$AAPL" --tif gtc

# taker — locks USDT
lightpool place-order \
  --wallet-path "$TAKER_WALLET" \
  --spot-market "$SPOT" --side buy --amount 5 --price 190 \
  --token-address "$USDT" --tif ioc

lightpool get-book --spot-market "$SPOT" --depth 10
```

## Mint more quote (if mintable)

```bash
lightpool mint --token-address "$USDT" --amount 1000
```
