# -*- coding: utf-8 -*-
"""build_s2t.py —— 產生「簡體 → 繁體候選組」表 data/variants.json

設計依據：切韻音系推導器 convertArticle（src/options.tsx:75-135）
--------------------------------------------------------------------
它的做法是把「本字」與異體字一起查，按「輸出結果是否相同」歸併成組，
多組時用 TooltipChar 彈窗讓使用者挑（當前選中標藍、缺來源標紅）。

本專案以**繁體為標準形**，所以在此之上多一層判斷：
    · 繁體字輸入 → 直接輸出它自己
    · 簡體字輸入 → 折成對應繁體；一簡多繁時全部列為候選，前端標紅
    · **簡繁同形字**（面、後、里…本身既是繁體正字，又兼作簡體）→ 視同繁體，不折

「簡繁同形」是關鍵坑：例如「面」既是「面貌」的繁體正字，又是「麪/麵」的簡體。
若不加區分，「上面」會被誤折成「上麪」。判斷方法：本字在字音站字典裡**有獨立收錄**
且它的讀音與那些「繁體候選」不同 → 它是獨立正字，不折。

輸出 data/variants.json
----------------------
  {
    "s2t": {"发":["髮","發"], ...},      # 簡→繁候選（繁體在前）
    "noConvert": ["个"],                 # 吳語中另有其字的簡體形，固定不折
    "convertWords": {"个人":"個人",...},  # 詞級例外
    "traditional": {繁字:1,...},         # 標準繁體集合（用於判斷同形字）
    "sameForm": ["面","後",...]          # 簡繁同形字（不折）
  }
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")


def main():
    with open(os.path.join(DATA, "dict.json"), encoding="utf-8") as f:
        d = json.load(f)
    chars = d["chars"]
    raw_s2t = d["s2t"]

    with open(os.path.join(DATA, "rules.json"), encoding="utf-8") as f:
        rules = json.load(f)
    no_convert = set(rules.get("noConvert") or [])
    convert_words = rules.get("convertWords") or {}

    # ---------------------------------------------------------------- 判定「簡繁同形」
    # 這類字本身是獨立的繁體正字，同時又被當作某個異體字的簡體形。
    # 例如「面」：面貌的「面」是本字，而「麪／麵」是它的異體；
    # 若不加區分，「上面」會被誤折成「上麪」。
    #
    # ---------------------------------------------------------------- 判定「簡繁同形」
    # 規則：**一律折成繁體**（使用者要求「以繁體為標準」），
    # 只有極少數「本身即獨立正字、折了反而錯」的字例外，列在 SAME_FORM。
    #
    # 目前只有一個：「面」。
    #   · 簡體「面」= 麵條的 麵／麪（如「面條」「吃面」）
    #   · 但繁體「面」本身是面貌、方面、上面的「面」（如「上面」「面子」）
    #   若把「面」一律折成「麪」，「上面」就變成「上麪」，錯得離譜。
    #
    # 反面例子（**不列**）：「后／里／干／台」雖然也有獨立用法，但使用者輸入
    # 時多數是要「後／裏／乾／臺」，按規則應列為多候選並標紅讓使用者自己挑。
    SAME_FORM = {"面"}
    same_form = set()
    for simp in raw_s2t:
        if simp in chars and simp in SAME_FORM:
            same_form.add(simp)

    # ---------------------------------------------------------------- 候選組
    variants = {}
    stats = {"simp": 0, "multi": 0, "single": 0, "sameform": 0, "unusable": 0}

    for simp, targets in raw_s2t.items():
        stats["simp"] += 1
        if simp in no_convert:
            if simp in chars:
                variants[simp] = [simp]
            continue
        if simp in same_form:
            # 簡繁同形：直接用本字
            variants[simp] = [simp]
            stats["sameform"] += 1
            continue
        out, seen = [], set()
        for tr in targets:
            if tr != simp and tr in chars and tr not in seen:
                seen.add(tr)
                out.append(tr)
        if simp in chars and simp not in seen:
            seen.add(simp)
            out.append(simp)
        if not out:
            stats["unusable"] += 1
            continue
        variants[simp] = out
        if len(out) > 1:
            stats["multi"] += 1
        else:
            stats["single"] += 1

    # ---------------------------------------------------------------- 標準繁體集
    simp_selves = {s for s, v in variants.items() if v != [s]}
    traditional = {ch: 1 for ch in chars if ch not in simp_selves}

    out = {
        "s2t": variants,
        "noConvert": sorted(no_convert),
        "convertWords": convert_words,
        "traditional": traditional,
        "sameForm": sorted(same_form),
    }
    with open(os.path.join(DATA, "variants.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    print("簡體字總數        :", stats["simp"])
    print("  一簡一繁        :", stats["single"])
    print("  一簡多繁（標紅）  :", stats["multi"])
    print("  簡繁同形（不折）  :", stats["sameform"])
    print("  繁體候選皆無收錄  :", stats["unusable"])
    print("標準繁體字        :", len(traditional))
    print("不轉繁            :", sorted(no_convert))
    print("詞級例外          :", convert_words)

    print("\n=== 關鍵詞驗證 ===")
    for w, expect in [("上面", ["上", "面"]), ("在許", ["在", "許"]),
                      ("个人", ["个", "人"]), ("中文", ["中", "文"])]:
        got = [variants.get(c, [c]) for c in w]
        print(f"  {w}: " + " ".join(f"{c}→{'/'.join(g)}" for c, g in zip(w, got)))

    print("\n=== 一簡多繁示例 ===")
    shown = 0
    for simp, ts in variants.items():
        if len(ts) > 1:
            print(f"  {simp} → {' / '.join(ts)}")
            shown += 1
            if shown >= 10:
                break


if __name__ == "__main__":
    main()
