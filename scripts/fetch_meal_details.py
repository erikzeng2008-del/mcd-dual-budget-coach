"""补齐多人餐/核心套餐的内部构成（rounds），落盘 party-details.json。

拼单算法必须知道「一份拼盘里有什么」才能算出人均、件数和对比基准，
否则只是在搬运商品名。本脚本只读不写，不下单。
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_client import McpClient  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 多人餐 + 拼单算法会用到的高频套餐
CODES = [
    "9900015730",  # BFF四宫格小食盘
    "9900005321",  # BFF四宫格小食盘双人餐
    "9900006332",  # 薄皮V翅双拼十翅
    "9900004066",  # 堡堡随心拼（7件任选）
    "9900015726",  # 韩式甜辣酱鸡块8块
    "9900015729",  # 蘸酱BFF四宫格小食盘
    "9900005439",  # 开心亲子双人餐
    "9900015602",  # 大堡口福三件套
    "9900004064",  # 精选单人餐三件套
    "9900013304",  # 人气经典随心配
    "9900015568",  # 精选超值随心配
    "9900005422",  # 汉堡开心乐园餐
    "9900016073",  # 龙焰鸡腿堡三件套
    "9900000891",  # 麦辣鸡腿堡四件套
]


def main():
    data = json.load(open(os.path.join(ROOT, "party-data.json"), encoding="utf-8"))
    store = data["store"]["storeCode"]
    c = McpClient()
    c.initialize()
    out = {}
    for code in CODES:
        name = (data["meals"].get(code) or {}).get("name", code)
        try:
            r = c.call("query-meal-detail",
                       {"beType": 1, "orderType": 1, "storeCode": store, "code": code})
        except Exception as e:  # 单个失败不拖垮整批
            print("[ERR]", code, name, str(e)[:160], flush=True)
            out[code] = {"name": name, "error": str(e)[:200]}
            continue
        out[code] = {"name": name, "json": r["json"], "text": r["text"][:200]}
        n_rounds = len(((r["json"] or {}).get("data") or {}).get("rounds") or [])
        print(f"[OK] {code} {name}  rounds={n_rounds}", flush=True)
        time.sleep(0.15)
    path = os.path.join(ROOT, "party-details.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("已写入", path, os.path.getsize(path), "bytes")


if __name__ == "__main__":
    main()
