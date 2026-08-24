#!/usr/bin/env python3
"""Scenario 1 - Single-node product path (daily).

Flow: create token -> create spot market -> fund taker -> resting sell ->
IOC buy fills -> maker cancels the resting remainder -> assert balances and
book via CLI/RPC.

Pass criteria (exit code 0):
  - Balances match expected values after the fill (exact, fees included)
  - Book keeps only the resting unfilled remainder after the fill
  - Cancel removes the remainder from the book and unlocks maker funds
  - Node process is still alive and its log has no panic

Run from the lightpool-node root:
  python3 tests/scenario1_single_node.py
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from lib.cli import LightpoolCli, wait_until
from lib.node import (
    RPC_URL,
    SingleNode,
    prepare_node,
    resolve_lightpool_binary,
    rpc_ready,
    start_node,
    stop_node,
)

DATA_DIR = TESTS_DIR / ".scenario1" / "node0"

USDT_SUPPLY = "10000000000"
AAPL_SUPPLY = "1000000"
TAKER_USDT_FUNDING = "100000"

MAKER_FEE_BPS = 10  # 1% (BPS base is 1000)
TAKER_FEE_BPS = 20  # 2%

SELL_AMOUNT = Decimal("10")
SELL_PRICE = Decimal("200")
BUY_AMOUNT = Decimal("5")

# notional = 5 * 200 = 1000 USDT; maker fee = 10, taker fee = 20
NOTIONAL = BUY_AMOUNT * SELL_PRICE
MAKER_FEE = NOTIONAL * MAKER_FEE_BPS / 1000
TAKER_FEE = NOTIONAL * TAKER_FEE_BPS / 1000

failures: list[str] = []


def check(label: str, actual, expected) -> None:
    if actual == expected:
        print(f"OK: {label} = {actual}", flush=True)
    else:
        failures.append(f"{label}: expected {expected}, got {actual}")
        print(f"FAIL: {label}: expected {expected}, got {actual}", flush=True)


def main() -> int:
    binary = resolve_lightpool_binary()
    cli = LightpoolCli(binary, RPC_URL)

    node: SingleNode | None = None
    try:
        node = prepare_node(DATA_DIR, binary)
        node = start_node(node, binary)
        if not rpc_ready():
            print(f"Node RPC did not come up on {RPC_URL}; see {node.log_path}", file=sys.stderr)
            return 1

        maker_wallet = node.wallet_path
        maker_address = node.owner_address()
        print(f"Maker (node wallet): {maker_address}", flush=True)

        usdt = cli.create_token(maker_wallet, "USDT", "USDT", USDT_SUPPLY)
        aapl = cli.create_token(maker_wallet, "Apple", "AAPL", AAPL_SUPPLY)
        print(f"USDT={usdt} AAPL={aapl}", flush=True)

        spot = cli.create_spot_market(maker_wallet, "AAPL/USDT", aapl, usdt, MAKER_FEE_BPS, TAKER_FEE_BPS)
        print(f"SPOT={spot}", flush=True)

        taker_wallet = DATA_DIR / "taker" / "wallet.json"
        cli.create_wallet(taker_wallet)
        import json
        taker_address = json.loads(taker_wallet.read_text(encoding="utf-8"))["address"]
        if not taker_address.startswith("0x"):
            taker_address = f"0x{taker_address}"
        print(f"Taker: {taker_address}", flush=True)

        cli.transfer(maker_wallet, usdt, taker_address, TAKER_USDT_FUNDING)
        wait_until(
            "taker funded with 100000 USDT",
            lambda: cli.balance(usdt, account=taker_address)["total"] == Decimal(TAKER_USDT_FUNDING),
        )

        maker_order_id = cli.place_order(maker_wallet, spot, "sell", str(SELL_AMOUNT), str(SELL_PRICE), aapl, "gtc")
        if maker_order_id is None:
            raise RuntimeError("place-order did not print an Order ID")
        print(f"Maker order id: {maker_order_id}", flush=True)
        wait_until(
            "resting ask 10 @ 200 on the book",
            lambda: cli.book(spot)["best_asks"] == [(SELL_PRICE, SELL_AMOUNT)],
        )

        maker_aapl = cli.balance(aapl, account=maker_address)
        check("maker AAPL total after placing sell", maker_aapl["total"], Decimal(AAPL_SUPPLY))
        check("maker AAPL locked after placing sell", maker_aapl["locked"], SELL_AMOUNT)
        check("maker AAPL available after placing sell", maker_aapl["available"], Decimal(AAPL_SUPPLY) - SELL_AMOUNT)

        cli.place_order(taker_wallet, spot, "buy", str(BUY_AMOUNT), str(SELL_PRICE), usdt, "ioc")
        wait_until(
            "taker received 5 AAPL",
            lambda: cli.balance(aapl, account=taker_address)["total"] == BUY_AMOUNT,
        )

        maker_aapl = cli.balance(aapl, account=maker_address)
        maker_usdt = cli.balance(usdt, account=maker_address)
        taker_aapl = cli.balance(aapl, account=taker_address)
        taker_usdt = cli.balance(usdt, account=taker_address)
        book = cli.book(spot)

        check("taker AAPL total", taker_aapl["total"], BUY_AMOUNT)
        check("taker USDT total", taker_usdt["total"], Decimal(TAKER_USDT_FUNDING) - NOTIONAL - TAKER_FEE)
        check("maker AAPL total after fill", maker_aapl["total"], Decimal(AAPL_SUPPLY) - BUY_AMOUNT)
        check("maker AAPL locked after fill", maker_aapl["locked"], SELL_AMOUNT - BUY_AMOUNT)
        check("maker AAPL available after fill", maker_aapl["available"], Decimal(AAPL_SUPPLY) - SELL_AMOUNT)
        check(
            "maker USDT total after fill",
            maker_usdt["total"],
            Decimal(USDT_SUPPLY) - Decimal(TAKER_USDT_FUNDING) + NOTIONAL - MAKER_FEE,
        )
        check("book asks after fill", book["best_asks"], [(SELL_PRICE, SELL_AMOUNT - BUY_AMOUNT)])
        check("book bids after fill", book["best_bids"], [])

        cli.cancel_order(maker_wallet, spot, maker_order_id)
        wait_until(
            "book empty after maker cancels remainder",
            lambda: cli.book(spot) == {"best_bids": [], "best_asks": []},
        )

        maker_aapl = cli.balance(aapl, account=maker_address)
        check("maker AAPL total after cancel", maker_aapl["total"], Decimal(AAPL_SUPPLY) - BUY_AMOUNT)
        check("maker AAPL locked after cancel", maker_aapl["locked"], Decimal(0))
        check("maker AAPL available after cancel", maker_aapl["available"], Decimal(AAPL_SUPPLY) - BUY_AMOUNT)

        if not node.is_alive():
            failures.append("node process exited unexpectedly")
            print("FAIL: node process exited unexpectedly", flush=True)
        if "panicked at" in node.log_text():
            failures.append("node log contains a panic")
            print("FAIL: node log contains 'panicked at'", flush=True)
    except Exception as error:  # noqa: BLE001 - report and exit non-zero
        failures.append(str(error))
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
    finally:
        if node is not None:
            stop_node(node)

    if failures:
        print(f"\nScenario 1 FAILED ({len(failures)} failure(s)):", flush=True)
        for failure in failures:
            print(f"  - {failure}", flush=True)
        print(f"Node log: {DATA_DIR / 'lightpool.log'}", flush=True)
        return 1

    print("\nScenario 1 PASSED", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
