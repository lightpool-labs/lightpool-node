from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Iterable

from lib.config import STAKING_BOND_AMOUNTS, STAKING_NODE1_FUNDING
from lib.node_utils import NodeSpec
from lib.rpc_utils import rpc_url_for_port
from lib.wallet_utils import resolve_cli_binary, wallet_identity

TOKEN_ADDRESS_PATTERN = re.compile(
    r"Token Address:\s*(0x[0-9a-fA-F]+)",
    re.MULTILINE,
)

CREATE_LPL_TOKEN = {
    "name": "LightPool",
    "symbol": "LPL",
    "total_supply": "100000000",
    "mintable": False,
}

INIT_CONFIG = {
    "min_bond": "10000",
    "committee_size": 32,
}


def staking_state_path(data_dir: Path) -> Path:
    return data_dir / "staking_state.json"


def load_staking_state(data_dir: Path) -> dict:
    path = staking_state_path(data_dir)
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_staking_state(data_dir: Path, **updates) -> dict:
    state = load_staking_state(data_dir)
    state.update(updates)
    path = staking_state_path(data_dir)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def run_cli(
    rpc_spec: NodeSpec,
    wallet_spec: NodeSpec,
    subcommand: Iterable[str],
    *,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        resolve_cli_binary(),
        "--rpc-url",
        rpc_url_for_port(rpc_spec.rpc_port),
        "--wallet-path",
        str(wallet_spec.wallet_path),
        *subcommand,
    ]
    print(f"+ {' '.join(cmd)}", flush=True)
    return subprocess.run(
        cmd,
        check=True,
        text=True,
        capture_output=capture_output,
    )


def create_lpl_token(leader: NodeSpec) -> str:
    args = [
        "create-token",
        "--name",
        CREATE_LPL_TOKEN["name"],
        "--symbol",
        CREATE_LPL_TOKEN["symbol"],
        "--total-supply",
        CREATE_LPL_TOKEN["total_supply"],
    ]
    if CREATE_LPL_TOKEN["mintable"]:
        args.append("--mintable")

    result = run_cli(leader, leader, args, capture_output=True)
    stdout = result.stdout or ""
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n", flush=True)
    match = TOKEN_ADDRESS_PATTERN.search(stdout)
    if not match:
        raise RuntimeError("create-token did not return a token address")
    return match.group(1)


def init_staking_config(leader: NodeSpec, lpl_token: str) -> None:
    run_cli(
        leader,
        leader,
        [
            "init-config",
            "--lpl-token",
            lpl_token,
            "--min-bond",
            INIT_CONFIG["min_bond"],
            "--committee-size",
            str(INIT_CONFIG["committee_size"]),
        ],
    )


def bond_lpl(rpc_spec: NodeSpec, wallet_spec: NodeSpec, lpl_token: str, amount: str) -> None:
    run_cli(
        rpc_spec,
        wallet_spec,
        [
            "bond-lpl",
            "--lpl-token",
            lpl_token,
            "--amount",
            amount,
        ],
    )


def transfer_lpl(
    rpc_spec: NodeSpec,
    wallet_spec: NodeSpec,
    lpl_token: str,
    to_address: str,
    amount: str,
) -> None:
    run_cli(
        rpc_spec,
        wallet_spec,
        [
            "transfer",
            "--token-address",
            lpl_token,
            "--to",
            to_address,
            "--amount",
            amount,
        ],
    )


def run_staking_setup(
    leader: NodeSpec,
    follower: NodeSpec,
    data_dir: Path,
) -> None:
    state = load_staking_state(data_dir)
    if state.get("follower_bond_done"):
        print("Staking setup already completed; skipping.", flush=True)
        return

    lpl_token = state.get("lpl_token")

    print(
        f"Staking setup on node{leader.index} chain: create LPL + init-config + "
        f"bond {STAKING_BOND_AMOUNTS[0]}...",
        flush=True,
    )
    if not lpl_token:
        lpl_token = create_lpl_token(leader)
        save_staking_state(data_dir, lpl_token=lpl_token)
    if not state.get("init_config_done"):
        init_staking_config(leader, lpl_token)
        save_staking_state(data_dir, init_config_done=True)
    bond_lpl(leader, leader, lpl_token, STAKING_BOND_AMOUNTS[0])

    follower_owner, _ = wallet_identity(follower.wallet_path)
    print(
        f"Funding node{follower.index} wallet with {STAKING_NODE1_FUNDING} LPL from "
        f"node{leader.index}...",
        flush=True,
    )
    transfer_lpl(leader, leader, lpl_token, follower_owner, STAKING_NODE1_FUNDING)

    print(
        f"Staking setup for node{follower.index} on node{leader.index} chain: "
        f"bond {STAKING_BOND_AMOUNTS[1]}...",
        flush=True,
    )
    bond_lpl(leader, follower, lpl_token, STAKING_BOND_AMOUNTS[1])
    save_staking_state(data_dir, follower_bond_done=True)
