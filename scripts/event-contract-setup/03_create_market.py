#!/usr/bin/env python3
"""Create an event contract market via lightpool-cli."""

from __future__ import annotations

from cli_utils import main_runner
from config import CREATE_MARKET


def build_args() -> list[str]:
    args = [
        "create-market",
        "--question",
        CREATE_MARKET["question"],
        "--collateral-token",
        CREATE_MARKET["collateral_token"],
        "--resolution-deadline",
        CREATE_MARKET["resolution_deadline"],
        "--tick-size",
        CREATE_MARKET["tick_size"],
        "--min-order-size",
        CREATE_MARKET["min_order_size"],
        "--maker-fee-bps",
        CREATE_MARKET["maker_fee_bps"],
        "--taker-fee-bps",
        CREATE_MARKET["taker_fee_bps"],
    ]
    if CREATE_MARKET["allow_market_orders"]:
        args.append("--allow-market-orders")
    return args


if __name__ == "__main__":
    raise SystemExit(main_runner("create-market", build_args))
