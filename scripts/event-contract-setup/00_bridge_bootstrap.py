#!/usr/bin/env python3
"""Deploy EVM MockUSDT + Bridge, init LightPool bridge, write cash/bridge env.

Phases (so LightPool starts only once, with Link):
  deploy — Reth only: deploy MockUSDT + Bridge, write .env.bridge + bridge-config.json
  init   — LightPool running: init-bridge, fund maker LP USDT via Bridge.deposit, set CASH_TOKEN
  all    — deploy + init in one shot (requires LightPool already running)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from cli_utils import base_args, resolve_cli_binary
from config import RPC_URL, WALLET_PATH

REPO_ROOT = Path(__file__).resolve().parents[3]
BRIDGE_DIR = REPO_ROOT / "lightpool-bridge"
CONTRACTS_DIR = BRIDGE_DIR / "contracts"
SETUP_DIR = Path(__file__).resolve().parent
APP_BACKEND_ENV = REPO_ROOT / "event-contract-app" / "backend" / ".env"
APP_BACKEND_ENV_EXAMPLE = REPO_ROOT / "event-contract-app" / "backend" / ".env.example"
BRIDGE_CONFIG_JSON = REPO_ROOT / "tools" / "bridge-local" / "bridge-config.json"

RETH_RPC = os.environ.get("RETH_RPC", "http://127.0.0.1:8545")
EVM_CHAIN_ID = os.environ.get("EVM_CHAIN_ID", "1337")
LP_RPC = os.environ.get("LIGHTPOOL_RPC_URL", RPC_URL)
DEPLOYER_PK = os.environ.get(
    "BRIDGE_DEPLOYER_PK",
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
)
NODE_WALLET = os.environ.get(
    "LIGHTPOOL_WALLET_PATH",
    str(Path.home() / ".lightpool" / "wallet.json"),
)
USER_ETH = os.environ.get(
    "USER_ETH",
    "0xC019cECd52FE1f68b53daf766c4aF0Dea667A2c7",
)
# Whole USDT (6 decimals applied when minting via DeployLocal / cast).
MAKER_USDT_WHOLE = os.environ.get("MAKER_USDT_WHOLE", "1000000000000")  # 1e12
USER_USDT_WHOLE = os.environ.get("USER_USDT_WHOLE", "10000")  # 10_000
# Whole USDT deposited for maker via Bridge after init-bridge (Link mints LP USDT).
# Default covers liquidity-maker --bootstrap-markets (5 × ~1e9 mint) plus book inventory.
MAKER_LP_DEPOSIT_WHOLE = os.environ.get("MAKER_LP_DEPOSIT_WHOLE", "10000000000")  # 1e10
MAKER_LP_CREDIT_TIMEOUT_SECS = int(os.environ.get("MAKER_LP_CREDIT_TIMEOUT_SECS", "90"))
FOUNDRY_BIN = Path.home() / ".foundry" / "bin"

def _run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> str:
    print(f"+ {' '.join(cmd)}", flush=True)
    merged = os.environ.copy()
    if FOUNDRY_BIN.is_dir():
        merged["PATH"] = f"{FOUNDRY_BIN}:{merged.get('PATH', '')}"
    if env:
        merged.update(env)
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=merged,
        check=True,
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n", flush=True)
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", flush=True)
    return (result.stdout or "") + "\n" + (result.stderr or "")


def _ensure_wallet() -> None:
    wallet = Path(NODE_WALLET)
    if wallet.is_file():
        return
    cmd = base_args() + ["create-wallet", "--force"]
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True, text=True)


def _cli_address() -> str:
    _ensure_wallet()
    cmd = base_args() + ["address"]
    print(f"+ {' '.join(cmd)}", flush=True)
    out = subprocess.run(cmd, check=True, text=True, capture_output=True)
    text = (out.stdout or "") + (out.stderr or "")
    print(text, flush=True)
    match = re.search(r"0x[0-9a-fA-F]{40}", text)
    if not match:
        raise RuntimeError("failed to parse LightPool wallet address")
    return match.group(0)


def _ensure_forge_std() -> None:
    marker = CONTRACTS_DIR / "lib" / "forge-std" / "src" / "Test.sol"
    if marker.is_file():
        return
    _run(["forge", "install", "foundry-rs/forge-std"], cwd=CONTRACTS_DIR)


def _deploy_bridge(validator_eth: str) -> tuple[str, str]:
    _ensure_forge_std()
    output = _run(
        [
            "forge",
            "script",
            "script/DeployLocal.s.sol:DeployLocal",
            "--rpc-url",
            RETH_RPC,
            "--broadcast",
            "--private-key",
            DEPLOYER_PK,
            "-vvv",
        ],
        cwd=CONTRACTS_DIR,
        env={
            "VALIDATOR_ETH": validator_eth,
            "USER_ETH": USER_ETH,
        },
    )
    usdt = re.search(r"USDT\s+(0x[0-9a-fA-F]{40})", output)
    bridge = re.search(r"BRIDGE\s+(0x[0-9a-fA-F]{40})", output)
    if not usdt or not bridge:
        raise RuntimeError("failed to parse ETH_USDT / BRIDGE from forge output")
    return usdt.group(1), bridge.group(1)


def _fund_eth(address: str, amount: str = "10ether") -> None:
    try:
        _run(
            [
                "cast",
                "send",
                address,
                "--value",
                amount,
                "--rpc-url",
                RETH_RPC,
                "--private-key",
                DEPLOYER_PK,
            ]
        )
    except subprocess.CalledProcessError as error:
        print(f"warning: fund ETH to {address} failed: {error}", flush=True)


def _print_usdt_balance(eth_usdt: str, label: str, address: str) -> None:
    try:
        out = _run(
            [
                "cast",
                "call",
                eth_usdt,
                "balanceOf(address)(uint256)",
                address,
                "--rpc-url",
                RETH_RPC,
            ]
        )
        print(f"{label} {address} USDT raw balance: {out.strip()}", flush=True)
    except subprocess.CalledProcessError as error:
        print(f"warning: balanceOf {address} failed: {error}", flush=True)


def _init_bridge(eth_usdt: str) -> str:
    cmd = base_args() + [
        "init-bridge",
        "--evm-chain-id",
        EVM_CHAIN_ID,
        "--evm-token",
        eth_usdt,
        "--name",
        "Tether USD",
        "--symbol",
        "USDT",
        "--epoch",
        "0",
        "--node-wallet",
        NODE_WALLET,
    ]
    print(f"+ {' '.join(cmd)}", flush=True)
    out = subprocess.run(cmd, check=True, text=True, capture_output=True)
    text = (out.stdout or "") + (out.stderr or "")
    print(text, flush=True)
    labeled = re.search(
        r"LP USDT[^\n]*(0x02[0-9a-fA-F]{14})",
        text,
        flags=re.IGNORECASE,
    )
    if labeled:
        return labeled.group(1)
    matches = re.findall(r"0x02[0-9a-fA-F]{14}", text, flags=re.IGNORECASE)
    if matches:
        return matches[-1]
    raise RuntimeError("failed to parse LP USDT from init-bridge output")


def _load_bridge_env() -> dict[str, str]:
    path = SETUP_DIR / ".env.bridge"
    if not path.is_file():
        raise RuntimeError(f"missing {path}; run deploy phase first")
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _write_env(eth_usdt: str, bridge: str, lp_usdt: str | None = None) -> None:
    lp_value = lp_usdt or ""
    content = (
        f"ETH_USDT={eth_usdt}\n"
        f"BRIDGE={bridge}\n"
        f"EVM_CHAIN_ID={EVM_CHAIN_ID}\n"
        f"EVM_RPC_URL={RETH_RPC}\n"
        f"CASH_TOKEN_ADDRESS={lp_value}\n"
        f"CASH_TOKEN_SYMBOL=USDT\n"
        f"LP_USDT={lp_value}\n"
    )
    bridge_env = SETUP_DIR / ".env.bridge"
    bridge_env.write_text(content, encoding="utf-8")
    print(f"wrote {bridge_env}", flush=True)

    os.environ["ETH_USDT"] = eth_usdt
    os.environ["BRIDGE"] = bridge
    os.environ["EVM_CHAIN_ID"] = EVM_CHAIN_ID
    os.environ["EVM_RPC_URL"] = RETH_RPC
    os.environ["CASH_TOKEN_SYMBOL"] = "USDT"
    if lp_usdt:
        os.environ["CASH_TOKEN_ADDRESS"] = lp_usdt
        os.environ["LP_USDT"] = lp_usdt

    target = APP_BACKEND_ENV if APP_BACKEND_ENV.exists() else APP_BACKEND_ENV_EXAMPLE
    if not target.exists():
        print(f"skip app env write; missing {target}", flush=True)
        return

    lines = target.read_text(encoding="utf-8").splitlines()
    updates = {
        "ETH_USDT": eth_usdt,
        "BRIDGE": bridge,
        "EVM_CHAIN_ID": EVM_CHAIN_ID,
        "EVM_RPC_URL": RETH_RPC,
        "CASH_TOKEN_SYMBOL": "USDT",
    }
    if lp_usdt:
        updates["CASH_TOKEN_ADDRESS"] = lp_usdt

    seen = set()
    new_lines: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line and not line.strip().startswith("#") else None
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            new_lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            new_lines.append(f"{key}={value}")
    out_path = APP_BACKEND_ENV
    out_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"wrote {out_path}", flush=True)


def _write_bridge_config(bridge: str) -> None:
    BRIDGE_CONFIG_JSON.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "{\n"
        '  "enabled": true,\n'
        f'  "wallet_path": "{NODE_WALLET}",\n'
        f'  "evm_rpc_url": "{RETH_RPC}",\n'
        f'  "evm_bridge_address": "{bridge}",\n'
        '  "evm_confirmations": 1,\n'
        f'  "lightpool_rpc_url": "{LP_RPC}",\n'
        '  "poll_interval_ms": 1000,\n'
        '  "dispute_period_seconds": 5,\n'
        '  "start_block": 0\n'
        "}\n"
    )
    BRIDGE_CONFIG_JSON.write_text(content, encoding="utf-8")
    print(f"wrote {BRIDGE_CONFIG_JSON}", flush=True)


def _phase_deploy() -> None:
    _run(["cast", "chain-id", "--rpc-url", RETH_RPC])

    validator_eth = _cli_address()
    print(f"VALIDATOR_ETH (validator/maker)={validator_eth}", flush=True)
    print(f"USER_ETH (frontend user)={USER_ETH}", flush=True)
    print(
        f"DeployLocal mints ~{MAKER_USDT_WHOLE} USDT to deployer+validator "
        f"and ~{USER_USDT_WHOLE} USDT to USER_ETH",
        flush=True,
    )

    # Gas for Bridge.deposit / Link txs.
    _fund_eth(validator_eth, "100ether")
    _fund_eth(USER_ETH, "10ether")

    eth_usdt, bridge = _deploy_bridge(validator_eth)
    print(f"ETH_USDT={eth_usdt}", flush=True)
    print(f"BRIDGE={bridge}", flush=True)

    _print_usdt_balance(eth_usdt, "validator/maker", validator_eth)
    _print_usdt_balance(eth_usdt, "user", USER_ETH)

    _write_env(eth_usdt, bridge, lp_usdt=None)
    _write_bridge_config(bridge)
    print(
        "Deploy phase done. Start LightPool, then the bridge process:\n"
        "  lightpool node --role validator\n"
        f"  cargo run --release --manifest-path {REPO_ROOT / 'lightpool-bridge' / 'Cargo.toml'} "
        f"-- --config {BRIDGE_CONFIG_JSON}\n"
        "Then run: python3 00_bridge_bootstrap.py --phase init",
        flush=True,
    )


def _wallet_eth_private_key() -> str:
    """Return 0x-hex secp256k1 key from node wallet (same key as LightPool eth address)."""
    path = Path(NODE_WALLET)
    if not path.is_file():
        raise RuntimeError(f"missing wallet {path}; run deploy / create-wallet first")
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = str(data.get("private_key") or "").strip()
    if not raw:
        raise RuntimeError(f"wallet {path} has empty private_key")
    if raw.startswith("0x"):
        return raw
    if re.fullmatch(r"[0-9a-fA-F]{64}", raw):
        return "0x" + raw
    raise RuntimeError(f"unsupported private_key format in {path}")


def _parse_lp_available_raw(balance_output: str) -> int | None:
    """Parse lightpool balance Available into raw units (6 decimals).

    CLI prints whole USDT when the fractional part is zero (e.g. ``100`` not ``100.000000``).
    """
    match = re.search(r"Available:\s*([0-9]+(?:\.[0-9]+)?)", balance_output)
    if not match:
        return None
    text = match.group(1)
    if "." in text:
        whole, frac = text.split(".", 1)
        frac = (frac + "000000")[:6]
        return int(whole) * 1_000_000 + int(frac)
    return int(text) * 1_000_000


def _wait_maker_lp_balance(lp_usdt: str, account: str, min_available_raw: int) -> None:
    deadline = time.time() + MAKER_LP_CREDIT_TIMEOUT_SECS
    last = ""
    while time.time() < deadline:
        cmd = base_args() + [
            "balance",
            "--token-address",
            lp_usdt,
            "--account",
            account,
        ]
        print(f"+ {' '.join(cmd)}", flush=True)
        out = subprocess.run(cmd, check=False, text=True, capture_output=True)
        last = (out.stdout or "") + (out.stderr or "")
        print(last, flush=True)
        available = _parse_lp_available_raw(last)
        if available is not None and available >= min_available_raw:
            print(
                f"maker LP USDT credited: available_raw={available} account={account}",
                flush=True,
            )
            return
        time.sleep(2)
    raise RuntimeError(
        "timed out waiting for Link confirm_dep to credit maker LP USDT; "
        f"last balance output:\n{last}"
    )


def _fund_maker_lp_usdt(eth_usdt: str, bridge: str, lp_usdt: str) -> None:
    """Approve + Bridge.deposit maker EVM USDT → LP USDT (requires Link running)."""
    maker = _cli_address()
    maker_pk = _wallet_eth_private_key()
    whole = int(MAKER_LP_DEPOSIT_WHOLE)
    if whole <= 0:
        raise RuntimeError("MAKER_LP_DEPOSIT_WHOLE must be > 0")
    amount_raw = whole * 1_000_000
    if amount_raw > (2**64 - 1):
        raise RuntimeError(f"deposit amount {amount_raw} exceeds uint64")

    print(
        f"Funding maker LP USDT via Bridge.deposit: maker={maker} "
        f"whole={whole} raw={amount_raw} lp={lp_usdt}",
        flush=True,
    )
    _print_usdt_balance(eth_usdt, "maker EVM USDT before deposit", maker)

    _run(
        [
            "cast",
            "send",
            eth_usdt,
            "approve(address,uint256)",
            bridge,
            str(amount_raw),
            "--rpc-url",
            RETH_RPC,
            "--private-key",
            maker_pk,
        ]
    )
    _run(
        [
            "cast",
            "send",
            bridge,
            "deposit(uint64,address)",
            str(amount_raw),
            maker,
            "--rpc-url",
            RETH_RPC,
            "--private-key",
            maker_pk,
        ]
    )
    _wait_maker_lp_balance(lp_usdt, maker, min_available_raw=amount_raw)


def _phase_init() -> None:
    values = _load_bridge_env()
    eth_usdt = values.get("ETH_USDT") or ""
    bridge = values.get("BRIDGE") or ""
    if not eth_usdt or not bridge:
        raise RuntimeError(".env.bridge missing ETH_USDT / BRIDGE; run --phase deploy first")

    existing_lp = (values.get("LP_USDT") or values.get("CASH_TOKEN_ADDRESS") or "").strip()
    try:
        lp_usdt = _init_bridge(eth_usdt)
    except (RuntimeError, subprocess.CalledProcessError) as error:
        if existing_lp.lower().startswith("0x02") and len(existing_lp) >= 18:
            print(
                f"init-bridge failed ({error}); reusing existing LP_USDT={existing_lp}",
                flush=True,
            )
            lp_usdt = existing_lp
        else:
            raise

    print(f"LP_USDT={lp_usdt}", flush=True)
    _write_env(eth_usdt, bridge, lp_usdt)

    _fund_maker_lp_usdt(eth_usdt, bridge, lp_usdt)

    print(
        "Init phase done. CASH_TOKEN_ADDRESS is bridge LP USDT; "
        "maker already holds LP USDT from Bridge.deposit + Link confirm_dep. "
        "liquidity-maker --bootstrap-markets can mint without Balance object not found.",
        flush=True,
    )


def run(phase: str = "all") -> int:
    try:
        resolve_cli_binary()
        print(f"RPC_URL={RPC_URL} phase={phase}", flush=True)
        if WALLET_PATH:
            print(f"WALLET_PATH={WALLET_PATH}", flush=True)

        if phase == "deploy":
            _phase_deploy()
        elif phase == "init":
            _phase_init()
        elif phase == "all":
            _phase_deploy()
            _phase_init()
        else:
            raise RuntimeError(f"unknown phase: {phase}")
        return 0
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(f"command failed with exit code {error.returncode}", file=sys.stderr)
        if error.stdout:
            print(error.stdout, file=sys.stderr)
        if error.stderr:
            print(error.stderr, file=sys.stderr)
        return error.returncode or 1
    except Exception as error:  # noqa: BLE001
        print(f"bridge bootstrap failed: {error}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge bootstrap for event-contract setup")
    parser.add_argument(
        "--phase",
        choices=("deploy", "init", "all"),
        default=os.environ.get("BRIDGE_BOOTSTRAP_PHASE", "all"),
        help="deploy=Reth only; init=init-bridge after node+Link up; all=both (node must be up)",
    )
    args = parser.parse_args()
    return run(args.phase)


if __name__ == "__main__":
    raise SystemExit(main())
