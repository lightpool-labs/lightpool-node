# Event contract setup

Cash collateral is **bridge LP USDT** from inbound bridge **create** (`init-bridge` CLI), not the old `create-token` mint path.

## Recommended order (start LightPool once)

1. Start **Reth**.
2. `python3 00_bridge_bootstrap.py --phase deploy` — deploy MockUSDT + Bridge; write `.env.bridge` and empty-route `lightpool-bridge/bridge-config.json`.
3. Start LightPool and **lightpool-bridge** (`--config lightpool-bridge/bridge-config.json`).

   ```bash
   lightpool node --role validator
   ```

4. `python3 00_bridge_bootstrap.py --phase create` — create inbound bridge; set `LP_USDT` / `INBOUND_BRIDGE`; upsert **reth-usdt** route into `bridge-config.json` (and Admin UI if bridge is running).
5. `python3 00_bridge_bootstrap.py --phase fund` — optional maker EVM deposit (requires bridge process with USDT route).
6. Optional: `python3 05_create_vault.py` (needs LP USDT on the node wallet).

`python3 setup.py` still runs bootstrap as `--phase all` (deploy+create), which requires LightPool already running for the create step — prefer the phased flow above for local testing.

**Note:** `--phase init` was removed; use `create` and `fund` instead.

Frontend deposit/withdraw steps: [`../../doc/frontend-bridge-deposit-withdraw.md`](../../doc/frontend-bridge-deposit-withdraw.md).
