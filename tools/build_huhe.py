# -*- coding: utf-8 -*-
"""build_huhe.py —— 產出湖/河韻變體對照表 data/huhe.json

背景（使用者 2026-10-22 兩次更正）
----------------------------------
① 湖韻 u[uᵝ] 與河韻 ou[əuᵝ] **是同一個音位的兩個音值變體**，不是重複格位。
   除 pu/phu/mu/fu/vu 五個音節只有湖韻外，每個湖/河韻字都有對應的兩讀。
② **河湖韻按鈕的優先級高於逐字默認音**：
   逐字默認音、詞內特例等規則寫的是「原型」（dict.json 原樣，多為湖形 u），
   套用完規則之後，再依按鈕設定把音節規範化成湖形或河形。
   例：個 的默認原型是 ku5
       → 混合腔默認／全走河 → kou5
       → 全走湖          → ku5

三種取向
--------
  默認   零聲母 u 與 wu 走湖；其餘有變體的聲母（t th n l k kh g h ng ts tsh s z）走河
  全走湖 一律 u 形
  全走河 一律 ou 形（匣母 ghou 本就是河形；零聲母 ou）

輸出 data/huhe.json
-------------------
  toHu / toHe   音節（含調）→ 另一形的音節
  defaultHe     默認走河的聲母清單
  ipa           音節 → 音標（沿用 build_data 產生的 syl.json）
"""
from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

TONE = re.compile(r"^([a-z]+)([0-9]?)$")
INIS = ("tsh", "gh", "kh", "ng", "ph", "ts", "th", "p", "b", "m", "f", "v",
        "t", "d", "n", "l", "k", "g", "h", "s", "z")

DEFAULT_HE_INITIALS = ["t", "th", "n", "l", "k", "kh", "g", "h", "ng",
                       "ts", "tsh", "s", "z"]


def split(s):
    m = TONE.match(s or "")
    return (m.group(1), m.group(2)) if m else (None, None)


def initial_of(letters):
    for p in INIS:
        if letters.startswith(p):
            return p
    return ""


def main():
    with open(os.path.join(DATA, "dict.json"), encoding="utf-8") as f:
        d = json.load(f)
    with open(os.path.join(DATA, "syl.json"), encoding="utf-8") as f:
        syl_ipa = json.load(f)

    syllables = set()
    tones = set()
    for rs in d["chars"].values():
        for syl, _ipa, _note in rs:
            syllables.add(syl)
            t = split(syl)[1]
            if t:
                tones.add(t)

    # 只有湖韻、沒有河變體的聲母（脣音）——不建湖→河對應
    HU_ONLY = {"p", "ph", "b", "m", "f", "v"}
    # 有哪些聲母真的存在「湖／河」兩種形
    VAR_INITIALS = {"t", "th", "n", "l", "k", "kh", "g", "h", "ng",
                    "ts", "tsh", "s", "z"}

    to_hu, to_he = {}, {}

    for s_ in sorted(syllables):
        letters, tone = split(s_)
        if not (letters and tone):
            continue
        ini = initial_of(letters)
        tail = letters[len(ini):]

        if ini == "gh" and tail == "ou":
            # 匣母只有河形，湖形是濁零 wu
            to_hu[s_] = "wu" + tone
            to_he.setdefault("wu" + tone, s_)
        elif ini == "" and tail == "u":
            to_he[s_] = "ou" + tone
            to_hu.setdefault("ou" + tone, s_)
        elif ini == "" and tail == "ou":
            to_hu[s_] = "u" + tone
            to_he.setdefault("u" + tone, s_)
        elif ini in VAR_INITIALS and tail == "u":
            to_he[s_] = ini + "ou" + tone
            to_hu.setdefault(ini + "ou" + tone, s_)
        elif ini in VAR_INITIALS and tail == "ou":
            to_hu[s_] = ini + "u" + tone
            to_he.setdefault(ini + "u" + tone, s_)
        # 脣音（HU_ONLY）與其他聲母：不建湖/河對應，維持原樣

    # 補齊 wu ↔ ghou 與 u ↔ ou 的所有聲調
    for t in sorted(tones):
        to_he.setdefault("wu" + t, "ghou" + t)
        to_hu.setdefault("ghou" + t, "wu" + t)
        to_he.setdefault("u" + t, "ou" + t)
        to_hu.setdefault("ou" + t, "u" + t)

    out = {
        "toHu": to_hu,
        "toHe": to_he,
        "defaultHe": DEFAULT_HE_INITIALS,
        "ipa": syl_ipa,
    }
    with open(os.path.join(DATA, "huhe.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    print("湖→河:", len(to_he), "條 | 河→湖:", len(to_hu), "條")
    print("\n=== 關鍵對應檢查 ===")
    for s in ("ku5", "kou5", "tu1", "tou1", "wu2", "ghou2", "pu1", "u1", "ou1"):
        print(f"  {s:7s} 湖形={to_hu.get(s, '—'):7s} 河形={to_he.get(s, '—'):7s}")
    print("\n默認走河的聲母:", DEFAULT_HE_INITIALS)


if __name__ == "__main__":
    main()
