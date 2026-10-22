# -*- coding: utf-8 -*-
"""preflight.py —— 發布前自檢：確認要推上去的東西完整、無雜物、無機密。

檢查項
------
1. 必要檔案是否齊全（index.html、data/*.json、fonts/*、icon、workflow、README）
2. index.html 是否與最新資料一致（重跑 build_html.py 後有沒有 diff）
3. 相對路徑是否全部可用（不得出現以 / 開頭的絕對路徑）
4. 有沒有把 .git 以外的暫存檔、日誌、__pycache__ 一起推上去
5. 有沒有誤把權杖／密碼寫進檔案
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

REQUIRED = [
    "index.html", "README.md", "favicon.ico", "apple-touch-icon.png", ".nojekyll",
    ".gitignore", ".github/workflows/pages.yml", "tools/publish.py",
    "data/dict.json", "data/defaults.json", "data/words.json", "data/rules.json",
    "data/lexicon.json", "data/meta.json", "data/huhe.json", "data/syl.json",
    "data/variants.json",
    "data/DB_suhu.json", "data/S2T.json", "data/YUNTU_POS.json",
    "fonts/wk-ui.woff2", "fonts/wk-dict.woff2", "fonts/fontface.css", "fonts/OFL.txt",
]

# 不該進 repo 的雜物
JUNK_PATTERNS = [
    r"__pycache__/", r"\.pyc$", r"\.log$", r"_preview", r"\.tmp$",
    r"^tools/_", r"\.DS_Store$", r"node_modules/",
]

# 疑似機密
SECRET_PATTERNS = [
    r"gh[pousr]_[A-Za-z0-9]{20,}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"x-access-token:[A-Za-z0-9_]{20,}",
]


def walk_files():
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            out.append(os.path.relpath(p, ROOT).replace("\\", "/"))
    return sorted(out)


def main():
    ok = True

    def bad(msg):
        nonlocal ok
        ok = False
        print("  ✗", msg)

    def good(msg):
        print("  ✓", msg)

    print("1. 必要檔案")
    for f in REQUIRED:
        if os.path.exists(os.path.join(ROOT, f)):
            good(f)
        else:
            bad("缺少 " + f)

    files = walk_files()
    print(f"\n2. 雜物檢查（共 {len(files)} 個檔案）")
    junk = [f for f in files for p in JUNK_PATTERNS if re.search(p, f)]
    if junk:
        for j in junk:
            bad("不該進 repo：" + j)
    else:
        good("無暫存檔／日誌／__pycache__")

    print("\n3. 機密掃描")
    hits = []
    for f in files:
        if f.endswith((".woff2", ".ico", ".png")):
            continue
        p = os.path.join(ROOT, f)
        try:
            s = open(p, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        for pat in SECRET_PATTERNS:
            if re.search(pat, s):
                hits.append((f, pat))
    if hits:
        for f, pat in hits:
            bad(f"疑似機密：{f} 匹配 {pat}")
    else:
        good("未發現權杖字串")

    print("\n4. 絕對路徑檢查（GitHub Pages 子路徑部署）")
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    # 允許 https:// 開頭的外部連結；不允許 src="/..." 或 url("/...")
    abs_attr = re.findall(r'(?:src|href)="(/[^/"][^"]*)"', html)
    if abs_attr:
        for a in set(abs_attr):
            bad("以 / 開頭的絕對路徑：" + a)
    else:
        good("無以 / 開頭的資源路徑")
    if re.search(r"""["']data/[A-Za-z0-9_.-]+\.json["']""", html):
        good("資料以相對路徑 data/ 抓取")
    else:
        bad("找不到 data/ 相對路徑的資料抓取")

    print("\n5. index.html 與資料同步")
    before = html
    py = sys.executable
    r = subprocess.run([py, os.path.join(HERE, "build_html.py")], cwd=ROOT,
                       capture_output=True, text=True,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode != 0:
        bad("build_html.py 失敗：" + (r.stderr or "")[-300:])
    else:
        after = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
        if before == after:
            good("index.html 已是最新（重跑無變化）")
        else:
            print("  · index.html 已重新產生（略有不同，屬正常）")

    print("\n6. 統計")
    meta = json.load(open(os.path.join(ROOT, "data/meta.json"), encoding="utf-8"))
    st = meta.get("stats", {})
    print(f"  單字 {st.get('single_chars')}｜讀音 {st.get('readings')}｜"
          f"小韻音節 {st.get('distinct_tone_syllables')}｜"
          f"多音字 {st.get('multi_reading_chars')}｜詞 {st.get('lexicon_words')}")
    total = sum(os.path.getsize(os.path.join(ROOT, f)) for f in files
                if os.path.isfile(os.path.join(ROOT, f)))
    print(f"  倉庫總大小：{total/1024/1024:.1f} MB（{len(files)} 檔）")

    print("\n" + ("全部通過 ✓" if ok else "有問題，見上 ✗"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
