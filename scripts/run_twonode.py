#!/usr/bin/env python3
"""Orchestrate the two-node local network flow end-to-end.

Flow:
  1. init
  2. start node0 (Validator)
  3. burst until tip > 800
  4. start node1 immediately (while tip is still before the first checkpoint)
  5. burst again so tip passes 999/1000 and node1 syncs the first checkpoint,
     then stop burst
  6. staking (between 1000 and 2000)
  7. burst again until tip passes 3000 (node1 should start proposing after 2000)

Press Ctrl+C to stop nodes and exit.
"""
from __future__ import annotations

import atexit
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from lib.bin_utils import require_binary
from lib.config import (
    BURST_CLIENT_BIN,
    BURST_FRONT,
    BUILD_BURST_HINT,
    BUILD_LIGHTPOOL_HINT,
    DATA_DIR,
    EPOCH_LENGTH,
    LIGHTPOOL_BIN,
    LIGHTPOOL_CLI,
)
from lib.network_init import init_network
from lib.node_utils import (
    ROLE_PENDING_MEMBER,
    ROLE_VALIDATOR,
    boot_peer_url,
    build_node_spec,
    lightpool_argv,
    resolve_lightpool_binary,
    rpc_ready,
)
from lib.rpc_utils import committed_block_num, wait_for_committed_block
from lib.staking_utils import run_staking_setup

# Start node1 as soon as tip crosses this, so it can sync checkpoint epoch 1
# at block 1000 (not wait for epoch 2 at 2000).
PRE_JOIN_MIN_BLOCK = 800
# First checkpoint is produced when committed_block_num passes 999.
FIRST_CHECKPOINT_BLOCK = EPOCH_LENGTH  # 1000
FINAL_DUAL_PROPOSAL_BLOCK = 3000

BURST_SENDERS = "128"
BURST_RECIPIENTS = "128"
BURST_TASKS = "2"
BURST_RATE_PER_TASK = "200"
BURST_DURATION_SEC = "3600"
BURST_TRANSFER_AMOUNT = "2048"

_children: list[subprocess.Popen[str]] = []


def _register(proc: subprocess.Popen[str]) -> subprocess.Popen[str]:
    _children.append(proc)
    return proc


def _terminate_all() -> None:
    for proc in reversed(_children):
        if proc.poll() is not None:
            continue
        try:
            proc.terminate()
        except OSError:
            pass
    deadline = time.monotonic() + 10.0
    for proc in reversed(_children):
        if proc.poll() is not None:
            continue
        remaining = max(0.1, deadline - time.monotonic())
        try:
            proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass


