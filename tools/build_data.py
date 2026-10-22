# -*- coding: utf-8 -*-
"""build_data.py —— 蘇滬混合腔拼音轉換器 · 資料構建

輸入（全部來自字音站 wugniu_zyinzozin，唯讀抓取）：
  data/DB_suhu.json   —— 蘇滬混合腔字音本體（繁體字為鍵）
  data/S2T.json       —— 簡→繁對照（{id,s,t:[繁...]}）
  data/YUNTU_POS.json —— 音節（含調）→ 韻圖位置串

輸出：
  data/dict.json      —— 緊湊字典，前端唯一需要抓的大檔
  data/lexicon.json   —— 分詞詞表（給拼音文的自動分詞用）
  data/meta.json      —— 版本戳／統計，給「與字音站聯動」的更新比對用

設計要點
--------
* **不推導字音**：本專案不內建任何音系規則去「算」一個字的讀音，
  純粹是把字音站的資料搬過來、按字聚合。字音站更新 → 重跑本腳本 → 跟著更新。
* 繁體字直接是 DB 的鍵；簡體字靠 S2T 展開，一個簡體字可能對應多個繁體
  （→ 前端按「多音字」的方式處理，讓使用者挑）。
* 只收單字條目；多字條目（如何／如何然／介兒）不進字典，但記在 meta 裡。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

# 音節 = 字母 + 可選聲調數字（1-8，沒有 4）
TONE_RE = re.compile(r"^(.*?)([0-9])$")
# 只認「一個字」的條目（排除「如何」「如何然」這種詞）
SINGLE_RE = re.compile(r"^.$", re.UNICODE)


def load(name):
    path = os.path.join(DATA, name)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha256_of(name):
    path = os.path.join(DATA, name)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    db = load("DB_suhu.json")
    s2t_records = load("S2T.json")
    positions = load("YUNTU_POS.json")

    # ---------------------------------------------------------------- 1. 繁體字 → 讀音表
    # readings[trad] = [[syllable, ipa, note], ...]  依 DB 原順序，去重
    readings = {}
    multi_char_entries = []
    untone = []          # 沒有聲調數字的讀音（ba / kha / don）
    skipped = []

    for rec in db:
        ch = rec["character"]
        if not SINGLE_RE.match(ch):
            multi_char_entries.append({"character": ch,
                                       "readings": [m[0] for m in rec["meaning"]]})
            continue
        bucket = readings.setdefault(ch, [])
        seen = {tuple(r) for r in bucket}
        for m in rec["meaning"]:
            syll, ipa = m[0], m[1]
            note = m[2] if len(m) > 2 and m[2] else ""
            key = (syll, ipa, note)
            if key in seen:
                continue
            seen.add(key)
            if TONE_RE.match(syll):
                bucket.append([syll, ipa, note])
            else:
                # 無調讀音：保留（使用者可能查得到），但不參與拼音文
                bucket.append([syll, ipa, note])
                untone.append([ch, syll])

    # ---------------------------------------------------------------- 2. 簡體 → 繁體候選
    # s2t[simp] = [trad, ...]（只保留「轉換結果在本字典查得到」的）
    s2t = {}
    s2t_full = {}
    for rec in s2t_records:
        src = rec["s"]
        targets = [t for t in rec["t"] if t != src]
        s2t_full[src] = targets
        usable = [t for t in targets if t in readings]
        if usable:
            s2t[src] = usable

    # ---------------------------------------------------------------- 3. 音節 → 韻圖位置
    # 位置表本身已按「音節（含調）」為鍵，直接沿用
    pos = {k: v for k, v in positions.items() if isinstance(v, str)}

    # ---------------------------------------------------------------- 4. 統計與校驗
    tone_syllables = {s for rs in readings.values() for s, _, _ in rs if TONE_RE.match(s)}
    base_syllables = {TONE_RE.match(s).group(1) for s in tone_syllables}
    missing_pos = sorted(tone_syllables - set(pos))
    orphan_pos = sorted(set(pos) - tone_syllables)

    multi_reading_chars = [ch for ch, rs in readings.items() if len(rs) > 1]
    simp_multi = {s: ts for s, ts in s2t.items() if len(ts) > 1}

    stats = {
        "records": len(db),
        "single_chars": len(readings),
        "multi_char_entries": len(multi_char_entries),
        "readings": sum(len(rs) for rs in readings.values()),
        "distinct_tone_syllables": len(tone_syllables),
        "distinct_base_syllables": len(base_syllables),
        "positions": len(pos),
        "multi_reading_chars": len(multi_reading_chars),
        "s2t_pairs": len(s2t),
        "s2t_multi": len(simp_multi),
        "untone": untone,
        "missing_pos": missing_pos,
        "orphan_pos": orphan_pos,
    }

    # ---------------------------------------------------------------- 4.5 音節 → 音標
    # 給「河湖韻處理」用：音節被規範化成湖形／河形之後，要能查到對應的音值。
    syl_ipa = {}
    for _ch, _rs in readings.items():
        for _syl, _ipa, _note in _rs:
            if _syl not in syl_ipa:
                syl_ipa[_syl] = _ipa

    # ---------------------------------------------------------------- 5. 輸出
    # dict.json：前端唯一大檔。用陣列而不是物件，省體積。
    #   chars: { 繁字: [[音節, 音標, 註記], ...] }
    #   s2t:   { 簡字: [繁字, ...] }
    #   pos:   { 音節: 位置 }
    out = {
        "chars": readings,
        "s2t": s2t,
        "pos": pos,
    }
    with open(os.path.join(DATA, "dict.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    with open(os.path.join(DATA, "syl.json"), "w", encoding="utf-8") as f:
        json.dump(syl_ipa, f, ensure_ascii=False, separators=(",", ":"))

    meta = {
        "source": "https://siqyin.github.io/wugniu_zyinzozin/",
        "db_url": "https://siqyin.github.io/wugniu_zyinzozin/data/DB_suhu.json",
        "db_sha256": sha256_of("DB_suhu.json"),
        "s2t_sha256": sha256_of("S2T.json"),
        "pos_sha256": sha256_of("YUNTU_POS.json"),
        "stats": stats,
    }
    # 詞表統計（若 build_lexicon.py 已跑過）
    lex_path = os.path.join(DATA, "lexicon.json")
    if os.path.exists(lex_path):
        with open(lex_path, encoding="utf-8") as f:
            lex = json.load(f)
        meta["stats"]["lexicon_words"] = lex.get("total", len(lex.get("words", {})))
    with open(os.path.join(DATA, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, separators=(",", ":"), indent=0)

    print("單字條目      :", stats["single_chars"])
    print("讀音條目      :", stats["readings"])
    print("小韻音節(帶調):", stats["distinct_tone_syllables"])
    print("不帶調音節    :", stats["distinct_base_syllables"])
    print("韻圖位置      :", stats["positions"])
    print("多音字        :", stats["multi_reading_chars"])
    print("簡→繁對（可用）:", stats["s2t_pairs"], "| 一簡多繁:", stats["s2t_multi"])
    print("無調讀音      :", untone)
    print("有音節無位置  :", len(missing_pos), missing_pos[:5])
    print("有位置無音節  :", len(orphan_pos), orphan_pos[:5])
    print("多字條目      :", [e["character"] for e in multi_char_entries])


if __name__ == "__main__":
    main()
