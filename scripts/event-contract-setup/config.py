from __future__ import annotations

import os
from pathlib import Path

# Decimal amounts are passed directly to lightpool-cli, which converts them
# to base units using TOKEN_SCALE (1 token = 1_000_000 base units).
# Examples: "1" -> 1000000, "0.001" -> 1000

RPC_URL = os.environ.get("LIGHTPOOL_RPC_URL", "http://localhost:26300")
WALLET_PATH = os.environ.get("LIGHTPOOL_WALLET_PATH")

# Prefer LIGHTPOOL_CLI; otherwise use bin/lightpool-cli under lightpool-node.
CLI_BINARY = os.environ.get(
    "LIGHTPOOL_CLI",
    str(
        Path(__file__).resolve().parents[2]
        / "bin"
        / "lightpool-cli"
    ),
)

CREATE_TOKEN = {
    "name": "USDT",
    "symbol": "USDT",
    "total_supply": "10000000000000",
    "mintable": True,
}

TRANSFER = {
    "token_address": "0x0200000000000001",
    "to": "0xC019cECd52FE1f68b53daf766c4aF0Dea667A2c7",
    # Enough for ~5 markets × 1e9 mint + leftover collateral for mirrored bids.
    "amount": "20000000000",
}

CREATE_MARKET = {
    "question": "Will France win the 2026 fifa world cup?",
    "collateral_token": "0x0200000000000001",
    "resolution_deadline": "2026-12-31T23:59:59Z",
    "tick_size": "0.001",
    "min_order_size": "0.1",
    "maker_fee_bps": "10",
    "taker_fee_bps": "20",
    "allow_market_orders": True,
}

CREATE_VAULT = {
    "name": "Event LP Vault",
    "quote_token": "0x0200000000000001",
    "share_name": "Event LP Share",
    "share_symbol": "vEVT",
    "seed_amount": "100000",
}

MINT_MARKET = {
    "market_address": "0x0400000000000001",
    "amount": "5000000",
    "collateral_token": "0x0200000000000001",
    "yes_token": "0x0200000000000002",
    "no_token": "0x0200000000000003",
}
