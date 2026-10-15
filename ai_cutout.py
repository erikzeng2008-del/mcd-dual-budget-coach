# -*- coding: utf-8 -*-
"""AI 抠图批处理（RMBG-1.4 / ONNX Runtime，本地 CPU）

要点（都来自实测踩坑）：
- 预处理必须按 RMBG 官方做法：**直接拉伸到 1024×1024**（不要 letterbox 留白，letterbox 会出残片）
- 归一化是 (x - 0.5) / 1.0（不是 u2net 的 mean/std 那套）
- 输出 min-max 归一化后**缩回原图尺寸** → 长宽比自动还原，商品永不变形
- 全程不裁切：只把 alpha 通道换掉，商品一个像素不动

用法：python ai_cutout.py [输入目录] [输出目录]
"""
import os
import sys
import time

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, r"F:\mcd_tools\pylibs")
import onnxruntime as ort  # noqa: E402

MODEL = r"F:\mcd_tools\models\rmbg14.onnx"   # RMBG-1.4，商品图专精
SIZE = 1024
MEAN = 0.5
STD = 1.0


def get_session():
    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    so.intra_op_num_threads = 6
    return ort.InferenceSession(MODEL, sess_options=so, providers=["CPUExecutionProvider"])


def cutout(session, img):
    im = np.asarray(img.convert("RGB").resize((SIZE, SIZE), Image.LANCZOS), dtype=np.float32) / 255.0
    x = ((im - MEAN) / STD).transpose(2, 0, 1)[None, ...].astype(np.float32)
    out = session.run(None, {session.get_inputs()[0].name: x})[0]
    p = np.squeeze(out).astype(np.float32)
    if p.ndim == 3:
        p = p[0]
    pmin, pmax = float(p.min()), float(p.max())
    pred = (p - pmin) / (pmax - pmin) if pmax > pmin else p
    mask = Image.fromarray((np.clip(pred, 0, 1) * 255).astype(np.uint8), "L")
    mask = mask.resize(img.size, Image.LANCZOS)
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
            im = Image.open(os.path.join(src_dir, f))
            cutout(sess, im).save(dst, "PNG", optimize=True)
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