# -*- coding: utf-8 -*-
"""麦门拼单军师 · 自测运行器（party.html + selftest_party.js）
用法: python scripts/run_party_selftest.py [目标文件]   默认 party.html
退出码: 0=全过, 1=有失败
"""
import html as _html
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TESTS = os.path.join(HERE, "selftest_party.js")
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
    target = sys.argv[1] if len(sys.argv) > 1 else "party.html"
    demo = target if os.path.isabs(target) else os.path.join(ROOT, target)
    if not os.path.exists(demo):
        print("❌ 找不到目标文件:", demo)
        return 1
    browser = find_browser()
    if not browser:
        print("❌ 未找到 Chrome/Edge")
        return 1
    html = open(demo, encoding="utf-8").read()
    tests = open(TESTS, encoding="utf-8").read()
    assert "</body>" in html
    injected = html.replace("</body>", "<script>" + tests + "</script></body>")
    tmp = os.path.join(tempfile.gettempdir(), "mcd_party_selftest.html")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(injected)
    udd = tempfile.mkdtemp(prefix="mcd_party_chrome_")
    try:
        r = subprocess.run(
            [browser, "--headless", "--disable-gpu", "--no-sandbox",
             "--user-data-dir=" + udd, "--virtual-time-budget=9000",
             "--allow-file-access-from-files", "--dump-dom",
             "file:///" + tmp.replace("\\", "/")],
            capture_output=True, text=True, timeout=150, encoding="utf-8", errors="replace")
        dom = r.stdout or ""
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    results = None
    for raw in reversed(re.findall(r'<pre id="stout">(.*?)</pre>', dom, re.S)):
        try:
            results = json.loads(_html.unescape(raw))
            break
        except (json.JSONDecodeError, ValueError):
            continue
    if results is None:
        print("❌ 未能解析自测输出，DOM 长度", len(dom))
        print(dom[-2500:])
        return 1
    passed = sum(1 for x in results if x["pass"])
    print("=" * 60)
    print("麦门拼单军师 · 自测 · 目标: " + os.path.basename(demo))
    print("=" * 60)
    for x in results:
        print(("  ✅ " if x["pass"] else "  ❌ ") + x["name"]
              + (("  ← " + x["detail"]) if x["detail"] else ""))
    print("-" * 60)
    print("共 %d 项 | 通过 %d | 失败 %d" % (len(results), passed, len(results) - passed))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
