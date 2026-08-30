#!/usr/bin/env python3
"""Scenario 3 - Four-node committee join + one-node restart.

  1. init a 4-node network (node0 validator, node1–3 pending-member)
  2. node0 up, burst past block 800
  3. node1–3 join and sync the first checkpoint at block 1000
  4. staking: create LPL, init-config, bond + register + allocate all four
  5. wait until the committee has 4 staked members
  6. all four tips / hashes match
  7. stop node3: with a 4-member committee (HotStuff quorum 3) the chain
     must keep advancing
  8. restart node3: catch up; all four tips match again

Pass criteria (exit code 0):
  - joiners store-ready after checkpoint 1000
  - committee has 4 staked members
  - tips match across all nodes before restart
  - tip advances while node3 is down (liveness with n=4, f=1)
  - after restart all four tips / hashes match
  - no node panicked

Run from the lightpool-node root:
  python3 tests/scenario3_four_nodes.py
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
DATA_DIR = TESTS_DIR / ".scenario3"

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
from lib.staking_utils import (  # noqa: E402
    allocate_stake,
    bond_lpl,
    create_lpl_token,
    init_staking_config,
    load_staking_state,
    register_validator,
    save_staking_state,
    transfer_lpl,
)
from lib.wallet_utils import create_wallet, wallet_identity  # noqa: E402

NODE_COUNT = 4
PRE_JOIN_MIN_BLOCK = 800
FIRST_CHECKPOINT_BLOCK = EPOCH_LENGTH  # 1000
RESTART_GAP_BLOCKS = 5
# Consensus timeout_delay is 6s; after killing one validator tip may only move via TC.
# Poll until tip advances instead of a short fixed sleep.
LIVENESS_TIMEOUT_SEC = 120.0

# Equal bonds so all four enter committee selection with the same stake weight.
VALIDATOR_BOND = "10000"
JOINER_FUNDING = "11000"

BURST_ARGV = [
    "--address", BURST_FRONT,
    "--senders", "128",
    "--tasks", "2",
    "--rate-per-task", "200",
    "--duration", "3600",
    "--transfer-amount", "2048",
]

NODE_RUST_LOG = "info,lightpool_consensus::proposer=debug"

failures: list[str] = []
children: list[subprocess.Popen] = []
SPECS: list[NodeSpec] = []


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


def init_four_network(data_dir: Path) -> list[NodeSpec]:
    if data_dir.is_dir():
        print(f"Removing old data dir: {data_dir}", flush=True)
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    specs: list[NodeSpec] = [
        build_node_spec(0, data_dir, role=ROLE_VALIDATOR),
    ]
    for index in range(1, NODE_COUNT):
        specs.append(
            build_node_spec(
                index,
                data_dir,
                role=ROLE_PENDING_MEMBER,
                boot_peer=boot_peer_url(0),
            )
        )

    for spec in specs:
        create_wallet(spec.wallet_path, force=True)
        _, consensus_pubkey = wallet_identity(spec.wallet_path)
        payload = {
            "consensus_pubkey": consensus_pubkey,
            "mempool_address": f"127.0.0.1:{spec.mempool_port}",
            "consensus_address": f"127.0.0.1:{spec.consensus_port}",
        }
        spec.validator_path.parent.mkdir(parents=True, exist_ok=True)
        spec.validator_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {spec.validator_path}", flush=True)

    print(f"Data dir: {data_dir}", flush=True)
    return specs


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


def run_staking_setup_four(leader: NodeSpec, joiners: list[NodeSpec], data_dir: Path) -> None:
    state = load_staking_state(data_dir)
    if state.get("all_bonds_done"):
        print("Staking setup already completed; skipping.", flush=True)
        return

    lpl_token = state.get("lpl_token")
    if not lpl_token:
        lpl_token = create_lpl_token(leader)
        save_staking_state(data_dir, lpl_token=lpl_token)
    if not state.get("init_config_done"):
        init_staking_config(leader, lpl_token)
        save_staking_state(data_dir, init_config_done=True)

    print(f"Bonding node0 with {VALIDATOR_BOND} LPL...", flush=True)
    bond_lpl(leader, leader, lpl_token, VALIDATOR_BOND)
    register_validator(leader, leader)
    allocate_stake(leader, leader, VALIDATOR_BOND)

    for joiner in joiners:
        owner, _ = wallet_identity(joiner.wallet_path)
        print(
            f"Funding node{joiner.index} with {JOINER_FUNDING} LPL, then bond {VALIDATOR_BOND}...",
            flush=True,
        )
        transfer_lpl(leader, leader, lpl_token, owner, JOINER_FUNDING)
        bond_lpl(leader, joiner, lpl_token, VALIDATOR_BOND)
        register_validator(leader, joiner)
        allocate_stake(leader, joiner, VALIDATOR_BOND)

    save_staking_state(data_dir, all_bonds_done=True)


def wait_n_member_committee(n: int, timeout_sec: float = 900.0) -> dict:
    deadline = time.monotonic() + timeout_sec
    leader = SPECS[0]
    while time.monotonic() < deadline:
        try:
            committee = json_rpc(rpc_url_for_port(leader.rpc_port), "getCommitteeInfo")
        except RuntimeError:
            time.sleep(1.0)
            continue
        members = committee.get("members", [])
        stakes = [int(m["stake"]) for m in members]
        if len(members) == n and all(s > 0 for s in stakes):
            print(
                f"{n}-member committee active at epoch {committee['epoch']}: stakes={stakes}",
                flush=True,
            )
            return committee
        print(
            f"Waiting for {n}-member staked committee (epoch={committee.get('epoch')}, "
            f"members={len(members)}, stakes={stakes})...",
            flush=True,
        )
        time.sleep(2.0)
    raise TimeoutError(f"committee never reached {n} staked members")


def wait_joiner_checkpoint_synced(spec: NodeSpec, timeout_sec: float = 600.0) -> int:
    deadline = time.monotonic() + timeout_sec
    last = -1
    while time.monotonic() < deadline:
        log_text = (
            spec.log_path.read_text(encoding="utf-8", errors="replace")
            if spec.log_path.is_file()
            else ""
        )
        if "root_mismatch" in log_text:
            raise RuntimeError(
                f"node{spec.index} state root diverged from node0 "
                "(attest validate root_mismatch)"
            )
        try:
            last = committed_block_num(spec.rpc_port)
        except RuntimeError:
            time.sleep(1.0)
            continue
        if last >= FIRST_CHECKPOINT_BLOCK:
            print(
                f"node{spec.index} committed_block_num={last} (>= {FIRST_CHECKPOINT_BLOCK})",
                flush=True,
            )
            return last
        print(
            f"Waiting for node{spec.index} committed_block_num >= "
            f"{FIRST_CHECKPOINT_BLOCK} (now {last})...",
            flush=True,
        )
        time.sleep(1.0)
    raise TimeoutError(
        f"node{spec.index} never committed block {FIRST_CHECKPOINT_BLOCK} (last={last})"
    )


def wait_matching_tips(specs: list[NodeSpec], timeout_sec: float = 300.0) -> tuple[int, str]:
    deadline = time.monotonic() + timeout_sec
    hashes: dict[int, dict[int, str]] = {spec.index: {} for spec in specs}
    while time.monotonic() < deadline:
        try:
            infos = {spec.index: get_sync_info(spec.rpc_port) for spec in specs}
        except RuntimeError:
            time.sleep(0.5)
            continue
        for index, info in infos.items():
            hashes[index][int(info["committed_block_num"])] = info["committed_block_hash"]
        common = set.intersection(*(set(h) for h in hashes.values()))
        if common:
            num = max(common)
            values = {index: hashes[index][num] for index in hashes}
            first = next(iter(values.values()))
            if any(value != first for value in values.values()):
                raise AssertionError(f"committed hash mismatch at block {num}: {values}")
            return num, first
        time.sleep(0.3)
    raise TimeoutError("nodes never reported the same committed_block_num in time")


def main() -> int:
    global SPECS

    require_binary(LIGHTPOOL_BIN, "set LIGHTPOOL_BIN to a lightpool binary")
    require_binary(BURST_CLIENT_BIN, "set BURST_CLIENT_BIN to a burst_transfer binary")

    signal.signal(signal.SIGINT, lambda *_: sys.exit(130))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))

    procs: dict[int, subprocess.Popen | None] = {i: None for i in range(NODE_COUNT)}
    burst: subprocess.Popen | None = None
    try:
        print("=== 1) init (4 nodes) ===", flush=True)
        kill_stray_nodes()
        SPECS = init_four_network(DATA_DIR)
        leader = SPECS[0]
        joiners = SPECS[1:]

        print("=== 2) start node0 (validator) ===", flush=True)
        procs[0] = start_node(leader)
        if not rpc_ready(leader.rpc_port, timeout_sec=120.0):
            raise RuntimeError(f"node0 RPC not ready; see {leader.log_path}")

        print(f"=== 3) burst until node0 tip > {PRE_JOIN_MIN_BLOCK} ===", flush=True)
        burst = start_burst("pre_join")
        wait_for_committed_block(
            leader.rpc_port,
            PRE_JOIN_MIN_BLOCK + 1,
            timeout_sec=900.0,
            poll_sec=0.5,
            label="node0",
        )
        stop_proc(burst, "burst")
        burst = None
        ensure_alive(procs[0], "node0")

        print("=== 4) start node1–3 (pending-member) ===", flush=True)
        for joiner in joiners:
            procs[joiner.index] = start_node(joiner, reset_store=True)

        print(f"=== 5) burst until tip >= {FIRST_CHECKPOINT_BLOCK} ===", flush=True)
        burst = start_burst("first_checkpoint")
        wait_for_committed_block(
            leader.rpc_port,
            FIRST_CHECKPOINT_BLOCK,
            timeout_sec=900.0,
            poll_sec=0.5,
            label="node0",
        )
        stop_proc(burst, "burst")
        burst = None

        print("Waiting for joiners first-checkpoint sync...", flush=True)
        for joiner in joiners:
            if not rpc_ready(joiner.rpc_port, timeout_sec=600.0):
                raise RuntimeError(f"node{joiner.index} RPC not ready; see {joiner.log_path}")
            wait_joiner_checkpoint_synced(joiner, timeout_sec=600.0)
            check_true(
                f"node{joiner.index} perpetual store ready",
                perpetual_store_ready(joiner),
                f"{joiner.store_path / 'perpetual'} missing or empty",
            )
        for index, proc in procs.items():
            ensure_alive(proc, f"node{index}")

        print("=== 6) staking (all four) ===", flush=True)
        run_staking_setup_four(leader, joiners, DATA_DIR)

        print("=== 7) burst until 4-member committee ===", flush=True)
        burst = start_burst("four_member_committee")
        try:
            committee = wait_n_member_committee(NODE_COUNT, timeout_sec=900.0)
        finally:
            stop_proc(burst, "burst")
            burst = None

        check_true(
            "committee epoch >= 2",
            int(committee["epoch"]) >= 2,
            f"epoch={committee['epoch']}",
        )
        check("committee member count", len(committee["members"]), NODE_COUNT)

        tip, block_hash = wait_matching_tips(SPECS, timeout_sec=600.0)
        print(f"OK: all nodes committed block {tip} with hash {block_hash}", flush=True)

        restart_spec = SPECS[NODE_COUNT - 1]
        print(f"=== 8) restart node{restart_spec.index} mid-run ===", flush=True)
        stop_proc(procs[restart_spec.index], f"node{restart_spec.index}")
        procs[restart_spec.index] = None
        tip_at_stop = committed_block_num(leader.rpc_port)
        print(
            f"node{restart_spec.index} stopped at node0 tip={tip_at_stop}",
            flush=True,
        )

        # n=4, f=1 → quorum 3: chain must keep moving while one validator is down.
        # Allow multiple consensus timeouts (6s each) before declaring failure.
        tip_while_down = wait_for_committed_block(
            leader.rpc_port,
            tip_at_stop + 1,
            timeout_sec=LIVENESS_TIMEOUT_SEC,
            poll_sec=1.0,
            label="node0",
        )
        check_true(
            f"chain advances while node{restart_spec.index} is down (liveness)",
            tip_while_down >= tip_at_stop + 1,
            f"tip_at_stop={tip_at_stop} tip_while_down={tip_while_down}",
        )

        procs[restart_spec.index] = start_node(restart_spec)
        if not rpc_ready(restart_spec.rpc_port, timeout_sec=600.0):
            raise RuntimeError(
                f"node{restart_spec.index} RPC not ready after restart; "
                f"see {restart_spec.log_path}"
            )
        wait_for_committed_block(
            leader.rpc_port,
            tip_while_down + RESTART_GAP_BLOCKS,
            timeout_sec=900.0,
            poll_sec=1.0,
            label="node0",
        )
        tip, block_hash = wait_matching_tips(SPECS, timeout_sec=600.0)
        print(
            f"OK: after restart all nodes committed block {tip} with hash {block_hash}",
            flush=True,
        )

        for index, proc in procs.items():
            ensure_alive(proc, f"node{index}")
        for spec in SPECS:
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
        print(f"\nScenario 3 FAILED ({len(failures)} failure(s)):", flush=True)
        for failure in failures:
            print(f"  - {failure}", flush=True)
        logs = ", ".join(str(DATA_DIR / f"node{i}" / "lightpool.log") for i in range(NODE_COUNT))
        print(f"Logs: {logs}", flush=True)
        return 1

    print("\nScenario 3 PASSED", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
