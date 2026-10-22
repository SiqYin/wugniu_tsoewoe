# -*- coding: utf-8 -*-
"""build_html.py —— 由模板 + 資料生成 index.html

資料檔（全部由 tools/ 下的腳本產生，前端用 fetch 抓）：
  data/dict.json      chars（繁字→[[音節,音標,註記],...]）/ s2t（簡→繁）/ pos（音節→韻圖位置）
  data/defaults.json  逐字預設音（多音字取哪一個）
  data/words.json     詞組既定讀音候選（已按與逐字預設的一致度排序）
  data/lexicon.json   分詞詞表（只收吳語詞）
  data/meta.json      統計與版本戳
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")


# ============================================================ CSS
CSS = r"""
:root{
--ink:#1a2a3a; --ink2:#5b7f9e; --ink3:#7a99b5;
--line:#c8dae8; --line2:#dbe7f2;
--bg:#eef3f9; --card:#fff;
--yin:#e8f0f8; --yinb:#2980b9;
--sys:#1a5276; --sys2:#1a6da2;
--warn:#c0392b; --warnbg:#fdf0f0;
--ok:#2e7d4f; --okbg:#eef7f1;
--gold:#8a6d1c; --goldbg:#fdf8ef;
--sep:#d9a441;
--segbar:#16324f;   /* 分詞小豎槓：深藍黑（與 --sys 同色系但更深） */
--segbar-hi:#1a5276;
}
*{box-sizing:border-box}
html,body{height:100%}
body{
margin:0;background:var(--bg);color:var(--ink);
font-family:"LXGW WenKai","SimSun-ExtB","MingLiU-ExtB","Songti SC","Source Han Serif SC","Noto Serif CJK SC",Georgia,"SimSun",serif;
font-size:15px;line-height:1.75;
-webkit-text-size-adjust:100%;-webkit-tap-highlight-color:transparent;
display:flex;flex-direction:column;min-height:100vh;
}
.tricolor-bar{width:100%;height:9px;flex-shrink:0;
background:linear-gradient(to bottom,#000 0%,#000 33.33%,#fff 33.33%,#fff 66.66%,#3a6da2 66.66%,#3a6da2 100%)}
.wrap{flex:1;max-width:1000px;margin:0 auto;padding:22px 20px 80px;width:100%}

header.top{border-bottom:2px solid var(--sys);padding-bottom:14px;margin-bottom:18px;position:relative}
h1{color:var(--sys);font-size:27px;margin:0 0 6px;letter-spacing:.05em;font-weight:700}
.sub{color:var(--ink2);font-size:13.5px;margin:4px 0}
.syncbar{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;
margin-top:6px;padding:3px 10px;border-radius:12px;background:#f4f8fd;
border:1px solid var(--line2);color:var(--ink2)}
.syncbar.ok{background:var(--okbg);border-color:#bfe0cd;color:var(--ok)}
.syncbar.warn{background:var(--warnbg);border-color:#f0c8c8;color:var(--warn)}
.syncbar .dot{width:7px;height:7px;border-radius:50%;background:currentColor;flex-shrink:0}

.lang-switcher{position:absolute;top:0;right:0}
.lang-btn{font-family:inherit;font-size:13px;color:var(--sys);background:#fff;
border:1px solid var(--line);border-radius:6px;padding:4px 10px;cursor:pointer}
.lang-btn:hover{background:var(--yin);border-color:var(--yinb)}
.lang-menu{display:none;position:absolute;top:100%;right:0;margin-top:4px;
background:#fff;border:1px solid var(--line);border-radius:6px;
box-shadow:0 4px 14px rgba(26,82,118,.13);overflow:hidden;z-index:100;min-width:110px}
.lang-menu.on{display:block}
.lang-menu button{display:block;width:100%;text-align:left;font-family:inherit;font-size:13px;
padding:6px 14px;background:none;border:0;cursor:pointer;color:var(--ink)}
.lang-menu button:hover{background:var(--yin)}

section{margin:22px 0}
h2{color:var(--sys);font-size:19px;margin:0 0 10px;letter-spacing:.03em}
.card{background:var(--card);border:1px solid var(--line2);border-radius:8px;padding:16px 18px}

.modes{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.mode-btn{font-family:inherit;font-size:14px;color:var(--sys);background:#fff;
border:1px solid var(--line);border-radius:6px;padding:7px 16px;cursor:pointer;transition:.15s}
.mode-btn:hover{background:var(--yin);border-color:var(--yinb)}
.mode-btn.on{background:var(--yinb);border-color:var(--yinb);color:#fff;font-weight:700}
.modes .sep{width:1px;background:var(--line);margin:2px 4px}
.modes{position:relative}
.mode-btn.huhe{display:flex;align-items:center;gap:4px}
.mode-btn.huhe #huheCur{font-weight:400;color:var(--gold);font-size:13px}
.mode-btn.huhe.on{background:var(--sep);border-color:var(--sep);color:#fff}
.mode-btn.huhe.on #huheCur{color:#fff9e6}
.huhe-menu{display:none;position:absolute;top:100%;left:0;margin-top:4px;z-index:120;
background:#fff;border:1px solid var(--line);border-radius:6px;
box-shadow:0 4px 14px rgba(26,82,118,.13);overflow:hidden;min-width:150px}
.huhe-menu.on{display:block}
.huhe-menu button{display:block;width:100%;text-align:left;font-family:inherit;font-size:13.5px;
padding:7px 14px;background:none;border:0;cursor:pointer;color:var(--ink)}
.huhe-menu button:hover{background:var(--goldbg)}
.huhe-menu button.on{background:var(--goldbg);color:var(--gold);font-weight:700}

textarea#src{
width:100%;min-height:120px;resize:vertical;font-family:inherit;font-size:16px;
line-height:1.9;padding:12px 14px;color:var(--ink);background:#fff;
border:1px solid var(--line);border-radius:8px;outline:none;transition:.15s
}
textarea#src:focus{border-color:var(--yinb);box-shadow:0 0 0 3px rgba(41,128,185,.12)}
textarea#src::placeholder{color:var(--ink3)}
#segview{display:none;min-height:120px;font-size:17px;line-height:2.2;
padding:12px 14px;background:#fff;border:1px solid var(--yinb);border-radius:8px;
word-break:break-word}
#segview.on{display:block}
#segview .seg{display:inline-block;padding:0 1px;border-radius:4px;position:relative}
/* 已有小豎槓：可拖動 */
#segview .sepmark{display:inline-block;color:var(--segbar);font-weight:700;
cursor:grab;padding:0 2px;border-radius:3px;user-select:none;transition:background .12s,color .12s;
font-size:15px;position:relative;touch-action:none}
#segview .sepmark:hover{background:var(--yinb);color:#fff}
#segview .sepmark.dragging{background:var(--segbar);color:#fff;cursor:grabbing;opacity:.55}
#segview .sepmark.dropzone{background:var(--yinb);color:#fff;box-shadow:0 0 0 2px rgba(41,128,185,.35)}
/* 字間隙：游標移上去出現淡淡的小豎槓提示；需要實際可點擊的寬度 */
#segview .gap{display:inline-block;width:7px;position:relative;vertical-align:middle;
cursor:pointer;height:1.2em}
#segview .gap::after{content:"|";position:absolute;left:50%;top:-1px;transform:translateX(-50%);
color:var(--segbar);opacity:0;font-weight:700;font-size:15px;
transition:opacity .12s;pointer-events:none;white-space:nowrap}
#segview .gap:hover::after{opacity:.45}
#segview .gap:hover{background:rgba(41,128,185,.07);border-radius:2px}
/* 確認彈窗 */
#cfm{position:fixed;inset:0;z-index:400;background:rgba(26,42,58,.18);
display:flex;align-items:center;justify-content:center}
#cfm .cfm-in{background:#fff;border:1px solid var(--line);border-radius:10px;
box-shadow:0 10px 32px rgba(26,82,118,.22);padding:18px 20px;max-width:min(88vw,340px);
font-size:14.5px;color:var(--ink)}
#cfm p{margin:0 0 14px;line-height:1.7}
#cfm .cfm-btns{display:flex;gap:10px;justify-content:flex-end}
#cfm button{font-family:inherit;font-size:13.5px;border-radius:6px;padding:7px 16px;
cursor:pointer;border:1px solid var(--line);background:#fff;color:var(--ink2)}
#cfm button:hover{background:var(--yin);color:var(--sys)}
#cfm .cfm-yes{background:var(--yinb);border-color:var(--yinb);color:#fff;font-weight:700}
#cfm .cfm-yes:hover{background:var(--sys2);color:#fff}

