from __future__ import annotations

import shutil
import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from config import (
    BASE_CONSENSUS_PORT,
    BASE_FRONT_PORT,
    BASE_MEMPOOL_PORT,
    BASE_RPC_PORT,
    BASE_WS_PORT,
    LIGHTPOOL_BIN,
    PORT_STEP,
)


@dataclass(frozen=True)
class NodeSpec:
    index: int
    wallet_path: Path
    store_path: Path
    validator_path: Path
    log_path: Path
    front_port: int
    rpc_port: int
    ws_port: int
    mempool_port: int
    consensus_port: int
    boot_peer: str | None = None


def resolve_lightpool_binary() -> str:
    release_binary = Path(LIGHTPOOL_BIN)
    if release_binary.is_file():
        return str(release_binary)

    debug_binary = release_binary.parent.parent / "debug" / release_binary.name
    if debug_binary.is_file():
        return str(debug_binary)

    found = shutil.which("lightpool")
    if found:
        return found

    raise FileNotFoundError(
        "lightpool not found. Run 'cargo build --release' in lightpool-node "
        "or set LIGHTPOOL_BIN."
    )


def node_ports(index: int) -> tuple[int, int, int, int, int]:
    offset = index * PORT_STEP
    return (
        BASE_FRONT_PORT + offset,
        BASE_RPC_PORT + offset,
        BASE_WS_PORT + offset,
        BASE_MEMPOOL_PORT + offset,
        BASE_CONSENSUS_PORT + offset,
    )


def build_node_spec(
    index: int,
    data_dir: Path,
    *,
    boot_peer: str | None = None,
) -> NodeSpec:
    node_dir = data_dir / f"node{index}"
    front_port, rpc_port, ws_port, mempool_port, consensus_port = node_ports(index)
    return NodeSpec(
        index=index,
        wallet_path=node_dir / "wallet.json",
        store_path=node_dir / "store",
        validator_path=node_dir / "validator.json",
        log_path=node_dir / "lightpool.log",
        front_port=front_port,
        rpc_port=rpc_port,
        ws_port=ws_port,
        mempool_port=mempool_port,
        consensus_port=consensus_port,
        boot_peer=boot_peer,
    )


def rpc_ready(rpc_port: int, timeout_sec: float = 120.0) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", rpc_port), timeout=2):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def wait_for_nodes(specs: list[NodeSpec], timeout_sec: float = 120.0) -> bool:
    for spec in specs:
        print(f"Waiting for node{spec.index} RPC on 127.0.0.1:{spec.rpc_port}...", flush=True)
        if not rpc_ready(spec.rpc_port, timeout_sec=timeout_sec):
            print(
                f"Timed out waiting for node{spec.index} RPC on port {spec.rpc_port}. "
                f"Check {spec.log_path}.",
                file=sys.stderr,
            )
            return False
        print(f"node{spec.index} RPC is ready on http://127.0.0.1:{spec.rpc_port}", flush=True)
    return True
