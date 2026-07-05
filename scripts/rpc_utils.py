from __future__ import annotations

import json
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
