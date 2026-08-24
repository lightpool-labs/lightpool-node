from __future__ import annotations

import json
import re
import subprocess
import time
from decimal import Decimal
from pathlib import Path

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
TOKEN_ADDRESS_PATTERN = re.compile(r"\b0x02[0-9a-fA-F]{14}\b")
SPOT_MARKET_PATTERN = re.compile(r"\b0x03[0-9a-fA-F]{14}\b")
BALANCE_LINE_PATTERN = re.compile(r"^(Total|Locked|Available):\s*([0-9]+(?:\.[0-9]+)?)\s*$", re.MULTILINE)
ORDER_ID_PATTERN = re.compile(r"Order ID:\s*([0-9]+)")


class CliError(RuntimeError):
    pass


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


def wait_until(description: str, check, timeout_sec: float = 60.0, poll_sec: float = 1.0) -> None:
    deadline = time.monotonic() + timeout_sec
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            if check():
                print(f"OK: {description}", flush=True)
                return
        except Exception as error:  # noqa: BLE001 - polled until the deadline
            last_error = error
        time.sleep(poll_sec)
    raise TimeoutError(f"Timed out: {description} (last error: {last_error})")


class LightpoolCli:
    def __init__(self, binary: str, rpc_url: str):
        self.binary = binary
        self.rpc_url = rpc_url

    def run(self, *args: str, wallet_path: Path | None = None) -> str:
        cmd = [self.binary, "--rpc-url", self.rpc_url]
        if wallet_path is not None:
            cmd.extend(["--wallet-path", str(wallet_path)])
        cmd.extend(args)
        print(f"+ {' '.join(cmd)}", flush=True)
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = strip_ansi(result.stdout + result.stderr)
        if result.returncode != 0:
            raise CliError(f"command failed ({result.returncode}): {' '.join(cmd)}\n{output}")
        return output

    def create_wallet(self, wallet_path: Path) -> None:
        wallet_path.parent.mkdir(parents=True, exist_ok=True)
        self.run("create-wallet", "--force", "--wallet-path", str(wallet_path))

    def create_token(self, wallet_path: Path, name: str, symbol: str, total_supply: str) -> str:
        output = self.run(
            "create-token",
            "--name", name,
            "--symbol", symbol,
            "--total-supply", total_supply,
            "--mintable",
            wallet_path=wallet_path,
        )
        match = TOKEN_ADDRESS_PATTERN.search(output)
        if not match:
            raise CliError(f"token address not found in output:\n{output}")
        return match.group(0)

    def create_spot_market(
        self,
        wallet_path: Path,
        name: str,
        base_token: str,
        quote_token: str,
        maker_fee_bps: int,
        taker_fee_bps: int,
    ) -> str:
        output = self.run(
            "create-spot-market",
            "--name", name,
            "--base-token", base_token,
            "--quote-token", quote_token,
            "--tick-size", "0.01",
            "--min-order-size", "0.1",
            "--maker-fee-bps", str(maker_fee_bps),
            "--taker-fee-bps", str(taker_fee_bps),
            "--allow-market-orders",
            wallet_path=wallet_path,
        )
        match = SPOT_MARKET_PATTERN.search(output)
        if not match:
            raise CliError(f"spot market address not found in output:\n{output}")
        return match.group(0)

    def transfer(self, wallet_path: Path, token_address: str, to: str, amount: str) -> None:
        self.run(
            "transfer",
            "--token-address", token_address,
            "--to", to,
            "--amount", amount,
            wallet_path=wallet_path,
        )

    def place_order(
        self,
        wallet_path: Path,
        spot_market: str,
        side: str,
        amount: str,
        price: str,
        token_address: str,
        tif: str,
    ) -> int | None:
        output = self.run(
            "place-order",
            "--spot-market", spot_market,
            "--side", side,
            "--amount", amount,
            "--price", price,
            "--token-address", token_address,
            "--tif", tif,
            wallet_path=wallet_path,
        )
        match = ORDER_ID_PATTERN.search(output)
        return int(match.group(1)) if match else None

    def cancel_order(self, wallet_path: Path, spot_market: str, order_id: int) -> None:
        self.run(
            "cancel-order",
            "--spot-market", spot_market,
            "--order-id", str(order_id),
            wallet_path=wallet_path,
        )

    def balance(
        self,
        token_address: str,
        *,
        wallet_path: Path | None = None,
        account: str | None = None,
    ) -> dict[str, Decimal]:
        args = ["balance", "--token-address", token_address]
        if account is not None:
            args.extend(["--account", account])
        output = self.run(*args, wallet_path=wallet_path)
        values = {key.lower(): Decimal(value) for key, value in BALANCE_LINE_PATTERN.findall(output)}
        if set(values) != {"total", "locked", "available"}:
            raise CliError(f"could not parse balance output:\n{output}")
        return values

    def book(self, spot_market: str, depth: int = 10) -> dict[str, list[tuple[Decimal, Decimal]]]:
        output = self.run("get-book", "--spot-market", spot_market, "--depth", str(depth), "--json")
        start = output.find("{")
        if start < 0:
            raise CliError(f"no JSON in get-book output:\n{output}")
        data = json.loads(output[start:])
        return {
            side: [(Decimal(level["price"]), Decimal(level["total_quantity"])) for level in data[side]]
            for side in ("best_bids", "best_asks")
        }
