# -*- coding: utf-8 -*-
"""AI 抠图批处理（u2net / ONNX Runtime，本地 CPU）
要点：
- 等比缩放 + 居中 padding 到 320×320 → **不破坏原始比例**
- min-max 归一化 → 软 alpha（保留毛边/反光）
- 只去底，不裁切商品本身
用法：python ai_cutout.py [输入目录] [输出目录]
"""
import os
import sys
import time

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, r"F:\mcd_tools\pylibs")
import onnxruntime as ort  # noqa: E402

MODEL = r"C:\Users\erikz\.rembg\models\u2net\u2net.onnx"
SIZE = 320
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def get_session():
    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    so.intra_op_num_threads = 4
    return ort.InferenceSession(MODEL, sess_options=so, providers=["CPUExecutionProvider"])


def cutout(session, img):
    """img: PIL RGBA -> RGBA（透明底）"""
    W, H = img.size
    scale = min(SIZE / W, SIZE / H)
    nw, nh = max(1, int(round(W * scale))), max(1, int(round(H * scale)))
    small = img.convert("RGB").resize((nw, nh), Image.LANCZOS)
    # 居中 padding
    canvas = Image.new("RGB", (SIZE, SIZE), (255, 255, 255))
    ox, oy = (SIZE - nw) // 2, (SIZE - nh) // 2
    canvas.paste(small, (ox, oy))
    x = np.asarray(canvas, dtype=np.float32) / 255.0
    x = (x - MEAN) / STD
    x = x.transpose(2, 0, 1)[None, ...]
    out = session.run(None, {session.get_inputs()[0].name: x})[0][0, 0]
    # min-max 归一化
    o_min, o_max = float(out.min()), float(out.max())
    pred = (out - o_min) / (o_max - o_min) if o_max > o_min else out
    # 去掉 padding 区域（pad 处预测为 0，无所谓），缩回原图
    mask = Image.fromarray((pred * 255).astype(np.uint8), "L")
    mask = mask.resize((nw, nh), Image.LANCZOS)
    mask = mask.filter(ImageFilter.GaussianBlur(0.6))
    full = Image.new("L", (W, H), 0)
    full.paste(mask, (ox, oy))
    # 轻微对比拉伸：把 0.35~0.65 区间压掉，让边缘更干净
    a = np.asarray(full, dtype=np.float32) / 255.0
    a = np.clip((a - 0.30) / 0.55, 0, 1)
    full = Image.fromarray((a * 255).astype(np.uint8), "L")
    rgba = img.convert("RGBA")
    rgba.putalpha(full)
    return rgba


def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else r"F:\WorkBuddy默认工作空间存储\2026-10-09-15-17-04\mcd-dual-budget-coach\demo-assets"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else r"F:\mcd_tools\cutouts"
    os.makedirs(out_dir, exist_ok=True)
    files = sorted([f for f in os.listdir(src_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
    sess = get_session()
    t0 = time.time()
    for i, f in enumerate(files, 1):
        dst = os.path.join(out_dir, os.path.splitext(f)[0] + ".png")
        if os.path.exists(dst):
            continue
        try:
            im = Image.open(os.path.join(src_dir, f))
            out = cutout(sess, im)
            out.save(dst, "PNG", optimize=True)
            if i % 10 == 0 or i == len(files):
                print("  %d/%d  %.1fs" % (i, len(files), time.time() - t0), flush=True)
        except Exception as e:
            print("  ✗ %s: %s" % (f, e))
    print("完成 %d 张，用时 %.1fs（均 %.2fs/张）-> %s"
          % (len(files), time.time() - t0, (time.time() - t0) / max(len(files), 1), out_dir))


if __name__ == "__main__":
    main()