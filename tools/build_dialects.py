# -*- coding: utf-8 -*-
"""build_dialects.py —— 產生四種參考方言的資料檔（清末蘇州話／蘇州話／上海話／蘇州評彈）。

**不自行推導**：四種方言的字表全部原樣取自字音站
  https://siqyin.github.io/wugniu_zyinzozin/data/DB_qingmo.json   清末蘇州話
  https://siqyin.github.io/wugniu_zyinzozin/data/DB_suzhou.json   蘇州話
  https://siqyin.github.io/wugniu_zyinzozin/data/DB_shanghai.json 上海話
  https://siqyin.github.io/wugniu_zyinzozin/data/DB_pingtan.json  蘇州評彈

這四種的 meaning 格式是 [音標含調號, 註記]（兩條），與蘇滬混合腔的三條不同，
所以原樣保留音標，不做任何音系轉換。

輸出（每種方言一個檔，避免一次載入全部）：
  data/dialect_qingmo.json
  data/dialect_suzhou.json
  data/dialect_shanghai.json
  data/dialect_pingtan.json

格式：
  {"code":"qingmo", "name":"清末蘇州話",
   "chars": {"字": [["音標","註記"], ...]}, "count": N}
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

#: (代碼, 顯示名, 來源檔, 輸出檔)
DIALECTS = [
    ("qingmo",   "清末蘇州話", "DB_qingmo.json",   "dialect_qingmo.json"),
    ("suzhou",   "蘇州話",     "DB_suzhou.json",   "dialect_suzhou.json"),
    ("shanghai", "上海話",     "DB_shanghai.json", "dialect_shanghai.json"),
    ("pingtan",  "蘇州評彈",   "DB_pingtan.json",  "dialect_pingtan.json"),
]


def main():
    ok = True
    summary = []
    for code, name, src, dst in DIALECTS:
        path = os.path.join(DATA, src)
        if not os.path.exists(path):
            print(f"!! 缺少 {src}，請先跑 tools/update_from_upstream.py")
            ok = False
            continue
        with open(path, encoding="utf-8") as f:
            db = json.load(f)

        chars = {}
        entries = 0
        for rec in db:
            ch = rec.get("character")
            if not ch:
                continue
            bucket = chars.setdefault(ch, [])
            for m in rec.get("meaning") or []:
                if not m:
                    continue
                ipa = m[0] if len(m) > 0 else ""
                note = m[1] if len(m) > 1 else ""
                if not ipa:
                    continue
                item = [ipa, note or ""]
                if item not in bucket:
                    bucket.append(item)
                    entries += 1

        out = {"code": code, "name": name, "chars": chars,
               "count": len(chars), "readings": entries}
        with open(os.path.join(DATA, dst), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

        summary.append((code, name, len(chars), entries,
                        os.path.getsize(os.path.join(DATA, dst))))

    print("四種參考方言（原樣取自字音站，不推導）：")
    for code, name, n, r, size in summary:
        print(f"  {name:8s} [{code:8s}] 收字 {n:5d}  讀音 {r:5d}  {size/1024:7.0f} KB")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
