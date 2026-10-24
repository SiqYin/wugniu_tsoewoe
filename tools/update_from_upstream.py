# -*- coding: utf-8 -*-
"""update_from_upstream.py —— 從字音站抓最新資料，重建全部產物。

這是「與字音站聯動」的落地方式：字音站 DB_suhu.json 更新後跑這支腳本，
重新抓取 → 重建 dict/defaults/words/lexicon → 重建 index.html。

用法：
    python tools/update_from_upstream.py            # 抓線上最新
    python tools/update_from_upstream.py --local    # 用本機 data/ 既有檔（不連網）
    python tools/update_from_upstream.py --check    # 只檢查有無新版，不寫檔

判斷依據：sha256 與本機檔案不同 → 有更新。
另記錄 upstream_sig（Content-Length + Last-Modified）給前端做「是否有新版」的輕量比對。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

BASE = "https://siqyin.github.io/wugniu_zyinzozin/data/"
FILES = {
    "DB_suhu.json": BASE + "DB_suhu.json",
    "S2T.json": BASE + "S2T.json",
    "YUNTU_POS.json": BASE + "YUNTU_POS.json",
    # 四種參考方言（原樣取自字音站，不推導）
    "DB_qingmo.json": BASE + "DB_qingmo.json",
    "DB_suzhou.json": BASE + "DB_suzhou.json",
    "DB_shanghai.json": BASE + "DB_shanghai.json",
    "DB_pingtan.json": BASE + "DB_pingtan.json",
}


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "wugniu-tsoewoe/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.headers.get("Last-Modified")


def main():
    local = "--local" in sys.argv
    check_only = "--check" in sys.argv
    os.makedirs(DATA, exist_ok=True)

    meta_path = os.path.join(DATA, "meta.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

    changed = []
    upstream_sig = None

    for name, url in FILES.items():
        path = os.path.join(DATA, name)
        if local:
            if os.path.exists(path):
                print(f"  {name}: 使用本機既有檔")
                continue
            sys.exit(f"缺少 {path}")
        print(f"  抓取 {name} …", end=" ", flush=True)
        try:
            raw, lm = fetch(url)
        except Exception as e:
            print("失敗:", e)
            if os.path.exists(path):
                print(f"    → 沿用既有 {name}")
                continue
            sys.exit(f"無法取得 {name} 且本機無備份")
        if name == "DB_suhu.json":
            upstream_sig = f"{len(raw)}|{lm or ''}"
            print(f"({len(raw)} bytes, {lm})", end=" ")
        new_hash = sha256_bytes(raw)
        old_hash = sha256_file(path) if os.path.exists(path) else None
        if new_hash == old_hash:
            print("無變化")
            continue
        print(f"有更新 ({str(old_hash)[:8]} → {new_hash[:8]})")
        changed.append(name)
        if not check_only:
            with open(path, "wb") as f:
                f.write(raw)

    if check_only:
        print("\n有更新的檔案:", changed or "（無）")
        return

    print("\n重建資料 …")
    py = sys.executable
    for step in ("build_data.py", "build_lexicon.py", "build_readings.py",
                 "build_huhe.py", "build_dialects.py", "build_html.py"):
        print(f"  {step}")
        r = subprocess.run([py, os.path.join(HERE, step)], cwd=ROOT,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if r.returncode != 0:
            sys.exit(f"{step} 失敗")

    # 把上游簽章寫進 meta.json（build_data.py 會整份重寫，所以在它之後補）
    if upstream_sig:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        meta["upstream_sig"] = upstream_sig
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, separators=(",", ":"), indent=0)
        print("  記錄 upstream_sig =", upstream_sig)

    print("\n完成。更新的檔案:", changed or "（無，僅重建）")


if __name__ == "__main__":
    main()
