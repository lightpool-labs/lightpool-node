#!/usr/bin/env python3
"""Transfer USDT to a recipient via lightpool-cli."""

from __future__ import annotations

from cli_utils import main_runner
from config import TRANSFER


def build_args() -> list[str]:
    return [
        "transfer",
        "--token-address",
        TRANSFER["token_address"],
        "--to",
        TRANSFER["to"],
        "--amount",
        TRANSFER["amount"],
    ]


if __name__ == "__main__":
    raise SystemExit(main_runner("transfer", build_args))
