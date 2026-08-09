#!/usr/bin/env python3
"""Create USDT collateral token via lightpool."""

from __future__ import annotations

from cli_utils import main_runner
from config import CREATE_TOKEN


def build_args() -> list[str]:
    args = [
        "create-token",
        "--name",
        CREATE_TOKEN["name"],
        "--symbol",
        CREATE_TOKEN["symbol"],
        "--total-supply",
        CREATE_TOKEN["total_supply"],
    ]
    if CREATE_TOKEN["mintable"]:
        args.append("--mintable")
    return args


if __name__ == "__main__":
    raise SystemExit(main_runner("create-token", build_args))
