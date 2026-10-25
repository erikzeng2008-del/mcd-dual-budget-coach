"""麦当劳 MCP 最小客户端（streamable-http）。

直接对 https://mcp.mcd.cn 发 JSON-RPC，绕开「工具结果只存在于对话里」的限制，
让菜单/活动/券数据可以落盘成快照、可复现、可进 Git。

Token 从环境变量 MCD_MCP_TOKEN 或 ~/.workbuddy/mcp.json 读取，绝不写进代码。
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.error

MCP_URL = os.environ.get("MCD_MCP_URL", "https://mcp.mcd.cn")
CONFIG = os.path.expanduser("~/.workbuddy/mcp.json")


def load_token() -> str:
    tok = os.environ.get("MCD_MCP_TOKEN", "").strip()
    if tok:
        return tok
    with open(CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    auth = cfg["mcpServers"]["mcd-mcp"]["headers"]["Authorization"]
    return auth.split(" ", 1)[1].strip()


class McpClient:
    def __init__(self, token: str | None = None, timeout: int = 45):
        self.token = token or load_token()
        self.timeout = timeout
        self.session = None
        self._id = 0
        self.calls: list[dict] = []  # 调用日志，供评审溯源

    def _post(self, payload: dict, notify: bool = False):
        self._id += 1
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(MCP_URL, data=body, method="POST")
        req.add_header("Authorization", "Bearer " + self.token)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        if self.session:
            req.add_header("Mcp-Session-Id", self.session)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=self.timeout) as resp:
            sid = resp.headers.get("Mcp-Session-Id")
            if sid:
                self.session = sid
            raw = resp.read().decode("utf-8", "replace")
        if notify:
            return None
        return self._parse(raw)

    @staticmethod
    def _parse(raw: str):
        """streamable-http 可能回 JSON，也可能回 SSE。"""
        raw = raw.strip()
        if raw.startswith("{") or raw.startswith("["):
            return json.loads(raw)
        for line in raw.splitlines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk and chunk != "[DONE]":
                    return json.loads(chunk)
        raise ValueError("无法解析 MCP 响应: " + raw[:300])

    def initialize(self):
        r = self._post({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "mcd-party-builder", "version": "1.0.0"},
            },
        })
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, notify=True)
        return r

    def call(self, tool: str, args: dict | None = None):
        args = args or {}
        payload = {
            "jsonrpc": "2.0", "id": self._id + 1, "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        }
        try:
            r = self._post(payload)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            self.calls.append({"tool": tool, "args": args, "error": f"HTTP {e.code} {detail}"})
            raise RuntimeError(f"{tool} HTTP {e.code}: {detail}") from e
        text = ""
        if isinstance(r, dict):
            content = (r.get("result") or {}).get("content") or []
            text = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
        data = extract_json(text)
        self.calls.append({"tool": tool, "args": args, "ok": data is not None})
        return {"text": text, "json": data, "raw": r}


def extract_json(text: str):
    """MCP 返回「markdown 说明 + 原始 JSON」混合文本，取 JSON 部分。"""
    if not text:
        return None
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = dec.raw_decode(text[m.start():])
        except ValueError:
            continue
        if isinstance(obj, dict) and ("data" in obj or "success" in obj):
            return obj
    return None


if __name__ == "__main__":
    c = McpClient()
    print("initialize ->", json.dumps(c.initialize(), ensure_ascii=False)[:200])
    r = c.call("now-time-info")
    print("now-time-info ->", json.dumps(r["json"], ensure_ascii=False)[:300])