.actions{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:12px}
.go{font-family:inherit;font-size:15px;font-weight:700;color:#fff;background:var(--yinb);
border:1px solid var(--yinb);border-radius:6px;padding:9px 30px;cursor:pointer;transition:.15s}
.go:hover{background:var(--sys2);border-color:var(--sys2)}
.go:active{transform:translateY(1px)}
.ghost{font-family:inherit;font-size:13.5px;color:var(--ink2);background:#fff;
border:1px solid var(--line);border-radius:6px;padding:8px 16px;cursor:pointer}
.ghost:hover{background:var(--yin);color:var(--sys);border-color:var(--yinb)}
.hint{color:var(--ink3);font-size:12.5px}

#out{display:none}
#out.on{display:block}
.sent{margin:0 0 20px;padding:0 0 16px;border-bottom:1px dashed var(--line)}
.sent:last-child{border-bottom:0;margin-bottom:0;padding-bottom:0}
.sent .no{display:inline-block;font-size:11.5px;color:var(--ink3);
border:1px solid var(--line2);border-radius:10px;padding:0 7px;margin-right:8px;vertical-align:2px}
.hanline{font-size:26px;line-height:2.0;letter-spacing:.04em;word-break:break-word}
.pyline{font-size:17px;line-height:2.0;color:var(--sys);
letter-spacing:.02em;word-break:break-word;margin-top:2px}
.pyline.plain{font-size:19px}

.tok{display:inline-block;position:relative;cursor:pointer;border-radius:4px;
padding:0 1px;transition:.12s;white-space:pre}
.tok:hover{background:var(--yin)}
.tok.var{color:var(--warn)}
.tok.var::after{content:"";position:absolute;left:1px;right:1px;bottom:-1px;height:2px;
background:var(--warn);border-radius:1px;opacity:.7}
.tok.unk{color:var(--ink3);text-decoration:underline dotted var(--ink3)}
.tok.picked{background:#fff3d6;box-shadow:inset 0 0 0 1px var(--sep)}
.tokword{display:inline-block;margin-right:.34em}
.punct-tok{color:var(--ink2);cursor:default;white-space:pre}
.punct-tok:hover{background:none}

#pop{display:none;position:fixed;z-index:300;background:#fff;border:1px solid var(--line);
border-radius:8px;box-shadow:0 8px 28px rgba(26,82,118,.18);max-width:min(92vw,470px);
overflow:hidden}
#pop.on{display:block}
#pop .ph{padding:8px 12px;background:var(--yin);border-bottom:1px solid var(--line2);
display:flex;align-items:center;gap:8px;flex-wrap:wrap}
#pop .ph b{font-size:20px;color:var(--sys)}
#pop .ph .alt{font-size:12px;color:var(--ink2)}
#pop .ph .close{margin-left:auto;cursor:pointer;color:var(--ink2);font-size:18px;
line-height:1;padding:2px 6px;border-radius:4px}
#pop .ph .close:hover{background:#fff;color:var(--warn)}
#pop .pb{max-height:min(60vh,430px);overflow:auto;padding:6px 0}
#pop .row{display:flex;gap:10px;padding:8px 14px;cursor:pointer;align-items:baseline;
border-left:3px solid transparent;flex-wrap:wrap}
#pop .row:hover{background:var(--yin)}
#pop .row.sel{background:#fff3d6;border-left-color:var(--sep)}
#pop .row .syl{font-size:16px;color:var(--sys);font-weight:700;min-width:76px}
#pop .row .ipa{color:var(--ink2);font-size:14px;min-width:92px}
#pop .row .pos{font-size:12.5px;color:var(--ink2);background:#f4f8fd;border:1px solid var(--line2);
border-radius:4px;padding:1px 7px;white-space:nowrap}
#pop .row .note{font-size:12.5px;color:var(--ink3);flex-basis:100%}
#pop .row .chtag{font-size:12.5px;color:var(--gold);flex-basis:100%}
#pop .noread{padding:14px;color:var(--ink3);font-size:13.5px}

