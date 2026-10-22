# -*- coding: utf-8 -*-
"""make_font.py —— 把霞鶩文楷（LXGW WenKai Regular）子集化為自託管 woff2。

字型來源：使用者指定
  D:\\Wu\\NetDisk Download\\lxgw-wenkai-v1.530\\lxgw-wenkai-v1.530\\LXGWWenKai-Regular.ttf

分兩級（與韻圖站同一套策略）：
  fonts/wk-ui.woff2    首屏字集：介面文字＋規則表＋統計標籤＋常用示例字
  fonts/wk-dict.woff2  字典字集：字音站 8199 個單字 + 簡繁對照的繁體字

每個檔案的 unicode-range 由它自己 cmap 裡真實存在的碼位壓縮而成（精確 range），
這樣瀏覽器遇到字型沒有的字會立刻回退到系統字型，不會白下載。

輸出 fonts/fontface.css（由 build_html.py 內嵌進 index.html）。
"""
from __future__ import annotations

import json
import os
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "fonts")

SRC = r"D:\Wu\NetDisk Download\lxgw-wenkai-v1.530\lxgw-wenkai-v1.530\LXGWWenKai-Regular.ttf"

BASE_ARGS = [
    "--flavor=woff2", "--no-hinting", "--desubroutinize", "--layout-features=",
    "--drop-tables+=GSUB,GPOS,GDEF,BASE,JSTF,vhea,vmtx,VORG,DSIG,mort,kerx,ankr,trak,kern,opbd,prop",
    "--notdef-outline", "--recalc-bounds",
]

# 介面固定會用到的字（三語 + 規則表 + 提示），直接硬列，保證首屏不缺字
UI_TEXT = (
    "蘇滬混合腔拼音轉換器吳語字音查詢韻圖位置標記來自"
    "輸入漢字輸出不自行推導支援繁體與簡體標點換行會切分句子"
    "轉換清空複製結果漢語日本語English"
    "已自動分詞下方便是實際的分詞結果點兩字之間的金色小豎槓可切開合併詞按這個連寫"
    "正在讀取字音站資料就緒與同步無法請檢查網路後重新整理"
    "請先輸入漢字沒有可的內容此字在未收錄簡體對應紅為多音字點擊選擇其他讀音"
    "規則說明例子詞內以單位詞與空格分隔首陰平調在音節前加小撇聲母後韻母只在隻其餘調類一律標字元用句大寫無論它有"
    "資料統計單字讀音小韻音節多簡繁對"
    "白相去雞排作興美好蠻兒戲人民風煙俱淨天山共色"
    "帶調拼音文"
    "載入中成功失敗重試"
    "一二三四五六七八九十百千萬億零年月日時分秒"
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    "，。！？；：、（）「」『』《》…—·／％＃＠＆＊＋－＝＜＞"
    "'\"()[]{}<>=+-*/%&@#!?.,;:·—…｜"
)


def cmap_codepoints(path):
    f = TTFont(path, lazy=True)
    cps = set()
    for t in f["cmap"].tables:
        cps |= set(t.cmap.keys())
    f.close()
    return cps


def compact_ranges(cps):
    cps = sorted(cps)
    out, i = [], 0
    while i < len(cps):
        j = i
        while j + 1 < len(cps) and cps[j + 1] == cps[j] + 1:
            j += 1
        out.append("U+%04X" % cps[i] if cps[i] == cps[j]
                   else "U+%04X-%04X" % (cps[i], cps[j]))
        i = j + 1
    return out


def subset_to(chars, dest, label):
    """把 chars 子集化成 woff2，回傳實際涵蓋的碼位集合。"""
    chars = {c for c in chars if c.strip()}
    text = "".join(sorted(chars))
    tmp = os.path.join(OUT, "_tmp.txt")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    args = list(BASE_ARGS) + [f"--text-file={tmp}", f"--output-file={dest}", SRC]
    subset.main(args)
    os.remove(tmp)
    cps = cmap_codepoints(dest)
    size = os.path.getsize(dest)
    print(f"  {label}: {len(chars)} chars -> {os.path.basename(dest)} "
          f"{size/1024:.0f} KB, {len(cps)} codepoints")
    return cps


def main():
    if not os.path.exists(SRC):
        sys.exit("font source not found: " + SRC)
    os.makedirs(OUT, exist_ok=True)

    print("reading dict for charset…")
    with open(os.path.join(DATA, "dict.json"), encoding="utf-8") as f:
        d = json.load(f)
    dict_chars = set(d["chars"].keys())
    for ts in d["s2t"].values():
        dict_chars.update(ts)

    ui_chars = set(UI_TEXT) | set("0123456789")
    # 首屏字集：介面文字 + 示例用字 + 基本拉丁與標點
    ui_chars |= set(chr(c) for c in range(0x20, 0x7F))

    print("subsetting…")
    ui_cps = subset_to(ui_chars, os.path.join(OUT, "wk-ui.woff2"), "ui  ")
    # 字典字集：字典裡的字，扣掉已在 ui 的
    dict_only = dict_chars - {chr(c) for c in ui_cps}
    dict_cps = subset_to(dict_only, os.path.join(OUT, "wk-dict.woff2"), "dict")

    css = []
    for name, cps in (("wk-ui", ui_cps), ("wk-dict", dict_cps)):
        rng = ",".join(compact_ranges(cps))
        css.append(
            '@font-face{font-family:"LXGW WenKai";font-style:normal;font-weight:400;'
            'font-display:swap;'
            'src:local("LXGW WenKai"),local("霞鶩文楷"),url("fonts/%s.woff2") format("woff2");'
            'unicode-range:%s}' % (name, rng)
        )
    css_text = "\n".join(css)
    with open(os.path.join(OUT, "fontface.css"), "w", encoding="utf-8") as f:
        f.write(css_text)
    print("  wrote fonts/fontface.css", len(css_text), "bytes")
    print("done.")


if __name__ == "__main__":
    main()
