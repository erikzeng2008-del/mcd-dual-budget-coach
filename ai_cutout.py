# -*- coding: utf-8 -*-
"""AI 抠图批处理（RMBG-2.0 + 暗色残留清理，ONNX Runtime 本地 CPU）

为什么是这套组合（全部来自实测对比，四个模型都真跑过）：
- u2net：紫底/青底/黑块都清不掉——它把阴影直接判成前景
- RMBG-1.4：比 u2net 强，但黑底招牌图（如「巨无霸三件套」）会把整块面板+徽章留下
- BiRefNet：实测更差，灰底和招牌都保留
- RMBG-2.0：黑底招牌图抠得干干净净
- + 暗色残留清理：2.0 在部分图上（如「板烧鸡腿堡四件套」）仍留一条黑边，
  补一步「删掉与画面边框连通的暗色低饱和区域」即可——食物内部的暗部（牛肉饼等）被包裹不连边，安全

预处理铁律（RMBG 官方做法，照抄）：
  直接拉伸到 1024（不要 letterbox，留白会出残片）→ 归一化 (x-mean)/std
  → squeeze → min-max → 缩回原图尺寸（长宽比自动还原）
全程不裁切：只换 alpha 通道，商品一个像素不动。

用法：python ai_cutout.py [输入目录] [输出目录]
"""
import os
import sys
import time

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, r"F:\mcd_tools\pylibs")
import onnxruntime as ort  # noqa: E402
from scipy import ndimage  # noqa: E402

MODEL = r"F:\mcd_tools\models\rmbg20.onnx"   # RMBG-2.0
SIZE = 1024
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)

V_THR = 118        # 暗色残留：亮度上限
SAT_THR = 0.30     # 暗色残留：饱和上限
DILATE = 4         # 膨胀半径（吃掉阴影边缘的过渡带）


def get_session():
    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    so.intra_op_num_threads = 6
    return ort.InferenceSession(MODEL, sess_options=so, providers=["CPUExecutionProvider"])


def matte(session, img):
    im = np.asarray(img.convert("RGB").resize((SIZE, SIZE), Image.LANCZOS), dtype=np.float32) / 255.0
    x = ((im - MEAN) / STD).transpose(2, 0, 1)[None, ...].astype(np.float32)
    p = np.squeeze(session.run(None, {session.get_inputs()[0].name: x})[0]).astype(np.float32)
    if p.ndim == 3:
        p = p[0]
    pmin, pmax = float(p.min()), float(p.max())
    pred = (p - pmin) / (pmax - pmin) if pmax > pmin else p
    return Image.fromarray((np.clip(pred, 0, 1) * 255).astype(np.uint8), "L").resize(img.size, Image.LANCZOS)


def strip_dark_border(mask, rgb):
    """删掉「暗色低饱和 且 与画面边框连通」的区域。
    产品下方的阴影垫、黑底残留会消失；被食物包裹的暗部（牛肉饼/巧克力）不连边，安全。"""
    a = np.asarray(mask, dtype=np.float32) / 255.0
    r = rgb[:, :, 0].astype(int)
    g = rgb[:, :, 1].astype(int)
    b = rgb[:, :, 2].astype(int)
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = (mx - mn) / np.maximum(mx, 1)
    dark = (mx < V_THR) & (sat < SAT_THR)
    st = np.ones((3, 3), int)
    if DILATE:
        dark = ndimage.binary_dilation(dark, iterations=DILATE)
    lab, n = ndimage.label(dark, structure=st)
    if n:
        border_ids = set(lab[0, :].tolist()) | set(lab[-1, :].tolist()) \
            | set(lab[:, 0].tolist()) | set(lab[:, -1].tolist())
        border_ids.discard(0)
        a[np.isin(lab, list(border_ids))] = 0.0
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "L")


def cutout(session, img):
    rgb = np.array(img.convert("RGB"))
    mask = matte(session, img)
    mask = strip_dark_border(mask, rgb)
    mask = mask.filter(ImageFilter.GaussianBlur(0.4))
    res = img.convert("RGBA")
    res.putalpha(mask)
    return res


def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else \
        r"F:\WorkBuddy默认工作空间存储\2026-10-09-15-17-04\mcd-dual-budget-coach\demo-assets"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else r"F:\mcd_tools\cutouts"
    os.makedirs(out_dir, exist_ok=True)
    files = sorted([f for f in os.listdir(src_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
    sess = get_session()
    t0 = time.time()
    ok = 0
    for i, f in enumerate(files, 1):
        dst = os.path.join(out_dir, os.path.splitext(f)[0] + ".png")
        if os.path.exists(dst):
            continue
        try:
            cutout(sess, Image.open(os.path.join(src_dir, f))).save(dst, "PNG", optimize=True)
            ok += 1
            if i % 20 == 0 or i == len(files):
                print("  %d/%d  %.1fs" % (i, len(files), time.time() - t0), flush=True)
        except Exception as e:
            print("  x %s: %s" % (f, e))
    dt = time.time() - t0
    print("完成 %d/%d 张，用时 %.1fs（均 %.2fs/张）-> %s"
          % (ok, len(files), dt, dt / max(ok, 1), out_dir))


if __name__ == "__main__":
    main()