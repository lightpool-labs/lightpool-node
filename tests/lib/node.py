from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = TESTS_DIR.parent

FRONT_PORT = int(os.environ.get("LIGHTPOOL_TEST_FRONT_PORT", "36000"))
MEMPOOL_PORT = int(os.environ.get("LIGHTPOOL_TEST_MEMPOOL_PORT", "36100"))
CONSENSUS_PORT = int(os.environ.get("LIGHTPOOL_TEST_CONSENSUS_PORT", "36200"))
RPC_PORT = int(os.environ.get("LIGHTPOOL_TEST_RPC_PORT", "36300"))
WS_PORT = int(os.environ.get("LIGHTPOOL_TEST_WS_PORT", "36400"))

RPC_URL = f"http://127.0.0.1:{RPC_PORT}"

LIGHTPOOL_BIN = os.environ.get("LIGHTPOOL_BIN", str(PROJECT_ROOT / "bin" / "lightpool"))


def resolve_lightpool_binary() -> str:
    release_binary = Path(LIGHTPOOL_BIN)
    if release_binary.is_file():
        return str(release_binary)
    found = shutil.which("lightpool")
    if found:
        return found
    raise FileNotFoundError(
        f"lightpool not found at {LIGHTPOOL_BIN}. "
        "Run 'cargo build --release' in lightpool-node or set LIGHTPOOL_BIN."
    )


def rpc_ready(timeout_sec: float = 120.0) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", RPC_PORT), timeout=2):
                return True
        except OSError:
            time.sleep(0.5)
    return False


@dataclass
class SingleNode:
    proc: subprocess.Popen
    data_dir: Path
    wallet_path: Path
    store_path: Path
    log_path: Path

    def owner_address(self) -> str:
        wallet = json.loads(self.wallet_path.read_text(encoding="utf-8"))
        address = wallet.get("address", "")
        return address if address.startswith("0x") else f"0x{address}"

    def is_alive(self) -> bool:
        return self.proc.poll() is None

    def log_text(self) -> str:
        return self.log_path.read_text(encoding="utf-8", errors="replace") if self.log_path.is_file() else ""


def prepare_node(data_dir: Path, binary: str) -> SingleNode:
    if data_dir.is_dir():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    wallet_path = data_dir / "wallet.json"
    store_path = data_dir / "store"
    validator_path = data_dir / "validator.json"
    log_path = data_dir / "lightpool.log"

    subprocess.run(
        [binary, "create-wallet", "--force", "--wallet-path", str(wallet_path)],
        check=True,
        capture_output=True,
    )
    wallet = json.loads(wallet_path.read_text(encoding="utf-8"))
    consensus_pubkey = wallet.get("consensus_pubkey")
    if not consensus_pubkey:
        raise RuntimeError(f"wallet {wallet_path} is missing consensus_pubkey")

    validator_path.write_text(
        json.dumps(
            {
                "consensus_pubkey": consensus_pubkey,
                "mempool_address": f"127.0.0.1:{MEMPOOL_PORT}",
                "consensus_address": f"127.0.0.1:{CONSENSUS_PORT}",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return SingleNode(
        proc=None,  # type: ignore[arg-type]
        data_dir=data_dir,
        wallet_path=wallet_path,
        store_path=store_path,
        log_path=log_path,
    )


def start_node(node: SingleNode, binary: str) -> SingleNode:
    node.store_path.mkdir(parents=True, exist_ok=True)
    log_fd = open(node.log_path, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [
            binary,
            "node",
            "--wallet", str(node.wallet_path),
            "--store", str(node.store_path),
            "--validator", str(node.data_dir / "validator.json"),
            "--role", "validator",
            "--front-listen-addr", f"0.0.0.0:{FRONT_PORT}",
            "--rpc-listen-addr", f"0.0.0.0:{RPC_PORT}",
            "--ws-listen-addr", f"0.0.0.0:{WS_PORT}",
        ],
        stdout=log_fd,
        stderr=subprocess.STDOUT,
    )
    print(f"Started node (pid {proc.pid}, RPC {RPC_URL}, log {node.log_path})", flush=True)
    return SingleNode(proc=proc, data_dir=node.data_dir, wallet_path=node.wallet_path,
                      store_path=node.store_path, log_path=node.log_path)


def stop_node(node: SingleNode) -> None:
    if node.proc is None or node.proc.poll() is not None:
        return
    try:
        node.proc.terminate()
        try:
            node.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            node.proc.kill()
            node.proc.wait(timeout=10)
        print("Node stopped", flush=True)
    except OSError as error:
        print(f"Warning: could not stop node (pid {node.proc.pid}): {error}", flush=True)
