"""把真实 MCP 快照组装成单文件 party.html（麦门拼单军师）。

输入：party-data.json + party-details.json（由 fetch_*.py 生成）
输出：party.html —— 数据全部内嵌，图片走麦当劳官方 CDN，无构建依赖。
"""
from __future__ import annotations

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "party.html")

# 拼单会用到的分类（其余如麦咖啡周边玩具不进算法，但保留展示）
KEEP_CATS = ["小食拼盘", "多人餐", "精选单人餐", "鸡肉汉堡", "巨无霸", "牛鱼肉堡",
             "安格斯", "炸鸡", "蘸酱炸鸡", "随心配", "大堡口福", "开心乐园",
             "小食甜品", "500", "饮品", "麦咖啡"]

# 纯周边/玩具，不是食物，一律不进拼单算法
NON_FOOD = ["毛绒", "周边", "按摩捶", "痒痒挠", "水手帽", "丝巾", "徽章"]


def norm_text(text: str) -> str:
    """MCP 部分接口把换行转义成字面 \\n 两字符，先统一成真换行。"""
    return (text or "").replace("\\r\\n", "\n").replace("\\n", "\n")


def parse_nutrition(text: str) -> dict:
    """营养表是 `[160]{productName,...}:` 后跟随行 CSV 的文本格式。"""
    out = {}
    for line in norm_text(text).splitlines():
        line = line.strip()
        if not line or line.startswith("[") or "{" in line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 9:
            continue
        name = parts[0]
        try:
            nums = [float(p) if p not in ("", "null") else None for p in parts[2:]]
        except ValueError:
            continue
        out[name] = {"kcal": nums[1], "protein": nums[2], "fat": nums[3],
                     "carb": nums[4], "sodium": nums[5]}
    return out


def parse_calendar(text: str):
    """从 campaign-calendar 的 markdown 里抽出 日期/标题/正文/图。"""
    events = []
    day = ""
    cur = None
    for raw in norm_text(text).splitlines():
        line = raw.strip()
        m = re.match(r"^####\s*(\d{4}年\d{1,2}月\d{1,2}日)(.*)$", line)
        if m:
            day = m.group(1) + (" " + m.group(2).strip() if m.group(2).strip() else "")
            continue
        if line.startswith("-   **活动标题**"):
            if cur:
                events.append(cur)
            cur = {"day": day, "title": line.split("：", 1)[1].strip(),
                   "body": "", "img": ""}
            continue
        if cur is None:
            continue
        if "**活动内容介绍**" in line:
            cur["body"] += line.split("：", 1)[1].strip() + "\n"
        elif cur["body"] and line and not line.startswith("<img") \
                and "活动图片" not in line and not line.startswith("###"):
            cur["body"] += line + "\n"
        im = re.search(r'<img src="([^"]+)"', line)
        if im and not cur["img"]:
            cur["img"] = im.group(1)
    if cur:
        events.append(cur)
    # 去重：同一标题只保留第一次出现
    seen, uniq = set(), []
    for e in events:
        e["body"] = e["body"].strip()
        if e["title"] in seen:
            continue
        seen.add(e["title"])
        uniq.append(e)
    return uniq


def parse_coupons(text: str):
    out = []
    for m in re.finditer(r"优惠券标题：(.+?)\\\s*\n\s*状态：(.+?)\\", norm_text(text)):
        out.append({"name": m.group(1).strip(), "status": m.group(2).strip()})
    return out


def norm_name(s: str) -> str:
    """营养表与套餐构成的命名不一致：麦乐鸡-5块 / 麦乐鸡5块、可乐中杯 / 中杯可乐。
    统一去掉分隔符与杯型词序差异后再比对。"""
    s = re.sub(r"[\s\-—_（）()【】\[\]·%％]", "", (s or "")).lower()
    s = s.replace("中杯", "").replace("大杯", "").replace("小杯", "")
    return s


def make_nut_lookup(nutrition: dict):
    idx = {norm_name(k): v for k, v in nutrition.items()}

    def lookup(name: str):
        if not name:
            return None
        if name in nutrition:
            return nutrition[name]
        key = norm_name(name)
        if key in idx:
            return idx[key]
        # 退而求其次：营养表名是构成名的子串（如「可乐」命中「可口可乐」）
        cands = [(k, v) for k, v in idx.items() if key and (key in k or k in key)]
        if len(cands) == 1:
            return cands[0][1]
        return None

    return lookup


