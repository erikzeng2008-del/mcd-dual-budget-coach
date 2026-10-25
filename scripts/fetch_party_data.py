"""拉取聚餐拼单所需的全量真实数据，落盘为 party-data.json。

用法：
    python scripts/fetch_party_data.py                # 默认福州金洲南路
    python scripts/fetch_party_data.py 上海 人民广场    # 换城市/商圈

产物：party-data.json（菜单+营养+活动+券+门店+调用日志）
所有数字均来自麦当劳 MCP 实时返回，脚本不做任何估算或补全。
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_client import McpClient  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "party-data.json")

CITY = sys.argv[1] if len(sys.argv) > 1 else "福州"
KEYWORD = sys.argv[2] if len(sys.argv) > 2 else "仓山"
PREFER_STORE = os.environ.get("MCD_STORE_NAME", "金洲南路")


def main():
    c = McpClient()
    c.initialize()
    log = []

    def step(name, tool, args=None):
        t0 = time.time()
        r = c.call(tool, args)
        dt = time.time() - t0
        ok = r["json"] is not None
        log.append({"step": name, "tool": tool, "args": args or {},
                    "seconds": round(dt, 2), "ok": ok})
        print(f"[{'OK' if ok else '!!'}] {name:<14} {tool:<24} {dt:.1f}s", flush=True)
        return r

    now = step("服务器时间", "now-time-info")
    stores = step("附近门店", "query-nearby-stores",
                  {"beType": 1, "city": CITY, "keyword": KEYWORD, "searchType": 2})
    store_list = (stores["json"] or {}).get("data") or []
    if not store_list:
        raise SystemExit("未取到门店，检查 city/keyword")
    store = next((s for s in store_list if PREFER_STORE in s.get("storeName", "")),
                 store_list[0])
    print("    选用门店:", store["storeName"], store["storeCode"])

    meals = step("菜单与价格", "query-meals",
                 {"beType": 1, "orderType": 1, "storeCode": store["storeCode"]})
    nutrition = step("营养表", "list-nutrition-foods")
    calendar = step("活动日历", "campaign-calendar")
    avail = step("可领券", "available-coupons")
    mine = step("我的券", "query-my-coupons")

    md = (meals["json"] or {}).get("data") or {}
    payload = {
        "snapshot_at": (now["json"] or {}).get("datetime"),
        "fetched_at_local": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "https://mcp.mcd.cn (麦当劳官方 MCP)",
        "city": CITY, "keyword": KEYWORD,
        "store": store,
        "stores": store_list,
        "categories": md.get("categories") or [],
        "meals": md.get("meals") or {},
        "nutrition_text": nutrition["text"],
        "calendar_text": calendar["text"],
        "available_coupons_text": avail["text"],
        # 个人券属于账户隐私，不进公开快照；只在本地单独留一份（已加入 .gitignore）
        "call_log": log,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    local = os.path.join(ROOT, "party-data.local.json")
    with open(local, "w", encoding="utf-8") as f:
        json.dump({"snapshot_at": payload["snapshot_at"],
                   "my_coupons_text": mine["text"]}, f, ensure_ascii=False, indent=1)
    print(f"\n菜单 SKU: {len(payload['meals'])}  分类: {len(payload['categories'])}")
    print("已写入", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
