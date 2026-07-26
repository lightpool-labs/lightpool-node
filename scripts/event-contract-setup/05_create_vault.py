#!/usr/bin/env python3
"""Create a vault via lightpool-cli."""

from __future__ import annotations

from cli_utils import main_runner
from config import CREATE_VAULT


def build_args() -> list[str]:
    return [
        "create-vault",
        "--name",
        CREATE_VAULT["name"],
        "--quote-token",
        CREATE_VAULT["quote_token"],
        "--share-name",
        CREATE_VAULT["share_name"],
        "--share-symbol",
        CREATE_VAULT["share_symbol"],
        "--seed-amount",
        CREATE_VAULT["seed_amount"],
    ]


if __name__ == "__main__":
    raise SystemExit(main_runner("create-vault", build_args))
