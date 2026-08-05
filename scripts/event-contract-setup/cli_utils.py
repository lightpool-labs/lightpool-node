from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from config import CLI_BINARY, RPC_URL, WALLET_PATH

# event-contract-setup/ → lightpool-labs (monorepo root)
# Under lightpool-node/scripts/... parents[3]; under lightpool/crates/lightpool-cli/scripts/... parents[5]
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = next(
    (
        p
        for p in _HERE.parents
        if (p / "lightpool" / "target" / "release" / "lightpool-cli").is_file()
        or (p / "lightpool-node").is_dir() and (p / "lightpool").is_dir()
    ),
    _HERE.parents[3],
)
_MONOREPO_CLI = _REPO_ROOT / "lightpool" / "target" / "release" / "lightpool-cli"


def resolve_cli_binary() -> str:
    candidates = [
        CLI_BINARY,
        str(_MONOREPO_CLI),
        str(_HERE.parents[4] / "target" / "release" / "lightpool-cli"),
    ]
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    found = shutil.which("lightpool-cli")
    if found:
        return found

    raise FileNotFoundError(
        "lightpool-cli not found. Tried:\n"
        f"  - {CLI_BINARY}\n"
        f"  - {_MONOREPO_CLI}\n"
        "  - PATH\n"
        "Build with 'cargo build --release -p lightpool-cli' in lightpool/, "
        "or set LIGHTPOOL_CLI=/path/to/lightpool-cli."
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
