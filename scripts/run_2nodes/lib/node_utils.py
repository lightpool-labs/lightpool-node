from __future__ import annotations

import os
import shutil
import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from lib.config import (
    BASE_CONSENSUS_PORT,
    BASE_FRONT_PORT,
    BASE_MEMPOOL_PORT,
    BASE_RPC_PORT,
    BASE_WS_PORT,
    LIGHTPOOL_BIN,
    PORT_STEP,
)
from lib.rpc_utils import rpc_url_for_port

ROLE_VALIDATOR = "validator"
ROLE_PENDING_MEMBER = "pending-member"


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
    role: str = ROLE_VALIDATOR
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


def boot_peer_url(leader_index: int = 0) -> str:
    _, rpc_port, _, _, _ = node_ports(leader_index)
    return rpc_url_for_port(rpc_port)


def build_node_spec(
    index: int,
    data_dir: Path,
    *,
    role: str = ROLE_VALIDATOR,
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
        role=role,
        boot_peer=boot_peer,
    )


def lightpool_argv(spec: NodeSpec) -> list[str]:
    argv = [
        "--wallet",
        str(spec.wallet_path),
        "--store",
        str(spec.store_path),
        "--validator",
        str(spec.validator_path),
        "--role",
        spec.role,
        "--front-listen-addr",
        f"0.0.0.0:{spec.front_port}",
        "--rpc-listen-addr",
        f"0.0.0.0:{spec.rpc_port}",
        "--ws-listen-addr",
        f"0.0.0.0:{spec.ws_port}",
    ]
    if spec.boot_peer:
        argv.extend(["--boot-peer", spec.boot_peer])
    return argv


def exec_lightpool(spec: NodeSpec, *, log_file: Path | str | None = None) -> None:
    binary = resolve_lightpool_binary()
    argv = lightpool_argv(spec)
    rpc_url = rpc_url_for_port(spec.rpc_port)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        print(
            f"Starting node{spec.index} role={spec.role} "
            f"(RPC {rpc_url}, log {log_path})",
            flush=True,
        )
        fd = os.open(str(log_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        os.dup2(fd, 1)
        os.dup2(fd, 2)
        if fd > 2:
            os.close(fd)
    elif spec.role == ROLE_PENDING_MEMBER:
        print(
            f"Starting node{spec.index} as PendingMember (stake=0), "
            f"boot-peer={spec.boot_peer}; will spawn_committee_member_announcement "
            f"Join to node0",
            flush=True,
        )
    else:
        print(
            f"Starting node{spec.index} as Validator (RPC {rpc_url})",
            flush=True,
        )

    os.execv(binary, [binary, *argv])


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


def run_local_node(
    index: int,
    data_dir: Path,
    *,
    role: str,
    boot_peer: str | None = None,
    log_file: Path | str | None = None,
    reset_store: bool = False,
    require_boot_peer_ready: bool = False,
) -> None:
    if role == ROLE_PENDING_MEMBER and not boot_peer:
        print("PendingMember requires --boot-peer (node0 RPC)", file=sys.stderr)
        raise SystemExit(1)

    spec = build_node_spec(index, data_dir, role=role, boot_peer=boot_peer)

    if not spec.wallet_path.is_file() or not spec.validator_path.is_file():
        print("Run init.py first", file=sys.stderr)
        raise SystemExit(1)

    if require_boot_peer_ready and boot_peer:
        leader_rpc_port = node_ports(0)[1]
        print(f"Waiting for node0 RPC on {boot_peer} before joining...", flush=True)
        if not rpc_ready(leader_rpc_port, timeout_sec=30.0):
            print(
                f"node0 RPC is not ready at {boot_peer}.\n"
                "Start node0 first with run_node0.py and wait until you see:\n"
                "  Node is running; press Ctrl+C to stop",
                file=sys.stderr,
            )
            raise SystemExit(1)

    if reset_store and spec.store_path.is_dir():
        print(f"Removing stale node{index} store: {spec.store_path}")
        shutil.rmtree(spec.store_path)

    spec.store_path.mkdir(parents=True, exist_ok=True)
    exec_lightpool(spec, log_file=log_file)
