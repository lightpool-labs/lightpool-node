from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from config import CLI_BINARY, RPC_URL, WALLET_PATH

_HERE = Path(__file__).resolve().parent
_NODE_BIN = _HERE.parents[2] / "bin" / "lightpool"
_REPO_ROOT = next(
    (
        p
        for p in _HERE.parents
        if (p / "lightpool" / "target" / "release" / "lightpool").is_file()
        or ((p / "lightpool-node").is_dir() and (p / "lightpool").is_dir())
    ),
    _HERE.parents[3],
)
_MONOREPO_BIN = _REPO_ROOT / "lightpool" / "target" / "release" / "lightpool"


def resolve_cli_binary() -> str:
    candidates = [
        CLI_BINARY,
        str(_NODE_BIN),
        str(_MONOREPO_BIN),
    ]
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    found = shutil.which("lightpool")
    if found:
        return found

    raise FileNotFoundError(
        "lightpool not found. Tried:\n"
        f"  - {CLI_BINARY}\n"
        f"  - {_NODE_BIN}\n"
        f"  - {_MONOREPO_BIN}\n"
        "  - PATH\n"
        "Build with 'cargo build --release' in lightpool-node/ "
        "(or 'cargo build --release -p lightpool' in lightpool/), "
        "or set LIGHTPOOL_BIN=/path/to/lightpool."
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
