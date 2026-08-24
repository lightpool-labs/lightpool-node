# LightPool full-system auto tests

Scripted end-to-end scenarios. Each script asserts via RPC/CLI and exits
non-zero on failure (no log eyeballing required).

## Run

```bash
cd ~/work/lightpool-labs/lightpool-node
cargo build --release          # refreshes bin/lightpool
python3 tests/scenario1_single_node.py
```

## Scenarios

| Script | Scenario | Frequency |
| --- | --- | --- |
| `scenario1_single_node.py` | Single-node product path: create token -> spot market -> fund taker -> resting sell -> IOC fill -> maker cancel -> balance/book assertions | Daily |
| `scenario2_two_nodes.py` | Two-node consensus + staking: pending-member checkpoint sync -> bond/register/allocate -> dual proposals -> tip/hash match -> mid-run restart catch-up | Weekly / sync/epoch changes |

Scenario 2 notes:

- Currently RED: it exposed a node-side bug — after node1 boots via
  checkpoint + buffered blocks, its state root diverges from node0 from the
  first post-boot block (`attest validate Invalid(root_mismatch)` on every
  block), and its `committed_block_num` is offset by the boot tip.
  See `tools/testing/lightpool-0.3.0-testing.md` Scenario 2 for details.
- Ports: node0 26000–26400, node1 27000–27400 (fixed by
  `scripts/run_2nodes/lib/config.py`).
- Data dir: `tests/.scenario2/` (wiped on every run).
- Node logs: `tests/.scenario2/node{0,1}/lightpool.log`.

Scenario 1 notes:

- Ports: front 36000, mempool 36100, consensus 36200, RPC 36300, WS 36400
  (override with `LIGHTPOOL_TEST_*_PORT`).
- Data dir: `tests/.scenario1/` (wiped on every run).
- Node log on failure: `tests/.scenario1/node0/lightpool.log`.
- The cancel step uses the `cancel-order` CLI subcommand; run with a binary
  built from the `lightpool` workspace (`LIGHTPOOL_BIN=/path/to/lightpool`)
  until the release tarball in `bin/` is repacked.
