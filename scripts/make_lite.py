"""生成 lite.html：把 demo.html（11.7MB）压成 ≤1MB 的轻量试算页。
策略：保留全部功能与五屏，只压缩内嵌图片——
  · DATA 单品图  → 宽 120px JPEG q62
  · PIECES 构件图 → 宽 90px JPEG q58（套餐 PS 拼图用）
输出：仓库根目录 lite.html
"""
import re, base64, io, os, sys, collections
from PIL import Image

BASE = r"F:\WorkBuddy默认工作空间存储\2026-10-09-15-17-04\mcd-dual-budget-coach"
SRC = os.path.join(BASE, "demo.html")
OUT = os.path.join(BASE, "lite.html")

src = open(SRC, encoding="utf-8", errors="ignore").read()
m = re.search(r"const DATA = \[.*?\];", src, re.S)
data_end = m.end() if m else 0
print(f"源文件 {len(src):,} 字符；DATA 结束位置 {data_end:,}")

fmt_count = collections.Counter()
for mm in re.finditer(r"data:image/(\w+);base64,([A-Za-z0-9+/=]+)", src):
    fmt_count[mm.group(1)] += 1
print("图片格式分布:", dict(fmt_count))

stats = {"single": 0, "piece": 0}
orig_bytes = 0
new_bytes = 0


def process(match):
    global orig_bytes, new_bytes
    ext, b64 = match.group(1), match.group(2)
    # 按位置判定用途：DATA 区间内 = 单品图，区间外 = 套餐构件图
    kind = "single" if match.start() < data_end else "piece"
    if kind == "single":
        max_w, q = 100, 58
    else:
        max_w, q = 76, 54
    raw = base64.b64decode(b64)
    orig_bytes += len(raw)
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
        if im.mode in ("RGBA", "LA", "P"):
            # 带透明通道：合成到白底再转 JPEG（避免黑底）
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        if im.width > max_w:
            h = max(1, int(im.height * max_w / im.width))
            im = im.resize((max_w, h), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        out = base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        print("  跳过一张（解码失败）:", str(e)[:50])
        return match.group(0)
    new_bytes += len(raw) - len(out)
    stats[kind] += 1
    return f"data:image/jpeg;base64,{out}"


print("开始压缩图片……")
out_html = re.sub(r"data:image/(\w+);base64,([A-Za-z0-9+/=]+)",
                   lambda mm: process(mm), src)

# --- lite 版标识与入口提示 ---
out_html = out_html.replace(
    "<title>",
    "<title>麦当劳点餐测算 · 轻量版（秒开）| ", 1)

LITE_BAR = (
    '<div style="background:#fff3cd;border-bottom:2px solid #e3d9c3;'
    'padding:9px 14px;text-align:center;font-size:13px;color:#4a4034;line-height:1.6">'
    '⚡ <b>轻量版</b>：964KB 秒开，手机流量也扛得住，商品图是缩略图。'
    '想要高清大图与素材审阅台，请开 '
    '<a href="demo.html" style="color:#DA291C;font-weight:700">完整版</a>'
    ' · <a href="https://github.com/erikzeng2008-del/mcd-dual-budget-coach" '
    'style="color:#DA291C;font-weight:700">GitHub 源码</a>'
    '<div style="margin-top:7px;font-size:12.5px;color:#4a4034">'
    '🏆 在参加麦当劳开发者大赛，<b>排名只看 GitHub Star 数</b>——'
    '<a href="https://github.com/erikzeng2008-del/mcd-dual-budget-coach" '
    'target="_blank" rel="noopener" '
    'style="display:inline-block;margin-left:6px;background:#FFC72C;color:#1a1a1a;'
    'font-weight:800;padding:5px 14px;border-radius:999px;'
    'border:2px solid #1a1a1a;text-decoration:none">⭐ 点一下 Star</a>'
    '</div></div>'
)
out_html = out_html.replace("<body>", "<body>\n" + LITE_BAR, 1)

print(f"压缩完成：单品图 {stats['single']} 张，构件图 {stats['piece']} 张")
print(f"图片净减 {orig_bytes/1024/1024:.1f}MB")
print(f"lite.html 体积 {len(out_html.encode('utf-8'))/1024:.0f} KB")
open(OUT, "w", encoding="utf-8").write(out_html)
print("已写入", OUT)
