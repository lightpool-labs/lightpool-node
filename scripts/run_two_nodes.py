#!/usr/bin/env python3
"""Start a local two-validator LightPool network."""

from __future__ import annotations

import argparse
import json
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from config import DATA_DIR, NODE_COUNT, VALIDATOR_STAKE
from node_utils import (
    build_binaries,
    build_node_spec,
    start_node,
    stop_processes,
    wait_for_nodes,
)
from wallet_utils import create_wallet, wallet_identity


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a local LightPool network with two validator nodes.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help=f"Directory for wallets, stores, and validators.json (default: {DATA_DIR})",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Build lightpool-cli and install bin/lightpool before starting nodes.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove the data directory before starting.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Pass -v to lightpool for debug logging.",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Start nodes and exit without waiting for RPC readiness.",
    )
    return parser.parse_args()


def write_validators_json(data_dir: Path, specs: list) -> None:
    validators = []
    for spec in specs:
        owner, consensus_pubkey = wallet_identity(spec.wallet_path)
        validators.append(
            {
                "owner": owner,
                "consensus_pubkey": consensus_pubkey,
                "mempool_address": f"127.0.0.1:{spec.mempool_port}",
                "consensus_address": f"127.0.0.1:{spec.consensus_port}",
                "stake": VALIDATOR_STAKE,
            }
        )

    validators_path = data_dir / "validators.json"
    validators_path.write_text(
        json.dumps({"validators": validators}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote validator registry to {validators_path}", flush=True)


def prepare_wallets(specs: list) -> None:
    for spec in specs:
        create_wallet(spec.wallet_path, force=True)


def print_summary(specs: list, data_dir: Path) -> None:
    print("\nLocal network is running.", flush=True)
    print(f"Data directory: {data_dir}", flush=True)
    print(f"Validators: {data_dir / 'validators.json'}", flush=True)
    for spec in specs:
        print(
            f"node{spec.index}: "
            f"front=127.0.0.1:{spec.front_port} "
            f"rpc=http://127.0.0.1:{spec.rpc_port} "
            f"ws=ws://127.0.0.1:{spec.ws_port} "
            f"mempool=127.0.0.1:{spec.mempool_port} "
            f"consensus=127.0.0.1:{spec.consensus_port} "
            f"log={spec.log_path}",
            flush=True,
        )
    print(
        "\nNotes:\n"
        "- Both nodes share one bootstrap committee (50/50 stake split).\n"
        "- Node0 starts first; node1 joins the same network via P2P sync.\n"
        "- Front address is derived as mempool port minus 100 for each validator.\n"
        "- Use RPC endpoints above for CLI calls, e.g. LIGHTPOOL_RPC_URL=http://127.0.0.1:26300.\n"
        "- Press Ctrl+C to stop all nodes.",
        flush=True,
    )


def main() -> int:
    args = parse_args()
    data_dir = args.data_dir.resolve()

    if args.clean and data_dir.exists():
        print(f"Removing {data_dir}", flush=True)
        shutil.rmtree(data_dir)

    data_dir.mkdir(parents=True, exist_ok=True)

    if args.build:
        build_binaries()

    validators_path = data_dir / "validators.json"
    specs = [build_node_spec(index, data_dir, validators_path) for index in range(NODE_COUNT)]

    prepare_wallets(specs)
    write_validators_json(data_dir, specs)

    processes = []
    interrupted = False

    def handle_signal(signum, _frame) -> None:
        nonlocal interrupted
        interrupted = True
        print(f"\nReceived signal {signum}, stopping nodes...", flush=True)
        stop_processes(processes)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        for index, spec in enumerate(specs):
            processes.append(start_node(spec, verbose=args.verbose))
            if index == 0 and len(specs) > 1 and not args.no_wait:
                print("Waiting for node0 before starting remaining validators...", flush=True)
                if not wait_for_nodes([spec]):
                    stop_processes(processes)
                    return 1

        if args.no_wait:
            print_summary(specs, data_dir)
            return 0

        if not wait_for_nodes(specs):
            stop_processes(processes)
            return 1

        print_summary(specs, data_dir)

        while not interrupted:
            for process in processes:
                code = process.poll()
                if code is not None:
                    print(
                        f"A node exited unexpectedly with code {code}. "
                        "Stopping the remaining nodes.",
                        file=sys.stderr,
                    )
                    stop_processes(processes)
                    return code or 1
            signal.pause()
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        stop_processes(processes)
        return 1
    except subprocess.CalledProcessError as error:
        print(f"Command failed with exit code {error.returncode}", file=sys.stderr)
        stop_processes(processes)
        return error.returncode or 1
    finally:
        stop_processes(processes)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
