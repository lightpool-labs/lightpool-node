from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any


def json_rpc(url: str, method: str, params: list[Any] | None = None) -> Any:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as error:
        raise RuntimeError(f"JSON-RPC request to {url} failed: {error}") from error

    if "error" in body:
        raise RuntimeError(f"JSON-RPC {method} failed: {body['error']}")
    return body.get("result")


def rpc_url_for_port(rpc_port: int) -> str:
    return f"http://127.0.0.1:{rpc_port}"


def get_sync_info(rpc_port: int) -> dict[str, Any]:
    result = json_rpc(rpc_url_for_port(rpc_port), "getSyncInfo")
    if not isinstance(result, dict):
        raise RuntimeError(f"Unexpected getSyncInfo result: {result!r}")
    return result


def committed_block_num(rpc_port: int) -> int:
    info = get_sync_info(rpc_port)
    return int(info["committed_block_num"])


def wait_for_committed_block(
    rpc_port: int,
    target: int,
    *,
    timeout_sec: float = 600.0,
    poll_sec: float = 1.0,
    label: str = "node",
) -> int:
    """Poll getSyncInfo until committed_block_num >= target. Returns the tip."""
    deadline = time.monotonic() + timeout_sec
    last = -1
    while time.monotonic() < deadline:
        try:
            last = committed_block_num(rpc_port)
        except RuntimeError:
            time.sleep(poll_sec)
            continue
        if last >= target:
            print(
                f"{label} committed_block_num={last} (>= {target})",
                flush=True,
            )
            return last
        print(
            f"Waiting for {label} committed_block_num >= {target} "
            f"(now {last})...",
            flush=True,
        )
        time.sleep(poll_sec)
    raise TimeoutError(
        f"Timed out waiting for {label} committed_block_num >= {target} "
        f"(last={last})"
    )
