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

**另外**補一份「常見實詞表」COMMON_WORDS：輸入法詞庫偏方言特色詞，
缺大量現代漢語常見雙音節實詞（中文、朋友、時間…）。不補的話，
自動分詞會把它們切成一字一詞，看起來很碎。這些詞用字的讀音仍取自字音站，
只是承認「它們是一個詞」。

權重沿用 build_romazy_dict.py 的既定方案：
  單字       0
  word/map   min(10, 1 + 字數)
  phrase     min(20, 10 + 字數)
  常見實詞   6（介於 word 與 phrase 之間，低於詞庫詞，避免搶掉方言詞）

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

#: 常見實詞權重：低於詞庫詞（避免搶掉吳語特色詞），高於單字
COMMON_WEIGHT = 6

#: 常見實詞：現代漢語高頻雙音節／三音節詞，輸入法詞庫普遍缺收。
#: 只列「用字都查得到音」的詞（腳本會自動過濾），不影響任何讀音判斷，
#: 純粹讓分詞結果好看、連寫自然。
COMMON_WORDS = """
中文 中國 美國 英國 日本 韓國 德國 法國 俄國 台灣 香港 澳門 上海 北京 南京 杭州 蘇州
世界 國家 城市 地方 地區 社會 政府 人民 群眾 個人 家庭 朋友 同學 同事 老師 學生 醫生
護士 警察 律師 工程師 科學家 作家 畫家 音樂家 演員 導演 記者 編輯 職員 老闆 經理 主管
父親 母親 爸爸 媽媽 哥哥 姐姐 弟弟 妹妹 兒子 女兒 丈夫 妻子 孩子 寶寶 親戚 鄰居
父母 夫婦 夫妻 兄弟 姊妹 姐妹 爺爺 奶奶 外公 外婆 姥姥 姥爺 舅舅 舅媽 舅母 姑姑
姑媽 姨媽 叔叔 阿姨 表哥 表姐 表妹 表弟 堂哥 堂姐 堂妹 堂弟 侄子 侄女 孫子 孫女
媳婦 女婿 岳父 岳母 公公 婆婆 親家 長輩 晚輩 家長 家人 親人
時間 時候 年代 世紀 今天 明天 昨天 前天 後天 早上 上午 中午 下午 晚上 夜裡 半夜 現在
過去 將來 未來 從前 剛才 馬上 立刻 突然 終於 已經 曾經 一直 總是 經常 偶爾 從來
天氣 空氣 陽光 月光 星光 風雨 雨雪 雲彩 彩虹 溫度 季節 春天 夏天 秋天 冬天 氣候
山水 河流 海洋 湖泊 森林 草原 沙漠 島嶼 山脈 風景 自然 環境 汙染 生態 動物 植物
食物 糧食 蔬菜 水果 肉類 魚類 飲料 咖啡 牛奶 米飯 麵包 蛋糕 糖果 味道 香味 口感
衣服 褲子 鞋子 帽子 襪子 手套 圍巾 外套 裙子 首飾 眼鏡 手錶 手機 電腦 電話 電視
房子 房間 客廳 廚房 臥室 陽台 樓梯 窗戶 門口 桌子 椅子 沙發 床鋪 櫃子 鏡子 燈泡
學校 教室 圖書館 醫院 銀行 商店 市場 車站 機場 碼頭 公園 廣場 街道 馬路 橋樑 隧道
汽車 火車 飛機 輪船 自行車 摩托車 公交車 地鐵 出租車 交通 道路 方向 距離 速度 路程
工作 職業 事業 生意 公司 工廠 農場 辦公室 會議 項目 計劃 目標 任務 責任 效率 成果
學習 知識 文化 教育 科學 技術 藝術 文學 歷史 地理 數學 物理 化學 生物 醫學 法律
經濟 政治 軍事 外交 貿易 市場 價格 成本 利潤 工資 收入 支出 稅收 銀行 貨幣 投資
問題 答案 方法 辦法 原因 結果 目的 意義 價值 標準 規格 條件 情況 狀態 過程 變化
思想 感情 心情 態度 性格 習慣 興趣 愛好 夢想 希望 理想 願望 信心 勇氣 力量 精神
健康 疾病 感冒 發燒 咳嗽 頭痛 肚子 眼睛 耳朵 鼻子 嘴巴 牙齒 舌頭 頭髮 皮膚 骨頭
顏色 紅色 黃色 藍色 綠色 白色 黑色 灰色 紫色 橙色 粉紅 深藍 淺綠 明亮 黑暗 光線
聲音 音樂 歌曲 歌詞 舞蹈 電影 戲劇 節目 新聞 報道 廣告 圖片 照片 視頻 動畫 遊戲
說話 語言 文字 漢字 拼音 字母 句子 段落 文章 故事 小說 詩歌 散文 劇本 報告 文件
閱讀 寫作 翻譯 演講 討論 商量 交流 溝通 表達 描述 解釋 說明 介紹 推薦 建議 意見
移動 運動 走路 跑步 游泳 騎車 開車 飛翔 旅行 旅遊 出發 到達 返回 經過 通過 繼續
開始 結束 完成 準備 參加 舉行 慶祝 紀念 歡迎 告別 見面 約會 聚會 結婚 生日 節日
吃飯 喝水 睡覺 起床 洗澡 刷牙 穿衣 做飯 洗碗 打掃 購物 付款 排隊 等待 休息 工作
喜歡 討厭 高興 快樂 傷心 難過 生氣 害怕 擔心 放心 滿意 失望 感動 驚訝 好奇 無聊
相信 懷疑 記得 忘記 明白 理解 認識 知道 覺得 認為 希望 打算 決定 同意 反對 支持
幫助 照顧 保護 影響 改變 提高 降低 增加 減少 擴大 縮小 解決 處理 安排 組織 管理
重要 主要 必要 一般 特別 普通 簡單 複雜 容易 困難 方便 舒服 漂亮 美麗 可愛 好看
乾淨 整齊 整潔 安靜 吵鬧 熱鬧 擁擠 寬闊 狹窄 明亮 昏暗 溫暖 寒冷 涼爽 炎熱 潮濕
第一 第二 第三 最後 首先 其次 然後 接著 同時 一起 共同 分別 各自 互相 彼此 所有
大家 自己 別人 東西 事情 物件 材料 工具 機器 設備 儀器 零件 產品 商品 禮物 紀念品
中文 英文 日文 法文 德文 漢語 英語 日語 外語 母語 方言 吳語 蘇滬 普通話
轉換器 轉換 計算機 計算 圖書館 辦公室 科學家 工程師 服務員 電影院 火車站 飛機場
大學生 中學生 小學生 幼兒園 博物館 體育館 實驗室 資料庫 互聯網 顯示器 鍵盤 滑鼠
印表機 照相機 攝影機 收音機 洗衣機 電冰箱 空調機 微波爐 熱水器 自行車 摩托車
公交車 計程車 地鐵站 停車場 加油機 售貨員 營業員 管理員 主持人 運動員 藝術家
音樂家 美術家 舞蹈家 攝影師 設計師 程式員 分析師 研究生 博士生 留學生 畢業生
班主任 輔導員 校長 教授 講師 研究員 發明家 企業家 公務員 法官 藥劑師 獸醫
總經理 董事長 負責人 客戶 供應商 合作伙伴
東西 衣服 鞋子 帽子 襪子 手套 圍巾 外套 裙子 首飾 眼鏡 手錶 手機 電腦 電話 電視
房子 房間 客廳 廚房 臥室 陽台 樓梯 窗戶 門口 桌子 椅子 沙發 床鋪 櫃子 鏡子 燈泡
學校 教室 醫院 銀行 商店 市場 車站 機場 碼頭 公園 廣場 街道 馬路 橋樑 隧道
汽車 火車 飛機 輪船 交通 道路 方向 距離 速度 路程
工作 職業 事業 生意 公司 工廠 農場 會議 項目 計劃 目標 任務 責任 效率 成果
學習 知識 文化 教育 科學 技術 藝術 文學 歷史 地理 數學 物理 化學 生物 醫學 法律
經濟 政治 軍事 外交 貿易 價格 成本 利潤 工資 收入 支出 稅收 貨幣 投資
問題 答案 方法 辦法 原因 結果 目的 意義 價值 標準 規格 條件 情況 狀態 過程 變化
思想 感情 心情 態度 性格 習慣 興趣 愛好 夢想 希望 理想 願望 信心 勇氣 力量 精神
健康 疾病 感冒 發燒 咳嗽 頭痛 肚子 眼睛 耳朵 鼻子 嘴巴 牙齒 舌頭 頭髮 皮膚 骨頭
顏色 紅色 黃色 藍色 綠色 白色 黑色 灰色 紫色 橙色 粉紅 深藍 淺綠 明亮 黑暗 光線
聲音 音樂 歌曲 歌詞 舞蹈 電影 戲劇 節目 新聞 報道 廣告 圖片 照片 視頻 動畫 遊戲
說話 語言 文字 漢字 拼音 字母 句子 段落 文章 故事 小說 詩歌 散文 劇本 報告 文件
閱讀 寫作 翻譯 演講 討論 商量 交流 溝通 表達 描述 解釋 說明 介紹 推薦 建議 意見
移動 運動 走路 跑步 游泳 騎車 開車 飛翔 旅行 旅遊 出發 到達 返回 經過 通過 繼續
開始 結束 完成 準備 參加 舉行 慶祝 紀念 歡迎 告別 見面 約會 聚會 結婚 生日 節日
吃飯 喝水 睡覺 起床 洗澡 刷牙 穿衣 做飯 洗碗 打掃 購物 付款 排隊 等待 休息 工作
喜歡 討厭 高興 快樂 傷心 難過 生氣 害怕 擔心 放心 滿意 失望 感動 驚訝 好奇 無聊
相信 懷疑 記得 忘記 明白 理解 認識 知道 覺得 認為 希望 打算 決定 同意 反對 支持
幫助 照顧 保護 影響 改變 提高 降低 增加 減少 擴大 縮小 解決 處理 安排 組織 管理
重要 主要 必要 一般 特別 普通 簡單 複雜 容易 困難 方便 舒服 漂亮 美麗 可愛 好看
乾淨 整齊 整潔 安靜 吵鬧 熱鬧 擁擠 寬闊 狹窄 昏暗 溫暖 寒冷 涼爽 炎熱 潮濕
第一 第二 第三 最後 首先 其次 然後 接著 同時 一起 共同 分別 各自 互相 彼此 所有
大家 自己 別人 物件 材料 工具 機器 設備 儀器 零件 產品 商品 禮物 紀念品
"""


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

    # ---- 常見實詞 ----
    common = [w for w in COMMON_WORDS.split() if w]
    common_kept = 0
    common_dropped = 0
    for w in common:
        if not (2 <= len(w) <= MAX_WORD_CHARS) or not is_cjk(w):
            continue
        if not all(known(c) for c in w):
            common_dropped += 1
            continue
        # 不覆蓋詞庫裡已有的詞（尊重吳語詞庫的權重）
        if w not in words:
            words[w] = COMMON_WEIGHT
            common_kept += 1
    per_file.append(("(常見實詞表)", "common", len(common), common_kept))

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

    # ---------------------------------------------------------------- 繁→簡鏡像
    # 詞庫是繁體形（圖書館、辦公室、轉換器…），但使用者常輸入簡體（图书馆、转换器），
    # 若不補簡體鏡像，簡體輸入會被切成一字一詞。用 S2T 反向把每個繁體詞映射成簡體形，
    # 只要簡體形與繁體形不同就一併收錄（權重相同）。
    # 這樣「圖書館 / 图书馆」都能整詞切出，輸出時再由前端折回繁體。
    trad2simp = {}
    for simp, targets in s2t.items():
        for tr in targets:
            # 一個繁體可能對應多個簡體，取第一個（最常見）
            trad2simp.setdefault(tr, simp)

    mirrored = 0
    for w in list(words.keys()):
        if not all(c in trad2simp or c in chars for c in w):
            continue
        s = "".join(trad2simp.get(c, c) for c in w)
        if s == w or len(s) < 2:
            continue
        if not all(known(c) for c in s):
            continue
        if s not in words:
            words[s] = words[w]
            mirrored += 1
    print(f"繁→簡鏡像詞        : +{mirrored}")

    max_len = max((len(w) for w in words), default=1)
    out = {"words": {w: v for w, v in sorted(words.items())}, "maxLen": max_len,
           "total": len(words)}
    with open(os.path.join(DATA, "lexicon.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    print("來源（吳語詞庫 + 常見實詞，不含普通話詞庫）：")
    for fn, cat, n, kept in per_file:
        print(f"  {fn:26s} [{cat:6s}] 讀入 {n:6d} → 收 {kept:6d}")
    print()
    print("去重後詞條 :", len(words))
    print("最長詞長   :", max_len)
    print("丟棄(字音站查無此字):", dropped_charset)
    print("丟棄(非漢字)        :", dropped_nonhan)
    print(f"常見實詞：讀入 {len(common)}，新增 {common_kept}，"
          f"查無此字 {common_dropped}")
    print()
    print("分詞效果驗證：")
    for w in ["中文", "朋友", "時間", "東西", "我伲", "白相", "上海", "歡喜",
              "電腦", "手機", "問題", "世界"]:
        mark = "IN " if w in words else "-- "
        print(f"  {mark}{w}  {words.get(w, '')}")


if __name__ == "__main__":
    main()
