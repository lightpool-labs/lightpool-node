#!/usr/bin/env python3
"""Mint a complete YES/NO set for an event contract market."""

from __future__ import annotations

from cli_utils import main_runner
from config import MINT_MARKET


def build_args() -> list[str]:
    return [
        "mint-market",
        "--market-address",
        MINT_MARKET["market_address"],
        "--amount",
        MINT_MARKET["amount"],
        "--collateral-token",
        MINT_MARKET["collateral_token"],
        "--yes-token",
        MINT_MARKET["yes_token"],
        "--no-token",
        MINT_MARKET["no_token"],
    ]


if __name__ == "__main__":
    raise SystemExit(main_runner("mint-market", build_args))