def _start_node(
    index: int,
    *,
    role: str,
    boot_peer: str | None = None,
    reset_store: bool = False,
) -> subprocess.Popen[str]:
    spec = build_node_spec(index, DATA_DIR, role=role, boot_peer=boot_peer)
    if not spec.wallet_path.is_file() or not spec.validator_path.is_file():
        raise SystemExit("Run init first (missing wallet/validator)")

    if reset_store and spec.store_path.is_dir():
        print(f"Removing stale node{index} store: {spec.store_path}", flush=True)
        shutil.rmtree(spec.store_path)
    spec.store_path.mkdir(parents=True, exist_ok=True)

    binary = resolve_lightpool_binary()
    argv = [binary, *lightpool_argv(spec)]
    spec.log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fp = open(spec.log_path, "ab")
    print(
        f"Starting node{index} role={role} "
        f"(RPC http://127.0.0.1:{spec.rpc_port}, log {spec.log_path})",
        flush=True,
    )
    proc = subprocess.Popen(
        argv,
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return _register(proc)


def _burst_argv() -> list[str]:
    return [
        BURST_CLIENT_BIN,
        "--address",
        BURST_FRONT,
        "--senders",
        BURST_SENDERS,
        "--recipients",
        BURST_RECIPIENTS,
        "--tasks",
        BURST_TASKS,
        "--rate-per-task",
        BURST_RATE_PER_TASK,
        "--duration",
        BURST_DURATION_SEC,
        "--transfer-amount",
        BURST_TRANSFER_AMOUNT,
    ]


def _start_burst(*, label: str) -> subprocess.Popen[str]:
    log_path = DATA_DIR / f"burst_{label}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fp = open(log_path, "ab")
    print(f"Starting burst ({label}), log {log_path}", flush=True)
    proc = subprocess.Popen(
        _burst_argv(),
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return _register(proc)


def _stop_proc(proc: subprocess.Popen[str] | None, *, label: str) -> None:
    if proc is None or proc.poll() is not None:
        return
    print(f"Stopping {label} (pid={proc.pid})...", flush=True)
    try:
        proc.terminate()
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    except OSError:
        pass
    if proc in _children:
        _children.remove(proc)


def _ensure_alive(proc: subprocess.Popen[str], *, label: str) -> None:
    code = proc.poll()
    if code is not None:
        raise RuntimeError(f"{label} exited early with code {code}")


def main() -> None:
    require_binary(LIGHTPOOL_BIN, BUILD_LIGHTPOOL_HINT)
    require_binary(LIGHTPOOL_CLI, BUILD_LIGHTPOOL_HINT)
    require_binary(BURST_CLIENT_BIN, BUILD_BURST_HINT)

    atexit.register(_terminate_all)
    signal.signal(signal.SIGINT, lambda *_: sys.exit(130))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))

    print("=== 1) init ===", flush=True)
    init_network(DATA_DIR)

    leader = build_node_spec(0, DATA_DIR, role=ROLE_VALIDATOR)
    follower = build_node_spec(
        1,
        DATA_DIR,
        role=ROLE_PENDING_MEMBER,
        boot_peer=boot_peer_url(0),
    )

    print("=== 2) run node0 ===", flush=True)
    node0 = _start_node(0, role=ROLE_VALIDATOR)
    if not rpc_ready(leader.rpc_port, timeout_sec=120.0):
        raise SystemExit(f"node0 RPC not ready on port {leader.rpc_port}")
    print(f"node0 RPC ready on http://127.0.0.1:{leader.rpc_port}", flush=True)

    print(
        f"=== 3) burst until tip > {PRE_JOIN_MIN_BLOCK}, "
        f"then start node1 immediately ===",
        flush=True,
    )
    burst = _start_burst(label="pre_join")
    tip = wait_for_committed_block(
        leader.rpc_port,
        PRE_JOIN_MIN_BLOCK + 1,
        timeout_sec=900.0,
        poll_sec=0.2,
        label="node0",
    )
    print(f"Pre-join tip={tip}; pausing burst and starting node1 now", flush=True)
    _stop_proc(burst, label="burst")
    burst = None
    _ensure_alive(node0, label="node0")

    print("=== 4) run node1 ===", flush=True)
    node1 = _start_node(
        1,
        role=ROLE_PENDING_MEMBER,
        boot_peer=boot_peer_url(0),
        reset_store=True,
    )
    tip = committed_block_num(leader.rpc_port)
    if tip >= FIRST_CHECKPOINT_BLOCK:
        print(
            f"WARNING: node0 tip={tip} already past first checkpoint "
            f"({FIRST_CHECKPOINT_BLOCK}); node1 may wait for epoch-2 checkpoint",
            flush=True,
        )

    print(
        f"=== 5) burst again until tip >= {FIRST_CHECKPOINT_BLOCK} "
        f"(node1 syncs first checkpoint), then stop ===",
        flush=True,
    )
    burst = _start_burst(label="first_checkpoint")
    wait_for_committed_block(
        leader.rpc_port,
        FIRST_CHECKPOINT_BLOCK,
        timeout_sec=600.0,
        poll_sec=0.5,
        label="node0",
    )
    _stop_proc(burst, label="burst")
    burst = None

    print("Waiting for node1 RPC / first-checkpoint sync...", flush=True)
    if not rpc_ready(follower.rpc_port, timeout_sec=600.0):
        raise SystemExit(f"node1 RPC not ready on port {follower.rpc_port}")
    wait_for_committed_block(
        follower.rpc_port,
        FIRST_CHECKPOINT_BLOCK,
        timeout_sec=600.0,
        poll_sec=1.0,
        label="node1",
    )
    _ensure_alive(node0, label="node0")
    _ensure_alive(node1, label="node1")

    print(
        "=== 6) staking (between first and second checkpoint) ===",
        flush=True,
    )
    run_staking_setup(leader, follower, DATA_DIR)
    print("Staking setup done.", flush=True)

    print(
        f"=== 7) burst until tip >= {FINAL_DUAL_PROPOSAL_BLOCK} "
        f"(node1 should start proposing) ===",
        flush=True,
    )
    burst = _start_burst(label="dual_proposal")
    wait_for_committed_block(
        leader.rpc_port,
        FINAL_DUAL_PROPOSAL_BLOCK,
        timeout_sec=1200.0,
        poll_sec=1.0,
        label="node0",
    )
    try:
        tip1 = committed_block_num(follower.rpc_port)
        print(f"node1 tip={tip1}", flush=True)
    except RuntimeError as error:
        print(f"Could not read node1 tip: {error}", flush=True)

    _stop_proc(burst, label="burst")
    print(
        f"Reached block {FINAL_DUAL_PROPOSAL_BLOCK}. "
        "Both nodes should be proposing. "
        "Nodes keep running; press Ctrl+C to stop.",
        flush=True,
    )
    while True:
        _ensure_alive(node0, label="node0")
        _ensure_alive(node1, label="node1")
        time.sleep(5.0)


if __name__ == "__main__":
    main()