def main():
    data = json.load(open(os.path.join(ROOT, "party-data.json"), encoding="utf-8"))
    details = json.load(open(os.path.join(ROOT, "party-details.json"), encoding="utf-8"))
    nutrition = parse_nutrition(data["nutrition_text"])
    nut_of = make_nut_lookup(nutrition)
    print(f"营养表解析 {len(nutrition)} 条")

    # 「人气热卖」是营销位不是品类，同一 SKU 会重复出现；
    # 真实品类必须优先，否则精选单人餐/龙焰三件套会被误判出候选池。
    cat_of = {}
    for c in data["categories"]:
        cname = (c.get("name") or "").replace("\n", "")
        if "人气热卖" in cname:
            continue
        for m in c.get("meals") or []:
            cat_of[m["code"]] = cname
    for c in data["categories"]:
        cname = (c.get("name") or "").replace("\n", "")
        for m in c.get("meals") or []:
            cat_of.setdefault(m["code"], cname)

    items = []
    for code, m in data["meals"].items():
        name = m.get("name") or ""
        if any(bad in name for bad in NON_FOOD):
            continue
        cat = cat_of.get(code, "")
        if not any(k in cat for k in KEEP_CATS):
            continue
        det = (details.get(code) or {}).get("json") or {}
        rounds = []
        for r in ((det.get("data") or {}).get("rounds") or []):
            chs = r.get("choices") or []
            default = next((c for c in chs if c.get("isDefault") == 1), chs[0] if chs else {})
            alts = [c.get("name") for c in chs if c.get("name") != default.get("name")]
            rounds.append({
                "name": r.get("name"), "qty": r.get("quantity") or 1,
                "default": default.get("name"), "code": default.get("code"),
                "alts": alts[:20],
            })
        price = float(m.get("currentPrice") or 0)
        orig = float(m.get("originalPrice") or price)
        n = nut_of(name)
        items.append({
            "code": code, "name": name, "cat": cat, "price": price, "orig": orig,
            "img": m.get("image") or "", "discount": m.get("discountType") or "",
            "rounds": rounds, "nut": n,
        })

    # 套餐热量 = 默认构成单品求和；任一单品未知则标记部分未知
    for it in items:
        if it["rounds"]:
            total, unknown, missing = 0.0, 0, []
            for r in it["rounds"]:
                if re.search(r"玩具|周边|随机", r["default"] or ""):
                    continue  # 玩具不是食物，不计热量也不计「营养未知」
                nn = nut_of(r["default"] or "")
                if nn and nn.get("kcal") is not None:
                    total += nn["kcal"] * (r["qty"] or 1)
                else:
                    unknown += 1
                    missing.append(r["default"] or r["name"])
            it["kcal"] = round(total) if total else None
            it["kcalUnknown"] = unknown
            it["kcalMissing"] = missing
        else:
            it["kcal"] = (it["nut"] or {}).get("kcal")
            it["kcalUnknown"] = 0 if it["kcal"] is not None else 1

    payload = {
        "at": data["snapshot_at"], "store": data["store"]["storeName"],
        "storeCode": data["store"]["storeCode"], "city": data["city"],
        "address": data["store"].get("address") or "",
        "items": items,
        "events": parse_calendar(data["calendar_text"]),
        "coupons": parse_coupons(data["available_coupons_text"]),
        "calls": data["call_log"],
    }
    print(f"SKU 进算法 {len(items)} | 活动 {len(payload['events'])} | 可领券 {len(payload['coupons'])}")
    print(f"含构成套餐 {sum(1 for i in items if i['rounds'])} 个")

    html = TEMPLATE.replace("/*__PARTY_DATA__*/", json.dumps(payload, ensure_ascii=False))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("已生成", OUT, os.path.getsize(OUT), "bytes")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>麦门拼单军师 · 聚餐一键点麦当劳</title>
