# -*- coding: utf-8 -*-
"""make_font.py —— 把霞鶩文楷（LXGW WenKai Regular）子集化為自託管 woff2。

字型來源：
  D:\\Wu\\NetDisk Download\\lxgw-wenkai-v1.530\\lxgw-wenkai-v1.530\\LXGWWenKai-Regular.ttf

**三片策略（與韻圖站一致）**
  fonts/wk-ui.woff2      首屏字集：介面文字（三語，含日文假名）＋規則表＋統計＋示例
  fonts/wk-dict.woff2    字典字集：字音站全部單字（含四種參考方言）
  fonts/wk-ext.woff2     完整字集：霞鶩文楷在 CJK 區段的全部字形，最後回退，平時不下載

**字集必須從「頁面實際用到的字」收集**，不能只從字典收集 ——
否則介面裡的日文假名、日文專用漢字會整片缺失（這正是上一版的 bug）。

每片宣告「精確 unicode-range」（由自己 cmap 壓縮而成），
瀏覽器遇到字型沒有的字會直接回退系統字型，不會白下載。

輸出 fonts/fontface.css（由 build_html.py 內嵌進 index.html）
     fonts/font_report.json（覆蓋率報告）
"""
from __future__ import annotations

import json
import os
import re
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

#: 完整字集只取 CJK 及相關區段（拉丁／音標／假名已在 ui 片）
EXT_MIN_CP = 0x2E80

