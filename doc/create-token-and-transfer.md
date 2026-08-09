# Create token and transfer

Requires a running node (Docker venue in `docker/`, or `lightpool node` in another terminal).

From the `lightpool-node` root:

```shell
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
lightpool address --wallet-path data/recipient/wallet.json

lightpool transfer \
  --token-address "0x0200000000000001" \
  --to "RECIPIENT_ADDRESS" \
  --amount "100"
```

Replace `RECIPIENT_ADDRESS` with the address from the previous command.

```shell
lightpool balance --token-address "0x0200000000000001"
lightpool balance \
  --token-address "0x0200000000000001" \
  --account "RECIPIENT_ADDRESS"
```

## 4. Optional mint

```shell
lightpool mint \
  --token-address "0x0200000000000001" \
  --amount "1000"
```