<style>
:root{--y:#FFC72C;--r:#DA291C;--ink:#1f1a17;--mut:#7a6f66;--line:#e8e0d5;--bg:#faf7f2;--card:#fff;--ok:#0F6E56}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--ink);line-height:1.65;font-size:15px;-webkit-text-size-adjust:100%}
.wrap{max-width:1060px;margin:0 auto;padding:0 16px 70px}
header{background:var(--ink);color:#fff;padding:26px 0 30px;border-bottom:5px solid var(--y)}
header .wrap{padding-bottom:0}
h1{font-size:27px;letter-spacing:.5px;font-weight:800}
h1 .dot{color:var(--y)}
.sub{color:#d9d0c6;font-size:13.5px;margin-top:7px}
.meta{margin-top:13px;font-size:12px;color:#a89d92;line-height:1.8}
.meta b{color:var(--y);font-weight:600}
nav.quick{margin-top:14px;display:flex;gap:8px;flex-wrap:wrap}
nav.quick a{color:#fff;text-decoration:none;font-size:12.5px;border:1px solid #4a423b;padding:4px 12px;border-radius:999px}
nav.quick a:hover{background:var(--y);color:var(--ink);border-color:var(--y)}
section{margin-top:26px}
h2{font-size:19px;font-weight:800;display:flex;align-items:center;gap:8px}
h2:before{content:"";width:5px;height:19px;background:var(--r);border-radius:3px}
h2 small{font-size:12.5px;color:var(--mut);font-weight:400}
.panel{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px;margin-top:13px}
label.lbl{display:block;font-size:13px;color:var(--mut);margin-bottom:7px;font-weight:600}
.row{display:flex;gap:18px;flex-wrap:wrap}
.row>.col{flex:1;min-width:230px}
.stepper{display:flex;align-items:center;gap:14px}
.stepper button{width:42px;height:42px;border-radius:12px;border:1.5px solid var(--line);background:#fff;font-size:22px;cursor:pointer;color:var(--ink);line-height:1}
.stepper button:active{background:var(--y)}
.stepper .n{font-size:34px;font-weight:800;min-width:78px;text-align:center}
.stepper .n small{font-size:14px;font-weight:400;color:var(--mut)}
input[type=number]{width:100%;padding:11px 13px;font-size:17px;border:1.5px solid var(--line);border-radius:12px;font-family:inherit;background:#fff;color:var(--ink)}
.chips{display:flex;gap:8px;flex-wrap:wrap}
.chip{border:1.5px solid var(--line);background:#fff;border-radius:999px;padding:7px 15px;font-size:13.5px;cursor:pointer;user-select:none}
.chip.on{background:var(--y);border-color:var(--ink);font-weight:700}
.hint{font-size:12px;color:var(--mut);margin-top:8px}
.compare{margin-top:14px;background:#fff8e6;border:1.5px dashed #e3c76a;border-radius:14px;padding:14px 16px;font-size:14px}
.compare b{color:var(--r)}
.plans{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin-top:14px}
.plan{background:var(--card);border:1.5px solid var(--line);border-radius:18px;overflow:hidden;display:flex;flex-direction:column}
.plan.best{border-color:var(--ink);box-shadow:0 0 0 3px var(--y)}
.plan .ph{padding:14px 16px 11px;border-bottom:1px solid var(--line);background:#fffdf7}
.plan .ph .t{font-size:17px;font-weight:800}
.plan .ph .d{font-size:12.5px;color:var(--mut);margin-top:3px}
.badge{display:inline-block;background:var(--r);color:#fff;font-size:11px;padding:2px 8px;border-radius:5px;margin-left:7px;vertical-align:2px}
.plan .pb{padding:12px 16px 16px;flex:1;display:flex;flex-direction:column}
.line{display:flex;justify-content:space-between;gap:10px;padding:7px 0;border-bottom:1px dashed #f0e9df;font-size:13.5px}
.line:last-child{border-bottom:0}
.line .nm{flex:1}
.line .nm small{display:block;color:var(--mut);font-size:11.5px;line-height:1.5}
.line .pr{white-space:nowrap;font-weight:700}
.qty{display:inline-block;background:#f4efe7;border-radius:5px;padding:0 6px;font-size:12px;margin-right:5px;font-weight:700}
.total{margin-top:12px;padding-top:12px;border-top:2px solid var(--ink);display:flex;justify-content:space-between;align-items:baseline}
.total .p{font-size:27px;font-weight:800;color:var(--r)}
.total .p small{font-size:13px;color:var(--mut);font-weight:400}
.kv{display:flex;justify-content:space-between;font-size:12.5px;color:var(--mut);padding:3px 0}
.kv b{color:var(--ink)}
.save{background:#eaf5ee;color:var(--ok);border-radius:10px;padding:9px 12px;font-size:13px;margin-top:11px;font-weight:600}
.warn{background:#fdf0ec;color:#8c3a24;border-radius:10px;padding:9px 12px;font-size:12.5px;margin-top:11px}
.btn{margin-top:13px;background:var(--y);border:1.5px solid var(--ink);color:var(--ink);font-weight:800;padding:12px;border-radius:12px;cursor:pointer;font-size:14.5px;width:100%;font-family:inherit}
.btn:active{transform:translateY(1px)}
.btn.ghost{background:#fff;font-weight:600}
.plan .pb .btn.ghost{margin-top:auto}
.plan .pb .save,.plan .pb .warn{margin-bottom:14px}
textarea{width:100%;min-height:230px;margin-top:13px;border:1.5px solid var(--line);border-radius:12px;padding:13px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;line-height:1.75;background:#fff;color:var(--ink);resize:vertical}
.events{display:grid;grid-template-columns:repeat(auto-fill,minmax(245px,1fr));gap:14px;margin-top:14px}
.ev{background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.ev img{width:100%;height:150px;object-fit:cover;background:#f2ede5;display:block}
.ev .eb{padding:11px 13px 13px}
.ev .day{font-size:11px;color:var(--r);font-weight:700;letter-spacing:.4px}
.ev .tt{font-size:14px;font-weight:700;margin:4px 0 6px;line-height:1.45}
.ev .bd{font-size:12px;color:var(--mut);white-space:pre-line;max-height:118px;overflow:auto}
.empty{padding:26px;text-align:center;color:var(--mut);font-size:14px}
footer{margin-top:34px;border-top:1px solid var(--line);padding-top:18px;font-size:12px;color:var(--mut);line-height:1.9}
footer a{color:var(--r)}
.cpn{display:flex;gap:9px;flex-wrap:wrap;margin-top:12px}
.cpn span{background:#fff;border:1px solid var(--line);border-radius:9px;padding:7px 13px;font-size:13px}
.cpn span b{color:var(--r)}
@media(max-width:640px){h1{font-size:23px}.plans{grid-template-columns:1fr}.total .p{font-size:24px}}
@media print{header,nav.quick,.panel,.btn,footer{display:none}}
</style>
</head>
<body>
<header><div class="wrap">
<h1>🍔 麦门拼单军师<span class="dot"> · </span>聚餐一键点麦当劳</h1>
<div class="sub">几个人、多少钱、什么场景 —— 一次算出整桌怎么点，比各点各的省多少直接写给你看。</div>
<div class="meta">📍 <b id="storeName"></b><br>数据快照 <b id="snapAt"></b> · 来源：麦当劳官方 MCP（query-meals / query-meal-detail / list-nutrition-foods / campaign-calendar）</div>
<nav class="quick">
<a href="lite.html">← 单人双预算（轻量版）</a><a href="demo.html">完整版</a><a href="card.html">全息人设卡</a><a href="https://github.com/erikzeng2008-del/mcd-dual-budget-coach" target="_blank" rel="noopener">GitHub 源码</a>
</nav>
</div></header>
<div class="wrap">

<section>
<h2>① 这桌几个人 <small>人数和预算是两道闸门，跟单人版同一套思路</small></h2>
<div class="panel"><div class="row">
<div class="col"><label class="lbl">聚餐人数</label>
<div class="stepper"><button id="minus" aria-label="减少">−</button><div class="n"><span id="nVal">4</span> <small>人</small></div><button id="plus" aria-label="增加">+</button></div>
<div class="hint">2–12 人。双人餐、多人拼盘会按人头自动组合。</div></div>
<div class="col"><label class="lbl">整桌预算（元，留空 = 不限）</label>
<input type="number" id="budget" min="0" step="10" placeholder="例如 150">
<div class="hint" id="perHead"></div></div>
</div>
<div style="margin-top:18px"><label class="lbl">什么场景</label>
<div class="chips" id="scenes">
<div class="chip on" data-v="friends">🍻 朋友聚餐</div>
<div class="chip" data-v="office">💻 办公室加班</div>
<div class="chip" data-v="family">👨‍👩‍👧 家庭带娃</div>
<div class="chip" data-v="tea">☕ 下午茶</div>
</div></div>
<div style="margin-top:16px"><label class="lbl">偏好（可多选）</label>
<div class="chips" id="prefs">
<div class="chip" data-v="noSpicy">🌶️ 不要辣</div>
<div class="chip" data-v="kids">🧸 有小孩</div>
<div class="chip" data-v="coffee">☕ 想来杯咖啡</div>
<div class="chip" data-v="light">🥗 想轻一点</div>
<div class="chip" data-v="dessert">🍦 加个甜品</div>
</div></div>
</div>
<div class="compare" id="compare"></div>
</section>

<section>
<h2>② 三档整桌方案 <small>点开清单能看到每份套餐里面有什么</small></h2>
<div class="plans" id="plans"></div>
</section>

<section>
<h2>③ 点单接龙 <small>复制发到群里，谁点什么一目了然</small></h2>
<div class="panel">
<div class="chips" id="textWhich">
<div class="chip on" data-v="0">🎉 最省钱</div>
<div class="chip" data-v="1">🍗 最丰盛</div>
<div class="chip" data-v="2">⚖️ 最均衡</div>
</div>
<textarea id="orderText" readonly></textarea>
<button class="btn" id="copyBtn">📋 复制接龙文案</button>
<div class="hint">本工具只算价、不下单。拿着清单到麦当劳 App / 小程序或门店下单即可；价格以实际结算为准。</div>
</div>
</section>

<section>
<h2>④ 本周活动与新品 <small>campaign-calendar 实时拉取，不是手写文案</small></h2>
<div class="cpn" id="coupons"></div>
<div class="events" id="events"></div>
</section>

<footer>
<b>数据与边界</b><br>
· 全部价格、套餐构成、营养与活动来自麦当劳官方 MCP 实时返回，快照时间见页首；本页不估算、不补全、不凭记忆写价。<br>
· 标注「营养未知」的单品是 MCP 营养表暂无数据，不参与热量合计，绝不拿猜测数字凑数。<br>
· 热量为整桌估值，仅供感知，不构成医疗或营养建议。<br>
· 麦当劳程序员创意开发大赛参赛作品 · 麦门双预算军师 之 多人拼单模块 · <a href="https://github.com/erikzeng2008-del/mcd-dual-budget-coach" target="_blank" rel="noopener">源码与开发记录</a>
</footer>
</div>

<script>
const SNAPSHOT = /*__PARTY_DATA__*/;
const $ = id => document.getElementById(id);
const money = x => (Math.round(x*10)/10).toFixed(1);
const ITEMS = SNAPSHOT.items;
const byCode = {}; ITEMS.forEach(i=>byCode[i.code]=i);
const byName = {}; ITEMS.forEach(i=>byName[i.name]=i);
const find = n => ITEMS.find(i=>i.name===n);
const has = n => !!find(n);
const P = n => { const it=find(n); return it?it.price:0; };

// ── 场景与偏好状态 ──
const S = { n:4, budget:null, scene:'friends', prefs:new Set() };

// ── 拼单引擎：所有数字来自快照，不在前端写死价格 ──
// 每个方案 = [{code, qty}]，展开 rounds 得到件数与构成
function line(code, qty){ return {code, qty}; }

function expand(plan){
  let items=[], counts={主食:0,小食:0,饮品:0,甜品:0,玩具:0};
  plan.forEach(l=>{
    const it=byCode[l.code]; if(!it) return;
    items.push({it, qty:l.qty});
    if(it.rounds.length){
      it.rounds.forEach(r=>{
        const nm=r.default||r.name||'';
        const q=(r.qty||1)*l.qty;
        if(/玩具/.test(nm)) counts.玩具+=q;
        else if(/饮料|可乐|牛奶|咖啡|麦炫酷|果汁|纯悦|红茶|苹果汁/.test(nm+r.name)) counts.饮品+=q;
        else if(/汉堡|鸡排|主食|卷|麦满分|鱼堡/.test(nm+r.name)) counts.主食+=q;
        else if(/麦旋风|新地|圆筒|派|冰淇淋/.test(nm)) counts.甜品+=q;
        else counts.小食+=q;
      });
    } else {
      if(/可乐|牛奶|咖啡|麦炫酷|纯悦|红茶|苹果汁|饮品/.test(it.name+it.cat)) counts.饮品+=l.qty;
      else if(/麦旋风|新地|圆筒|派$|冰淇淋/.test(it.name)) counts.甜品+=l.qty;
      else if(/汉堡|鸡排|卷|麦满分|鱼堡|开心乐园餐|随心配|套餐|单人餐|双人餐|三件套|四件套/.test(it.name)) counts.主食+=l.qty;
      else counts.小食+=l.qty;
    }
  });
  return {items, counts};
}

function totals(plan){
  let price=0, orig=0, kcal=0, unknown=0;
  plan.forEach(l=>{
    const it=byCode[l.code]; if(!it) return;
    price+=it.price*l.qty; orig+=it.orig*l.qty;
    if(it.kcal) kcal+=it.kcal*l.qty;
    unknown+=(it.kcalUnknown||0)*l.qty;
  });
  const ex=expand(plan);
  return {price, orig, kcal:Math.round(kcal), unknown,
          pieces:Object.values(ex.counts).reduce((a,b)=>a+b,0), counts:ex.counts, items:ex.items};
}

// 各点各的基准：每人一份标准三件套（麦当劳最常规的一个人点法）
function baseline(n){
  const std = find('精选单人餐三件套') || find('麦辣鸡腿堡四件套') || ITEMS[0];
  return {code:std.code, qty:n, price:std.price*n, name:std.name, unit:std.price};
}

// 场景决定候选池
function pool(){
  const spicy = S.prefs.has('noSpicy');
  const light = S.prefs.has('light');
  const onePlus = ITEMS.filter(i=>/随心配/.test(i.cat) && i.price>0).sort((a,b)=>a.price-b.price);
  const shareAll = ITEMS.filter(i=>/多人餐/.test(i.cat) && !/双人餐|亲子/.test(i.name));
  // 不要辣时把名字带辣的共享小食也剔掉，不能只换主食
  const share = (spicy?shareAll.filter(s=>!/辣/.test(s.name)):shareAll).sort((a,b)=>a.price-b.price);
  const duo = ITEMS.filter(i=>/双人餐/.test(i.name));
  const family = ITEMS.filter(i=>/亲子|开心乐园/.test(i.name));
  const coffee = ITEMS.filter(i=>/麦咖啡/.test(i.cat) && i.price<20).sort((a,b)=>a.price-b.price);
  const dessert = ITEMS.filter(i=>/圆筒|麦旋风|新地/.test(i.name)).sort((a,b)=>a.price-b.price);
  // 轻食档在 500 大卡套餐里选「最便宜的」，否则会把最省钱档顶成全场最贵
  const lightSet = ITEMS.filter(i=>/500/.test(i.cat)).sort((a,b)=>a.price-b.price);
  // 不要辣：BFF 双人餐默认含麦辣鸡腿汉堡，改用「主食任选」的随心拼
  const freeChoice = ITEMS.filter(i=>/随心拼/.test(i.name));
  return {onePlus, share, duo, family, coffee, dessert, lightSet, freeChoice, spicy, light};
}

function cheapest(list){ return list.length?list[0]:null; }

// 在预算内给方案加菜（加共享小食，而不是给每人加一份，才符合拼单逻辑）
function topUp(plan, budget, candidates){
  if(!budget) return plan;
  let cur=totals(plan).price;
  let changed=true, guard=0;
  while(changed && guard++<12){
    changed=false;
    for(const c of candidates){
      if(!c) continue;
      if(cur + c.price <= budget*0.97){
        const ex=plan.find(l=>l.code===c.code);
        if(ex) ex.qty++; else plan.push(line(c.code,1));
        cur+=c.price; changed=true; break;
      }
    }
  }
  return plan;
}

// 超预算时降档：先砍加菜与共享拼盘，主食尽量保到人手一份；
// 实在保不住就砍，但由 shortfall() 把「还差几份」明确写出来，不偷偷少给。
function shrink(plan, budget){
  if(!budget) return plan;
  let guard=0;
  while(totals(plan).price>budget && guard++<24){
    const sorted=[...plan].sort((a,b)=>byCode[b.code].price-byCode[a.code].price);
    // 先砍非主食行（拼盘/加菜/甜品/咖啡）
    let victim=sorted.find(l=>!isMainLine(l) && l.qty>=1);
    if(!victim) victim=sorted.find(l=>l.qty>1);
    if(!victim) victim=sorted[sorted.length-1];
    if(!victim) break;
    if(plan.length===1 && victim.qty===1) break;
    victim.qty--;
    if(victim.qty<=0) plan=plan.filter(l=>l!==victim);
  }
  return plan;
}

// 这一行是不是「管饱的主食」（决定砍单顺序与人数覆盖校验）
function isMainLine(l){
  const it=byCode[l.code]; if(!it) return false;
  if(/双人餐|亲子|随心配|三件套|四件套|单人餐|开心乐园餐|套餐/.test(it.name)) return true;
  if(/多人餐/.test(it.cat)) return false;
  return /汉堡|鸡排|卷$|麦满分|鱼堡/.test(it.name);
}

// 主食能覆盖几个人：双人餐算 2 人，单人餐/随心配/单品汉堡算 1 人
function covered(plan){
  let n=0;
  plan.forEach(l=>{
    const it=byCode[l.code]; if(!it||!isMainLine(l)) return;
    n += (/双人餐|亲子/.test(it.name)?2:1)*l.qty;
  });
  return n;
}

function buildPlans(){
  const n=S.n, p=pool(), B=S.budget;
  const isTea=S.scene==='tea';
  const isFamily=S.scene==='family'||S.prefs.has('kids');
  const plans=[];

  // 🎉 最省钱：随心配解决「主食+饮品」，共享拼盘解决「小食」
  // 这一档绝不顶格加菜——加满了就不是「最省钱」了
  {
    const op=cheapest(p.onePlus);
    let plan=[];
    if(op && !isTea) plan.push(line(op.code,n));
    const shareCount=Math.max(1,Math.round(n/4));
    const sh=cheapest(p.share);
    if(sh) plan.push(line(sh.code, isTea?Math.max(1,Math.round(n/3)):shareCount));
    if(p.light && p.lightSet.length && !isTea){
      plan=plan.filter(l=>l.code!==(op&&op.code));
      plan.push(line(p.lightSet[0].code,n));
    }
    if(isTea){ const d=cheapest(p.dessert); if(d) plan.push(line(d.code,n)); }
    plan=shrink(plan,B);
    plans.push({key:'cheap',icon:'🎉',title:'最省钱',desc:'主食饮品走随心配，小食全桌共享',plan});
  }

  // 🍗 最丰盛：双人餐打底 + 加菜，件数优先
  {
    let plan=[];
    const duo = p.spicy ? (p.freeChoice[0]||p.duo[0])
                        : (p.duo.find(d=>/BFF/.test(d.name)) || p.duo[0]);
    if(isFamily && p.family.length){
      const fam=p.family.find(f=>/亲子/.test(f.name))||p.family[0];
      plan.push(line(fam.code,Math.max(1,Math.round(n/2))));
    } else if(duo && !isTea){
      plan.push(line(duo.code,Math.max(1,Math.round(n/2))));
    } else if(!isTea) {
      const op=cheapest(p.onePlus); if(op) plan.push(line(op.code,n));
    }
    // 加菜优先「十翅」这种真正的分享装，其次鸡块
    const feast=p.share.filter(s=>/十翅/.test(s.name));
    const add=feast[0]||p.share.filter(s=>/鸡块/.test(s.name))[0]||p.share[p.share.length-1];
    if(add) plan.push(line(add.code,Math.max(1,Math.round(n/4))));
    if(S.prefs.has('dessert')||isTea){ const d=cheapest(p.dessert); if(d) plan.push(line(d.code,n)); }
    if(S.prefs.has('coffee')||S.scene==='office'){ const c=cheapest(p.coffee); if(c) plan.push(line(c.code,Math.max(1,Math.round(n/2)))); }
    plan=shrink(plan,B);
    plans.push({key:'feast',icon:'🍗',title:'最丰盛',desc:'双人餐/亲子餐打底，件数拉满',plan});
  }

  // ⚖️ 最均衡：双人餐 + 单人补足，奇数人不落空；有预算再考虑加菜
  {
    let plan=[];
    const duo = p.spicy ? (p.freeChoice[0]||p.duo[0])
                        : (p.duo.find(d=>/BFF/.test(d.name))||p.duo[0]);
    const pairs=Math.floor(n/2), odd=n%2;
    if(isFamily && p.family.length){
      const fam=p.family.find(f=>/亲子/.test(f.name))||p.family[0];
      plan.push(line(fam.code,Math.max(1,pairs)));
      if(odd){ const op=cheapest(p.onePlus); if(op) plan.push(line(op.code,1)); }
    } else if(duo && !isTea){
      if(pairs) plan.push(line(duo.code,pairs));
      if(odd){ const single=find('大堡口福三件套')||cheapest(p.onePlus); if(single) plan.push(line(single.code,1)); }
    } else if(!isTea) {
      const op=cheapest(p.onePlus); if(op) plan.push(line(op.code,n));
    }
    // 双人餐本身已含小食，只有纯小食场景才补共享拼盘
    if(isTea){
      const sh=p.share.find(s=>/四宫格/.test(s.name))||cheapest(p.share);
      if(sh) plan.push(line(sh.code,1));
      const d=cheapest(p.dessert); if(d) plan.push(line(d.code,n));
    }
    if(S.prefs.has('coffee')||S.scene==='office'){ const c=cheapest(p.coffee); if(c) plan.push(line(c.code,Math.max(1,Math.round(n/2)))); }
    if(S.prefs.has('dessert')&&!isTea){ const d=cheapest(p.dessert); if(d) plan.push(line(d.code,n)); }
    if(B){ plan=topUp(plan,B*0.9,[p.share[1],p.share[0],cheapest(p.dessert),cheapest(p.coffee)]); }
    plan=shrink(plan,B);
    plans.push({key:'balanced',icon:'⚖️',title:'最均衡',desc:'双人餐+单人补足，预算用在刀刃上',plan});
  }
  return plans;
}

function render(){
  $('nVal').textContent=S.n;
  const b=$('budget').value;
  S.budget=b&&Number(b)>0?Number(b):null;
  $('perHead').textContent=S.budget?('人均上限 ¥'+money(S.budget/S.n)+' · 三档都会尽量不破顶'):'不限预算时，均衡档按结构完整来配';
  document.querySelectorAll('#scenes .chip').forEach(c=>c.classList.toggle('on',c.dataset.v===S.scene));
  document.querySelectorAll('#prefs .chip').forEach(c=>c.classList.toggle('on',S.prefs.has(c.dataset.v)));

  const base=baseline(S.n);
  const plans=buildPlans().map(p=>({...p,t:totals(p.plan)}));
  window.PLANS=plans;

  const cheapestPlan=plans.reduce((a,b)=>a.t.price<b.t.price?a:b);
  const diff=base.price-cheapestPlan.t.price;
  $('compare').innerHTML = S.scene==='tea'
    ? `☕ 下午茶不按人头配主食，按「共享小食 + 饮品/甜品」来凑。当前最便宜的一桌 <b>¥${money(cheapestPlan.t.price)}</b>，人均 <b>¥${money(cheapestPlan.t.price/S.n)}</b>。`
    : `🆚 <b>各点各的</b>：${S.n} × ${base.name}（¥${money(base.unit)}/人）= <b>¥${money(base.price)}</b><br>🧩 <b>拼单共享</b>：最便宜的一桌 ¥${money(cheapestPlan.t.price)}，人均 ¥${money(cheapestPlan.t.price/S.n)}${diff>0?` —— <b>这一桌省 ¥${money(diff)}</b>，相当于白得 ${Math.max(1,Math.floor(diff/5))} 个圆筒冰淇淋`:' —— 这个人数下拼单不一定更便宜，看清单挑你要的'}`;

  if(S.prefs.has('noSpicy')) $('compare').innerHTML+='<br>🌶️ 已避开辣款：双人餐改走「堡堡随心拼」（主食可自选不辣），共享小食同步剔除辣款。';
  if(S.prefs.has('light')) $('compare').innerHTML+='<br>🥗 想轻一点：最省钱档已换成 500 大卡套餐，热量优先于价格——这一档可能更贵，是口味选择不是算错。';

  $('plans').innerHTML=plans.map((p,idx)=>{
    const t=p.t;
    const rows=t.items.map(({it,qty})=>{
      const sub=it.rounds.length
        ? it.rounds.map(r=>`${r.default||r.name}×${r.qty||1}`).join('、')
        : (it.kcal?`${it.kcal} kcal`:'营养未知');
      return `<div class="line"><div class="nm"><span class="qty">×${qty}</span>${it.name}<small>${sub}</small></div><div class="pr">¥${money(it.price*qty)}</div></div>`;
    }).join('');
    const per=t.price/S.n;
    const saved=t.orig-t.price;
    const vsBase=base.price-t.price;
    const over=S.budget&&t.price>S.budget;
    const cov=covered(p.plan);
    const short=S.scene==='tea'?0:Math.max(0,S.n-cov);
    return `<div class="plan ${idx===0?'best':''}">
      <div class="ph"><div class="t">${p.icon} ${p.title}${idx===0?'<span class="badge">推荐</span>':''}</div><div class="d">${p.desc}</div></div>
      <div class="pb">${rows}
        <div class="total"><span>整桌合计</span><span class="p">¥${money(t.price)} <small>/ 人均 ¥${money(per)}</small></span></div>
        <div class="kv"><span>份数</span><b>${t.pieces} 份（主食${t.counts.主食} · 小食${t.counts.小食} · 饮品${t.counts.饮品}${t.counts.玩具?` · 玩具${t.counts.玩具}`:''}）</b></div>
        <div class="kv"><span>整桌热量</span><b>${t.kcal?t.kcal+' kcal':'部分未知'}${t.unknown?`（${t.unknown} 项营养未知）`:''}</b></div>
        <div class="kv"><span>对比划线价</span><b>¥${money(t.orig)}</b></div>
        ${S.scene!=='tea'?`<div class="kv"><span>主食覆盖</span><b>${cov} / ${S.n} 人</b></div>`:''}
        ${short>0?`<div class="warn">🍚 这个预算下主食只够 ${cov} 人，还差 ${short} 份。要么加预算、要么减人——不偷偷少给你。</div>`:''}
        ${saved>0?`<div class="save">🎫 比划线价省 ¥${money(saved)}${vsBase>0?` ｜ 比各点各的再省 ¥${money(vsBase)}`:''}</div>`:''}
        ${over?`<div class="warn">⚠️ 这一档超出预算 ¥${money(t.price-S.budget)}，人数和预算下只能配到这里；想不破顶就选最省钱档。</div>`:''}
        <button class="btn ghost" data-plan="${idx}">📋 复制这一档接龙</button>
      </div></div>`;
  }).join('');

  document.querySelectorAll('[data-plan]').forEach(btn=>{
    btn.onclick=()=>{ window.TEXTIDX=Number(btn.dataset.plan); syncTextTabs(); fillText(); copyText(); };
  });
  fillText();
}

function syncTextTabs(){
  document.querySelectorAll('#textWhich .chip').forEach(c=>c.classList.toggle('on',Number(c.dataset.v)===(window.TEXTIDX||0)));
}

function fillText(){
  const plans=window.PLANS||[]; if(!plans.length) return;
  const idx=window.TEXTIDX||0; const p=plans[idx]; const t=p.t;
  const base=baseline(S.n);
  const lines=[`🍔 麦门拼单接龙 · ${S.n}人 · ${p.icon}${p.title}`,`📍 ${SNAPSHOT.store}（到店自提）`,''];
  t.items.forEach(({it,qty})=>{
    lines.push(`${it.name} ×${qty} — ¥${money(it.price*qty)}`);
    if(it.rounds.length) lines.push('   含：'+it.rounds.map(r=>`${r.default||r.name}×${r.qty||1}`).join('、'));
  });
  lines.push('');
  lines.push(`合计 ¥${money(t.price)} ｜ 人均 ¥${money(t.price/S.n)} ｜ 共 ${t.pieces} 份`);
  if(t.orig-t.price>0) lines.push(`比划线价省 ¥${money(t.orig-t.price)}`);
  const d=base.price-t.price;
  if(d>0&&S.scene!=='tea') lines.push(`比各点各的（${S.n}×${base.name} ¥${money(base.price)}）省 ¥${money(d)}`);
  if(t.kcal) lines.push(`整桌约 ${t.kcal} kcal，人均约 ${Math.round(t.kcal/S.n)} kcal${t.unknown?'（含营养未知项，合计不完整）':''}`);
  lines.push('');
  lines.push('接龙：');
  for(let i=1;i<=S.n;i++) lines.push(`${i}. `);
  lines.push('');
  lines.push(`—— 数据：麦当劳官方 MCP 快照 ${SNAPSHOT.at}，以实际结算为准`);
  $('orderText').value=lines.join('\n');
}

function copyText(){
  const ta=$('orderText'); ta.focus(); ta.select();
  const done=()=>{ const b=$('copyBtn'); const o=b.textContent; b.textContent='✅ 已复制，去群里粘贴吧'; setTimeout(()=>b.textContent=o,1800); };
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(ta.value).then(done).catch(()=>{document.execCommand('copy');done();});
  } else { document.execCommand('copy'); done(); }
}

function renderEvents(){
  const ev=SNAPSHOT.events||[];
  $('events').innerHTML=ev.slice(0,12).map(e=>`<div class="ev">
    ${e.img?`<img src="${e.img}" alt="" loading="lazy" onerror="this.style.display='none'">`:''}
    <div class="eb"><div class="day">${e.day||'进行中'}</div><div class="tt">${e.title}</div><div class="bd">${e.body||''}</div></div></div>`).join('')
    || '<div class="empty">本次快照未取到活动数据</div>';
  const cp=SNAPSHOT.coupons||[];
  $('coupons').innerHTML=cp.length?cp.map(c=>`<span>🎟️ ${c.name} <b>${c.status}</b></span>`).join(''):'';
}

$('minus').onclick=()=>{S.n=Math.max(2,S.n-1);render();};
$('plus').onclick=()=>{S.n=Math.min(12,S.n+1);render();};
$('budget').oninput=render;
document.querySelectorAll('#scenes .chip').forEach(c=>c.onclick=()=>{S.scene=c.dataset.v;render();});
document.querySelectorAll('#prefs .chip').forEach(c=>c.onclick=()=>{
  const v=c.dataset.v; S.prefs.has(v)?S.prefs.delete(v):S.prefs.add(v); render();
});
document.querySelectorAll('#textWhich .chip').forEach(c=>c.onclick=()=>{window.TEXTIDX=Number(c.dataset.v);syncTextTabs();fillText();});
$('copyBtn').onclick=copyText;

$('storeName').textContent=SNAPSHOT.store+' · '+SNAPSHOT.address;
$('snapAt').textContent=SNAPSHOT.at;
renderEvents();
render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
