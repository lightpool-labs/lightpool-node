from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from lib.config import LIGHTPOOL_CLI

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
ADDRESS_PATTERN = re.compile(r"(0x[0-9a-fA-F]{40})")
PUBLIC_KEY_PATTERN = re.compile(r"Public Key:\s*(.+)", re.IGNORECASE)


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


def normalize_owner_address(address: str) -> str:
    address = address.strip()
    if not address.startswith("0x"):
        address = f"0x{address}"
    if not ADDRESS_PATTERN.fullmatch(address):
        raise ValueError(f"Invalid wallet address: {address}")
    return address


def parse_cli_address_output(output: str) -> tuple[str | None, str | None]:
    address = None
    public_key = None
    for line in output.splitlines():
        stripped = strip_ansi(line).strip()
        if match := PUBLIC_KEY_PATTERN.match(stripped):
            public_key = match.group(1).strip()
            continue
        if match := ADDRESS_PATTERN.search(stripped):
            address = match.group(1)
    return address, public_key


def cli_binary_candidates() -> list[str]:
    candidates: list[str] = []
    release_binary = Path(LIGHTPOOL_CLI)
    if release_binary.is_file():
        candidates.append(str(release_binary))

    debug_binary = release_binary.parent.parent / "debug" / release_binary.name
    if debug_binary.is_file():
        candidates.append(str(debug_binary))

    found = shutil.which("lightpool-cli")
    if found and found not in candidates:
        candidates.append(found)

    return candidates


def resolve_cli_binary() -> str:
    candidates = cli_binary_candidates()
    if candidates:
        return candidates[0]
    raise FileNotFoundError(
        "lightpool-cli not found. Run 'cargo build --release' in lightpool-node "
        "or set LIGHTPOOL_CLI."
    )


def create_wallet(wallet_path: Path, *, force: bool = True) -> None:
    wallet_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [resolve_cli_binary(), "create-wallet"]
    if force:
        cmd.append("--force")
    cmd.extend(["--wallet-path", str(wallet_path)])
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)


def consensus_pubkey_from_cli(wallet_path: Path) -> str | None:
    for binary in cli_binary_candidates():
        try:
            output = subprocess.check_output(
                [binary, "address", "--wallet-path", str(wallet_path)],
                text=True,
                stderr=subprocess.STDOUT,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        _, public_key = parse_cli_address_output(output)
        if public_key:
            return public_key
    return None


def wallet_identity(wallet_path: Path) -> tuple[str, str]:
    if not wallet_path.is_file():
        raise FileNotFoundError(
            f"Wallet not found at {wallet_path}. Create one with lightpool-cli create-wallet."
        )

    wallet = json.loads(wallet_path.read_text(encoding="utf-8"))

    owner = wallet.get("address")
    if not owner:
        raise RuntimeError(f"Wallet file is missing the address field: {wallet_path}")
    owner = normalize_owner_address(owner)

    consensus_pubkey = wallet.get("consensus_pubkey")
    if not consensus_pubkey:
        consensus_pubkey = consensus_pubkey_from_cli(wallet_path)
    if not consensus_pubkey:
        raise RuntimeError(
            f"Could not resolve consensus public key for {wallet_path}. "
            "Recreate the wallet with lightpool-cli create-wallet --force."
        )

    return owner, consensus_pubkey
