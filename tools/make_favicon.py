# -*- coding: utf-8 -*-
"""make_favicon.py —— 把字音查詢站的圖示搬到本頁（與韻圖站完全同一做法）。

字音查詢站的 favicon 是**內嵌在 HTML 裡的 base64 ICO**（256×256），沒有獨立檔案可抓，
所以這裡從它的首頁把那段 base64 解出來，再切成：

    favicon.ico             16／32／48／64 四種尺寸（瀏覽器分頁圖示）
    apple-touch-icon.png    180×180（iOS 加到主畫面用）

這樣本站的標誌與字音站、韻圖站**完全一致**（同一張源圖）。

執行（需要 Pillow）：
    python tools/make_favicon.py
"""
from __future__ import annotations

import base64
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SRC = "https://siqyin.github.io/wugniu_zyinzozin/"
UA = "Mozilla/5.0 (compatible; wugniu_tsoewoe icon sync)"
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64)]
TOUCH = 180


def main():
    print("· 抓取字音站首頁…", SRC)
    req = urllib.request.Request(SRC, headers={"User-Agent": UA})
    page = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")

    raw = None
    m = re.search(r'<link[^>]+rel="icon"[^>]*base64,([A-Za-z0-9+/=]+)', page)
    if m:
        raw = base64.b64decode(m.group(1))
        print("· 找到內嵌 base64 圖示")
    else:
        m2 = re.search(r'<link[^>]+rel="icon"[^>]+href="([^"]+)"', page)
        if m2:
            url = m2.group(1)
            if url.startswith("data:"):
                raw = base64.b64decode(url.split("base64,")[-1])
            else:
                if not url.startswith("http"):
                    url = SRC.rstrip("/") + "/" + url.lstrip("./")
                print("· 抓取獨立圖示檔…", url)
                raw = urllib.request.urlopen(
                    urllib.request.Request(url, headers={"User-Agent": UA}),
                    timeout=60).read()
    if raw is None:
        print("!! 字音站首頁找不到 favicon，可能改版了")
        sys.exit(1)

    tmp = os.path.join(ROOT, "__icon_src.ico")
    with open(tmp, "wb") as f:
        f.write(raw)

    try:
        from PIL import Image
    except ImportError:
        print("!! 需要 Pillow：pip install pillow")
        sys.exit(1)

    im = Image.open(tmp).convert("RGBA")
    print(f"· 來源圖 {im.size[0]}×{im.size[1]}")

    im.save(os.path.join(ROOT, "favicon.ico"), sizes=ICO_SIZES)
    im.resize((TOUCH, TOUCH), Image.LANCZOS).save(
        os.path.join(ROOT, "apple-touch-icon.png"))
    os.remove(tmp)

    for name in ("favicon.ico", "apple-touch-icon.png"):
        p = os.path.join(ROOT, name)
        print(f"  {name:22s} {os.path.getsize(p):6d} bytes")
    print("完成（與字音站、韻圖站同一張圖）")


if __name__ == "__main__":
    main()
