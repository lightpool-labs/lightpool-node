# Spot: create market, place order, fill

Requires a running node (Docker one-node in `docker/`, or `lightpool node`).

From the `lightpool-node` root:

```shell
source ./env.sh
```

Collateral USDT should already exist — see [`create-token-and-transfer.md`](create-token-and-transfer.md). On a fresh chain the first token is usually `0x0200000000000001`.

`lightpool create-market` creates an **event contract**. That also creates YES/NO **spot** order books. You mint a complete set (YES + NO), then trade YES (or NO) on its spot market. Matching happens when a resting order and a crossing order meet.

---

## 1. Create market

```shell
export COLLATERAL=0x0200000000000001
export DEADLINE=$(date -u -d '+30 days' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v+30d +%Y-%m-%dT%H:%M:%SZ)

lightpool create-market \
  --question "Will it rain in SF tomorrow?" \
  --collateral-token "$COLLATERAL" \
  --resolution-deadline "$DEADLINE" \
  --tick-size "0.01" \
  --min-order-size "0.1" \
  --allow-market-orders | tee /tmp/create-market.out

export MARKET=$(grep -oE '"market_address": "0x[0-9a-fA-F]+"' /tmp/create-market.out | head -1 | grep -oE '0x[0-9a-fA-F]+')
export YES_TOKEN=$(grep -oE '"yes_token": "0x[0-9a-fA-F]+"' /tmp/create-market.out | head -1 | grep -oE '0x[0-9a-fA-F]+')
export NO_TOKEN=$(grep -oE '"no_token": "0x[0-9a-fA-F]+"' /tmp/create-market.out | head -1 | grep -oE '0x[0-9a-fA-F]+')
export YES_SPOT=$(grep -oE '"yes_spot_market": "0x[0-9a-fA-F]+"' /tmp/create-market.out | head -1 | grep -oE '0x[0-9a-fA-F]+')
export NO_SPOT=$(grep -oE '"no_spot_market": "0x[0-9a-fA-F]+"' /tmp/create-market.out | head -1 | grep -oE '0x[0-9a-fA-F]+')
echo "MARKET=$MARKET YES_TOKEN=$YES_TOKEN YES_SPOT=$YES_SPOT"
```

(Or copy the printed `Market Address` / `YES Token` / `YES Spot Market` lines into `export` yourself.)

---

## 2. Mint YES + NO (complete set)

Burns collateral and credits equal YES and NO to the default wallet:

```shell
lightpool mint-market \
  --market-address "$MARKET" \
  --amount "1000" \
  --collateral-token "$COLLATERAL" \
  --yes-token "$YES_TOKEN" \
  --no-token "$NO_TOKEN"

lightpool balance --token-address "$YES_TOKEN"
lightpool balance --token-address "$COLLATERAL"
```

---

## 3. Fund a second trader (taker)

Maker keeps YES to sell; taker needs collateral (USDT) to buy YES:

```shell
mkdir -p data/taker
lightpool create-wallet --force --wallet-path data/taker/wallet.json
export TAKER=$(lightpool address --wallet-path data/taker/wallet.json | grep -oE '0x[0-9a-fA-F]{40}' | head -1)
echo "$TAKER"

lightpool transfer \
  --token-address "$COLLATERAL" \
  --to "$TAKER" \
  --amount "500"
```

---

## 4. Place and fill (SDK demo)

`lightpool` does not expose `place-order` yet. Use the spot example in sibling `lightpool-sdk-rust` (creates its own BTC/USDT spot market, places a sell, then fills with a buy):

```shell
cd ../lightpool-sdk-rust
cargo run --release --example simple_spot_client
```

What that example does:

1. Create BTC + USDT tokens for two traders  
2. Create a **BTC/USDT spot** market  
3. Place a resting **sell** (maker)  
4. Place a **market buy** / **limit buy** (taker) that **fills** against the sell  
5. Optional update / cancel on the residual order  
6. Print balances  

Node RPC must be `http://localhost:26300` (Docker one-node default).

---

## 5. Query the order book

After you have a spot market address (`YES_SPOT` from step 1, or the market printed by the SDK example):

```shell
lightpool get-book --spot-market "$YES_SPOT" --depth 10
```

Empty book is normal until orders rest on that market.

---

## Optional: burn complete set

```shell
lightpool burn-market \
  --market-address "$MARKET" \
  --amount "100" \
  --collateral-token "$COLLATERAL" \
  --yes-token "$YES_TOKEN" \
  --no-token "$NO_TOKEN"
```
