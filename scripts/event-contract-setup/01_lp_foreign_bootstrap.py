#!/usr/bin/env python3
"""Bootstrap LightPool-as-foreign bridge (two LP nodes, no Reth).

Phases:
  local-init    — init inbound bridge on local node (:26300)
  foreign-setup — create USDT + outbound bridge on foreign node (:27300)
  config        — write .env.lp-foreign
  all           — local-init + foreign-setup + config (nodes must be up)

Run ``--phase all`` once per clean chain. Each ``local-init`` allocates the next
inbound bridge instance (…0001, …0002, …0003, …). Re-running ``all`` without Reset
creates a new pair and invalidates earlier Admin UI routes.

If ``all`` fails after ``local-init`` succeeds, recover with:
  python3 01_lp_foreign_bootstrap.py --phase foreign-setup
  python3 01_lp_foreign_bootstrap.py --phase config
Do not re-run ``all``.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from cli_utils import base_args, resolve_cli_binary

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


OUTBOUND_MODULE_ROOT = "0x0800000000000000"


def _parse_outbound_bridge(text: str) -> str:
    labeled = re.search(
        r"Outbound bridge contract:\s*(0x08[0-9a-fA-F]{14})",
        text,
        flags=re.IGNORECASE,
    )
    if labeled:
        addr = labeled.group(1)
        if addr.lower() != OUTBOUND_MODULE_ROOT:
            return addr
    matches = [
        match
        for match in re.findall(r"0x08[0-9a-fA-F]{14}", text, flags=re.IGNORECASE)
        if match.lower() != OUTBOUND_MODULE_ROOT
    ]
    if matches:
        return matches[-1]
    raise RuntimeError(
        "failed to parse outbound bridge instance from create-outbound-bridge output "
        f"(expected 0x0800000000000001 or higher, not module root {OUTBOUND_MODULE_ROOT})"
    )


def _parse_foreign_token(text: str) -> str:
    matches = re.findall(r"0x02[0-9a-fA-F]{14}", text, flags=re.IGNORECASE)
    if not matches:
        raise RuntimeError("failed to parse foreign USDT from create-token output")
    return matches[-1]


def _parse_inbound_bridge(text: str) -> str:
    labeled = re.search(
        r"Inbound bridge contract:\s*(0x06[0-9a-fA-F]{14})",
        text,
        flags=re.IGNORECASE,
    )
    if labeled:
        return labeled.group(1)
    matches = re.findall(r"0x06[0-9a-fA-F]{14}", text, flags=re.IGNORECASE)
    if matches:
        return matches[-1]
    raise RuntimeError("failed to parse inbound bridge from init-bridge output")


def _phase_local_init() -> tuple[str, str]:
    foreign_addr = _cli_address(FOREIGN_RPC, FOREIGN_WALLET)
    foreign_token_placeholder = _contract_to_foreign_token(foreign_addr)
    out = _cli(
        [
            "init-bridge",
            "--foreign-chain-id",
            str(FOREIGN_CHAIN_ID),
            "--foreign-token",
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
    inbound_bridge = _parse_inbound_bridge(out)
    print(f"LOCAL_LP_USDT={lp_usdt}", flush=True)
    print(f"LOCAL_INBOUND_BRIDGE={inbound_bridge}", flush=True)
    return lp_usdt, inbound_bridge


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
        wallet=LOCAL_WALLET,
    )
    outbound_bridge = _parse_outbound_bridge(out)
    print(f"FOREIGN_USDT={foreign_usdt}", flush=True)
    print(f"OUTBOUND_BRIDGE={outbound_bridge}", flush=True)
    return foreign_usdt, outbound_bridge


def _load_env_file() -> dict[str, str]:
    if not ENV_FILE.is_file():
        return {}
    values: dict[str, str] = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _print_admin_route_fields(
    local_inbound_bridge: str,
    local_lp_usdt: str,
    foreign_usdt: str,
    outbound_bridge: str,
) -> None:
    print("=== LightPool foreign route — Admin UI (from .env.lp-foreign) ===", flush=True)
    print("Route ID:                  foreign-lp-usdt", flush=True)
    print("Enabled:                   yes", flush=True)
    print("Kind:                      lightpool", flush=True)
    print(f"Local inbound bridge:      {local_inbound_bridge}", flush=True)
    print(f"Local LP token:            {local_lp_usdt}", flush=True)
    print(f"Foreign LP RPC:            {FOREIGN_RPC}", flush=True)
    print(f"Foreign chain ID:          {FOREIGN_CHAIN_ID}", flush=True)
    print(f"Outbound bridge contract:  {outbound_bridge}", flush=True)
    print(f"Foreign token:             {foreign_usdt}", flush=True)


def _write_env(
    local_lp_usdt: str,
    local_inbound_bridge: str,
    foreign_usdt: str,
    outbound_bridge: str,
) -> None:
    env_lines = [
        f"LOCAL_LP_USDT={local_lp_usdt}",
        f"LOCAL_INBOUND_BRIDGE={local_inbound_bridge}",
        f"FOREIGN_USDT={foreign_usdt}",
        f"OUTBOUND_BRIDGE={outbound_bridge}",
        f"LP_RPC={LOCAL_RPC}",
        f"LP_FOREIGN_RPC={FOREIGN_RPC}",
        f"LOCAL_CHAIN_ID={LOCAL_CHAIN_ID}",
        f"FOREIGN_CHAIN_ID={FOREIGN_CHAIN_ID}",
    ]
    ENV_FILE.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    print(f"wrote {ENV_FILE}", flush=True)
    _print_admin_route_fields(local_inbound_bridge, local_lp_usdt, foreign_usdt, outbound_bridge)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("local-init", "foreign-setup", "config", "all"),
        default="all",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow --phase all when .env.lp-foreign already exists (creates a new instance pair)",
    )
    args = parser.parse_args()

    try:
        if args.phase == "all" and ENV_FILE.is_file() and not args.force:
            existing = _load_env_file()
            raise RuntimeError(
                f"{ENV_FILE} already exists (LOCAL_INBOUND_BRIDGE="
                f"{existing.get('LOCAL_INBOUND_BRIDGE', '?')}, LOCAL_LP_USDT="
                f"{existing.get('LOCAL_LP_USDT', '?')}). "
                "Use existing values in Admin UI, or run Reset and bootstrap again. "
                "If the first run failed after local-init, run --phase foreign-setup then "
                "--phase config instead of --phase all. "
                "Pass --force only when you intentionally want a new instance pair."
            )

        saved = _load_env_file()
        local_lp = os.environ.get("LOCAL_LP_USDT", saved.get("LOCAL_LP_USDT", "")).strip()
        local_inbound = os.environ.get(
            "LOCAL_INBOUND_BRIDGE", saved.get("LOCAL_INBOUND_BRIDGE", "")
        ).strip()
        foreign_usdt = os.environ.get("FOREIGN_USDT", saved.get("FOREIGN_USDT", "")).strip()
        outbound_bridge = os.environ.get(
            "OUTBOUND_BRIDGE", saved.get("OUTBOUND_BRIDGE", "")
        ).strip()

        if args.phase in ("local-init", "all"):
            local_lp, local_inbound = _phase_local_init()

        if args.phase == "local-init":
            return 0

        if args.phase in ("foreign-setup", "all"):
            foreign_usdt, outbound_bridge = _phase_foreign_setup(local_lp)
        elif args.phase == "config":
            if not local_lp or not local_inbound or not foreign_usdt or not outbound_bridge:
                raise RuntimeError(
                    "config phase needs LOCAL_LP_USDT, LOCAL_INBOUND_BRIDGE, FOREIGN_USDT, "
                    "OUTBOUND_BRIDGE (run foreign-setup first or source .env.lp-foreign)"
                )

        if args.phase in ("config", "all"):
            _write_env(local_lp, local_inbound, foreign_usdt, outbound_bridge)
        return 0
    except (subprocess.CalledProcessError, RuntimeError, FileNotFoundError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
