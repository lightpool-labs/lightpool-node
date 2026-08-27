#!/usr/bin/env python3
"""Run the full event-contract sample flow in order."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from cli_utils import main_runner


def load_step(filename: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


# Cash collateral comes from bridge LP USDT (not create-token mint supply).
# Market create/mint moved to liquidity_maker bootstrap (top-N from Polymarket).
STEPS = [
    ("bridge-bootstrap", "00_bridge_bootstrap.py"),
    ("create-vault", "05_create_vault.py"),
]


def main() -> int:
    for label, filename in STEPS:
        print(f"\n=== Step: {label} ===", flush=True)
        module = load_step(filename)
        if hasattr(module, "run"):
            code = module.run()
        else:
            code = main_runner(label, module.build_args)
        if code != 0:
            return code
    print("\nAll sample steps completed.", flush=True)
    print(
        "Preferred local order: --phase deploy → start lightpool once with "
        "--bridge-config → --phase create (see doc/frontend-bridge-deposit-withdraw.md).",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