.notebar{margin-top:10px;font-size:13px;color:var(--ink2);background:#f4f8fd;
border-left:3px solid var(--line);padding:8px 12px;border-radius:0 6px 6px 0}
.notebar.warn{background:var(--warnbg);border-left-color:#e8b4b4;color:#8c3a2f}
.notebar.ok{background:var(--okbg);border-left-color:#a8d5ba;color:#256b45}
.notebar code{background:#fff;border:1px solid var(--line2);
border-radius:3px;padding:0 4px;color:var(--sys)}

.stats{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.stat{background:#f4f8fd;border:1px solid var(--line2);border-radius:6px;
padding:6px 12px;font-size:12.5px;color:var(--ink2)}
.stat b{color:var(--sys);font-size:15px;margin-right:4px}

table.rules{border-collapse:collapse;width:100%;font-size:13.5px;margin-top:6px}
table.rules th,table.rules td{border:1px solid var(--line2);padding:6px 10px;text-align:left;
vertical-align:top}
table.rules th{background:var(--yin);color:var(--sys);font-weight:700;white-space:nowrap}
table.rules td code{color:var(--sys);background:#f4f8fd;border-radius:3px;padding:0 4px}
table.rules tr:nth-child(even) td{background:#fbfdff}

footer{margin-top:30px;padding-top:14px;border-top:1px solid var(--line2);
color:var(--ink3);font-size:12.5px;text-align:center;line-height:1.9}
footer a{color:var(--ink2)}
footer a:hover{color:var(--yinb)}

@media(max-width:640px){
.wrap{padding:16px 12px 60px}
h1{font-size:21px;padding-right:0}
.lang-switcher{position:static;margin-bottom:8px;text-align:right}
.hanline{font-size:22px}
.pyline{font-size:15.5px}
.pyline.plain{font-size:17px}
.card{padding:12px 13px}
.go{flex:1;padding:10px 18px}
table.rules{font-size:12.5px}
}
"""


# ============================================================ BODY
BODY = r"""
<div class="tricolor-bar"></div>
<div class="wrap">

<header class="top">
  <div class="lang-switcher">
    <button class="lang-btn" id="langBtn" onclick="toggleLang()" aria-haspopup="true">
      <span id="langCur">漢語</span> ▾
    </button>
    <div class="lang-menu" id="langMenu">
      <button data-lang="wu" onclick="pickLang('wu')">漢語</button>
      <button data-lang="en" onclick="pickLang('en')">English</button>
      <button data-lang="ja" onclick="pickLang('ja')">日本語</button>
    </div>
  </div>
  <h1 id="i-h1">蘇滬混合腔拼音轉換器</h1>
  <p class="sub" id="i-sub"></p>
  <div class="syncbar" id="syncbar"><span class="dot"></span><span id="syncText"></span></div>
</header>

<section>
  <div class="modes">
    <button class="mode-btn on" data-mode="han" onclick="setMode('han')" id="m-han"></button>
    <button class="mode-btn" data-mode="py" onclick="setMode('py')" id="m-py"></button>
    <span class="sep"></span>
    <button class="mode-btn on" data-out="tone" onclick="setOut('tone')" id="o-tone"></button>
    <button class="mode-btn" data-out="rom" onclick="setOut('rom')" id="o-rom"></button>
    <span class="sep"></span>
    <button class="mode-btn huhe" id="h-btn" onclick="toggleHuhe()" aria-haspopup="true">
      <span id="i-huhe">河湖韻處理</span><span id="huheCur"></span> ▾
    </button>
    <div class="huhe-menu" id="huheMenu">
      <button data-huhe="default" onclick="pickHuhe('default')" id="h-default"></button>
      <button data-huhe="hu" onclick="pickHuhe('hu')" id="h-hu"></button>
      <button data-huhe="he" onclick="pickHuhe('he')" id="h-he"></button>
    </div>
  </div>

  <div class="card">
    <textarea id="src" spellcheck="false" autocomplete="off" autocorrect="off"
      autocapitalize="off"></textarea>
    <div id="segview"></div>
    <div class="actions">
      <button class="go" id="btnGo" onclick="doConvert()"></button>
      <button class="ghost" id="btnClear" onclick="doClear()"></button>
      <button class="ghost" id="btnCopy" onclick="doCopy()" style="display:none"></button>
      <span class="hint" id="i-hint"></span>
    </div>
    <div class="notebar" id="segHint" style="display:none"></div>
  </div>
</section>

<section id="outSec" style="display:none">
  <h2 id="i-out-title"></h2>
  <div class="card" id="out"></div>
</section>

<section id="rulesSec">
  <h2 id="i-rules-title"></h2>
  <div class="card" id="rulesBody"></div>
</section>

<section id="statsSec" style="display:none">
  <h2 id="i-stats-title"></h2>
  <div class="stats" id="statsBody"></div>
</section>

<footer id="i-footer"></footer>
</div>

<div id="pop">
  <div class="ph"><b id="popCh"></b><span class="alt" id="popAlt"></span>
    <span class="close" onclick="closePop()">×</span></div>
  <div class="pb" id="popBody"></div>
</div>
"""


# ============================================================ JS
JS = r"""
/* ===================================================================
   蘇滬混合腔拼音轉換器 —— 前端
   -------------------------------------------------------------------
   本頁**不推導字音**。所有讀音來自字音站的 DB_suhu.json（經 tools/ 預處理）：
     dict.json     chars（繁字→[[音節,音標,註記],...]）/ s2t / pos
     defaults.json 逐字預設音
     words.json    詞組既定讀音（候選已按與逐字預設的一致度排序）
     lexicon.json  分詞詞表（只收吳語詞，不含普通話詞庫）
   =================================================================== */

var DICT=null, DEFAULTS=null, WORDS=null, LEX=null, META=null, RULES=null;
var LOADED=false;

var mode='han';       // han = 漢字拼音對照, py = 僅拼音
var outMode='tone';   // tone = 帶調拼音, rom = 拼音文
var lang='wu';
var huheMode='default';   // default | hu | he —— 河湖韻處理（優先於逐字默認音）
var HUHE=null;            // 湖/河變體對照表
var VARIANTS=null;        // 簡→繁候選組（仿切韻推導器的異體字展開）

/* 使用者選定的讀音：key = 全域字元索引, value = {ci: 繁候選索引, ri: 讀音索引} */
var picks={};
/* 使用者手動分詞：邊界位置集合（位置 i = 「第 i 個字之前切」） */
var seps=null;         // 使用者新增的切分點（Set<int>）
var sepsDeleted=null;  // 使用者刪除的自動切分點（Set<int>）
var lastText='';

/* ============================ 語言 ============================ */
var I18N={
wu:{
  h1:'蘇滬混合腔拼音轉換器',
  sub:'輸入漢字，輸出蘇滬混合腔拼音。字音即時取自字音站，本頁不自行推導。',
  m_han:'漢字拼音對照', m_py:'僅拼音',
  o_tone:'輸出帶調拼音', o_rom:'輸出拼音文',
  go:'轉換', clear:'清空', copy:'複製結果',
  hint:'支援繁體與簡體；標點與換行會切分句子。',
  out_title:'轉換結果', rules_title:'拼音文規則', stats_title:'資料統計',
  seg_hint:'已自動分詞。拖動小豎槓可移動；右鍵刪除；點字與字之間的淡淡小豎槓可新增分詞。拼音文按這個分詞連寫。',
  sync_loading:'正在讀取字音站資料…',
  sync_ok:'字音資料已就緒',
  sync_stale:'字音站有更新，本頁資料會在下次建置時同步（見 README）',
  sync_fail:'無法讀取字音資料，請檢查網路後重新整理',
  empty:'請先輸入漢字。', nocopy:'沒有可複製的內容。', copied:'已複製。',
  no_read:'此字在字音站未收錄。',
  alt_label:'簡體對應：', var_hint:'紅色為多音字，點擊可選擇其他讀音。',
  note_untone:'無調讀音', note_choosing:'點擊該字可從全部字音中挑選。',
  huhe:'河湖韻處理', huhe_default:'蘇滬混合腔默認', huhe_hu:'全走湖韻', huhe_he:'全走河韻',
  huhe_hint:'湖韻〔uᵝ〕與河韻〔əuᵝ〕是同一個音位的兩個音值變體。此設定優先於逐字默認音。',
  confirm:'確認', cancel:'取消',
  seg_add_q:'在此加分詞？', seg_del_q:'刪除這條分詞？',
  seg_hint2:'拖動小豎槓可移動；右鍵刪除；點字與字之間可加分詞。',
  footer:'字音資料來自 <a href="https://siqyin.github.io/wugniu_zyinzozin/" target="_blank" rel="noopener">吳語字音查詢</a>；韻圖位置標記來自 <a href="https://siqyin.github.io/wugniu_yundu/" target="_blank" rel="noopener">蘇滬混合腔韻圖</a>。本頁不自行推導字音。'
},
en:{
  h1:'Su-Hu Mixed Register Romanizer',
  sub:'Enter Han characters to get their Su-Hu mixed-register romanization. Readings come from the pronunciation database; nothing is derived here.',
  m_han:'Han + romanization', m_py:'Romanization only',
  o_tone:'With tone numbers', o_rom:'Orthographic romanization',
  go:'Convert', clear:'Clear', copy:'Copy result',
  hint:'Traditional and simplified characters both work; punctuation and line breaks split sentences.',
  out_title:'Result', rules_title:'Orthography rules', stats_title:'Data',
  seg_hint:'Segmented automatically (Wu vocabulary only, no Mandarin word list). Click the gold bars to split or merge words; the romanization follows this segmentation.',
  sync_loading:'Loading pronunciation data…',
  sync_ok:'Data ready',
  sync_stale:'Upstream has newer readings; this page syncs on the next build (see README).',
  sync_fail:'Could not load pronunciation data. Check your connection and reload.',
  empty:'Please enter some characters first.', nocopy:'Nothing to copy.', copied:'Copied.',
  no_read:'This character is not in the database.',
  alt_label:'Simplified for: ', var_hint:'Red characters have multiple readings; click to choose.',
  note_untone:'toneless reading', note_choosing:'Click the character to pick among all readings.',
  huhe:'Hu/He finals', huhe_default:'Su-Hu default', huhe_hu:'All Hu', huhe_he:'All He',
  huhe_hint:'Hu [uᵝ] and He [əuᵝ] are free variants of one phoneme. This overrides per-character defaults.',
  confirm:'Confirm', cancel:'Cancel',
  seg_add_q:'Add a word break here?', seg_del_q:'Delete this word break?',
  seg_hint2:'Drag a bar to move it, right-click to delete, click between characters to add.',
  footer:'Readings from <a href="https://siqyin.github.io/wugniu_zyinzozin/" target="_blank" rel="noopener">Wu pronunciation lookup</a>; rhyme-chart positions from <a href="https://siqyin.github.io/wugniu_yundu/" target="_blank" rel="noopener">the Su-Hu rhyme chart</a>. Nothing is derived on this page.'
},
ja:{
  h1:'蘇滬混合腔ローマ字変換器',
  sub:'漢字を入力すると蘇滬混合腔のローマ字を出力します。字音は字音サイトのデータによるもので、本ページでは推導しません。',
  m_han:'漢字＋ローマ字', m_py:'ローマ字のみ',
  o_tone:'声調数字つき', o_rom:'正書法ローマ字',
  go:'変換', clear:'クリア', copy:'結果をコピー',
  hint:'繁体字・簡体字ともに対応。句読点と改行で文を区切ります。',
  out_title:'変換結果', rules_title:'正書法の規則', stats_title:'データ',
  seg_hint:'自動分詞しました（呉語の語彙のみ、普通話の語彙表は不使用）。金色の縦線をクリックすると語を分割・統合できます。',
  sync_loading:'字音データを読み込み中…',
  sync_ok:'データ準備完了',
  sync_stale:'字音サイトに更新があります。次回ビルドで反映されます（README 参照）。',
  sync_fail:'字音データを取得できません。接続を確認して再読み込みしてください。',
  empty:'漢字を入力してください。', nocopy:'コピーする内容がありません。', copied:'コピーしました。',
  no_read:'この字はデータベースにありません。',
  alt_label:'簡体字：', var_hint:'赤字は多音字です。クリックで読みを選べます。',
  note_untone:'声調なしの読み', note_choosing:'文字をクリックすると全ての読みから選べます。',
  huhe:'湖韻／河韻の扱い', huhe_default:'蘇滬混合腔デフォルト', huhe_hu:'全て湖韻', huhe_he:'全て河韻',
  huhe_hint:'湖韻〔uᵝ〕と河韻〔əuᵝ〕は同一音素の自由変異です。この設定は字ごとの既定読みより優先されます。',
  confirm:'確認', cancel:'キャンセル',
  seg_add_q:'ここに分かち書きを追加しますか？', seg_del_q:'この分かち書きを削除しますか？',
  seg_hint2:'縦線をドラッグで移動、右クリックで削除、文字間をクリックで追加。',
  footer:'字音は<a href="https://siqyin.github.io/wugniu_zyinzozin/" target="_blank" rel="noopener">吳語字音查詢</a>、韻図位置は<a href="https://siqyin.github.io/wugniu_yundu/" target="_blank" rel="noopener">蘇滬混合腔韻圖</a>より。本ページでは推導しません。'
}};
function t(k){ return (I18N[lang]&&I18N[lang][k])||I18N.wu[k]||k; }

function applyLang(){
  document.documentElement.lang = lang==='en'?'en':(lang==='ja'?'ja':'zh-Hant');
  var ids={h1:'i-h1',sub:'i-sub',m_han:'m-han',m_py:'m-py',o_tone:'o-tone',o_rom:'o-rom',
    go:'btnGo',clear:'btnClear',copy:'btnCopy',hint:'i-hint',out_title:'i-out-title',
    rules_title:'i-rules-title',stats_title:'i-stats-title',seg_hint:'segHint'};
  for(var k in ids){ var el=document.getElementById(ids[k]); if(el) el.textContent=t(k); }
  document.getElementById('i-footer').innerHTML=t('footer');
  document.getElementById('src').placeholder=t('hint');
  document.getElementById('langCur').textContent=lang==='en'?'English':(lang==='ja'?'日本語':'漢語');
  if(LOADED) setSync('ok',t('sync_ok'));
  syncHuheUI();
  renderRules();
  if(document.getElementById('out').dataset.done==='1') doConvert();
}
function toggleLang(){ document.getElementById('langMenu').classList.toggle('on'); }
function pickLang(l){ lang=l; try{localStorage.setItem('tsoewoe/lang',l);}catch(e){}
  document.getElementById('langMenu').classList.remove('on'); applyLang(); }
document.addEventListener('click',function(e){
  if(!e.target.closest('.lang-switcher')) document.getElementById('langMenu').classList.remove('on');
  if(!e.target.closest('.huhe')) document.getElementById('huheMenu').classList.remove('on'); });

/* ============================ 模式 ============================ */
function setMode(m){
  mode=m;
  document.querySelectorAll('[data-mode]').forEach(function(b){
    b.classList.toggle('on',b.dataset.mode===m); });
  updateSegVisibility();
  if(document.getElementById('out').dataset.done==='1') doConvert();
}
function setOut(o){
  outMode=o;
  document.querySelectorAll('[data-out]').forEach(function(b){
    b.classList.toggle('on',b.dataset.out===o); });
  updateSegVisibility();
  if(document.getElementById('out').dataset.done==='1') doConvert();
}
function needSeg(){ return outMode==='rom'; }
function updateSegVisibility(){
  var on=needSeg();
  document.getElementById('segview').classList.toggle('on',on);
  document.getElementById('src').style.display=on?'none':'block';
  document.getElementById('segHint').style.display=on?'block':'none';
  if(on){ lastText=document.getElementById('src').value; renderSegEditor(); }
  renderRules();
}

/* ============================ 載入 ============================ */
function setSync(kind,text){
  document.getElementById('syncbar').className='syncbar'+(kind==='ok'?' ok':(kind==='warn'?' warn':''));
  document.getElementById('syncText').textContent=text;
}
function getJSON(u,fallback){
  return fetch(u,{cache:'no-cache'}).then(function(r){
    if(!r.ok) throw new Error(u); return r.json();
  }).catch(function(){ if(fallback!==undefined) return fallback; throw new Error(u); });
}
function loadAll(){
  setSync('',t('sync_loading'));
  Promise.all([
    getJSON('data/dict.json'),
    getJSON('data/defaults.json',{}),
    getJSON('data/words.json',{}),
    getJSON('data/lexicon.json',{words:{},maxLen:1}),
    getJSON('data/meta.json',null),
    getJSON('data/rules.json',{}),
    getJSON('data/huhe.json',{}),
    getJSON('data/variants.json',{})
  ]).then(function(r){
    DICT=r[0]; DEFAULTS=r[1]; WORDS=r[2]; LEX=r[3]; META=r[4]; RULES=r[5];
    HUHE=r[6]; VARIANTS=r[7];
    LOADED=true; setSync('ok',t('sync_ok')); renderStats();
    checkUpstream();
  }).catch(function(e){ console.error(e); setSync('warn',t('sync_fail')); });
}

/* ============================ 與字音站聯動 ============================
   本頁的字音是字音站 DB_suhu.json 的預處理快照（data/*.json）。
   這裡在背景比對「字音站線上那條 DB_suhu.json」的大小與 Last-Modified，
   若與我們快照時記錄的不同，就在狀態條提示「有新版字音，請更新」。
   真正的重建由 tools/update_from_upstream.py 完成（見 README）。
   ------------------------------------------------------------------- */
function checkUpstream(){
  if(!META||!META.db_url) return;
  var ctrl = (typeof AbortController!=='undefined') ? new AbortController() : null;
  var timer = setTimeout(function(){ if(ctrl) ctrl.abort(); }, 8000);
  var sep = META.db_url.indexOf('?')>=0 ? '&' : '?';
  fetch(META.db_url + sep + 't=' + Date.now(), {cache:'no-store'})
    .then(function(r){
      clearTimeout(timer);
      if(!r.ok) throw new Error('upstream '+r.status);
      var len = r.headers.get('Content-Length');
      var lm  = r.headers.get('Last-Modified');
      var sig = (len||'') + '|' + (lm||'');
      var known = META.upstream_sig || '';
      if(known && sig && sig !== known){
        setSync('warn', t('sync_stale'));
      }else if(sig){
        setSync('ok', t('sync_ok'));
      }
    })
    .catch(function(){ clearTimeout(timer); /* 連不上就維持本地快照，不報錯 */ });
}

/* ============================ 河湖韻按鈕 ============================ */
function toggleHuhe(){
  document.getElementById('huheMenu').classList.toggle('on');
}
function pickHuhe(m){
  huheMode=m;
  try{ localStorage.setItem('tsoewoe/huhe',m); }catch(e){}
  document.getElementById('huheMenu').classList.remove('on');
  syncHuheUI();
  if(document.getElementById('out').dataset.done==='1') doConvert();
}
function syncHuheUI(){
  var names={default:'huhe_default',hu:'huhe_hu',he:'huhe_he'};
  var shortNames={default:'默認',hu:'湖',he:'河'};
  document.getElementById('i-huhe').textContent=t('huhe');
  document.getElementById('h-default').textContent=t('huhe_default');
  document.getElementById('h-hu').textContent=t('huhe_hu');
  document.getElementById('h-he').textContent=t('huhe_he');
  document.querySelectorAll('[data-huhe]').forEach(function(b){
    b.classList.toggle('on', b.dataset.huhe===huheMode);
  });
  var cur = huheMode==='default' ? '' : (huheMode==='hu'?'〔湖〕':'〔河〕');
  document.getElementById('huheCur').textContent=cur;
  document.getElementById('h-btn').classList.toggle('on', huheMode!=='default');
}

/* ============================ 讀音 ============================ */
/* 某字的候選組 —— 仿切韻推導器 convertArticle 的「異體字展開」思路：
   把該字與它對應的繁體字一起查，每個「不同的字 + 不同讀音」就是一個候選。
   繁體為標準形，所以繁體排在前面；一簡多繁時前端標紅，讓使用者自己挑。
   ------------------------------------------------------------------- */
function candidates(ch, wordHint){
  if(!DICT) return [];

  /* ① 詞級例外：如「个人」「个体」裡的「个」→「個」 */
  var cw=(RULES&&RULES.convertWords)||{};
  var w=wordHint||'';
  var trWord=cw[w];
  if(!trWord){
    for(var k in cw){ if(cw[k]===w){ trWord=w; break; } }
  }
  if(trWord && w.length===trWord.length){
    var pos=w.indexOf(ch);
    if(pos>=0){
      var trCh=trWord.charAt(pos);
      if(trCh && trCh!==ch && DICT.chars[trCh]){
        return [{ch:trCh, readings:DICT.chars[trCh], converted:true, from:ch}];
      }
    }
  }

  /* ② 不轉繁的字（如「个」）：固定用本字 */
  var noConv=(RULES&&RULES.noConvert)||[];
  var isNoConv = noConv.indexOf(ch)>=0;

  /* ③ 候選組：VARIANTS.s2t[ch] 已按「繁體在前、本字在後」排好 */
  var list = (VARIANTS && VARIANTS.s2t && VARIANTS.s2t[ch]) || null;
  if(isNoConv) list = DICT.chars[ch] ? [ch] : list;

  var out=[], seen={};
  if(list){
    list.forEach(function(trad){
      if(DICT.chars[trad] && !seen[trad]){
        seen[trad]=1;
        out.push({ch:trad, readings:DICT.chars[trad],
                  converted: trad!==ch, from: ch});
      }
    });
  }
  /* ④ 保底：候選組沒收錄時，本字若在字典裡就直接用 */
  if(!out.length && DICT.chars[ch]){
    out.push({ch:ch, readings:DICT.chars[ch], converted:false, from:ch});
  }
  return out;
}

/* 該字目前選定的讀音。wordHint = 該字所屬的詞（單字成詞就是它自己） */
function resolve(ch,idx,wordHint){
  var cands=candidates(ch, wordHint);
  if(!cands.length) return {ok:false,ch:ch};
  var p=picks[idx]||{};
  var ci=(p.ci!==undefined && p.ci<cands.length)?p.ci:0;
  var rs=cands[ci].readings;
  if(!rs || !rs.length) return {ok:false,ch:ch};
  var ri=(p.ri!==undefined && p.ri<rs.length)?p.ri:0;

  if(p.ri===undefined){
    var want=null;
    var isSingle = wordHint && wordHint.length===1;
    /* ① 單字成詞特例（如「在|我|該搭」的在 → leq8） */
    if(isSingle && RULES && RULES.singleOverride && RULES.singleOverride[ch]){
      want=RULES.singleOverride[ch];
    }
    /* ② 詞組既定讀音（繁體形為標準） */
    if(!want && wordHint && WORDS && WORDS[wordHint] && WORDS[wordHint].length && !isSingle){
      var w=WORDS[wordHint][0];
      for(var k=0;k<wordHint.length;k++){
        if(wordHint[k]===ch && w[k]){ want=w[k]; break; }
      }
    }
    /* ③ 逐字預設音（簡體字用它繁體對應的預設） */
    if(!want){
      want=DEFAULTS[cands[ci].ch];
      if(!want && VARIANTS && VARIANTS.s2t){
        var grp=VARIANTS.s2t[ch]||[];
        for(var g=0;g<grp.length && !want;g++){ want=DEFAULTS[grp[g]]; }
      }
    }
    if(want){ for(var i=0;i<rs.length;i++){ if(rs[i][0]===want){ ri=i; break; } } }
  }
  var rd=rs[ri];
  /* 河湖韻規範化：優先級高於逐字默認音 —— 原型先按規則選出，再規範化 */
  var shown=normHuhe(rd[0]);
  var shownIpa=ipaOf(shown, rd[0]);
  return {ok:true,ch:cands[ci].ch,ci:ci,ri:ri,readings:rs,cands:cands,
          syl:shown, origSyl:rd[0], ipa:shownIpa,
          note:rd[2]||'',
          /* 標紅條件：多個繁體候選、多個讀音，或本字被折成繁體 */
          multi:(cands.length>1 || rs.length>1 || cands[ci].converted===true)};
}

/* ============================ 河湖韻規範化 ============================
   湖韻 u[uᵝ] 與河韻 ou[əuᵝ] 是同一個音位的兩個音值變體。
   逐字默認音／詞內特例等規則寫的是「原型」（dict.json 原樣），
   套完規則之後，才依 huheMode 把音節規範化成湖形或河形。
   —— 因此本規範化的優先級高於逐字默認音。
   ------------------------------------------------------------------- */
var HUHE_VAR_INIS = ['t','th','n','l','k','kh','g','h','ng','ts','tsh','s','z'];

function isHuheSyl(syl){
  if(!syl) return false;
  var m=/^([a-z]+)([0-9])$/.exec(syl);
  if(!m) return false;
  var letters=m[1];
  var ini='';
  for(var i=0;i<INITIALS.length;i++){ if(letters.indexOf(INITIALS[i])===0){ ini=INITIALS[i]; break; } }
  var tail=letters.slice(ini.length);
  if(ini==='gh' && tail==='ou') return true;      /* 匣母河形，湖形為 wu */
  if(ini==='' && (tail==='u'||tail==='ou')) return true;
  if(ini==='' && tail==='wu') return true;
  if(HUHE_VAR_INIS.indexOf(ini)>=0 && (tail==='u'||tail==='ou')) return true;
  return false;
}

/* 把音節規範化成指定取向：'hu' 全走湖、'he' 全走河、其餘依默認規則 */
function normHuhe(syl){
  if(!HUHE || !isHuheSyl(syl)) return syl;
  var m=/^([a-z]+)([0-9])$/.exec(syl);
  if(!m) return syl;
  var letters=m[1], tone=m[2];
  var ini='';
  for(var i=0;i<INITIALS.length;i++){ if(letters.indexOf(INITIALS[i])===0){ ini=INITIALS[i]; break; } }
  var tail=letters.slice(ini.length);

  var wantHu;
  if(huheMode==='hu') wantHu=true;
  else if(huheMode==='he') wantHu=false;
  else {
    /* 默認：零聲母（u/wu）走湖；其餘有變體的聲母走河；匣母本就是河形 */
    if(ini==='') wantHu=true;
    else wantHu=(HUHE.defaultHe||[]).indexOf(ini)<0;
  }
  var target;
  if(wantHu){
    target = HUHE.toHu[syl];
    if(target) return target;
    /* 已是湖形就直接用 */
    if((ini===''&&tail==='u')||(ini===''&&tail==='wu')||
       (ini!=='gh'&&HUHE_VAR_INIS.indexOf(ini)>=0&&tail==='u')) return syl;
    return syl;
  } else {
    target = HUHE.toHe[syl];
    if(target) return target;
    if((ini===''&&tail==='ou')||(ini==='gh'&&tail==='ou')||
       (HUHE_VAR_INIS.indexOf(ini)>=0&&tail==='ou')) return syl;
    return syl;
  }
}

/* 給彈窗用：這個音節在目前取向下的顯示形 */
function displaySyl(syl){ return normHuhe(syl); }

/* 音標：依規範化後的音節查表；查不到就用原音節的音標 */
function ipaOf(syl, origSyl){
  if(!HUHE||!HUHE.ipa) return '';
  if(HUHE.ipa[syl]) return HUHE.ipa[syl];
  if(origSyl && HUHE.ipa[origSyl]) return HUHE.ipa[origSyl];
  return '';
}

/* ============================ 正字法 ============================ */
var INITIALS=['gn','ng','tsh','chi','shi','ji','ts','ph','th','kh','ci','gh',
              'p','b','m','f','v','t','d','n','l','k','g','h','s','z'];
var APOS={m:1,n:1,l:1,gn:1};
function splitSyl(s){
  var m=/^([a-z]+)([0-9])?$/.exec(s||'');
  if(!m) return null;
  var letters=m[1], tone=m[2]?+m[2]:null, ini='';
  for(var i=0;i<INITIALS.length;i++){ if(letters.indexOf(INITIALS[i])===0){ ini=INITIALS[i]; break; } }
  return {letters:letters,tone:tone,initial:ini,final:letters.slice(ini.length)};
}
/* 一個詞（音節陣列）→ 拼音文 */
function orthographize(syls){
  if(!syls.length) return '';
  var p=syls.map(splitSyl).filter(Boolean);
  if(!p.length) return '';
  var f=p[0], head;
  if(f.tone===1){ head="'"+f.letters; }
  else if(APOS[f.initial]&&(f.tone===3||f.tone===5||f.tone===7)){
    head = f.final ? (f.initial+"'"+f.final) : ("'"+f.letters);
  } else { head=f.letters; }
  var rest='';
  for(var i=1;i<p.length;i++) rest+=p[i].letters;
  return head+rest;
}
/* 句首字母大寫（無論前面有沒有小撇） */
function capitalizeFirst(s){
  for(var i=0;i<s.length;i++){
    if(/[a-z]/.test(s[i])) return s.slice(0,i)+s[i].toUpperCase()+s.slice(i+1);
  }
  return s;
}

/* ============================ 分詞 ============================ */
function isHan(c){ return /^[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]$/.test(c); }
function allHan(a){ for(var i=0;i<a.length;i++){ if(!isHan(a[i])) return false; } return true; }

/* 正向最大匹配：先取最長的吳語詞；同長度取權重高的 */
function autoSegment(chars){
  var out=[], i=0, n=chars.length, maxL=LEX?LEX.maxLen:1;
  while(i<n){
    if(!isHan(chars[i])){
      /* 標點／空白：附著在前一個詞上（「儂。」不拆成「儂|。」） */
      if(out.length) out[out.length-1].push(chars[i]);
      else out.push([chars[i]]);
      i++; continue;
    }
    var bestLen=1, bestW=0;
    var lim=Math.min(maxL,n-i);
    for(var L=lim;L>=2;L--){
      var sub=chars.slice(i,i+L);
      if(!allHan(sub)) continue;
      var w=chars.slice(i,i+L).join('');
      var wt=LEX&&LEX.words[w];
      if(wt&&(L>bestLen||(L===bestLen&&wt>bestW))){ bestLen=L; bestW=wt; }
    }
    out.push(chars.slice(i,i+bestLen));
    i+=bestLen;
  }
  return out;
}

/* 把句子切成「詞的陣列」。
   自動切分點來自詞表；使用者新增／刪除的切分點以 seps / sepsDeleted 覆蓋。
   注意：這裡的 pos 是「全文累計位置」，與 renderSegEditor 的計法必須一致。 */
var _segGpos = 0;   /* 由 splitSentencesForSeg 逐句累計 */

function segmentSentence(sent, startPos){
  var chars=Array.from(sent);
  var base=autoSegment(chars);
  var pos = (startPos===undefined) ? 0 : startPos;
  var hasManual = (seps && seps.size) || (sepsDeleted && sepsDeleted.size);
  var out=[], cur=[];
  for(var w=0;w<base.length;w++){
    var word=base[w];
    for(var i=0;i<word.length;i++){
      var isAutoBreak = (i===0 && w>0);
      var manualAdd = seps && seps.has(pos);
      var manualDel = sepsDeleted && sepsDeleted.has(pos);
      var doBreak;
      if(manualDel) doBreak=false;
      else if(manualAdd) doBreak=true;
      else doBreak=isAutoBreak;
      if(pos>0 && doBreak && cur.length){ out.push(cur); cur=[]; }
      cur.push(word[i]);
      pos++;
    }
  }
  if(cur.length) out.push(cur);
  return out;
}

/* 逐句套用、正確累計全文位置 */
function segmentAll(text){
  var res=[], pos=0;
  splitSentences(text).forEach(function(sent){
    res.push({sent:sent, words:segmentSentence(sent, pos), start:pos});
    pos += Array.from(sent).length;
  });
  return res;
}

/* ============================ 句子切分 ============================ */
var SENT_END='。！？!?…\n';
function splitSentences(text){
  var out=[], buf='';
  var chars=Array.from(text);
  for(var i=0;i<chars.length;i++){
    buf+=chars[i];
    if(SENT_END.indexOf(chars[i])>=0){ out.push(buf); buf=''; }
  }
  if(buf.trim()) out.push(buf);
  return out.filter(function(s){ return s.trim().length>0; });
}

/* ============================ 分詞編輯器 ============================
   自動切分點來自分詞詞表；使用者可以：
     · 拖動已有小豎槓到別處（移動）
     · 右鍵小豎槓 → 刪除
     · 點字與字之間的間隙 → 確認後新增
   實際切分 = 自動切分點 ∪ seps − sepsDeleted
   ------------------------------------------------------------------- */
function autoBoundaries(text){
  /* 回傳自動切分的邊界位置集合（全文累計字元位置） */
  var b=new Set(), gpos=0;
  splitSentences(text).forEach(function(sent){
    var words=segmentSentence(sent);
    words.forEach(function(word,wi){
      if(wi>0) b.add(gpos);
      gpos+=word.length;
    });
  });
  return b;
}

function effectiveBoundaries(text){
  var b=autoBoundaries(text);
  if(seps) seps.forEach(function(x){ b.add(x); });
  if(sepsDeleted) sepsDeleted.forEach(function(x){ b.delete(x); });
  /* 0 與 text.length 是句首句尾，不算切分點 */
  b.delete(0); b.delete(text.length);
  return b;
}

function renderSegEditor(){
  var text=lastText||'';
  var view=document.getElementById('segview');
  if(!text.trim()){ view.innerHTML=''; return; }
  if(seps===null) seps=new Set();
  if(sepsDeleted===null) sepsDeleted=new Set();

  var cuts=effectiveBoundaries(text);
  var chars=Array.from(text);
  var html='';
  for(var i=0;i<chars.length;i++){
    var c=chars[i];
    if(i>0){
      if(cuts.has(i)){
        html+='<span class="sepmark" data-pos="'+i+'" title="拖動可移動；右鍵刪除">|</span>';
      }else{
        html+='<span class="gap" data-pos="'+i+'" title="點擊在此加分詞"></span>';
      }
    }
    html+='<span class="seg" data-i="'+i+'">'+esc(c)+'</span>';
  }
  view.innerHTML=html;
}

/* ---- 找出滑鼠位置對應的「最接近字間隙」位置 ---- */
function nearestGap(view, clientX){
  var segs=view.querySelectorAll('.seg');
  if(!segs.length) return null;
  var best=null, bestDist=1e9;
  for(var i=0;i<segs.length;i++){
    var r=segs[i].getBoundingClientRect();
    /* 每個字的左右邊界都可能是間隙（位置 i 或 i+1） */
    var cands=[[i, Math.abs(clientX-r.left)],[i+1, Math.abs(clientX-r.right)]];
    for(var k=0;k<cands.length;k++){
      if(cands[k][1]<bestDist){ bestDist=cands[k][1]; best=cands[k][0]; }
    }
  }
  return best;
}

/* ---- 移動：拖動小豎槓 ---- */
var dragFrom=null, dragEl=null;
document.addEventListener('mousedown', function(e){
  var m = e.target.closest ? e.target.closest('#segview .sepmark') : null;
  if(!m) return;
  if(e.button!==0) return;          /* 只有左鍵拖動 */
  e.preventDefault();
  dragFrom = parseInt(m.getAttribute('data-pos'),10);
  dragEl = m;
  m.classList.add('dragging');
});

document.addEventListener('mouseover', function(e){
  if(dragFrom===null) return;
  var m = e.target.closest ? e.target.closest('#segview .sepmark') : null;
  if(m && m!==dragEl) m.classList.add('dropzone');
});
document.addEventListener('mouseout', function(e){
  var m = e.target.closest ? e.target.closest('#segview .sepmark') : null;
  if(m) m.classList.remove('dropzone');
});

document.addEventListener('mouseup', function(e){
  if(dragFrom===null){ return; }
  var view=document.getElementById('segview');
  var from=dragFrom;
  if(dragEl) dragEl.classList.remove('dragging');
  var to=null;

  /* 若放開在另一個小豎槓上 → 合併到那個位置（等於刪掉自己） */
  var over = e.target.closest ? e.target.closest('#segview .sepmark') : null;
  if(over && over!==dragEl){
    to = parseInt(over.getAttribute('data-pos'),10);
  }else if(view.contains(e.target) || e.target===view){
    to = nearestGap(view, e.clientX);
  }
  dragFrom=null;
  if(dragEl) dragEl.classList.remove('dropzone');
  dragEl=null;

  if(to===null || to===from) { renderSegEditor(); return; }
  moveCut(text_of(), from, to);
});

function text_of(){ return lastText||''; }

function moveCut(text, from, to){
  if(seps===null) seps=new Set();
  if(sepsDeleted===null) sepsDeleted=new Set();
  var n=text.length;
  if(to<=0 || to>=n) return;
  var auto=autoBoundaries(text);
  /* 起點：從原位置移除（若原本是自動切分，記入 deleted；否則從 seps 移除） */
  if(auto.has(from)) sepsDeleted.add(from);
  seps.delete(from);
  /* 終點：新增（若終點本來是自動切分，取消其 deleted） */
  if(auto.has(to)) sepsDeleted.delete(to);
  else seps.add(to);
  renderSegEditor();
  if(document.getElementById('out').dataset.done==='1') doConvert();
}

/* ---- 刪除：右鍵小豎槓 ---- */
document.addEventListener('contextmenu', function(e){
  var m = e.target.closest ? e.target.closest('#segview .sepmark') : null;
  if(!m) return;
  e.preventDefault();
  var pos=parseInt(m.getAttribute('data-pos'),10);
  if(isNaN(pos)) return;
  showConfirm(t('seg_del_q'), function(){
    if(seps===null) seps=new Set();
    if(sepsDeleted===null) sepsDeleted=new Set();
    var auto=autoBoundaries(text_of());
    if(auto.has(pos)) sepsDeleted.add(pos);
    seps.delete(pos);
    renderSegEditor();
    if(document.getElementById('out').dataset.done==='1') doConvert();
  });
});

/* ---- 新增：點字間隙 ---- */
document.addEventListener('click', function(e){
  var g = e.target.closest ? e.target.closest('#segview .gap') : null;
  if(!g) return;
  e.preventDefault();
  e.stopPropagation();
  var pos=parseInt(g.getAttribute('data-pos'),10);
  if(isNaN(pos)) return;
  showConfirm(t('seg_add_q'), function(){
    if(seps===null) seps=new Set();
    if(sepsDeleted===null) sepsDeleted=new Set();
    var auto=autoBoundaries(text_of());
    if(auto.has(pos)) sepsDeleted.delete(pos);
    seps.add(pos);
    renderSegEditor();
    if(document.getElementById('out').dataset.done==='1') doConvert();
  });
});

/* ---- 極簡確認彈窗（不用原生 confirm，維持視覺一致） ---- */
function showConfirm(msg, onYes){
  closeConfirm();
  var box=document.createElement('div');
  box.id='cfm';
  box.innerHTML='<div class="cfm-in"><p>'+esc(msg)+'</p>'
    + '<div class="cfm-btns"><button class="cfm-no">'+esc(t('cancel'))+'</button>'
    + '<button class="cfm-yes">'+esc(t('confirm'))+'</button></div></div>';
  document.body.appendChild(box);
  box.querySelector('.cfm-yes').onclick=function(ev){ ev.stopPropagation(); closeConfirm(); onYes(); };
  box.querySelector('.cfm-no').onclick=function(ev){ ev.stopPropagation(); closeConfirm(); };
  box.onclick=function(ev){ if(ev.target===box) closeConfirm(); };
}
function closeConfirm(){
  var b=document.getElementById('cfm');
  if(b) b.remove();
}

/* ============================ 轉換 ============================ */
function doConvert(){
  if(!LOADED){ setSync('warn',t('sync_fail')); return; }
  var text=needSeg()?lastText:document.getElementById('src').value;
  if(!text||!text.trim()){ alertBox(t('empty')); return; }
  lastText=text;

  var sentences=splitSentences(text);
  var outEl=document.getElementById('out');
  outEl.innerHTML='';
  outEl.dataset.done='1';
  /* #out 的 CSS 是 display:none，必須加上 .on 才會顯示 —— 否則內容生成了卻是空白 */
  outEl.classList.add('on');
  document.getElementById('outSec').style.display='block';
  document.getElementById('btnCopy').style.display='inline-block';

  var gIdx=0, unknowns=[], varCount=0;

  /* 先算出每句的（起始位置, 詞陣列），確保分詞點的全域位置正確 */
  var segPlan = segmentAll(text);
  var sentIndex = 0;

  sentences.forEach(function(sent,si){
    var words = segPlan[si] ? segPlan[si].words : segmentSentence(sent, segPlan[si] ? segPlan[si].start : 0);

    /* 先把這一句的每個字解析好：word 是它所屬的詞（給詞組既定讀音用） */
    var plan=[];   /* [{ch, idx, isHan, res, wordStart}] */
    words.forEach(function(word){
      for(var i=0;i<word.length;i++){
        var ch=word[i];
        var idx=gIdx;
        var isH=isHan(ch);
        plan.push({ch:ch, idx:idx, isHan:isH,
                   res: isH?resolve(ch,idx,word.join('')):null,
                   wordStart:i===0});
        gIdx++;
      }
    });

    var div=document.createElement('div');
    div.className='sent';
    var no=document.createElement('span');
    no.className='no'; no.textContent=(si+1);
    div.appendChild(no);

    /* ---- 漢字行 ---- */
    if(mode==='han'){
      var hanline=document.createElement('div');
      hanline.className='hanline';
      plan.forEach(function(it){
        if(!it.isHan){
          var sp=document.createElement('span');
          sp.className='punct-tok'; sp.textContent=it.ch;
          hanline.appendChild(sp); return;
        }
        var r=it.res;
        var span=document.createElement('span');
        span.className='tok';
        if(!r.ok){ span.classList.add('unk'); span.textContent=it.ch; unknowns.push(it.ch); }
        else{
          span.textContent=r.ch;
          if(r.multi){ span.classList.add('var'); varCount++; }
          if(picks[it.idx]) span.classList.add('picked');
          (function(ii,ss){ span.onclick=function(ev){ ev.stopPropagation(); openPop(ii,ss); }; })(it.idx,span);
        }
        hanline.appendChild(span);
      });
      div.appendChild(hanline);
    }

    /* ---- 拼音行 ---- */
    var pyline=document.createElement('div');
    pyline.className='pyline'+(mode==='py'?' plain':'');

    if(outMode==='rom'){
      /* 拼音文：詞內連寫、詞間空格、句首大寫 */
      /* 詞與詞之間空格；以標點開頭的「詞」緊貼前文、不另加空格 */
      var out='', pos=0;
      words.forEach(function(word){
        var syls=[], ok=true, allPunct=true;
        for(var i=0;i<word.length;i++){
          var it=plan[pos+i];
          if(!it) continue;
          if(it.isHan){ allPunct=false; }
          if(!it.isHan) continue;
          if(!it.res.ok){ ok=false; continue; }
          syls.push(it.res.syl);
        }
        var piece=(ok&&syls.length)?orthographize(syls):word.join('');
        if(!out||allPunct) out+=piece;
        else out+=' '+piece;
        pos+=word.length;
      });
      pyline.textContent=capitalizeFirst(out);
    } else {
      /* 帶調拼音：逐字輸出，可點 */
      var pos2=0;
      words.forEach(function(word){
        var wspan=document.createElement('span');
        wspan.className='tokword';
        for(var i=0;i<word.length;i++){
          var it=plan[pos2+i];
          if(!it){ continue; }
          if(!it.isHan){
            var p=document.createElement('span');
            p.className='punct-tok'; p.textContent=it.ch;
            wspan.appendChild(p); continue;
          }
          var r=it.res;
          var s=document.createElement('span');
          s.className='tok';
          if(!r.ok){ s.classList.add('unk'); s.textContent=it.ch; }
          else{
            s.textContent=r.syl;
            if(r.multi){ s.classList.add('var'); varCount++; }
            if(picks[it.idx]) s.classList.add('picked');
            (function(ii,ss){ s.onclick=function(ev){ ev.stopPropagation(); openPop(ii,ss); }; })(it.idx,s);
          }
          wspan.appendChild(s);
        }
        pyline.appendChild(wspan);
        pos2+=word.length;
      });
    }
    div.appendChild(pyline);
    outEl.appendChild(div);
  });

  /* 提示 */
  var tips=[];
  if(unknowns.length){
    var uniq=[]; unknowns.forEach(function(c){ if(uniq.indexOf(c)<0) uniq.push(c); });
    tips.push('<b>'+esc(uniq.join('、'))+'</b> '+esc(t('no_read')));
  }
  if(varCount) tips.push(esc(t('var_hint'))+' '+esc(t('note_choosing')));
  if(tips.length){
    var nb=document.createElement('div');
    nb.className='notebar warn';
    nb.innerHTML=tips.join('<br>');
    outEl.appendChild(nb);
  }
}

/* 依全域索引取字 */
function charAtFlatIndex(idx){
  var sentences=splitSentences(lastText);
  var g=0;
  for(var s=0;s<sentences.length;s++){
    var words=segmentSentence(sentences[s]);
    for(var w=0;w<words.length;w++){
      for(var c=0;c<words[w].length;c++){
        if(g===idx) return words[w][c];
        g++;
      }
    }
  }
  return null;
}

/* 依全域索引取該字所屬的詞 */
function wordAtFlatIndex(idx){
  var sentences=splitSentences(lastText);
  var g=0;
  for(var s=0;s<sentences.length;s++){
    var words=segmentSentence(sentences[s]);
    for(var w=0;w<words.length;w++){
      var n=words[w].length;
      if(idx>=g && idx<g+n) return words[w].join('');
      g+=n;
    }
  }
  return null;
}

/* ============================ 彈出：選字音 ============================ */
var popIdx=null, popWord=null;
function openPop(idx,anchor){
  if(!LOADED) return;
  var ch=charAtFlatIndex(idx);
  if(!ch) return;
  popIdx=idx;
  popWord=wordAtFlatIndex(idx);
  var cands=candidates(ch, popWord||null);
  document.getElementById('popCh').textContent=ch;
  var body=document.getElementById('popBody');
  body.innerHTML='';

  if(!cands.length){
    document.getElementById('popAlt').textContent='';
    body.innerHTML='<div class="noread">'+esc(t('no_read'))+'</div>';
  } else {
    /* 繁體候選：簡體輸入時列出它對應的全部繁體，讓使用者挑 */
    var tradList=cands.map(function(c){return c.ch;});
    document.getElementById('popAlt').textContent =
      (cands.length>1 || cands[0].ch!==ch)
        ? (t('alt_label')+tradList.join(' / ')) : '';
    var p=picks[idx]||{};
    var curCi=(p.ci!==undefined&&p.ci<cands.length)?p.ci:0;
    var curRi=p.ri;
    if(curRi===undefined){
      /* 預設選中：先看逐字預設音，简体字用它繁体对应的預設 */
      var def=DEFAULTS[cands[curCi].ch];
      if(!def && VARIANTS && VARIANTS.s2t){
        var grp=VARIANTS.s2t[ch]||[];
        for(var g=0;g<grp.length && !def;g++){ def=DEFAULTS[grp[g]]; }
      }
      curRi=0;
      if(def){ for(var i=0;i<cands[curCi].readings.length;i++){ if(cands[curCi].readings[i][0]===def){ curRi=i; break; } } }
    }
    cands.forEach(function(cand,ci){
      cand.readings.forEach(function(rd,ri){
        var syl=rd[0], ipa=rd[1], note=rd[2]||'';
        var pos=(DICT.pos&&DICT.pos[syl])||'';
        var row=document.createElement('div');
        row.className='row';
        if(ci===curCi&&ri===curRi) row.classList.add('sel');
        var h='<span class="syl">'+esc(syl)+'</span>'
            + '<span class="ipa">['+esc(ipa)+']</span>';
        if(pos) h+='<span class="pos">'+esc(pos)+'</span>';
        if(!/[0-9]$/.test(syl)) h+='<span class="note">'+esc(t('note_untone'))+'</span>';
        /* 顯示這一條屬於哪個繁體形（簡體輸入時尤其必要） */
        if(cands.length>1 || cand.ch!==ch)
          h+='<span class="chtag">'+esc(cand.ch)+'</span>';
        if(note) h+='<span class="note">'+esc(note)+'</span>';
        row.innerHTML=h;
        row.onclick=function(ev){
          ev.stopPropagation();
          picks[idx]={ci:ci,ri:ri};
          closePop(); doConvert();
        };
        body.appendChild(row);
      });
    });
  }
  var pop=document.getElementById('pop');
  pop.classList.add('on');
  positionPop(anchor);
}
function positionPop(anchor){
  var pop=document.getElementById('pop');
  var r=anchor.getBoundingClientRect();
  var pr=pop.getBoundingClientRect();
  var left=Math.min(r.left,window.innerWidth-pr.width-10);
  if(left<8) left=8;
  var top=r.bottom+6;
  if(top+pr.height>window.innerHeight-8) top=Math.max(8,r.top-pr.height-6);
  pop.style.left=left+'px'; pop.style.top=top+'px';
}
function closePop(){ document.getElementById('pop').classList.remove('on'); popIdx=null; }
document.addEventListener('click',function(e){ if(!e.target.closest('#pop')) closePop(); });
window.addEventListener('resize',closePop);

/* ============================ 雜項 ============================ */
function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
  .replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function alertBox(msg){
  var nb=document.createElement('div');
  nb.className='notebar warn tmp'; nb.textContent=msg;
  var card=document.querySelector('.card');
  card.appendChild(nb);
  setTimeout(function(){ nb.remove(); },2600);
}
function doClear(){
  document.getElementById('src').value='';
  lastText=''; picks={}; seps=null;
  document.getElementById('segview').innerHTML='';
  var outEl=document.getElementById('out');
  outEl.innerHTML='';
  outEl.dataset.done='';
  outEl.classList.remove('on');   /* 清空時要一併移除 .on，否則下次轉換前的空狀態仍是 display:block */
  document.getElementById('outSec').style.display='none';
  document.getElementById('btnCopy').style.display='none';
}
function doCopy(){
  var txt=document.getElementById('out').innerText.trim();
  if(!txt){ alertBox(t('nocopy')); return; }
  navigator.clipboard.writeText(txt).then(function(){
    var b=document.getElementById('btnCopy'), old=b.textContent;
    b.textContent=t('copied');
    setTimeout(function(){ b.textContent=old; },1400);
  }).catch(function(){ alertBox(t('nocopy')); });
}

document.getElementById('src').addEventListener('input',function(){
  var v=this.value;
  if(v!==lastText){ seps=null; picks={}; }
  lastText=v;
  if(needSeg()) renderSegEditor();
});

/* ============================ 規則表 ============================ */
function renderRules(){
  var zh=(lang!=='en'&&lang!=='ja');
  var head= zh?['規則','說明','例子']:(lang==='ja'?['規則','説明','例']:['Rule','Description','Example']);
  var rows= zh?[
    ['詞內連寫','以詞為單位連寫音節，詞與詞之間以空格分隔','<code>白相 beq8sian1</code> → <code>beqsian</code>；<code>去白相 chi5 beq8sian1</code> → <code>chi beqsian</code>'],
    ['詞首陰平（調 1）','在詞首音節前加小撇','<code>雞排 ci1ba2</code> → <code>\'ciba</code>'],
    ['詞首 m/n/l/gn ＋ 調 3・5・7','在聲母後、韻母前加小撇','<code>美好 me3hau3</code> → <code>m\'ehau</code>'],
    ['詞首 m/n/l/gn ＋ 調 1','只在音節前加一只小撇','<code>蠻好 me1hau3</code> → <code>\'mehau</code>'],
    ['詞首 er1','在音節前加小撇','<code>兒戲 er1shi5</code> → <code>\'ershi</code>'],
    ['其餘調類（2・3・5・6・7・8）','一律不標','<code>作興 tsoq7shin1</code> → <code>tsoqshin</code>'],
    ['小撇字元','一律 U+0027 APOSTROPHE，不用 U+2019','<code>\'</code> = U+0027'],
    ['句首大寫','句首的第一個字母要大寫，無論它前面有沒有小撇','<code>\'ershi</code> → <code>\'Ershi</code>'],
    ['多音字','全部標紅；預設取一個音，點擊可從全部字音中挑選','<code>儂 non6</code>（另有 non2 / ne6）']
  ]:[
    ['Join within a word','Syllables of one word are written together; words are separated by spaces','<code>白相 beq8sian1</code> → <code>beqsian</code>'],
    ['Word-initial tone 1','Apostrophe before the syllable','<code>雞排 ci1ba2</code> → <code>\'ciba</code>'],
    ['Word-initial m/n/l/gn + 3/5/7','Apostrophe between initial and final','<code>美好 me3hau3</code> → <code>m\'ehau</code>'],
    ['Word-initial m/n/l/gn + 1','Only an apostrophe before the syllable','<code>蠻好 me1hau3</code> → <code>\'mehau</code>'],
    ['Word-initial er1','Apostrophe before the syllable','<code>兒戲 er1shi5</code> → <code>\'ershi</code>'],
    ['All other tones (2/3/5/6/7/8)','No mark','<code>作興 tsoq7shin1</code> → <code>tsoqshin</code>'],
    ['Apostrophe','Always U+0027 APOSTROPHE, never U+2019','<code>\'</code> = U+0027'],
    ['Sentence case','The first letter of a sentence is capitalised, apostrophe or not','<code>\'ershi</code> → <code>\'Ershi</code>'],
    ['Polyphonic characters','All shown in red; a default is chosen, click to pick any reading','<code>儂 non6</code> (also non2 / ne6)']
  ];
  var html='<table class="rules"><thead><tr>'+head.map(function(h){
    return '<th>'+h+'</th>'; }).join('')+'</tr></thead><tbody>';
  rows.forEach(function(r){
    html+='<tr><td>'+esc(r[0])+'</td><td>'+esc(r[1])+'</td><td>'+r[2]+'</td></tr>';
  });
  html+='</tbody></table>';
  document.getElementById('rulesBody').innerHTML=html;
}

/* ============================ 統計 ============================ */
function renderStats(){
  if(!META||!META.stats) return;
  var s=META.stats;
  var items=[['單字',s.single_chars],['讀音',s.readings],
    ['小韻音節',s.distinct_tone_syllables],['韻圖位置',s.positions],
    ['多音字',s.multi_reading_chars],['簡繁對',s.s2t_pairs],['吳語詞',s.lexicon_words]];
  var html='';
  items.forEach(function(it){
    if(it[1]===undefined||it[1]===null) return;
    html+='<div class="stat"><b>'+it[1]+'</b>'+esc(it[0])+'</div>';
  });
  document.getElementById('statsBody').innerHTML=html;
  document.getElementById('statsSec').style.display='block';
}

/* ============================ 啟動 ============================ */
(function init(){
  try{ var l=localStorage.getItem('tsoewoe/lang'); if(l&&I18N[l]) lang=l; }catch(e){}
  try{ var h=localStorage.getItem('tsoewoe/huhe'); if(h) huheMode=h; }catch(e){}
  applyLang(); syncHuheUI(); updateSegVisibility(); loadAll();
})();
"""


HEAD = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>蘇滬混合腔拼音轉換器</title>
<meta name="description" content="把漢字轉換成吳語蘇滬混合腔拼音（帶調拼音與拼音文正字法）。字音即時取自吳語字音查詢站，不自行推導。">
<meta name="theme-color" content="#1a5276">
<link rel="icon" href="favicon.ico" sizes="16x16 32x32 48x48 64x64">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<style>
__FONTFACE__
__CSS__
</style>
</head>
<body>
"""

TAIL = """
<script>
__JS__
</script>
</body>
</html>
"""


def main():
    fontface_path = os.path.join(ROOT, "fonts", "fontface.css")
    fontface = ""
    if os.path.exists(fontface_path):
        with open(fontface_path, encoding="utf-8") as f:
            fontface = f.read()
    else:
        print("  (no fonts/fontface.css — 先跑 make_font.py)", file=sys.stderr)

    html = HEAD.replace("__FONTFACE__", fontface) \
               .replace("__CSS__", CSS) + BODY + TAIL.replace("__JS__", JS)

    out = os.path.join(ROOT, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", out, len(html), "bytes")


if __name__ == "__main__":
    main()
