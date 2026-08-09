# spot-lightpool (Cursor Plugin)

Cursor plugin that teaches Agent how to integrate an app with **LightPool spot**.

**LightPool is a blockchain L1** targeting **200k TPS**, with an **on-chain
orderbook**: spot CLOB **matching and settlement** both run on chain
(base/quote, e.g. AAPL/USDT). Apps do not call the node RPC/WS directly; they
use a deployed **clob-index** (HTTP/WS) for market data and
`POST /api/tx/submit`, and sign txs with `lightpool-sdk`.

## Contents

- Skill: `skills/spot-lightpool/` (`SKILL.md`, `http.md`, `ws.md`, `tx-submit.md`)
- Logo: `assets/logo.svg` (icon), `assets/logo-wordmark.svg` (mark + wordmark)

## Deploy the L1 venue

Node + clob-index package:

https://github.com/lightpool-labs/lightpool-node

Signing SDK:

https://github.com/lightpool-labs/lightpool-sdk-rust

## Test locally in Cursor

```bash
mkdir -p ~/.cursor/plugins/local
ln -sfn "$(pwd)" ~/.cursor/plugins/local/spot-lightpool
```

Reload Cursor window, then open **Customize → Skills** (or type `/spot-lightpool` in Agent chat).

## Marketplace

When ready, submit at https://cursor.com/marketplace/publish (plugin root = this directory, or the repo with this plugin path documented).
