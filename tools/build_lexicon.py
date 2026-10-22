# -*- coding: utf-8 -*-
"""build_lexicon.py —— 從蘇滬混合腔輸入法（wugniu_suwu）抽出分詞詞表。

為什麼不用普通話詞庫
--------------------
吳語的用詞和普通話差很遠（「我伲／我拉／渠拉」「白相」「作興」「弗」「箇」…）。
若拿搜狗詞庫（sougouciku）或 luna_pinyin 這種普通話詞庫來分詞，會把
「我伲」切成「我|伲」、「白相」切成「白|相」，拼音文連寫就全錯了。
所以本詞表**只收**輸入法自己認定的吳語詞，來源與
`dev/romazy/tools/build_romazy_dict.py` 的 `VOCAB_FILES` 完全一致：

  wuphin.word.dict.yaml     吳語詞      （我伲、我拉、渠拉、爾屬…）
  wuphin.map.dict.yaml      吳語地名    （上海、黃浦、南京東路…）
  wuphin.phrases.dict.yaml  吳語諺語    （白露身弗露、板板六十四…）

權重沿用 build_romazy_dict.py 的既定方案（該方案已用於線上輸入法）：
  單字       0
  word/map   min(10, 1 + 字數)
  phrase     min(20, 10 + 字數)

輸出 data/lexicon.json：
  {"words": {詞: 權重}, "maxLen": N, "total": N}
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

SRC = r"D:\Wu\Chrome\wugniu_suwu-main\wugniu_suwu-main"

VOCAB_FILES = (
    ("wuphin.word.dict.yaml", "word"),
    ("wuphin.map.dict.yaml", "map"),
    ("wuphin.phrases.dict.yaml", "phrase"),
)

CHAR_WEIGHT = 0
WORD_WEIGHT_BASE = 1
WORD_WEIGHT_MAX = 10
PHRASE_WEIGHT_BASE = 10
PHRASE_WEIGHT_MAX = 20
MAX_WORD_CHARS = 8


def read_rows(path):
    """讀 Rime 詞典 body，回傳 [(text, code)]。"""
    if not os.path.exists(path):
        print("  (missing)", path, file=sys.stderr)
        return []
    rows = []
    started = False
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            if not started:
                if line.strip() == "...":
                    started = True
                continue
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            text = parts[0].strip()
            if not text:
                continue
            code = parts[1].strip() if len(parts) > 1 else ""
            rows.append((text, code))
    return rows


def is_cjk(text):
    return all("\u3400" <= c <= "\u9fff" or "\uf900" <= c <= "\ufaff" for c in text)


def word_weight(category, text):
    if category == "phrase":
        return min(PHRASE_WEIGHT_MAX, PHRASE_WEIGHT_BASE + len(text))
    return min(WORD_WEIGHT_MAX, WORD_WEIGHT_BASE + len(text))


def main():
    with open(os.path.join(DATA, "dict.json"), encoding="utf-8") as f:
        d = json.load(f)
    chars = d["chars"]
    s2t = d["s2t"]

    def known(ch):
        return ch in chars or ch in s2t

    words = {}
    per_file = []
    dropped_charset = 0
    dropped_nonhan = 0

    for filename, category in VOCAB_FILES:
        rows = read_rows(os.path.join(SRC, filename))
        kept = 0
        for text, _code in rows:
            if not (2 <= len(text) <= MAX_WORD_CHARS):
                continue
            if not is_cjk(text):
                dropped_nonhan += 1
                continue
            # 每個字都必須在字音站的蘇滬混合腔字典裡查得到，否則分詞後算不出音
            if not all(known(c) for c in text):
                dropped_charset += 1
                continue
            w = word_weight(category, text)
            if text not in words or words[text] < w:
                words[text] = w
            kept += 1
        per_file.append((filename, category, len(rows), kept))

    # 把 rules.json 指定的補充詞加入分詞詞表（如 个人／个体／上面／在許）。
    # 這些詞可能不在輸入法詞庫，但必須能被切出來，詞內特例與繁簡例外才生效。
    rules_path = os.path.join(DATA, "rules.json")
    added = 0
    if os.path.exists(rules_path):
        with open(rules_path, encoding="utf-8") as f:
            rules = json.load(f)
        extra = list(rules.get("extraWords") or [])
        extra += list((rules.get("convertWords") or {}).keys())
        for w in extra:
            if len(w) < 2 or not all(known(c) for c in w):
                continue
            if w not in words:
                words[w] = WORD_WEIGHT_BASE + len(w)
                added += 1
    print(f"補充詞（來自 rules.json）: +{added}")

    max_len = max((len(w) for w in words), default=1)
    out = {"words": {w: v for w, v in sorted(words.items())}, "maxLen": max_len,
           "total": len(words)}
    with open(os.path.join(DATA, "lexicon.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    print("來源（只收吳語詞，不含普通話詞庫）：")
    for fn, cat, n, kept in per_file:
        print(f"  {fn:26s} [{cat:6s}] 讀入 {n:6d} → 收 {kept:6d}")
    print()
    print("去重後詞條 :", len(words))
    print("最長詞長   :", max_len)
    print("丟棄(字音站查無此字):", dropped_charset)
    print("丟棄(非漢字)        :", dropped_nonhan)
    print()
    print("吳語特色詞驗證：")
    for w in ["我伲", "我拉", "渠拉", "爾屬", "白相", "作興", "弗", "箇", "歡喜", "上海",
              "黃浦", "南京東路", "白露身弗露", "板板六十四", "我", "儂", "好"]:
        mark = "IN " if w in words else "-- "
        print(f"  {mark}{w}  {words.get(w, '')}")


if __name__ == "__main__":
    main()
