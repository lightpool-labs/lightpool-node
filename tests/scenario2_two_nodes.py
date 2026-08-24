#!/usr/bin/env python3
"""Scenario 2 - Two-node consensus + staking (weekly / sync/epoch changes).

Auto-asserting version of scripts/run_2nodes/run_2nodes.py:

  1. init a 2-node network (node0 validator, node1 pending-member)
  2. node0 up, burst past block 800
  3. node1 joins, syncs the first checkpoint at block 1000
  4. staking: create LPL, init-config, bond + register + allocate both nodes
  5. wait for the next epoch boundary: committee promotes both nodes
     (committee for epoch N is selected ~10 blocks before the boundary,
     so the promotion lands one epoch after staking at the latest)
  6. both nodes propose; committed tip and block hash match
  7. stop node1: with a 2-member committee the chain must halt (safety)
  8. restart node1: consensus resumes and both nodes commit the same tip

Pass criteria (exit code 0):
  - node1 store ready after the checkpoint at block 1000
  - after epoch 2 both committee members have stake and node1 proposes
  - committed_block_num / committed_block_hash match on both nodes
  - node0 does not commit while node1 is down (2-node committee safety)
  - after node1 restarts, the chain resumes and tips match again
  - neither node panicked

Run from the lightpool-node root:
  python3 tests/scenario2_two_nodes.py
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
DATA_DIR = TESTS_DIR / ".scenario2"

# The run_2nodes lib reads LIGHTPOOL_NETWORK_DATA_DIR at import time.
os.environ["LIGHTPOOL_NETWORK_DATA_DIR"] = str(DATA_DIR)

RUN_2NODES_DIR = TESTS_DIR.parent / "scripts" / "run_2nodes"
if str(RUN_2NODES_DIR) not in sys.path:
    sys.path.insert(0, str(RUN_2NODES_DIR))

from lib.config import (  # noqa: E402
    BURST_CLIENT_BIN,
    BURST_FRONT,
    EPOCH_LENGTH,
    LIGHTPOOL_BIN,
)
from lib.bin_utils import require_binary  # noqa: E402
from lib.network_init import init_network  # noqa: E402
from lib.node_utils import (  # noqa: E402
    ROLE_PENDING_MEMBER,
    ROLE_VALIDATOR,
    NodeSpec,
    boot_peer_url,
    build_node_spec,
    lightpool_argv,
    resolve_lightpool_binary,
    rpc_ready,
)
from lib.rpc_utils import (  # noqa: E402
    committed_block_num,
    get_sync_info,
    json_rpc,
    rpc_url_for_port,
    wait_for_committed_block,
)
from lib.staking_utils import run_staking_setup  # noqa: E402

PRE_JOIN_MIN_BLOCK = 800
FIRST_CHECKPOINT_BLOCK = EPOCH_LENGTH  # 1000
RESTART_GAP_BLOCKS = 30

BURST_ARGV = [
    "--address", BURST_FRONT,
    "--senders", "128",
    "--recipients", "128",
    "--tasks", "2",
    "--rate-per-task", "200",
    "--duration", "3600",
    "--transfer-amount", "2048",
]

# Proposer logs block creation at debug level; everything else stays at info.
NODE_RUST_LOG = "info,lightpool_consensus::proposer=debug"

failures: list[str] = []
children: list[subprocess.Popen] = []


def check(label: str, actual, expected) -> None:
    if actual == expected:
        print(f"OK: {label} = {actual}", flush=True)
    else:
        failures.append(f"{label}: expected {expected}, got {actual}")
        print(f"FAIL: {label}: expected {expected}, got {actual}", flush=True)


def check_true(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"OK: {label}", flush=True)
    else:
        failures.append(f"{label}: {detail}")
        print(f"FAIL: {label}: {detail}", flush=True)


def register(proc: subprocess.Popen) -> subprocess.Popen:
    children.append(proc)
    return proc


def stop_proc(proc: subprocess.Popen | None, label: str) -> None:
    if proc is None or proc.poll() is not None:
        return
    print(f"Stopping {label} (pid={proc.pid})...", flush=True)
    try:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    except OSError as error:
        print(f"Warning: could not stop {label}: {error}", flush=True)
    if proc in children:
        children.remove(proc)


def terminate_all() -> None:
    for proc in reversed(children):
        stop_proc(proc, f"pid={proc.pid}")


def kill_stray_nodes() -> None:
    marker = str(DATA_DIR)
    self_pid = os.getpid()
    for proc_dir in Path("/proc").iterdir():
        if not proc_dir.name.isdigit() or int(proc_dir.name) == self_pid:
            continue
        try:
            cmdline = (proc_dir / "cmdline").read_bytes().replace(b"\0", b" ").decode()
        except OSError:
            continue
        if "lightpool" in cmdline and marker in cmdline:
            pid = int(proc_dir.name)
            print(f"Killing stray node from previous run (pid={pid})", flush=True)
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError as error:
                print(f"Warning: could not kill stray pid={pid}: {error}", flush=True)


def start_node(spec: NodeSpec, reset_store: bool = False) -> subprocess.Popen:
    if reset_store and spec.store_path.is_dir():
        shutil.rmtree(spec.store_path)
    spec.store_path.mkdir(parents=True, exist_ok=True)

    binary = resolve_lightpool_binary()
    spec.log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fp = open(spec.log_path, "ab")
    env = dict(os.environ, RUST_LOG=NODE_RUST_LOG)
    print(
        f"Starting node{spec.index} role={spec.role} "
        f"(RPC http://127.0.0.1:{spec.rpc_port}, log {spec.log_path})",
        flush=True,
    )
    return register(
        subprocess.Popen(
            [binary, *lightpool_argv(spec)],
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            env=env,
        )
    )


def start_burst(label: str) -> subprocess.Popen:
    log_path = DATA_DIR / f"burst_{label}.log"
    log_fp = open(log_path, "ab")
    print(f"Starting burst ({label}), log {log_path}", flush=True)
    return register(
        subprocess.Popen(
            [BURST_CLIENT_BIN, *BURST_ARGV],
            stdout=log_fp,
            stderr=subprocess.STDOUT,
        )
    )


def ensure_alive(proc: subprocess.Popen, label: str) -> None:
    code = proc.poll()
    if code is not None:
        raise RuntimeError(f"{label} exited early with code {code}")


def perpetual_store_ready(spec: NodeSpec) -> bool:
    perpetual = spec.store_path / "perpetual"
    return perpetual.is_dir() and any(perpetual.iterdir())


def count_create_blocks(spec: NodeSpec) -> int:
    if not spec.log_path.is_file():
        return 0
    return spec.log_path.read_text(encoding="utf-8", errors="replace").count("create_block:")


def wait_two_member_committee(timeout_sec: float = 900.0) -> dict:
    """Poll until the running committee has 2 staked members.

    The committee for epoch N is selected ~10 blocks before the epoch boundary,
    so staking lands in epoch N+1 at the earliest; polling is deterministic
    while a fixed block target is not.
    """
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            committee = json_rpc(rpc_url_for_port(LEADER.rpc_port), "getCommitteeInfo")
        except RuntimeError:
            time.sleep(1.0)
            continue
        members = committee.get("members", [])
        stakes = [int(m["stake"]) for m in members]
        if len(members) == 2 and all(s > 0 for s in stakes):
            print(
                f"Two-member committee active at epoch {committee['epoch']}: stakes={stakes}",
                flush=True,
            )
            return committee
        print(
            f"Waiting for 2-member staked committee (epoch={committee.get('epoch')}, "
            f"members={len(members)}, stakes={stakes})...",
            flush=True,
        )
        time.sleep(2.0)
    raise TimeoutError("committee never reached 2 staked members")


def wait_node1_checkpoint_synced(timeout_sec: float = 600.0) -> int:
    """Wait for node1 to commit past the first checkpoint.

    Fails fast if node1's state root diverges from node0 (the known
    checkpoint-boot bug): with a diverged state node1 can never vote and the
    scenario cannot pass, so there is no point waiting for the timeout.
    """
    deadline = time.monotonic() + timeout_sec
    last = -1
    while time.monotonic() < deadline:
        if "root_mismatch" in (
            FOLLOWER.log_path.read_text(encoding="utf-8", errors="replace")
            if FOLLOWER.log_path.is_file()
            else ""
        ):
            raise RuntimeError(
                "node1 state root diverged from node0 right after the "
                "checkpoint boot (attest validate root_mismatch); known node "
                "bug, see tools/testing/lightpool-0.3.0-testing.md Scenario 2"
            )
        try:
            last = committed_block_num(FOLLOWER.rpc_port)
        except RuntimeError:
            time.sleep(1.0)
            continue
        if last >= FIRST_CHECKPOINT_BLOCK:
            print(f"node1 committed_block_num={last} (>= {FIRST_CHECKPOINT_BLOCK})", flush=True)
            return last
        print(
            f"Waiting for node1 committed_block_num >= {FIRST_CHECKPOINT_BLOCK} (now {last})...",
            flush=True,
        )
        time.sleep(1.0)
    raise TimeoutError(f"node1 never committed block {FIRST_CHECKPOINT_BLOCK} (last={last})")


def wait_node1_own_checkpoint(min_epoch: int = 2, timeout_sec: float = 180.0) -> int:
    """Poll until node1 has written its own checkpoint at epoch >= min_epoch.

    node1 keeps no snapshot from the boot checkpoint download; its first own
    checkpoint is written at the epoch-2 boundary (block 1999), which can lag
    the committee promotion observed at round 2000.
    """
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            epoch = get_sync_info(FOLLOWER.rpc_port).get("latest_checkpoint_epoch")
        except RuntimeError:
            epoch = None
        if epoch is not None and int(epoch) >= min_epoch:
            return int(epoch)
        time.sleep(2.0)
    raise TimeoutError(f"node1 checkpoint epoch never reached {min_epoch}")


def wait_node1_proposes(timeout_sec: float = 600.0) -> int:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        count = count_create_blocks(FOLLOWER)
        if count > 0:
            return count
        time.sleep(2.0)
    raise TimeoutError("node1 never proposed (no 'create_block:' in its log)")


def wait_matching_tips(timeout_sec: float = 300.0) -> tuple[int, str]:
    """Poll both nodes until they report the same block at the same height.

    Tips move in lockstep but RPC samples are not simultaneous, so collect
    height -> hash per node and compare once a height appears on both.
    """
    deadline = time.monotonic() + timeout_sec
    hashes0: dict[int, str] = {}
    hashes1: dict[int, str] = {}
    while time.monotonic() < deadline:
        try:
            info0 = get_sync_info(LEADER.rpc_port)
            info1 = get_sync_info(FOLLOWER.rpc_port)
        except RuntimeError:
            time.sleep(0.5)
            continue
        hashes0[int(info0["committed_block_num"])] = info0["committed_block_hash"]
        hashes1[int(info1["committed_block_num"])] = info1["committed_block_hash"]
        common = set(hashes0) & set(hashes1)
        if common:
            num = max(common)
            if hashes0[num] != hashes1[num]:
                raise AssertionError(
                    f"committed hash mismatch at block {num}: "
                    f"node0={hashes0[num]} node1={hashes1[num]}"
                )
            return num, hashes0[num]
        time.sleep(0.3)
    raise TimeoutError("nodes never reported the same committed_block_num in time")


LEADER: NodeSpec
FOLLOWER: NodeSpec


def main() -> int:
    global LEADER, FOLLOWER

    require_binary(LIGHTPOOL_BIN, "set LIGHTPOOL_BIN to a lightpool binary")
    require_binary(BURST_CLIENT_BIN, "set BURST_CLIENT_BIN to a burst_client binary")

    signal.signal(signal.SIGINT, lambda *_: sys.exit(130))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))

    node0 = node1 = None
    burst = None
    try:
        print("=== 1) init ===", flush=True)
        kill_stray_nodes()
        init_network(DATA_DIR)
        LEADER = build_node_spec(0, DATA_DIR, role=ROLE_VALIDATOR)
        FOLLOWER = build_node_spec(
            1, DATA_DIR, role=ROLE_PENDING_MEMBER, boot_peer=boot_peer_url(0)
        )

        print("=== 2) start node0 (validator) ===", flush=True)
        node0 = start_node(LEADER)
        if not rpc_ready(LEADER.rpc_port, timeout_sec=120.0):
            raise RuntimeError(f"node0 RPC not ready; see {LEADER.log_path}")

        print(f"=== 3) burst until node0 tip > {PRE_JOIN_MIN_BLOCK} ===", flush=True)
        burst = start_burst("pre_join")
        wait_for_committed_block(
            LEADER.rpc_port, PRE_JOIN_MIN_BLOCK + 1,
            timeout_sec=900.0, poll_sec=0.5, label="node0",
        )
        stop_proc(burst, "burst")
        burst = None
        ensure_alive(node0, "node0")

        print("=== 4) start node1 (pending-member) ===", flush=True)
        node1 = start_node(FOLLOWER, reset_store=True)

        print(f"=== 5) burst until tip >= {FIRST_CHECKPOINT_BLOCK} ===", flush=True)
        burst = start_burst("first_checkpoint")
        wait_for_committed_block(
            LEADER.rpc_port, FIRST_CHECKPOINT_BLOCK,
            timeout_sec=900.0, poll_sec=0.5, label="node0",
        )
        stop_proc(burst, "burst")
        burst = None

        print("Waiting for node1 first-checkpoint sync...", flush=True)
        if not rpc_ready(FOLLOWER.rpc_port, timeout_sec=600.0):
            raise RuntimeError(f"node1 RPC not ready; see {FOLLOWER.log_path}")
        wait_node1_checkpoint_synced(timeout_sec=600.0)
        ensure_alive(node0, "node0")
        ensure_alive(node1, "node1")

        sync1 = get_sync_info(FOLLOWER.rpc_port)
        check_true(
            "node1 committed past first checkpoint",
            int(sync1["committed_block_num"]) >= FIRST_CHECKPOINT_BLOCK,
            f"committed_block_num={sync1['committed_block_num']}",
        )
        check_true(
            "node1 perpetual store ready",
            perpetual_store_ready(FOLLOWER),
            f"{FOLLOWER.store_path / 'perpetual'} missing or empty",
        )

        print("=== 6) staking ===", flush=True)
        run_staking_setup(LEADER, FOLLOWER, DATA_DIR)

        print("=== 7) burst until both nodes are in the committee and propose ===", flush=True)
        burst = start_burst("dual_proposal")
        try:
            committee = wait_two_member_committee(timeout_sec=900.0)
        finally:
            stop_proc(burst, "burst")
            burst = None
        ensure_alive(node0, "node0")
        ensure_alive(node1, "node1")

        check_true(
            "committee epoch >= 2",
            int(committee["epoch"]) >= 2,
            f"epoch={committee['epoch']}",
        )
        check("committee member count", len(committee["members"]), 2)

        checkpoint_epoch = wait_node1_own_checkpoint(min_epoch=2)
        print(f"OK: node1 wrote own checkpoint epoch {checkpoint_epoch}", flush=True)

        node1_blocks = wait_node1_proposes(timeout_sec=600.0)
        print(f"OK: node1 proposed {node1_blocks} block(s)", flush=True)

        tip, block_hash = wait_matching_tips(timeout_sec=300.0)
        print(f"OK: both nodes committed block {tip} with hash {block_hash}", flush=True)

        print("=== 8) restart node1 mid-run ===", flush=True)
        stop_proc(node1, "node1")
        node1 = None
        tip_at_stop = committed_block_num(LEADER.rpc_port)
        print(f"node1 stopped at node0 tip={tip_at_stop}", flush=True)

        # With a 2-member committee and round-robin leadership the chain must
        # halt while one validator is down: votes for node0's blocks route to
        # the next leader (node1), so no QC can form. Assert safety (tip does
        # not move), then restart node1 and assert liveness resumes.
        time.sleep(45.0)
        tip_while_down = committed_block_num(LEADER.rpc_port)
        check_true(
            "chain halts while node1 is down (safety)",
            tip_while_down <= tip_at_stop + 2,
            f"tip_at_stop={tip_at_stop} tip_after_45s={tip_while_down}",
        )

        node1 = start_node(FOLLOWER)  # keep store: consensus catch-up path
        if not rpc_ready(FOLLOWER.rpc_port, timeout_sec=600.0):
            raise RuntimeError(f"node1 RPC not ready after restart; see {FOLLOWER.log_path}")
        wait_for_committed_block(
            LEADER.rpc_port, tip_while_down + RESTART_GAP_BLOCKS,
            timeout_sec=900.0, poll_sec=1.0, label="node0",
        )
        tip, block_hash = wait_matching_tips(timeout_sec=600.0)
        print(f"OK: after restart both nodes committed block {tip} with hash {block_hash}", flush=True)

        ensure_alive(node0, "node0")
        ensure_alive(node1, "node1")
        for spec in (LEADER, FOLLOWER):
            if spec.log_path.is_file() and "panicked at" in spec.log_path.read_text(
                encoding="utf-8", errors="replace"
            ):
                failures.append(f"node{spec.index} log contains a panic")
                print(f"FAIL: node{spec.index} log contains 'panicked at'", flush=True)
    except Exception as error:  # noqa: BLE001 - report and exit non-zero
        failures.append(str(error))
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
    finally:
        terminate_all()

    if failures:
        print(f"\nScenario 2 FAILED ({len(failures)} failure(s)):", flush=True)
        for failure in failures:
            print(f"  - {failure}", flush=True)
        print(f"Logs: {DATA_DIR}/node0/lightpool.log, {DATA_DIR}/node1/lightpool.log", flush=True)
        return 1

    print("\nScenario 2 PASSED", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
