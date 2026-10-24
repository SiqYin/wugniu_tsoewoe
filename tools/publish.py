# -*- coding: utf-8 -*-
"""publish.py —— 把本目錄發布到 GitHub：建倉庫 → 提交 → 推送 → 開 GitHub Pages。

沿用 wugniu_yundu / wugniu_zyinzozin 的做法。權杖只從環境變數讀取，
**不寫進任何檔案，也不寫進 .git/config**（remote 保持 SSH 形）。

用法
----
    $env:GITHUB_TOKEN="ghp_xxx"          # PowerShell
    set GITHUB_TOKEN=ghp_xxx             # cmd
    export GITHUB_TOKEN=ghp_xxx          # bash
    python publish.py                    # 預設 SiqYin/wugniu_tsoewoe
    python publish.py --check            # 只檢查權杖權限，不動任何東西
    python publish.py --no-api           # 倉庫已手動建好，只推送

需要的權杖權限
--------------
classic token（建議，最省事）：
    ☑ repo            （建倉庫、推送）
    ☑ workflow        （推送 .github/workflows/pages.yml 需要）
    ☑ delete_repo     （可選，只在需要刪倉庫時用）

fine-grained token：
    Repository access → All repositories（或先建好倉庫再選 Only select repositories）
    Permissions:
        Administration : Read and write   （建倉庫 / 改 Pages 設定）
        Contents       : Read and write   （推送）
        Pages          : Read and write   （啟用 GitHub Pages）
        Workflows      : Read and write   （推送 workflow 檔）
        Metadata       : Read-only        （自動附帶）

推送優先走既有 SSH 金鑰；SSH 不可用時才用權杖走 HTTPS（權杖只出現在那一條指令裡）。
用完請到 https://github.com/settings/tokens 撤銷。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BRANCH = "main"

OWNER = "SiqYin"
NAME = "wugniu_tsoewoe"
DESC = "吳語拼音轉換器：漢字轉吳語五種方言讀音（蘇滬混合腔帶調拼音與拼音文），字音即時取自字音查詢站"
HOMEPAGE = f"https://{OWNER.lower()}.github.io/{NAME}/"
# 與字音站（wugniu_zyinzozin）、韻圖站（wugniu_yundu）的 topics 保持同族
TOPICS = ["wugniu", "wu-chinese", "wuchinese", "chinese-dialects",
          "suzhou-dialect", "shanghainese", "romanization", "pinyin",
          "ipa", "linguistics", "github-pages"]


def token() -> str | None:
    t = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    return t or None


def api(path, tok, method="GET", body=None):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "wugniu-tsoewoe-publish")
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data, timeout=60) as r:
            raw = r.read().decode("utf-8")
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw}
    except Exception as e:
        return 0, {"error": str(e)}


def git(*args, check=True):
    r = subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        print("git %s 失敗：\n%s%s" % (" ".join(args), r.stdout, r.stderr))
        sys.exit(1)
    return (r.stdout + r.stderr).strip()


# ------------------------------------------------------------------ 權限自檢
def check_token(tok):
    print("· 檢查權杖與權限……")
    st, me = api("/user", tok)
    if st != 200:
        print(f"  ✗ 權杖無效（HTTP {st}）：{me}")
        return False
    login = me.get("login")
    print(f"  ✓ 身份：{login}")
    if login.lower() != OWNER.lower():
        print(f"  ! 注意：權杖屬於 {login}，不是 {OWNER}；建立倉庫會建在 {login} 名下。")

    # 能讀 scopes 頭（classic token）
    req = urllib.request.Request(API + "/user")
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "wugniu-tsoewoe-publish")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            scopes = r.headers.get("x-oauth-scopes")
        if scopes is not None:
            have = {s.strip() for s in scopes.split(",") if s.strip()}
            print(f"  · classic 權杖 scopes：{sorted(have) or '（無）'}")
            for need in ("repo", "workflow"):
                print(f"    {'✓' if need in have else '✗'} {need}")
            if "repo" not in have:
                print("  ✗ 缺 repo 權限，無法建倉庫／推送。")
                return False
        else:
            print("  · fine-grained 權杖（無 scopes 頭，無法列出細項）")
    except Exception as e:
        print("  · 無法讀取 scopes：", e)

    # 試探是否已有 Pages 權限（對不存在的倉庫會 404，屬正常）
    st, res = api(f"/repos/{OWNER}/{NAME}", tok)
    if st == 200:
        print(f"  · 倉庫 {OWNER}/{NAME} 已存在")
    elif st == 404:
        print(f"  · 倉庫 {OWNER}/{NAME} 尚未建立（稍後會建）")
    else:
        print(f"  · 查倉庫回傳 HTTP {st}")
    print("  ✓ 權杖可用")
    return True


def sync_repo_meta(tok, repo):
    """把倉庫 About（描述、主頁）與 topics（標籤）同步成本檔的設定。

    每次發布都跑一遍：站名或定位改了，改本檔頂部 DESC / TOPICS 即可，
    不用去網頁上手工改。
    """
    print("· 同步倉庫 About 與 topics……")
    st, res = api(f"/repos/{repo}", tok, "PATCH",
                  {"description": DESC, "homepage": HOMEPAGE})
    if st == 200:
        print(f"  ✓ 描述：{DESC}")
        print(f"  ✓ 主頁：{HOMEPAGE}")
    else:
        print(f"  ✗ 更新描述失敗（HTTP {st}）：{res}")

    st, res = api(f"/repos/{repo}/topics", tok, "PUT", {"names": TOPICS})
    if st == 200:
        print(f"  ✓ topics：{'、'.join(TOPICS)}")
    else:
        print(f"  ✗ 更新 topics 失敗（HTTP {st}）：{res}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", default=OWNER)
    ap.add_argument("--name", default=NAME)
    ap.add_argument("--public", action="store_true", default=True)
    ap.add_argument("--private", dest="public", action="store_false")
    ap.add_argument("--no-api", action="store_true",
                    help="倉庫已由使用者手動建好：不呼叫 API，只做 git 推送；"
                         "Pages 交給 .github/workflows/pages.yml 自動開啟")
    ap.add_argument("--check", action="store_true", help="只檢查權限，不推送")
    ap.add_argument("--message", default=None, help="自訂 commit 訊息")
    a = ap.parse_args()

    repo = f"{a.owner}/{a.name}"
    tok = token()

    if a.check:
        if not tok:
            print("找不到 GITHUB_TOKEN（或 GH_TOKEN）環境變數。")
            sys.exit(1)
        sys.exit(0 if check_token(tok) else 1)

    if not a.no_api and not tok:
        print("找不到 GITHUB_TOKEN 環境變數（建倉庫／開 Pages 必須提供）。")
        print("若倉庫已手動建好，可改用：python publish.py --no-api")
        sys.exit(1)
    if tok:
        if not check_token(tok):
            sys.exit(1)
        print()

    # 1) 建倉庫（已存在就沿用）
    if a.no_api:
        print(f"· --no-api：跳過建倉庫，假設 {repo} 已建好")
    else:
        st, res = api("/user/repos", tok, "POST", {
            "name": a.name,
            "description": DESC,
            "homepage": HOMEPAGE,
            "private": not a.public,
            "has_issues": True, "has_wiki": False, "has_projects": False,
            "auto_init": False,
        })
        if st == 201:
            print(f"· 已建立倉庫 {repo}")
        elif st == 422:
            print(f"· 倉庫 {repo} 已存在，沿用")
        else:
            print(f"建倉庫失敗（HTTP {st}）：{res}")
            sys.exit(1)

    # 2) 提交
    if not os.path.isdir(os.path.join(ROOT, ".git")):
        git("init", "-b", BRANCH)
        print("· 已初始化 git 倉庫")
    git("config", "user.name", a.owner)
    git("config", "user.email", f"{a.owner}@users.noreply.github.com")
    git("add", "-A")
    if git("status", "--porcelain"):
        msg = a.message or "吳語拼音轉換器：轉換頁面、正字法、分詞與霞鶩文楷字型"
        git("commit", "-m", msg)
        print("· 已提交")
    else:
        print("· 沒有新變更")

    # 3) 推送
    ssh_url = f"git@github.com:{repo}.git"
    remotes = git("remote").split()
    if "origin" in remotes:
        git("remote", "set-url", "origin", ssh_url)
    else:
        git("remote", "add", "origin", ssh_url)

    r = subprocess.run(["git", "push", "-u", "origin", BRANCH], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if r.returncode == 0:
        print(f"· 已推送（SSH）到 {ssh_url}")
    else:
        if not tok:
            print("SSH 推送失敗，且沒有權杖可回退：\n" + r.stdout + r.stderr)
            sys.exit(1)
        print("· SSH 不可用，改走 HTTPS 權杖通道……")
        https_url = f"https://x-access-token:{tok}@github.com/{repo}.git"
        r2 = subprocess.run(
            ["git", "-c", "credential.helper=", "push", https_url,
             f"{BRANCH}:{BRANCH}"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            errors="replace")
        if r2.returncode != 0:
            print("HTTPS 推送也失敗：\n"
                  + r2.stdout.replace(tok, "<TOKEN>")
                  + r2.stderr.replace(tok, "<TOKEN>"))
            sys.exit(1)
        print(f"· 已推送（HTTPS）到 {repo}")
        git(f"branch", f"--set-upstream-to=origin/{BRANCH}", check=False)

    # 4) 同步 About 與 topics（--no-api 時無權杖，跳過）
    if a.no_api:
        print("· --no-api：跳過 About / topics 同步")
    else:
        sync_repo_meta(tok, repo)

    # 5) 開 Pages
    if a.no_api:
        print("· --no-api：Pages 由 .github/workflows/pages.yml 自動開啟")
    else:
        st, res = api(f"/repos/{repo}/pages", tok)
        if st == 200 and res:
            print(f"· Pages 已開啟：{res.get('html_url')}")
        else:
            st, res = api(f"/repos/{repo}/pages", tok, "POST",
                          {"source": {"branch": BRANCH, "path": "/"}})
            if st in (201, 409):
                print("· 已啟用 GitHub Pages（分支模式：main 根目錄）")
            else:
                print(f"開 Pages 失敗（HTTP {st}）：{res}")
                print(f"  可手動到 https://github.com/{repo}/settings/pages "
                      f"選 {BRANCH} 分支根目錄")

        # 6) 等首次部署
        print("· 等待 Pages 首次部署（最多 5 分鐘）……")
        for _ in range(60):
            time.sleep(5)
            st, r2 = api(f"/repos/{repo}/pages/builds/latest", tok)
            if st == 200 and r2:
                if r2.get("status") == "built":
                    print("· 部署完成")
                    break
                if r2.get("status") == "errored":
                    print("· 部署出錯：", r2.get("error", {}).get("message"))
                    break
            else:
                try:
                    with urllib.request.urlopen(HOMEPAGE, timeout=10) as resp:
                        if resp.status == 200:
                            print("· 網站已可訪問")
                            break
                except Exception:
                    pass

    print(f"\n完成。線上網址：{HOMEPAGE}")
    print(f"倉庫地址：https://github.com/{repo}")
    if not a.no_api:
        print(f"部署進度：https://github.com/{repo}/actions")


if __name__ == "__main__":
    main()
