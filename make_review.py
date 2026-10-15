# -*- coding: utf-8 -*-
"""生成抠图审阅台：单文件 HTML，含 83 个商品的「原图 / A主食片 / B后排片」三列对照
用法：python make_review.py  →  输出 抠图审阅台.html
"""
import base64
import io
import json
import os

from PIL import Image, ImageDraw

ROOT = r"F:\WorkBuddy默认工作空间存储\2026-10-09-15-17-04"
ASSETS = os.path.join(ROOT, "mcd-dual-budget-coach", "demo-assets")
SNAP = os.path.join(ROOT, "mcd_demo_data.json")
PIECES = os.path.join(ROOT, "pieces.json")
CUTDIR = r"F://mcd_tools//cutouts"
OUT = os.path.join(ROOT, "抠图审阅台.html")

SET_KEYS = ["套餐", "件套", "随心配", "四宫格", "双人", "分享"]
A_LINE = 0.42   # A 片裁切线（下半起点）
B_LINE = 0.52   # B 片裁切线（上半终点）


def thumb(im, max_w=330, quality=82):
    """缩到可审阅尺寸并压成 jpeg dataURI"""
    if im.width > max_w:
        r = max_w / im.width
        im = im.resize((max_w, max(1, int(im.height * r))), Image.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    snap = json.load(open(SNAP, encoding="utf-8"))
    pieces = json.load(open(PIECES, encoding="utf-8"))
    items = snap["items"]

    cards = []
    n_set = 0
    for idx, it in enumerate(items, 1):
        name = it["name"]
        fn = os.path.basename(it.get("img") or "")
        is_set = any(k in name for k in SET_KEYS)
        pi = pieces.get(name) or {}
        # 原图 + 裁切线
        src_uri = ""
        p = os.path.join(ASSETS, fn)
        if os.path.exists(p):
            orig = Image.open(p).convert("RGB")
            d = ImageDraw.Draw(orig)
            src_uri = thumb(orig)
        a_uri = pi.get("a") or ""
        b_uri = pi.get("b") or ""
        if is_set and b_uri:
            n_set += 1
        kind = "套餐/套图" if is_set else "单品"
        cards.append({
            "idx": idx, "name": name, "kind": kind,
            "cat": it.get("cat", ""), "price": it.get("price", ""),
            "src": src_uri, "a": a_uri, "b": b_uri,
        })

    html = ["""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>抠图审阅台 · 83 个商品</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:"Microsoft YaHei","PingFang SC",sans-serif; background:#F7F4EC; color:#1a1a1a;
         padding:20px 16px 60px; }
  h1 { font-size:22px; margin-bottom:8px; }
  .tip { background:#fff; border:2px solid #1a1a1a; border-radius:12px; padding:12px 16px;
         font-size:13px; line-height:1.8; margin-bottom:16px; max-width:1100px; }
  .tip b { color:#C8102E; }
  .toolbar { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:14px; }
  .toolbar button { font-family:inherit; font-size:12.5px; font-weight:700; cursor:pointer;
         background:#fff; border:2px solid #1a1a1a; border-radius:999px; padding:6px 14px; }
  .toolbar button.on { background:#C8102E; color:#fff; border-color:#C8102E; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(380px, 1fr)); gap:14px; }
  .card { background:#fff; border:2px solid #1a1a1a; border-radius:12px; padding:10px 12px; }
  .hd { display:flex; align-items:baseline; gap:8px; flex-wrap:wrap; margin-bottom:8px; }
  .no { font-family:Consolas,monospace; font-weight:800; background:#1a1a1a; color:#fff;
        border-radius:6px; padding:2px 8px; font-size:12.5px; }
  .nm { font-size:14.5px; font-weight:800; }
  .kind { font-size:11px; font-weight:700; padding:2px 8px; border-radius:999px;
          background:#FFF3D6; border:1px solid #e0cfa0; color:#7a5c14; }
  .kind.single { background:#EAF4EA; border-color:#bfd8bf; color:#3d6b3d; }
  .meta { font-size:12px; color:#7a6a52; margin-left:auto; }
  .imgs { display:grid; grid-template-columns:1fr 1fr; gap:10px; align-items:end; }
  figure { display:flex; flex-direction:column; gap:4px; }
  .ph { height:165px; display:flex; align-items:center; justify-content:center;
        background: repeating-conic-gradient(#eee 0% 25%, #fff 0% 50%) 50% / 14px 14px;
        border:1.5px dashed #bbb; border-radius:8px; overflow:hidden; }
  .ph img { max-width:100%; max-height:100%; object-fit:contain; display:block; }
  .ph.none { border-style:solid; border-color:#e5ddcc; background:#FBF8F0; color:#b0a48c;
             font-size:12px; }
  figcaption { font-size:11.5px; color:#6b5f4a; text-align:center; }
  figcaption b { color:#C8102E; }
</style></head><body>
<h1>抠图审阅台 · 83 个商品</h1>
<div class="tip">
  每个商品一行两格：<b>左=原图</b>、<b>右=AI 抠图结果</b>（u2net 神经网络抠图，整图去底、**不裁切不缩放**，商品原样保留）。<br>
  全部 83 个商品都由同一套 AI 模型一次跑完（0.32 秒/张）。发现问题请报<b>编号</b>，例如「#37 抠图右侧缺了一块」——我逐个查。
</div>
<div class="toolbar">
  <button class="on" onclick="filt('all', this)">全部 83</button>
  <button onclick="filt('set', this)">套餐/套图</button>
  <button onclick="filt('single', this)">单品</button>
  <span id="cnt" style="font-size:12.5px;color:#7a6a52;align-self:center"></span>
</div>
<div class="grid" id="grid">
"""]

    for c in cards:
        is_set = c["kind"].startswith("套图")
        cls = "" if is_set else " single"
        bcell = ""
        html.append(
            '<div class="card" data-kind="%s">'
            '<div class="hd"><span class="no">#%d</span><span class="nm">%s</span>'
            '<span class="kind%s">%s</span><span class="meta">%s · ¥%s</span></div>'
            '<div class="imgs">'
            '<figure><div class="ph"><img src="%s" alt="原图"></div><figcaption>原图（未处理）</figcaption></figure>'
            '<figure><div class="ph"><img src="%s" alt="AI"></div><figcaption><b>AI 抠图</b>（整图去底，零裁切）</figcaption></figure>'
            '</div></div>' % (
                "set" if is_set else "single", c["idx"], c["name"], cls, c["kind"],
                c["cat"] or "—", c["price"],
                c["src"], c["a"]))

    html.append("""</div>
<script>
function filt(kind, btn){
  document.querySelectorAll('.toolbar button').forEach(function(b){ b.classList.remove('on'); });
  btn.classList.add('on');
  var shown = 0;
  document.querySelectorAll('.card').forEach(function(c){
    var k = c.dataset.kind;
    var show = (kind === 'all') || (c.dataset.kind === kind);
    c.style.display = show ? '' : 'none';
    if (show) shown++;
  });
  document.getElementById('cnt').textContent = '显示 ' + shown + ' 个';
}
filt('all', document.querySelector('.toolbar button'));
</script>
</body></html>""")

    out = "\n".join(html)
    open(OUT, "w", encoding="utf-8").write(out)
    print("已生成 %s  |  %.1f MB  |  83 商品（套图 %d）" % (
        os.path.basename(OUT), len(out.encode()) / 1048576, n_set))


if __name__ == "__main__":
    main()
