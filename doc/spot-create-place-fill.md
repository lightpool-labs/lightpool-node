# Spot: create market, place order, fill

Requires a running node (Docker one-node in `docker/`, or `lightpool node`).

Needs a `lightpool` build that includes `create-spot-market` and `place-order` (rebuild from the `lightpool` repo, then refresh `lightpool-node/bin/` / Docker binaries).

From the `lightpool-node` root:

```shell
source ./env.sh
```

This flow creates a **spot** CLOB (example: **AAPL/USDT**), not an event contract.

---

## 1. Create base and quote tokens

```shell
# Quote (cash)
lightpool create-token \
  --name "USDT" \
  --symbol "USDT" \
  --total-supply "10000000000" \
  --mintable | tee /tmp/create-usdt.out
export USDT=$(grep -oE '0x02[0-9a-fA-F]{14}' /tmp/create-usdt.out | head -1)
echo "USDT=$USDT"

# Base (e.g. Apple stock token)
lightpool create-token \
  --name "Apple" \
  --symbol "AAPL" \
  --total-supply "1000000" \
  --mintable | tee /tmp/create-aapl.out
export AAPL=$(grep -oE '0x02[0-9a-fA-F]{14}' /tmp/create-aapl.out | head -1)
echo "AAPL=$AAPL"
```

On a fresh chain the first token is often `0x0200000000000001` (USDT), the second `0x0200000000000002` (AAPL). Prefer the addresses printed above.

---

## 2. Create the spot market (AAPL/USDT)

```shell
lightpool create-spot-market \
  --name "AAPL/USDT" \
  --base-token "$AAPL" \
  --quote-token "$USDT" \
  --tick-size "0.01" \
  --min-order-size "0.1" \
  --allow-market-orders | tee /tmp/create-spot.out

export SPOT=$(grep -oE '0x03[0-9a-fA-F]{14}' /tmp/create-spot.out | head -1)
echo "SPOT=$SPOT"
```

Or copy the printed `Spot Market` address into `export SPOT=...`.

---

## 3. Fund a second trader (taker)

Maker (default wallet) keeps AAPL to sell. Taker needs USDT to buy:

```shell
mkdir -p data/taker
lightpool create-wallet --force --wallet-path data/taker/wallet.json
export TAKER=$(lightpool address --wallet-path data/taker/wallet.json | grep -oE '0x[0-9a-fA-F]{40}' | head -1)
echo "$TAKER"

lightpool transfer \
  --token-address "$USDT" \
  --to "$TAKER" \
  --amount "100000"
```

---

## 4. Place a resting sell (maker)

Sell locks **base** (`AAPL`):

```shell
lightpool place-order \
  --spot-market "$SPOT" \
  --side sell \
  --amount "10" \
  --price "190" \
  --token-address "$AAPL" \
  --tif gtc

lightpool get-book --spot-market "$SPOT" --depth 10
```

---

## 5. Fill with a buy (taker)

Buy locks **quote** (`USDT`). Use the taker wallet:

```shell
lightpool place-order \
  --wallet-path data/taker/wallet.json \
  --spot-market "$SPOT" \
  --side buy \
  --amount "5" \
  --price "190" \
  --token-address "$USDT" \
  --tif ioc
```

Or a market buy:

```shell
lightpool place-order \
  --wallet-path data/taker/wallet.json \
  --spot-market "$SPOT" \
  --side buy \
  --amount "5" \
  --price "190" \
  --token-address "$USDT" \
  --market
```

Check the book and balances:

```shell
lightpool get-book --spot-market "$SPOT" --depth 10
lightpool balance --token-address "$AAPL"
lightpool balance --token-address "$USDT"
lightpool balance --token-address "$AAPL" --account "$TAKER"
lightpool balance --token-address "$USDT" --account "$TAKER"
```

A fill happens when the buy crosses the resting sell (same or better price). Residual size stays on the book for GTC sells.
