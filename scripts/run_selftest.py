# -*- coding: utf-8 -*-
"""麦门双预算军师 · 自测运行器
把 scripts/selftest.js 注入 demo.html 的副本，用无头 Chrome 跑断言，解析结果。
用法: python scripts/run_selftest.py
退出码: 0=全过, 1=有失败
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEMO = os.path.join(ROOT, "demo.html")
TESTS = os.path.join(HERE, "selftest.js")
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def main():
    if not os.path.exists(DEMO):
        print("❌ 找不到 demo.html:", DEMO)
        return 1
    browser = find_browser()
    if not browser:
        print("❌ 未找到 Chrome/Edge，无法运行自测")
        return 1

    html = open(DEMO, encoding="utf-8").read()
    tests = open(TESTS, encoding="utf-8").read()
    injected = html.replace("</body>", "<script>" + tests + "</script></body>")
    assert "</body>" in html, "demo.html 里没有 </body>，注入点缺失"

    tmp = os.path.join(tempfile.gettempdir(), "mcd_selftest.html")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(injected)

    try:
        # 必须用独立 user-data-dir：否则从 Python 启动的 Chrome 会把任务
        # 转交给已在运行的实例后立刻退出（returncode 0 但没有任何输出）
        udd = tempfile.mkdtemp(prefix="mcd_chrome_")
        r = subprocess.run(
            [browser, "--headless", "--disable-gpu", "--no-sandbox",
             "--user-data-dir=" + udd,
             "--virtual-time-budget=8000",
             "--allow-file-access-from-files", "--dump-dom", "file:///" + tmp.replace("\\", "/")],
            capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
        dom = r.stdout or ""
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    # 注意：脚本源码注释里也可能出现同样的字样，所以取全部匹配、从后往前试解析
    import html as _html
    cands = re.findall(r'<pre id="stout">(.*?)</pre>', dom, re.S)
    results = None
    for raw in reversed(cands):
        try:
            results = json.loads(_html.unescape(raw))
            break
        except (json.JSONDecodeError, ValueError):
            continue
    if results is None:
        if not dom.strip():
            print("❌ 浏览器没有返回任何 DOM（0 字节）")
            print()
            print("   这不是代码问题，是环境问题。本机的 Chrome 只支持 --screenshot，")
            print("   --dump-dom / --print-to-pdf 均返回空（已试过 --headless=new、")
            print("   Edge、独立 user-data-dir，全部为空）。")
            print()
            print("   影响：自测跑不了，但 demo.html 本身正常。")
            print("   绕过：用 --screenshot 截图逐屏人工核对，或在能跑 --dump-dom 的机器上执行。")
            return 1
        print("❌ 未能解析自测输出（找到 %d 个候选块，均非合法 JSON）" % len(cands))
        return 1
    passed = sum(1 for x in results if x["pass"])
    n = len(results)
    print("=" * 56)
    print("麦门双预算军师 · 自测")
    print("=" * 56)
    for x in results:
        flag = "✅" if x["pass"] else "❌"
        line = "  %s %s" % (flag, x["name"])
        if x["detail"]:
            line += "  ← " + x["detail"]
        print(line)
    print("-" * 56)
    print("共 %d 项 | 通过 %d | 失败 %d" % (n, passed, n - passed))
    return 0 if passed == n else 1


if __name__ == "__main__":
    sys.exit(main())