#: 介面一定會用到、但可能不在任何資料檔裡的字（保險起見硬列）
EXTRA_UI = (
    "吳語拼音轉換器蘇滬混合腔吳語字音查詢韻圖位置標記來自"
    "輸入漢字輸出不自行推導支援繁體與簡體標點換行會切分句子"
    "轉換清空複製結果全文全部漢語日本語"
    "已自動分詞下方便是實際的分詞結果拖動小豎槓可移動右鍵刪除點字與之間新增"
    "正在讀取字音站資料就緒與同步無法請檢查網路後重新整理"
    "請先輸入漢字沒有可的內容此字在未收錄簡體對應藍色為多音字或繁體候選點擊選擇其他讀音紅色該方言"
    "規則說明例子詞內連寫以單位音節詞與空格分隔首陰平調在前加小撇聲母後韻母只在隻其餘調類一律標字元用句大寫無論它有"
    "資料統計單字讀音小韻多簡繁對"
    "白相去雞排作興美好蠻兒戲人民風煙俱淨天山共色儂我伲"
    "帶調拼音文湖韻處理混合默認走河"
    "清末蘇州話上海評彈參考各自獨立互不混用原樣取"
    "一二三四五六七八九十百千萬億零年月日時分秒"
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    "，。！？；：、（）「」『』《》…—·／％＃＠＆＊＋－＝＜＞"
    "'\"()[]{}<>=+-*/%&@#!?.,;:·—…｜"
    # 日文（介面文案全部假名＋常用漢字）
    "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
    "がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽっゃゅょゎ"
    "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
    "ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポッャュョヮヴ"
    "ー・〜、。「」（）"
    "漢字入力変換結果声調数字正書法規則説明例語内連写単位間区切前付声母後韻母一他調類切文頭大文字多音字青色表示既定読示"
    "呉越共通語蘇州語上海評弾清末参考方言独立字音対象繁体簡体句読点改行文切"
    "読込中準備完了取得確認再読込未収録赤字複数候補選択他"
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


# ---------------------------------------------------------------- 字集收集
def collect_ui_chars():
    """首屏字集：介面文字。
    直接掃 build_html.py 裡的 CSS/JS/HTML 字串，把所有出現的字元收進來，
    這樣介面（含三語文案）改了以後重跑本腳本就會自動跟上。"""
    chars = set(EXTRA_UI)
    chars |= set(chr(c) for c in range(0x20, 0x7F))          # 基本拉丁
    src = os.path.join(HERE, "build_html.py")
    if os.path.exists(src):
        text = open(src, encoding="utf-8").read()
        # 收所有字面量裡的 CJK／假名／標點
        for ch in text:
            o = ord(ch)
            if (0x2E80 <= o <= 0x9FFF or 0x3000 <= o <= 0x303F
                    or 0xFF00 <= o <= 0xFFEF or 0x3040 <= o <= 0x30FF
                    or 0x0400 <= o <= 0x04FF or 0x2000 <= o <= 0x206F
                    or 0x00A0 <= o <= 0x00FF or 0x0100 <= o <= 0x017F
                    or 0x0250 <= o <= 0x02FF or 0x1D00 <= o <= 0x1D7F
                    or 0x20A0 <= o <= 0x20CF or 0x2190 <= o <= 0x21FF
                    or 0x2200 <= o <= 0x22FF or 0x25A0 <= o <= 0x25FF):
                chars.add(ch)
    return chars


def collect_dict_chars():
    """字典字集：本站字典 + 四種參考方言的全部單字。"""
    chars = set()
    for name, key in (("dict.json", "chars"),
                      ("dialect_qingmo.json", "chars"),
                      ("dialect_suzhou.json", "chars"),
                      ("dialect_shanghai.json", "chars"),
                      ("dialect_pingtan.json", "chars")):
        p = os.path.join(DATA, name)
        if not os.path.exists(p):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        chars |= set((d.get(key) or {}).keys())
    # 簡繁對照裡的繁體字也要
    p = os.path.join(DATA, "dict.json")
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        for ts in (d.get("s2t") or {}).values():
            chars |= set(ts)
    # 字典裡有多字詞條（如何、如何然），cmap 只能查單字
    return {c for c in chars if isinstance(c, str) and len(c) == 1}


def subset_to(chars, dest, label):
    chars = {c for c in chars if c and c.strip()}
    tmp = os.path.join(OUT, "_tmp.txt")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("".join(sorted(chars)))
    args = list(BASE_ARGS) + [f"--text-file={tmp}", f"--output-file={dest}", SRC]
    subset.main(args)
    os.remove(tmp)
    cps = cmap_codepoints(dest)
    print(f"  {label}: 輸入 {len(chars):5d} 字 → {os.path.basename(dest)} "
          f"{os.path.getsize(dest)/1024/1024:5.2f} MB, {len(cps):5d} 碼位")
    return cps


def main():
    if not os.path.exists(SRC):
        sys.exit("找不到源字體：" + SRC)
    os.makedirs(OUT, exist_ok=True)

    print("· 收集字集")
    ui = collect_ui_chars()
    dic = collect_dict_chars()
    src_cmap = cmap_codepoints(SRC)
    print(f"  首屏字集 {len(ui)} 字｜字典字集 {len(dic)} 字｜源字體 {len(src_cmap)} 碼位")

    print("· 子集化")
    ui_cps = subset_to(ui, os.path.join(OUT, "wk-ui.woff2"), "首屏")
    dict_only = dic - {chr(c) for c in ui_cps}
    dict_cps = subset_to(dict_only, os.path.join(OUT, "wk-dict.woff2"), "字典")

    # 完整回退片：源字體 CJK 區段全部字形（不扣除前兩片，改介面時不必重跑）
    ext_cps_src = sorted(c for c in src_cmap if c >= EXT_MIN_CP)
    ext_arg = ",".join("U+%04X" % c for c in ext_cps_src)
    print(f"  完整回退: 源字體 CJK 區段 {len(ext_cps_src)} 碼位（約需 2-3 分鐘）")
    args = list(BASE_ARGS) + ["--unicodes=" + ext_arg,
                              "--output-file=" + os.path.join(OUT, "wk-ext.woff2"), SRC]
    subset.main(args)
    ext_cps = cmap_codepoints(os.path.join(OUT, "wk-ext.woff2"))
    print(f"  wk-ext.woff2 {os.path.getsize(os.path.join(OUT,'wk-ext.woff2'))/1024/1024:5.2f} MB, "
          f"{len(ext_cps)} 碼位")

    # ---- 覆蓋率自檢 ----
    print("· 覆蓋率自檢")
    covered = ui_cps | dict_cps
    # 只保留單一字元（字典裡有多字詞條，不能拿來查 cmap）
    page_chars = {c for c in (ui | dic) if isinstance(c, str) and len(c) == 1}
    need = {c for c in page_chars if ord(c) in src_cmap}
    missing = sorted(c for c in need if ord(c) not in covered and ord(c) < EXT_MIN_CP)
    print(f"  頁面需要且源字體有 {len(need)} 字；前兩片未覆蓋（非 CJK）{len(missing)} 個")
    if missing:
        print("    !! 未覆蓋：", "".join(missing[:40]))
    gone = sorted(c for c in page_chars if ord(c) not in src_cmap)
    print(f"  源字體本身沒有 {len(gone)} 字" + (("：" + "".join(gone[:20])) if gone else ""))

    # 關鍵字元專項檢查
    kana = [chr(c) for c in range(0x3040, 0x3100)]
    have_kana = [k for k in kana if ord(k) in ui_cps]
    print(f"  日文假名覆蓋：{len(have_kana)}/{len(kana)}")
    apos = 0x27
    print(f"  U+0027 小撇：{'在 wk-ui ✓' if apos in ui_cps else '缺失 ✗'}"
          f"（三語共用同一片字型）")

    # ---- fontface.css ----
    css = []
    for name, cps, fam in (
        ("wk-ui", ui_cps, "LXGW WenKai"),
        ("wk-dict", dict_cps, "LXGW WenKai"),
        ("wk-ext", ext_cps, "LXGW WenKai Fallback"),
    ):
        rng = ",".join(compact_ranges(cps))
        css.append(
            '@font-face{font-family:"%s";font-style:normal;font-weight:400;'
            'font-display:swap;'
            'src:local("LXGW WenKai"),local("霞鶩文楷"),url("fonts/%s.woff2") format("woff2");'
            'unicode-range:%s}' % (fam, name, rng)
        )
    css_text = "\n".join(css)
    with open(os.path.join(OUT, "fontface.css"), "w", encoding="utf-8") as f:
        f.write(css_text)

    report = {
        "ui": {"chars": len(ui), "codepoints": len(ui_cps),
               "mb": round(os.path.getsize(os.path.join(OUT, "wk-ui.woff2"))/1048576, 2)},
        "dict": {"chars": len(dict_only), "codepoints": len(dict_cps),
                 "mb": round(os.path.getsize(os.path.join(OUT, "wk-dict.woff2"))/1048576, 2)},
        "ext": {"codepoints": len(ext_cps),
                "mb": round(os.path.getsize(os.path.join(OUT, "wk-ext.woff2"))/1048576, 2)},
        "kana": f"{len(have_kana)}/{len(kana)}",
        "missing": "".join(missing[:200]),
    }
    json.dump(report, open(os.path.join(OUT, "font_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("  完成，報告寫入 fonts/font_report.json")
    print(f"  總計 {report['ui']['mb']+report['dict']['mb']+report['ext']['mb']:.2f} MB")


if __name__ == "__main__":
    main()
