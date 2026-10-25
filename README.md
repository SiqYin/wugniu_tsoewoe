# 吳語拼音轉換器

把漢字轉換成**吳語**讀音的網頁工具，支持五種方言（蘇滬混合腔、清末蘇州話、蘇州話、上海話、蘇州評彈）。線上版：<https://siqyin.github.io/wugniu_tsoewoe/>

與 [吳語字音查詢](https://siqyin.github.io/wugniu_zyinzozin/)、[蘇滬混合腔韻圖](https://siqyin.github.io/wugniu_yundu/) 同一套配色與字型，同為純靜態 GitHub Pages 頁面。

## 它做什麼

輸入一段漢字，按「轉換」，輸出對應讀音。**五種方言可選，各自獨立轉換、互不混用**（一次只能選一種）：

| 方言 | 說明 |
|---|---|
| **蘇滬混合腔**（預設） | 本站主體，兩種顯示模式 × 兩種輸出格式 |
| 清末蘇州話 / 蘇州話 / 上海話 / 蘇州評彈 | 參考方言，**字音原樣取自字音站**，只輸出字音 |

**五種方言都支持簡體輸入**：簡體自動折成繁體查詢，一簡多繁時標藍讓使用者挑（如 发 → 髮／發）。
「**个**」的處理兩邊不同：蘇滬混合腔裡它不轉繁（吳語中另有一字，默認 `keq7`）；
其餘四種方言照普通簡繁關係折成「**個**」再查。

蘇滬混合腔的兩種顯示模式 × 兩種輸出格式：

|  | 漢字拼音對照 | 僅拼音 |
|---|---|---|
| **帶調拼音** | 每句先列原文漢字，下一行列拼音 | 只列拼音 |
| **拼音文** | 同上，拼音行改用正字法 | 只列正字法拼音 |

選其餘四種方言時，「輸出帶調拼音／輸出拼音文」兩個按鈕合併為單一「**輸出字音**」，直接顯示字音站的音標（如 蘇州話 `儂好 → noŋ2男:hɐ3 女:hæ3`）。

### 標色規則

| 顏色 | 含義 |
|---|---|
| **藍色** | 多音字，或多繁體候選 —— 有不止一個可能的讀音，點擊可選 |
| **紅色** | 該方言**未收**此字 |

未收字的顯示方式：

- **漢字行**：該字直接標紅
- **帶調拼音 / 輸出字音**：顯示 `xxxx0`，標紅
- **拼音文**：顯示 `xxxx`，標紅，且**單獨成詞**——前後各留一個空格，與相鄰音節斷開

**多音字**預設給一個音，點擊該字即列出它的**全部**字音（拼音、音標、韻圖位置、註記），點哪條就改用哪條。

**簡繁**：輸入繁體輸出繁體，輸入簡體折成繁體。**一簡多繁**時（如 发 → 髮／發）標藍，點擊列出各繁體及其各自讀音；**一簡一繁**只有唯一讀音，不標色。

## 設計原則：不推導字音

**本頁不自行推導任何字音。** 所有讀音都是字音站 `DB_suhu.json` 的原樣搬運，本專案只做三件事：

1. **查表** —— 字 → 讀音
2. **分詞** —— 用吳語詞表切詞
3. **拼寫** —— 按正字法連寫、加小撇

字音站記什麼音就取什麼音；同一字多音就全部收錄；該音有註記也一併呈現。

## 拼音文正字法

小撇一律 **U+0027 APOSTROPHE**，不用 U+2019。

| 規則 | 說明 | 例子 |
|---|---|---|
| 詞內連寫 | 以詞為單位連寫音節，詞間以空格分隔 | `白相 beq8sian1` → `beqsian` |
| 詞首陰平（調 1） | 音節前加小撇 | `雞排 ci1ba2` → `'ciba` |
| 詞首 m/n/l/gn ＋ 調 3・5・7 | 聲母後、韻母前加小撇 | `美好 me3hau3` → `m'ehau` |
| 詞首 m/n/l/gn ＋ 調 1 | 只在音節前加一只小撇 | `蠻好 me1hau3` → `'mehau` |
| 詞首 er1 | 音節前加小撇 | `兒戲 er1shi5` → `'ershi` |
| 其餘調類（2・3・5・6・7・8） | 一律不標 | `作興 tsoq7shin1` → `tsoqshin` |
| 句首大寫 | 句首第一個字母大寫，無論前面有沒有小撇 | `'ershi` → `'Ershi` |
| 成音節鼻音 m/n/ng ＋ 陰調 | 無韻母縫隙，改在音節前加撇 | `m1` → `'m`、`n3` → `'n` |

### 分詞

拼音文按詞連寫，所以必須先分詞。分詞**只**用吳語詞表（`wuphin.word` / `wuphin.map` / `wuphin.phrases`，即輸入法自己的詞庫），**不含**普通話詞庫——吳語用詞與普通話差別很大（「我伲」「白相」「作興」「弗」「箇」），用普通話詞庫會切錯。

分詞結果在輸入欄以金色小豎槓 `|` 顯示。點槓可切開／合併詞，拼音文即時跟著改；**最終以使用者調整的結果為準**。

## 河湖韻處理

**湖韻 `u[uᵝ]` 與河韻 `ou[əuᵝ]` 是同一個音位的兩個音值變體**，不是重複格位。

除脣音 `pu phu mu fu vu`（另有 `bu`）只有湖韻、匣母 `ghou` 只有河韻（其湖形為濁零 `wu`）外，
有變體的聲母 `t th n l k kh g h ng ts tsh s z` 每個音節都有湖、河兩形。

工具列上有「河湖韻處理」按鈕，三種取向：

| 取向 | 說明 | 例 |
|---|---|---|
| 蘇滬混合腔默認 | 零聲母 `u`／`wu` 走湖；其餘有變體的聲母走河 | `都 tou1`、`我 ngou6`、`湖 wu2`、`個 kou5` |
| 全走湖韻 | 一律 u 形 | `都 tu1`、`我 ngu6`、`湖 wu2`、`個 ku5` |
| 全走河韻 | 一律 ou 形 | `都 tou1`、`我 ngou6`、`湖 ghou2`、`個 kou5` |

**此設定的優先級高於逐字默認音。** 下面各項規則寫的都是「原型」（多為湖形 u），
套完規則之後才依本設定規範化。例如「個」的原型默認是 `ku5`：
混合腔默認顯示 `kou5`，全走湖韻顯示 `ku5`。音標也跟著換（`tu1` = `[tuᵝ⁴⁴]`、`tou1` = `[təuᵝ⁴⁴]`）。

設定記在 `localStorage`。

## 個 / 个 的特別處理

- **个** 一般不轉繁體，默認音 `keq7`。**這條只適用於蘇滬混合腔**；
  其餘四種方言裡「个」照普通簡繁關係折成「個」查詢。
- 例外：**「个人」「个体」轉繁體為「個人」「個體」**，且其中「个」讀 `ku5`（經河湖韻規範化後，混合腔默認顯示 `kou5`）。
- **個** 默認音 `ku5`（同樣受河湖韻設定影響）。

## 讀音優先級（三層）

多音字取哪個音，按以下順序（高者優先）：

1. **河湖韻處理設定** —— 三取向規範化，優先於以下所有逐字規則
2. **使用者當場選擇** —— 點字挑音後覆蓋一切
3. **詞內特例** —— 某字在某個特定詞裡的讀法（如「白相」的白讀 `beq8`，而白一般讀 `baq8`）
4. **單字成詞特例** —— 該字被分成單音節詞時（如「在|我|該搭」的「在」讀 `leq8`）
5. **逐字預設音** —— 使用者校訂過的常用字預設，其餘沿用字音站 DB 順序首音

目前已校訂的規則見 `data/rules.json`（由 `tools/build_readings.py` 產生），要改就直接改該腳本頂部的 `OVERRIDE` / `WORD_OVERRIDE` / `SINGLE_OVERRIDE` / `NO_CONVERT` / `CONVERT_WORDS` / `EXTRA_WORDS`。

## 三語界面與語言自動判斷

界面支持 **吳語（繁體中文）／English／日本語**，右上角切換按鈕與字音站、韻圖站**完全同一套設計**（藍底 `#2980b9`、圓角 6px、`▾` 旋轉動畫）。

### 語言判斷優先級

與兩站一致：

1. `?lang=wu|en|ja` 強制指定（也接受 `?lang=auto` 清除手選）
2. `localStorage` 手選記憶 —— 使用者的明確選擇永遠優先
3. 瀏覽器語言（`zh*` → 吳語、`ja*` → 日語，零請求即可判定）
4. **IP 歸屬地**（`api.country.is`，失敗回退 Cloudflare `cdn-cgi/trace`）：
   - `CN` `HK` `MO` `TW` → 吳語
   - `JP` → 日語
   - 其餘 → English
5. 英文兜底

本機預覽（`localhost` / `127.0.0.1` / `file:`）與爬蟲不自動判斷，維持吳語，避免搜尋引擎收錄到英文版。

### 跨站語言聯動

- **從字音站／韻圖站過來**：兩站跳轉時都帶 `?lang=<code>`，本站直接採用該語言
- **從本站過去**：頁腳的字音站、韻圖站外鏈自動附上 `?lang=<當前語言>`

### 術語（與兩站一致）

| 中文 | English | 日本語 |
|---|---|---|
| 蘇滬混合腔 | common language | 呉越共通語 |
| 吳語 | Wu language | 呉越語 |
| 清末蘇州話 | Late Qing Suzhounese | 清末蘇州語 |
| 蘇州話 | Suzhounese | 蘇州語 |
| 上海話 | Shanghainese | 上海語 |
| 蘇州評彈 | Pingtan pronunciation | 蘇州評弾 |

## 與字音站聯動

頁面開啟時會在背景比對字音站線上 `DB_suhu.json` 的大小與 `Last-Modified`：

- 一致 → 狀態條顯示「字音資料已就緒」
- 有新版 → 狀態條轉橙，提示「字音站有更新」

真正的資料更新由建置完成：

```bash
python tools/update_from_upstream.py          # 抓線上最新並重建全部
python tools/update_from_upstream.py --check  # 只檢查有無新版
python tools/update_from_upstream.py --local  # 不連網，用本機既有檔重建
```

## 檔案

| 檔案 | 內容 |
|---|---|
| `index.html` | 頁面本體（由 `tools/build_html.py` 產生，**勿手改**） |
| `data/DB_suhu.json` | 字音站字典本體（上游快照） |
| `data/S2T.json` | 簡→繁對照（上游快照） |
| `data/YUNTU_POS.json` | 音節→韻圖位置（上游快照） |
| `data/dict.json` | 前端用：`chars` / `s2t` / `pos` |
| `data/defaults.json` | 逐字預設音 |
| `data/words.json` | 詞組既定讀音（第一條為預設） |
| `data/rules.json` | 三層優先級規則表（供前端套用） |
| `data/huhe.json` | 湖／河韻變體對照表（給「河湖韻處理」用） |
| `data/syl.json` | 音節 → 音標（河湖韻換形後查音值） |
| `data/lexicon.json` | 分詞詞表（只收吳語詞） |
| `data/meta.json` | 統計、上游簽章 |
| `data/readings.json` | 除錯用：每個多音字的候選與決策來源 |
| `fonts/wk-ui.woff2` | 霞鶩文楷首屏子集 |
| `fonts/wk-dict.woff2` | 霞鶩文楷字典子集 |
| `fonts/fontface.css` | `@font-face` 宣告（內嵌進 index.html） |
| `favicon.ico` / `apple-touch-icon.png` | 圖示 |

### 腳本

| 腳本 | 作用 |
|---|---|
| `tools/build_data.py` | 上游 JSON → `dict.json` / `meta.json` |
| `tools/build_lexicon.py` | 輸入法詞庫 → `lexicon.json`（只收吳語詞） |
| `tools/build_readings.py` | 三層優先級 → `defaults.json` / `words.json` / `rules.json` |
| `tools/build_huhe.py` | 湖／河變體 → `huhe.json` |
| `tools/build_html.py` | 模板 + 資料 → `index.html` |
| `tools/make_font.py` | 霞鶩文楷子集化 → `fonts/` |
| `tools/make_favicon.py` | 產生圖示 |
| `tools/update_from_upstream.py` | 抓上游最新並重建全部 |

### 重建流程

```bash
python tools/build_data.py       # → dict.json / syl.json / meta.json
python tools/build_lexicon.py    # → lexicon.json
python tools/build_readings.py   # → defaults.json / words.json / rules.json
python tools/build_huhe.py       # → huhe.json（須在 build_data 之後）
python tools/build_html.py       # → index.html
```

改字型時另跑 `python tools/make_font.py`（需 `fonttools` + `brotli`），再跑一次 `build_html.py` 把新的 `fontface.css` 嵌進去。

## 字型

頁面內嵌**霞鶩文楷 Regular**（LXGW WenKai v1.530，SIL OFL 1.1），子集化為兩個 woff2 自託管，`unicode-range` 由各檔實際 cmap 壓縮而成，遇到字型沒有的字瀏覽器會直接回退系統字型，不會白下載。授權見 `fonts/OFL.txt`。

## 發佈

GitHub Pages，來源為 `main` 分支根目錄。push 到 `main` 即上線；`.github/workflows/pages.yml` 會先跑一次 `build_html.py` 再部署。

## 授權

- 字音資料：依原字典專案（字音站）
- 字型：SIL Open Font License 1.1
- 程式碼：MIT
