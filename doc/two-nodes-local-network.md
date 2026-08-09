# Two Nodes: Local Network

Run two validators locally. node0 starts alone and produces the first checkpoint at block 1000; node1 joins afterward via state sync and staking. After the second epoch (~block 2000), both nodes should propose.

From the `lightpool-node` root with binaries on `PATH` (`source ./env.sh`).

## Listening addresses

| | node0 | node1 |
| --- | --- | --- |
| front | 127.0.0.1:26000 | 127.0.0.1:27000 |
| rpc | 127.0.0.1:26300 | 127.0.0.1:27300 |
| ws | 127.0.0.1:26400 | 127.0.0.1:27400 |

## Automated: `run_2nodes/run_2nodes.py`

One command drives the full flow (init → node0 → burst past 800 → node1 → first checkpoint sync → staking → burst to 3000):

```shell
python3 scripts/run_2nodes/run_2nodes.py
```

What it does:

1. `init` — reset `scripts/run_2nodes/.local-network`, create wallets/validator configs
2. Start **node0** as Validator
3. Burst until tip **> 800**, pause burst
4. Start **node1** as PendingMember (`--boot-peer` node0)
5. Burst again until tip **>= 1000**, stop burst so node1 can sync the first checkpoint
6. Run **staking** (LPL token, bonds for both nodes)
7. Burst until tip **>= 3000** (after 2000 both nodes should propose)

Logs:

- `scripts/run_2nodes/.local-network/node0/lightpool.log`
- `scripts/run_2nodes/.local-network/node1/lightpool.log`
- `scripts/run_2nodes/.local-network/burst_*.log`

Press **Ctrl+C** to stop both nodes.

## Manual step-by-step

Use separate terminals if you want to control each step yourself.

**Terminal 1** — init wallets and validator config (cleans old `scripts/run_2nodes/.local-network`):

```shell
python3 scripts/run_2nodes/init.py
```

**Terminal 2** — start node0:

```shell
python3 scripts/run_2nodes/run_node0.py
```

Wait until you see `Node is running; press Ctrl+C to stop`.

**Terminal 1** — burst transactions on node0 until near the first checkpoint, then start node1 before tip passes 1000:

```shell
python3 scripts/run_2nodes/burst_stage1.py
```

When tip is past **~800** and still before **1000**, in **Terminal 3** start node1:

```shell
python3 scripts/run_2nodes/run_node1.py
```

Continue burst until `committed_block_num` reaches **1000** (first checkpoint), then **Ctrl+C** the burst client so node1 can finish checkpoint sync.

Wait until node1 finishes boot sync, announces Join to node0, and shows `Node is running`.

**Terminal 1** — staking setup (LPL token, bonds for both validators):

```shell
python3 scripts/run_2nodes/staking.py
```

**Terminal 1** — burst again to advance the chain (past 2000 for dual proposal):

```shell
python3 scripts/run_2nodes/burst_stage1.py
```

Press Ctrl+C in any node terminal to stop.

## Optional: log to file (manual runs)

```shell
python3 scripts/run_2nodes/run_node0.py scripts/run_2nodes/.local-network/node0/lightpool.log
python3 scripts/run_2nodes/run_node1.py scripts/run_2nodes/.local-network/node1/lightpool.log
```

## Send transactions through either node

```shell
lightpool create-token \
  --rpc-url http://127.0.0.1:26300 \
  --name "Network Token" \
  --symbol "NET" \
  --total-supply "1000000" \
  --mintable
```
