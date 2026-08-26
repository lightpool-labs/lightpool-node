#!/usr/bin/env python3
"""Bootstrap LightPool-as-foreign bridge (two LP nodes, no Reth).

Phases:
  local-init   — init inbound bridge on local node (:26300)
  foreign-setup — create USDT + outbound bridge on foreign node (:27300)
  config       — write lightpool-bridge/bridge-config.json + .env.lp-foreign
  all          — local-init + foreign-setup + config (nodes + bridge must be up for later steps)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from cli_utils import base_args, resolve_cli_binary

REPO_ROOT = Path(__file__).resolve().parents[3]
BRIDGE_DIR = REPO_ROOT / "lightpool-bridge"
BRIDGE_CONFIG_JSON = BRIDGE_DIR / "bridge-config.json"
SETUP_DIR = Path(__file__).resolve().parent
ENV_FILE = SETUP_DIR / ".env.lp-foreign"

LOCAL_RPC = os.environ.get("LP_RPC", os.environ.get("LIGHTPOOL_RPC_URL", "http://127.0.0.1:26300"))
FOREIGN_RPC = os.environ.get("LP_FOREIGN_RPC", "http://127.0.0.1:27300")
LOCAL_CHAIN_ID = int(os.environ.get("LOCAL_CHAIN_ID", "1"))
FOREIGN_CHAIN_ID = int(os.environ.get("FOREIGN_CHAIN_ID", "2"))
LOCAL_WALLET = os.environ.get(
    "LIGHTPOOL_WALLET_PATH",
    str(Path.home() / ".lightpool" / "wallet.json"),
)
FOREIGN_WALLET = os.environ.get(
    "LIGHTPOOL_FOREIGN_WALLET_PATH",
    str(Path.home() / ".lightpool" / "foreign" / "wallet.json"),
)
VALIDATOR_STAKE = os.environ.get("VALIDATOR_STAKE", "100")


def _run(cmd: list[str], *, env: dict | None = None) -> str:
    print(f"+ {' '.join(cmd)}", flush=True)
    merged = os.environ.copy()
    if env:
        merged.update(env)
    result = subprocess.run(cmd, check=True, text=True, capture_output=True, env=merged)
    text = (result.stdout or "") + (result.stderr or "")
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n", flush=True)
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", flush=True)
    return text


def _cli(args: list[str], *, rpc: str, wallet: str | None = None) -> str:
    cmd = [resolve_cli_binary(), "--rpc-url", rpc]
    if wallet:
        cmd.extend(["--wallet-path", wallet])
    cmd.extend(args)
    return _run(cmd)


def _cli_address(rpc: str, wallet: str) -> str:
    out = _cli(["address"], rpc=rpc, wallet=wallet)
    match = re.search(r"0x[0-9a-fA-F]{40}", out)
    if not match:
        raise RuntimeError(f"failed to parse address from:\n{out}")
    return match.group(0)


def _contract_to_foreign_token(contract_hex: str) -> str:
    raw = bytes.fromhex(contract_hex.replace("0x", ""))
    if len(raw) > 20:
        raise RuntimeError(f"contract address too long: {contract_hex}")
    padded = b"\x00" * (20 - len(raw)) + raw
    return "0x" + padded.hex()


def _parse_lp_usdt(text: str) -> str:
    labeled = re.search(r"LP USDT[^\n]*(0x02[0-9a-fA-F]{14})", text, flags=re.IGNORECASE)
    if labeled:
        return labeled.group(1)
    matches = re.findall(r"0x02[0-9a-fA-F]{14}", text, flags=re.IGNORECASE)
    if matches:
        return matches[-1]
    raise RuntimeError("failed to parse LP USDT from init-bridge output")


def _parse_outbound_bridge(text: str) -> str:
    labeled = re.search(
        r"Outbound bridge contract:\s*(0x[0-9a-fA-F]{30,34})",
        text,
        flags=re.IGNORECASE,
    )
    if labeled:
        return labeled.group(1)
    matches = re.findall(r"0x08[0-9a-fA-F]{14}", text, flags=re.IGNORECASE)
    if matches:
        return matches[-1]
    return "0x0800000000000001"


def _parse_foreign_token(text: str) -> str:
    matches = re.findall(r"0x02[0-9a-fA-F]{14}", text, flags=re.IGNORECASE)
    if not matches:
        raise RuntimeError("failed to parse foreign USDT from create-token output")
    return matches[-1]


def _phase_local_init() -> str:
    foreign_addr = _cli_address(FOREIGN_RPC, FOREIGN_WALLET)
    foreign_token_placeholder = _contract_to_foreign_token(foreign_addr)
    out = _cli(
        [
            "init-bridge",
            "--evm-chain-id",
            str(FOREIGN_CHAIN_ID),
            "--evm-token",
            foreign_token_placeholder,
            "--name",
            "Tether USD",
            "--symbol",
            "USDT",
        ],
        rpc=LOCAL_RPC,
        wallet=LOCAL_WALLET,
    )
    lp_usdt = _parse_lp_usdt(out)
    print(f"LOCAL_LP_USDT={lp_usdt}", flush=True)
    return lp_usdt


def _phase_foreign_setup(local_lp_usdt: str) -> tuple[str, str]:
    out = _cli(
        [
            "create-token",
            "--name",
            "Tether USD",
            "--symbol",
            "USDT",
            "--total-supply",
            "10000000000000",
            "--mintable",
        ],
        rpc=FOREIGN_RPC,
        wallet=FOREIGN_WALLET,
    )
    foreign_usdt = _parse_foreign_token(out)

    local_lp_foreign = _contract_to_foreign_token(local_lp_usdt)
    out = _cli(
        [
            "create-outbound-bridge",
            "--token-address",
            foreign_usdt,
            "--foreign-chain-id",
            str(LOCAL_CHAIN_ID),
            "--foreign-token",
            local_lp_foreign,
            "--epoch",
            "0",
            "--stake",
            VALIDATOR_STAKE,
        ],
        rpc=FOREIGN_RPC,
        wallet=FOREIGN_WALLET,
    )
    outbound_bridge = _parse_outbound_bridge(out)
    print(f"FOREIGN_USDT={foreign_usdt}", flush=True)
    print(f"OUTBOUND_BRIDGE={outbound_bridge}", flush=True)
    return foreign_usdt, outbound_bridge


def _write_config(local_lp_usdt: str, foreign_usdt: str, outbound_bridge: str) -> None:
    local_lp_foreign = _contract_to_foreign_token(local_lp_usdt)
    content = {
        "enabled": True,
        "wallet_path": LOCAL_WALLET,
        "lightpool_rpc_url": LOCAL_RPC,
        "poll_interval_ms": 1000,
        "dispute_period_seconds": 5,
        "local": {"rpc_url": LOCAL_RPC, "chain_id": LOCAL_CHAIN_ID},
        "routes": [
            {
                "id": "foreign-lp-usdt",
                "enabled": True,
                "local_inbound": {
                    "bridge_contract": "0x0600000000000000",
                    "lp_token": local_lp_usdt,
                },
                "foreign": {
                    "kind": "lightpool",
                    "rpc_url": FOREIGN_RPC,
                    "chain_id": FOREIGN_CHAIN_ID,
                    "outbound_bridge_contract": outbound_bridge,
                    "foreign_token": local_lp_foreign,
                },
            }
        ],
    }
    BRIDGE_CONFIG_JSON.parent.mkdir(parents=True, exist_ok=True)
    BRIDGE_CONFIG_JSON.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {BRIDGE_CONFIG_JSON}", flush=True)

    env_lines = [
        f"LOCAL_LP_USDT={local_lp_usdt}",
        f"FOREIGN_USDT={foreign_usdt}",
        f"OUTBOUND_BRIDGE={outbound_bridge}",
        f"LP_RPC={LOCAL_RPC}",
        f"LP_FOREIGN_RPC={FOREIGN_RPC}",
        f"LOCAL_CHAIN_ID={LOCAL_CHAIN_ID}",
        f"FOREIGN_CHAIN_ID={FOREIGN_CHAIN_ID}",
    ]
    ENV_FILE.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    print(f"wrote {ENV_FILE}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("local-init", "foreign-setup", "config", "all"),
        default="all",
    )
    args = parser.parse_args()

    try:
        local_lp = os.environ.get("LOCAL_LP_USDT", "").strip()
        foreign_usdt = os.environ.get("FOREIGN_USDT", "").strip()
        outbound_bridge = os.environ.get("OUTBOUND_BRIDGE", "").strip()

        if args.phase in ("local-init", "all"):
            local_lp = _phase_local_init()

        if args.phase == "local-init":
            return 0

        if args.phase in ("foreign-setup", "all"):
            foreign_usdt, outbound_bridge = _phase_foreign_setup(local_lp)
        elif args.phase == "config":
            if not local_lp or not foreign_usdt or not outbound_bridge:
                raise RuntimeError(
                    "config phase needs LOCAL_LP_USDT, FOREIGN_USDT, OUTBOUND_BRIDGE "
                    "(run foreign-setup first or source .env.lp-foreign)"
                )

        if args.phase in ("config", "all"):
            _write_config(local_lp, foreign_usdt, outbound_bridge)
        return 0
    except (subprocess.CalledProcessError, RuntimeError, FileNotFoundError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
