# -*- coding: utf-8 -*-
"""build_readings.py —— 決定「預設讀音」與「詞組既定讀音」

三層規則（使用者 2026-10-22 逐條拍板）
------------------------------------
① 逐字預設音（OVERRIDE）：多音字若無更精確的上下文，用這個音。
   其餘多音字沿用 DB 檔案順序的第一個音。
② 詞內特例（WORD_OVERRIDE）：某字在某個特定詞裡要改用指定讀音。
   優先於①。例如「白相」的白讀 beq8，而白單獨或其它詞裡讀 baq8。
③ 單字成詞特例（SINGLE_OVERRIDE）：某字被分詞成「單音節詞」時用指定讀音。
   優先於①但低於②。例如「在|我|該搭」的「在」讀 leq8，
   而在「在上／在許／在裏」等詞內讀 leq8（由②指定），
   在其它多字詞內讀 ze6（①的預設）。

另有不轉繁（NO_CONVERT）：某些簡體字不展開成繁體候選，
例如「个」固定作「个」，不轉「個／箇」；但「个人」「个体」例外，
要轉為「個人」「個體」（CONVERT_WORDS）。

**河湖韻優先級**：這裡寫的都是「原型」讀音（dict.json 原樣，多為湖形 u）。
前端會在套完本檔的規則之後，再依「河湖韻處理」按鈕做規範化，
所以河湖韻設定的優先級高於逐字默認音。例如「個」默認 ku5，
在混合腔默認取向顯示 kou5，全走湖韻則顯示 ku5。

輸出
----
  data/defaults.json  {"char": 首選音節}
  data/words.json     {"詞": [[syl,...], ...]}   詞組候選（第一條即既定讀音）
  data/readings.json  除錯用：每個多音字的候選與決策來源
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

ROM = r"D:\Wu\Chrome\wugniu_suwu-main\wugniu_suwu-main\wugniu_suwu_romazy.dict.yaml"

SYL_RE = re.compile(r"[a-z]+[0-9]?")

# ------------------------------------------------------------------ ① 逐字預設音
OVERRIDE = {
    "我": "ngu6",   # 使用者指定
    "儂": "non6",   # 使用者指定（DB 首音 non2）
    "渠": "yi2",    # 使用者指定（DB 首音 li1）
    "上": "laon6",  # 使用者指定：一般情況默認 laon6（DB 首音 zan6）
    "在": "ze6",    # 多字詞內默認（DB 首音已是 ze6，明寫以示鎖定）
    "箇": "geq8",   # 使用者指定（DB 首音已是 geq8，明寫鎖定）
    "个": "keq7",   # 使用者指定：个 默認 keq7，且一般情況不轉繁
    "個": "ku5",    # 使用者指定：個 默認 ku5（再經河湖韻規範化 → 混合腔默認顯示 kou5）
    "許": "shiu3",  # 一般情況默認（幾許／場許／裏許→ho5，在許→he3，見②）
}

# ------------------------------------------------------------------ ② 詞內特例
# {詞: {字: 讀音}}
WORD_OVERRIDE = {
    # 白：一般 baq8，「白相」讀 beq8
    "白相": {"白": "beq8"},

    # 許：幾許／場許／裏許 讀 ho5；在許 讀 he3；其餘 shiu3
    "幾許": {"許": "ho5"},
    "几许": {"許": "ho5"},
    "場許": {"許": "ho5"},
    "场许": {"許": "ho5"},
    "裏許": {"許": "ho5"},
    "裡許": {"許": "ho5"},
    "里许": {"許": "ho5"},
    "在許": {"許": "he3", "在": "leq8"},
    "在许": {"許": "he3", "在": "leq8"},

    # 上：上面／上邊／上去／上下 讀 zaon6；皇上 讀 zan6；在上 讀 laon6
    "上面": {"上": "zaon6"},
    "上邊": {"上": "zaon6"},
    "上边": {"上": "zaon6"},
    "上去": {"上": "zaon6"},
    "上下": {"上": "zaon6"},
    "皇上": {"上": "zan6"},
    "在上": {"上": "laon6", "在": "leq8"},

    # 在：在許／在上／在裏 讀 leq8
    "在裏": {"在": "leq8"},
    "在裡": {"在": "leq8"},
    "在里": {"在": "leq8"},

    # 个：只有「个人」「个体」轉繁為 個人／個體，且「个」讀 ku5
    "个人": {"个": "ku5"},
    "個人": {"个": "ku5"},
    "个体": {"个": "ku5"},
    "個體": {"个": "ku5"},
}

# ------------------------------------------------------------------ ③ 單字成詞特例
# 該字單獨成一個詞時用這個音（例如「在|我|該搭」）
SINGLE_OVERRIDE = {
    "在": "leq8",
}

# ------------------------------------------------------------------ 不轉繁
# 這些簡體字不展開成繁體候選，固定作本字。
# 「个」有例外：「个人」「个体」要轉成 個人／個體（見 CONVERT_WORDS）。
NO_CONVERT = {"个"}

# 例外詞：在這些詞裡，本該「不轉繁」的字仍要轉成對應繁體。
# {簡體詞: 繁體詞}
CONVERT_WORDS = {
    "个人": "個人",
    "个体": "個體",
}

# ------------------------------------------------------------------ 補充詞
# 詞庫裡沒有、但使用者明確要求要當成「一個詞」的條目（讓分詞與詞內特例生效）。
# 讀音由 WORD_OVERRIDE／逐字預設拼出，這裡只登記「這是一個詞」。
EXTRA_WORDS = [
    "幾許", "几许", "場許", "场许", "裏許", "裡許", "里许", "在許", "在许",
    "上面", "上邊", "上边", "上下", "皇上", "在上",
    "在裏", "在裡", "在里",
    "个人", "個人", "个体", "個體",
    # 正字法示例詞：兒戲 的「兒」讀 er1（否則取默認 gni2，會拼成 Gni shi）
    "兒戲", "儿戏",
]

# 詞內特例的補充（放在 WORD_OVERRIDE 之後定義亦可，這裡集中宣告）
for _w in ("兒戲", "儿戏"):
    WORD_OVERRIDE.setdefault(_w, {})["兒"] = "er1"
    WORD_OVERRIDE[_w]["儿"] = "er1"


def read_word_codes(path):
    out = []
    if not os.path.exists(path):
        print("  (missing)", path, file=sys.stderr)
        return out
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
            if not text or len(text) < 2:
                continue
            code = parts[1].strip() if len(parts) > 1 else ""
            syls = SYL_RE.findall(code)
            if len(syls) != len(text):
                continue
            out.append((text, syls))
    return out


def main():
    with open(os.path.join(DATA, "dict.json"), encoding="utf-8") as f:
        d = json.load(f)
    chars = d["chars"]

    word_codes = read_word_codes(ROM)
    print("詞庫讀入:", len(word_codes), "條")

    # ---------------- ① 逐字預設音 ----------------
    defaults = {}
    report = {}
    for ch, rs in chars.items():
        order = [r[0] for r in rs]
        if ch in OVERRIDE and OVERRIDE[ch] in order:
            chosen, src = OVERRIDE[ch], "override"
        else:
            chosen, src = order[0], ("db-order" if len(order) > 1 else "single")
        defaults[ch] = chosen
        if len(order) > 1:
            report[ch] = {"order": order, "chosen": chosen, "source": src}

    # ---------------- ② 詞組候選讀音 ----------------
    # 有效讀音：WORD_OVERRIDE > 單字預設 > 簡體字轉成繁體後的預設
    _s2t = d["s2t"]

    def default_of(c):
        """逐字預設音；簡體字（不在 chars 裡）用它對應繁體字的預設。"""
        if defaults.get(c):
            return defaults[c]
        for tr in _s2t.get(c, []):
            if defaults.get(tr):
                return defaults[tr]
        return None

    def effective(word):
        eff = {}
        for i, c in enumerate(word):
            ov = WORD_OVERRIDE.get(word, {}).get(c)
            eff[i] = ov if ov else default_of(c)
        return eff

    words = {}
    for word, syls in word_codes:
        if not all(c in chars for c in word):
            continue
        words.setdefault(word, [])
        if syls not in words[word]:
            words[word].append(syls)

    # 補充詞：詞庫沒收但使用者要求當成一個詞的，用逐字預設音造一條候選。
    # 注意：簡體字（如 儿、戏）不在 chars 裡，要靠 s2t 的鍵才算「認得」，
    # 否則「儿戏」會被誤判成查無此字而漏掉。
    # 簡體字本身沒有默認音，一律改用其對應繁體字的默認音（簡→繁第一候選）。
    s2t_keys = d["s2t"]

    def reading_for(c, word):
        """這個字在該詞裡該用什麼音：詞內特例 > 逐字默認 > 其繁體對應的默認。"""
        ov = WORD_OVERRIDE.get(word, {}).get(c)
        if ov:
            return ov
        if defaults.get(c):
            return defaults[c]
        for tr in s2t_keys.get(c, []):
            if defaults.get(tr):
                return defaults[tr]
        return None

    extra_added = []
    for word in EXTRA_WORDS:
        if not all((c in chars) or (c in s2t_keys) for c in word):
            continue
        want = [reading_for(c, word) for c in word]
        if any(x is None for x in want):
            continue
        if word not in words:
            words[word] = [want]
            extra_added.append(word)
        else:
            # 正確的那條一定排第一；同時剔除任何含 None 的殘缺候選
            rest = [w for w in words[word] if w != want and all(x is not None for x in w)]
            words[word] = [want] + rest
    # 分詞詞表也要收這些詞
    extra_words_list = list(words.keys())

    def agreement(syls, word):
        eff = effective(word)
        return sum(1 for i, s in enumerate(syls) if eff.get(i) == s)

    for word in words:
        # 含 None 的殘缺候選（簡體字查不到音）永遠排最後
        words[word].sort(key=lambda s: (any(x is None for x in s),
                                        -agreement(s, word)))

    # 詞內特例：確保指定的那條讀音排第一（詞庫沒收就補一條）
    for word, ov in WORD_OVERRIDE.items():
        if word not in words:
            continue
        eff = effective(word)
        want = [eff[i] for i in range(len(word))]
        if want in words[word]:
            words[word].remove(want)
        words[word].insert(0, want)

    # ---------------- ③ 輸出 ----------------
    with open(os.path.join(DATA, "defaults.json"), "w", encoding="utf-8") as f:
        json.dump(defaults, f, ensure_ascii=False, separators=(",", ":"))

    with open(os.path.join(DATA, "words.json"), "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, separators=(",", ":"))

    rules = {
        "override": OVERRIDE,
        "wordOverride": WORD_OVERRIDE,
        "singleOverride": SINGLE_OVERRIDE,
        "noConvert": sorted(NO_CONVERT),
        "convertWords": CONVERT_WORDS,
        "extraWords": extra_added,
    }
    with open(os.path.join(DATA, "rules.json"), "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, separators=(",", ":"), indent=0)

    with open(os.path.join(DATA, "readings.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, separators=(",", ":"), indent=0)

    # ---------------- ④ 報告 ----------------
    multi = sum(1 for rs in chars.values() if len(rs) > 1)
    n_over = sum(1 for ch in report if report[ch]["source"] == "override")
    print(f"多音字 {multi} 個：{n_over} 個由 OVERRIDE 指定，其餘沿用 DB 順序")
    print(f"詞組候選 {len(words)} 個詞；詞內特例 {len(WORD_OVERRIDE)} 個詞；"
          f"單字特例 {len(SINGLE_OVERRIDE)} 個字；不轉繁 {sorted(NO_CONVERT)}")

    print("\n=== 使用者指定規則逐條驗證 ===")
    checks = [
        ("我", None, "ngu6"), ("儂", None, "non6"), ("渠", None, "yi2"),
        ("白", None, "baq8"), ("上", None, "laon6"), ("箇", None, "geq8"),
        ("个", None, "keq7"), ("許", None, "shiu3"),
        ("白", "白相", "beq8"),
        ("許", "幾許", "ho5"), ("許", "場許", "ho5"), ("許", "裏許", "ho5"),
        ("許", "在許", "he3"),
        ("上", "上面", "zaon6"), ("上", "上邊", "zaon6"),
        ("上", "上去", "zaon6"), ("上", "上下", "zaon6"),
        ("上", "皇上", "zan6"), ("上", "在上", "laon6"),
        ("在", "在許", "leq8"), ("在", "在上", "leq8"), ("在", "在裏", "leq8"),
    ]
    bad = 0
    for ch, word, want in checks:
        if word:
            ov = WORD_OVERRIDE.get(word, {}).get(ch)
            got = ov if ov else defaults.get(ch)
            src = "詞內特例" if ov else "逐字預設"
        else:
            got, src = defaults.get(ch), "逐字預設"
        ok = got == want
        if not ok:
            bad += 1
        print(f"  {ok and 'OK ' or 'BAD'} {ch}"
              f"{' @ ' + word if word else '（單字）':<10} -> {got}  [{src}]"
              f"{'' if ok else '  want ' + want}")

    print("\n=== 詞組既定讀音（第一條）===")
    for w in ["白相", "幾許", "場許", "裏許", "在許", "上面", "上邊", "上去",
              "上下", "皇上", "在上", "在裏", "我伲", "我拉", "渠拉", "歡喜"]:
        if w in words:
            print(f"  {w}: {words[w][0]}")
        else:
            print(f"  {w}: (詞庫無，需靠 EXTRA_WORDS 補)")
    print(f"\n{'FAILED ' + str(bad) if bad else 'ALL RULES OK'}")


if __name__ == "__main__":
    main()
