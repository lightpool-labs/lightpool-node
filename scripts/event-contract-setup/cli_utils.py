from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Iterable

from config import CLI_BINARY, RPC_URL, WALLET_PATH


def resolve_cli_binary() -> str:
    if os.path.isfile(CLI_BINARY):
        return CLI_BINARY

    found = shutil.which("lightpool-cli")
    if found:
        return found

    raise FileNotFoundError(
        "lightpool-cli not found. Build it with "
        "'cargo build --release -p lightpool-cli' or set LIGHTPOOL_CLI."
    )


def base_args() -> list[str]:
    args = [resolve_cli_binary(), "--rpc-url", RPC_URL]
    if WALLET_PATH:
        args.extend(["--wallet-path", WALLET_PATH])
    return args


def run_cli(subcommand: Iterable[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = base_args() + list(subcommand)
    print(f"+ {' '.join(cmd)}", flush=True)
    return subprocess.run(
        cmd,
        check=check,
        text=True,
    )


def main_runner(description: str, build_args) -> int:
    try:
        run_cli(build_args())
        return 0
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(f"command failed with exit code {error.returncode}", file=sys.stderr)
        return error.returncode or 1
