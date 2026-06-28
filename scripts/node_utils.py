from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
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
    PROJECT_ROOT,
)


@dataclass(frozen=True)
class NodeSpec:
    index: int
    wallet_path: Path
    store_path: Path
    validators_path: Path
    log_path: Path
    front_port: int
    rpc_port: int
    ws_port: int
    mempool_port: int
    consensus_port: int


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
        "lightpool not found. Run 'cargo build --release' in lightpool-node, "
        "set LIGHTPOOL_BIN, or place the binary at bin/lightpool."
    )


def build_binaries() -> None:
    launcher_cmd = ["cargo", "build", "--release"]
    print(f"+ {' '.join(launcher_cmd)}", flush=True)
    subprocess.run(launcher_cmd, check=True, cwd=PROJECT_ROOT)

    bin_path = PROJECT_ROOT / "bin" / "lightpool"
    cli_path = PROJECT_ROOT / "bin" / "lightpool-cli"
    missing = [
        path
        for path in (bin_path, cli_path)
        if not path.is_file()
    ]
    if missing:
        missing_list = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(
            "Missing binaries after build: "
            f"{missing_list}. Place lightpool-v*.tar.gz and "
            "lightpool-cli-v*.tar.gz in bin/ and run 'cargo build --release'."
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
    validators_path: Path,
) -> NodeSpec:
    node_dir = data_dir / f"node{index}"
    front_port, rpc_port, ws_port, mempool_port, consensus_port = node_ports(index)
    return NodeSpec(
        index=index,
        wallet_path=node_dir / "wallet.json",
        store_path=node_dir / "store",
        validators_path=validators_path,
        log_path=node_dir / "lightpool.log",
        front_port=front_port,
        rpc_port=rpc_port,
        ws_port=ws_port,
        mempool_port=mempool_port,
        consensus_port=consensus_port,
    )


def start_node(spec: NodeSpec, *, verbose: bool = False) -> subprocess.Popen[bytes]:
    spec.store_path.mkdir(parents=True, exist_ok=True)
    spec.log_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        resolve_lightpool_binary(),
        "--wallet",
        str(spec.wallet_path),
        "--store",
        str(spec.store_path),
        "--validators",
        str(spec.validators_path),
        "--front-listen-addr",
        f"0.0.0.0:{spec.front_port}",
        "--rpc-listen-addr",
        f"0.0.0.0:{spec.rpc_port}",
        "--ws-listen-addr",
        f"0.0.0.0:{spec.ws_port}",
    ]
    if verbose:
        cmd.append("-v")

    log_file = spec.log_path.open("ab")
    print(f"+ {' '.join(cmd)} >> {spec.log_path}", flush=True)
    return subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid if hasattr(os, "setsid") else None,
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


def stop_processes(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is not None:
            continue
        try:
            if hasattr(os, "killpg"):
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                process.terminate()
        except ProcessLookupError:
            continue

    deadline = time.monotonic() + 15.0
    for process in processes:
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.2)
        if process.poll() is None:
            try:
                if hasattr(os, "killpg"):
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                else:
                    process.kill()
            except ProcessLookupError:
                pass
