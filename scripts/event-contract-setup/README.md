# Event contract setup

Cash collateral is **bridge LP USDT** from `init-bridge`, not the old `create-token` mint path.

## Recommended order (start LightPool once)

1. Start **Reth**.
2. `python3 00_bridge_bootstrap.py --phase deploy` — deploy MockUSDT + Bridge; write `.env.bridge` and `tools/bridge-local/bridge-config.json`.
3. Start LightPool **once** with Link:

   ```bash
   lightpool node --role validator --bridge-config ~/work/lightpool-labs/tools/bridge-local/bridge-config.json
   ```

4. `python3 00_bridge_bootstrap.py --phase init` — `init-bridge`, set `CASH_TOKEN_ADDRESS` = LP USDT.
5. Optional: `python3 05_create_vault.py` (needs LP USDT on the node wallet).

`python3 setup.py` still runs bootstrap as `--phase all` (deploy+init), which requires LightPool already running for the init half — prefer the phased flow above for local testing.

Frontend deposit/withdraw steps: [`../../doc/frontend-bridge-deposit-withdraw.md`](../../doc/frontend-bridge-deposit-withdraw.md).
