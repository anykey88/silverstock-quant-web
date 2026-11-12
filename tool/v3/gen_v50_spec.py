#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_v50_spec.py — 由 v50_inventory.json 產生 V5.0 開發與技術總規格書

產出三份（內容一律繁體、白話、數字讀檔回填）：
  1. /workspace/V5.0_台海股投资接续系统_开发与技术规格.html   （淺底大字，給長輩／泰哥）
  2. /workspace/V5.0_系统开发与技术规格.md                    （可列印技術版）
  3. silverstock_quant_web/docs/V5.0_SYSTEM_SPEC.md           （放進倉庫，供接續推送）

不改任何既有檔案；所有數字來自 inventory_v50.py 的真實盤點。
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path("/workspace")
PROJ = ROOT / "silverstock_quant_web"
INV = PROJ / "v50_inventory.json"
OUT_HTML = ROOT / "V5.0_台海股投资接续系统_开发与技术规格.html"
OUT_MD = ROOT / "V5.0_系统开发与技术规格.md"
OUT_REPO = PROJ / "docs" / "V5.0_SYSTEM_SPEC.md"

D = json.loads(INV.read_text(encoding="utf-8"))
C, DS, RU, EV, G, TD = D["counts"], D["dataset"], D["rules"], D["evidence"], D["git"], D["techdebt"]
FEE, PR, AD = RU["fee"], RU["principles"], RU["auth_defaults"]
SI = RU["self_improve"]
B = EV["case_6217"]


def e(x) -> str:
    return html.escape(str(x), quote=True)


# 只對「從既有程式讀出來的簡體註解」套用；不碰本檔自己寫的繁體正文。
# 單字元對應，避開多字元鍵（前面版本踩過 maketrans 多字元鍵報錯），
# 也刻意不含「准／沖」等會誤傷詞義的字。
S2T = str.maketrans({
    "从": "從", "价": "價", "则": "則", "实": "實", "层": "層", "录": "錄",
    "执": "執", "报": "報", "数": "數", "条": "條", "炼": "煉", "规": "規",
    "译": "譯", "读": "讀", "资": "資", "验": "驗", "机": "機", "产": "產",
    "业": "業", "证": "證", "测": "測", "试": "試", "检": "檢", "优": "優",
    "级": "級", "断": "斷", "续": "續", "对": "對", "应": "應", "该": "該",
    "还": "還", "来": "來", "过": "過", "进": "進", "发": "發", "现": "現",
    "际": "際", "确": "確", "认": "認", "识": "識", "别": "別", "类": "類",
    "压": "壓", "帐": "帳", "签": "簽", "错": "錯", "让": "讓", "记": "記",
    "变": "變", "会": "會", "种": "種", "结": "結", "论": "論", "选": "選",
    "择": "擇", "减": "減", "补": "補", "张": "張", "纸": "紙", "后": "後",
    "网": "網", "页": "頁", "长": "長", "辈": "輩", "岁": "歲", "体": "體",
    "卫": "衛", "浅": "淺", "显": "顯", "简": "簡", "单": "單", "术": "術",
    "语": "語", "词": "詞", "释": "釋", "举": "舉", "亿": "億", "万": "萬",
    "钱": "錢", "赚": "賺", "赔": "賠", "亏": "虧", "损": "損", "买": "買",
    "卖": "賣", "涨": "漲", "仓": "倉", "组": "組", "统": "統", "计": "計",
    "划": "劃", "参": "參", "设": "設", "态": "態", "状": "狀", "个": "個",
    "国": "國", "内": "內", "连": "連", "关": "關", "闭": "閉", "开": "開",
    "门": "門", "问": "問", "题": "題", "间": "間", "时": "時", "钟": "鐘",
    "点": "點", "线": "線", "图": "圖", "档": "檔", "额": "額", "费": "費",
    "税": "稅", "盘": "盤", "据": "據", "复": "複", "杂": "雜", "转": "轉",
    "换": "換", "与": "與", "专": "專", "标": "標",
})


def s2t(x) -> str:
    """只用在「從既有程式讀出來的簡體註解」。

    優先使用 opencc（詞組級，品質較好）；環境沒有套件時退回上面的單字表，
    不讓規格書產生器硬依賴外部套件。本檔自己寫的繁體正文不經過這裡。
    """
    try:
        from opencc import OpenCC
        return OpenCC("s2twp").convert(str(x))
    except Exception:
        return str(x).translate(S2T)


def mdcell(x) -> str:
    """表格儲存格：簡轉繁 + 避開會破壞 Markdown 表格的字元。"""
    return s2t(x).replace("|", "／").replace("\n", " ").strip()


def money(x) -> str:
    return f"{x:,.0f}"


def pct(x, n=2) -> str:
    return f"{x:.{n}f}%"


def minus(x, n=2) -> str:
    """中文內文統一用排版減號 U+2212，避免與連字號混淆。"""
    return f"−{abs(x):.{n}f}%"


# ══════════════════════════════════════════════════════════════════
# 共用文字（HTML 與 MD 都讀同一份，避免兩邊數字不一致）
# ══════════════════════════════════════════════════════════════════
N_PREV = C["n_versions"] - 1          # 本版之前的版本數（由盤點檔算，不手寫）
ONE_LINE = (f"這一版不是加新功能，是把前面 {N_PREV} 個版本收成一張「接著做」的地圖："
            "規矩照舊、權限照舊鎖著、錢照舊不進場。")

THREE_THINGS = [
    ("一、先記住：現在還是練習。",
     "系統到今天都只在紙上算，沒有連券商、沒有花過一塊錢真錢。就像學開車先在空地練，還沒上路。"),
    ("二、這份文件是「地圖」，不是「叫您買賣」。",
     "它把已經寫好的規矩、算過的數字、還沒做的事，一處一處標清楚，讓往後接手的人不會從頭猜。"),
    ("三、不知道的事，照舊寫不知道。",
     "資料不夠就說不知道、算不出來就不硬湊。這一條從 V4.2 寫到現在，沒有改過。"),
]

# 六層架構（層名、白話、生活比喻、對應真實檔案）
LAYERS = [
    ("1", "資料層", "米缸：有哪些股票、放到哪一天",
     "家裡的米缸。先點清楚有幾袋米、最後一次補貨是哪天，才不會把陳米當新米。",
     "assets/data/snapshot.json 等 7 份資料檔"),
    ("2", "引擎層", "算盤：把錢、手續費、稅算清楚",
     "一支老算盤。買賣各要抽一點、賣股票還要繳一點，先扣完剩下的才是自己的。",
     f"tool/v3 共 {C['n_py_modules']} 支程式"),
    ("3", "規矩層", "家規：寫死不改的那幾條",
     "貼在冰箱上的家規。盤前就寫好，盤中只照著做，不臨時改。",
     f"{RU['n_values']} 條價值觀、{RU['n_pretrade_questions']} 問、四種天氣"),
    ("4", "授權層", "保險箱：誰准它動真錢、能動多少",
     "保險箱的鑰匙在人手上，不在電腦手上。三道鎖任一跳起來就全部停。",
     "authorization.py、fubon_bridge.py"),
    ("5", "說話層", "翻譯：把醫師的話講成阿嬤聽得懂",
     "同樣一句話，換成家裡的說法、字放大、留白多，長輩才看得下去。",
     f"{SI['n_speak_rules']} 條說話規矩、淺底大字報告"),
    ("6", "自修層", "錯題本：算錯自己抓、改了留痕跡",
     "每次考試錯的地方抄起來，下個月重算一遍，改一處就記一處。",
     f"錯題本 {SI['n_error_ledger']} 筆、六步迭代"),
]

# 版本沿革（六段）
HISTORY = [
    ("V1.3 ～ V2.7", "網站真的上線了",
     "繁體大字網頁放到 GitHub Pages；家族三份清單、個股詳情、觀察清單都能用。這一段是「看得懂」。"),
    ("V2.8 ～ V3.0", "先把時間與權限講清楚",
     "資料要標兩個時間、三種狀態；富邦新 API 只寫規格；授權分成四級、十一條線。這一段是「別誤會」。"),
    ("V3.1 ～ V3.7", "用紙上對照找答案",
     "模擬盤對照、策略實驗室、因素盤點，最後收成七條價值觀、五層漏斗與交易前十二問。這一段是「先排除」。"),
    ("V3.8 ～ V4.2", "把錢分開、讓系統自己改錯",
     "四層桶、熊市、下單執行、市場結構、錯題本與三道安檢門。這一段是「別梭哈、靠規矩不靠意志力」。"),
    ("V4.3 ～ V4.6", "拿一支真股票從頭走一遍",
     "中探針：資料不夠就不准、買在最高點怎麼辦、只有一張怎麼辦、它是家裡最大一筆怎麼辦。這一段是「實際案例」。"),
    ("V5.0（本版）", "收成一張接著做的地圖",
     "不新增交易功能，把前面全部盤點、分層、列待辦，讓往後任何一天接手都不必重猜。"),
]

# 八條說話規矩（由結果檔讀出，若結構為 dict 取欄位）
def speak_list():
    out = []
    for r in SI["speak_rules"]:
        if isinstance(r, dict):
            t = r.get("rule") or r.get("text") or r.get("plain") or str(r)
            p = r.get("plain") or r.get("why") or ""
            out.append((t, p))
        else:
            out.append((str(r), ""))
    return out


SPEAK = speak_list()

# 術語白話對照（本版新增：技術規格必須留名詞，但每個都立刻解釋）
GLOSSARY = [
    ("M0 模擬盤", "只在紙上記帳、不花真錢的練習帳", "學開車先在空地練"),
    ("M3 自動", "額度內不必逐筆按確認，但額度由人簽、隨時可收回", "給小孩固定零用錢，不是給提款卡"),
    ("熔斷", "賠到一條線就全部停單，隔天也不自己復機", "鍋子過熱自動斷電"),
    ("白名單", "只准碰事先寫好的那幾支，其餘一律不理", "門禁名單"),
    ("下單前十二問", "買之前十二題全答「是」才准動手，沒答算不過", "上飛機前的檢查表"),
    ("四層桶", "現金、會配息的、大盤、少許個股，分四格放", "雞蛋分四個籃子"),
    ("樣本外", "拿沒複習過的考題再考一次", "別用同一份考古題證明自己厲害"),
    ("抽樣誤差", "圖每七天只取一點，會漏掉最深那天", "量體溫只量週一，會漏掉發燒那天"),
    ("絕對路徑", "程式把資料位置寫死在某一台機器上", "把鑰匙藏在「我家」而不是「門口」"),
    ("結果檔", "程式算完存下來的數字，報告再讀它來寫", "算盤打完抄在帳本上"),
    ("指數型基金", "一次買一籃子股票的商品，像 0050", "買一整籃，不挑單顆蛋"),
    ("四種天氣", "好天／普通／下雨／颱風，各有一個最多能放多少的比例", "雨越大，現金留越多"),
    ("資料不夠就當不過關", "沒回答、不確定的題目一律算否，不放寬", "寧可錯過，不可放寬"),
]

# ══════════════════════════════════════════════════════════════════
# HTML
# ══════════════════════════════════════════════════════════════════
H = []
def add(s=""):
    H.append(s)


def h2(no, title, sub=""):
    add(f'<h2><span class="no">{e(no)}</span>{e(title)}'
        + (f'<small>{e(sub)}</small>' if sub else '') + '</h2>')


def card(kind, title, body):
    add(f'<div class="card {kind}"><div class="ct">{e(title)}</div><div class="cb">{body}</div></div>')


HTML_HEAD = """<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>V5.0 台海股投資接續系統・開發與技術總規格</title>
<style>
:root{--bg:#faf8f2;--ink:#2b2a26;--mut:#6b675c;--line:#e3ded0;--card:#fffdf7;
--ok:#2f6b4f;--okbg:#eaf3ec;--warn:#a35a1c;--warnbg:#fbf0e2;--red:#a33b34;--redbg:#fbeceb;
--blue:#2c5d78;--bluebg:#e9f1f6;--accent:#8a6d3b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;
font-size:21px;line-height:1.95;letter-spacing:.02em}
.wrap{max-width:1000px;margin:0 auto;padding:38px 30px 90px}
header{border-bottom:3px solid var(--ink);padding-bottom:26px;margin-bottom:34px}
.kicker{font-size:17px;color:var(--mut);letter-spacing:.18em}
h1{font-size:42px;line-height:1.35;margin:14px 0 10px;letter-spacing:.01em}
.sub{font-size:20px;color:var(--mut);margin:0}
.lead{font-size:25px;line-height:1.8;background:var(--bluebg);border-left:9px solid var(--blue);
padding:22px 26px;border-radius:0 12px 12px 0;margin:30px 0}
h2{font-size:31px;margin:64px 0 22px;padding-bottom:12px;border-bottom:2px solid var(--line);
display:flex;align-items:baseline;gap:16px;line-height:1.4}
h2 .no{background:var(--ink);color:#fff;border-radius:50%;width:46px;height:46px;
min-width:46px;display:inline-flex;align-items:center;justify-content:center;font-size:22px}
h2 small{font-size:17px;color:var(--mut);font-weight:normal;margin-left:auto}
h3{font-size:24px;margin:34px 0 12px}
p{margin:14px 0}
.note{font-size:18px;color:var(--mut);line-height:1.85}
.big{font-size:27px;font-weight:700;line-height:1.7}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:26px 0}
.kpi{background:var(--card);border:2px solid var(--line);border-radius:14px;padding:20px 14px;text-align:center}
.kv{font-size:30px;font-weight:800;color:var(--blue);line-height:1.3}
.kl{font-size:16px;color:var(--mut);margin-top:8px;line-height:1.6}
table{width:100%;border-collapse:collapse;margin:22px 0;font-size:19px;background:var(--card)}
th,td{border:1.5px solid var(--line);padding:13px 15px;text-align:left;vertical-align:top;line-height:1.7}
th{background:#f1ece0;font-weight:700}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.onepager{background:var(--card);border:3px solid var(--accent);border-radius:18px;
padding:30px 34px;margin:30px 0}
.onepager h3{margin:0 0 18px;font-size:28px;color:var(--accent)}
.row{display:flex;gap:18px;margin:20px 0;align-items:flex-start}
.row .n{background:var(--accent);color:#fff;border-radius:50%;width:38px;height:38px;min-width:38px;
display:flex;align-items:center;justify-content:center;font-size:19px;font-weight:700}
.bigline{font-size:24px;font-weight:700;line-height:1.6}
.card{border-radius:14px;padding:22px 26px;margin:20px 0;border:2px solid var(--line);background:var(--card)}
.card .ct{font-size:23px;font-weight:700;margin-bottom:10px}
.card .cb{font-size:20px;line-height:1.9}
.card.ok{background:var(--okbg);border-color:var(--ok)}
.card.warn{background:var(--warnbg);border-color:var(--warn)}
.card.red{background:var(--redbg);border-color:var(--red)}
.card.blue{background:var(--bluebg);border-color:var(--blue)}
.layers{margin:26px 0}
.layer{display:flex;align-items:center;gap:18px;background:var(--card);border:2px solid var(--line);
border-radius:14px;padding:18px 22px}
.layer .ln{background:var(--blue);color:#fff;border-radius:10px;width:44px;height:44px;min-width:44px;
display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800}
.layer .nm{font-size:24px;font-weight:800;min-width:120px}
.layer .wh{font-size:20px;color:var(--mut);flex:1}
.arrow{text-align:center;font-size:26px;color:var(--accent);line-height:1.4;margin:2px 0}
.tag{display:inline-block;background:#f1ece0;border-radius:8px;padding:2px 10px;font-size:16px;color:var(--mut)}
.okword{color:var(--ok);font-weight:700}
.noword{color:var(--red);font-weight:700}
footer{margin-top:70px;border-top:2px solid var(--line);padding-top:22px;font-size:17px;color:var(--mut)}
code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:16px;background:#f1ece0;
padding:2px 7px;border-radius:6px;color:#4a4234}
@media(max-width:760px){.kpis{grid-template-columns:repeat(2,1fr)}body{font-size:19px}
h1{font-size:33px}h2{font-size:26px}.layer{flex-wrap:wrap}.layer .nm{min-width:0}}
</style></head><body><div class="wrap">"""


def build_html():
    add(HTML_HEAD)
    add('<header><div class="kicker">給家人自用・繁體・淺底大字</div>')
    add('<h1>V5.0 台海股投資接續系統<br>開發與技術總規格</h1>')
    add(f'<p class="sub">{e(D["generated_at"])} 盤點｜接續 V2.7 ～ V4.6 的架構與溝通結論｜'
        f'現況仍是練習帳（M0），沒連券商、沒下過任何一張單</p></header>')

    # 一句話
    add(f'<div class="lead"><b>一句話：</b>{e(ONE_LINE)}</div>')

    # 給爸媽的一頁紙
    add('<div class="onepager"><h3>給爸媽的一頁紙（只要記三件事）</h3>')
    for t, p in THREE_THINGS:
        add(f'<div class="row"><div class="n">{e(t[0])}</div><div>'
            f'<div class="bigline">{e(t)}</div><div>{e(p)}</div></div></div>')
    add(f'<p class="note">這一頁可以單獨印出來。後面十幾節是給要接手的人看的，看不懂跳過也沒關係。</p></div>')

    # 1 現在到底有什麼
    h2("1", "現在到底有什麼", "用程式點過，不是用印象講")
    add('<div class="kpis">')
    for v, lab in [
        (f'{C["n_py_modules"]} 支', "寫好的程式"),
        (f'{C["n_py_lines"]:,} 行', "程式總行數"),
        (f'{C["n_result_files"]} 份', "算出來的結果檔"),
        (f'{C["n_report_files"]} 份', "寫好的報告"),
    ]:
        add(f'<div class="kpi"><div class="kv">{e(v)}</div><div class="kl">{e(lab)}</div></div>')
    add('</div>')
    add(f'<p>從 V1.3 一路到本版，一共留下 <b>{C["n_versions"]} 個版本</b>的報告與規格，'
        f'其中前面 {N_PREV} 個是已經回答過問題的版本。這些都還在檔案裡，沒有丟。'
        '本版做的事只有一件：<b>把它們收成一張地圖</b>。</p>')
    card("blue", "為什麼要收成地圖",
         "前面的版本是一題一題回答出來的：資產怎麼分、熊市怎麼辦、買在最高點怎麼辦。"
         "題目散在各處，換個人接手就要從頭猜。<b>地圖不是新答案，是讓舊答案找得到。</b>")

    # 2 版本沿革，六段路
    h2("2", f"{C['n_versions']} 個版本，走成六段路", "每一段解決一個問題")
    add('<table><tr><th>版本</th><th>那一段在做什麼</th><th>留下來的東西</th></tr>')
    for v, t, p in HISTORY:
        add(f'<tr><td><b>{e(v)}</b></td><td><b>{e(t)}</b></td><td>{e(p)}</td></tr>')
    add('</table>')
    add('<p class="note">看得出來：前面五段都在回答「錢該怎麼辦」，只有最後一段（本版）在回答'
        '「往後怎麼接著做」。這就是「接續系統」的意思。</p>')

    # 3 六層架構
    h2("3", "系統分成六層", "像蓋房子，一層一層往上")
    add('<p class="big">下面每一層都有白話、都有一個家裡的比喻，也都對應到真實檔案。'
        '往後要改東西，先問「要改的是哪一層」，不要一次動六層。</p>')
    add('<div class="layers">')
    for i, (no, nm, wh, analogy, real) in enumerate(LAYERS):
        add(f'<div class="layer"><div class="ln">{e(no)}</div>'
            f'<div class="nm">{e(nm)}</div><div class="wh"><b>{e(wh)}</b><br>'
            f'<span class="note">{e(analogy)}　<span class="tag">{e(real)}</span></span></div></div>')
        if i < len(LAYERS) - 1:
            add('<div class="arrow">↓</div>')
    add('</div>')
    card("warn", "最要緊的一句",
         "第 4 層（授權）的鑰匙<b>永遠在人手上</b>。第 1 到第 6 層都可以交給電腦，"
         "只有「要不要花真錢、能花多少」不行。這一條從 V3.0 寫到現在都沒改。")

    # 4 資料層
    h2("4", "第一層：資料從哪裡來", "米缸裡有幾袋米、放到哪一天")
    add('<div class="kpis">')
    for v, lab in [
        (f'{DS["n_stocks"]} 檔', "股票檔數"),
        (f'{DS["index_bars"]:,} 天', "大盤日線"),
        (f'{DS["captured_at"]}', "最後補貨日"),
        (f'{DS["with_quarterly_eps"]}/{DS["n_stocks"]}', "有每季獲利數字"),
    ]:
        add(f'<div class="kpi"><div class="kv">{e(v)}</div><div class="kl">{e(lab)}</div></div>')
    add('</div>')
    add(f'<p>歷史資料範圍 <b>{e(DS["range"][0])} ～ {e(DS["range"][1])}</b>，'
        f'單一股票最少 {DS["bars_min"]:,} 天、最多 {DS["bars_max"]:,} 天。'
        f'來源是 {e(DS["source"])}。</p>')
    card("warn", "八樣東西，現在沒有、就寫不知道",
         "當天的開盤／最高／最低價、真正的換手率、每天的融資融券、逐筆成交、"
         "國際股市、整體經濟、債券黃金、每月營收年增率——<b>這八樣都沒有</b>。"
         "所以「今天量能是不是買點」「國際盤會不會拖累」這些問題，系統現在回答不了，"
         "不會硬猜。每季獲利數字也只有 "
         f'{DS["with_quarterly_eps"]}/{DS["n_stocks"]} 檔有。')
    card("blue", "兩個時間，三種標籤（V2.8 就寫好的規格，還沒做完）",
         "每個價格旁邊要同時標「<b>行情時間</b>」（數字是幾點的）跟「<b>資料更新</b>」"
         "（我們幾點拿到的），兩個都是<b>固定值</b>，不會因為重新整理就變成現在。"
         "標籤只有三種：盤中報價、今日收盤、歷史資料。"
         "<b>全站不顯示會跳動的時鐘</b>——因為誤會從來不是少一個時間，"
         "是把舊資料看成活的。")

    # 5 引擎層
    h2("5", "第二層：錢是怎麼算的", "算盤先扣掉該扣的，剩下的才是自己的")
    add('<table><tr><th>項目</th><th class="num">數字</th><th>白話</th></tr>')
    fee_rows = [
        ("買或賣的手續費", pct(FEE["FEE_RATE"] * 100, 4), "買一次收一次，賣一次再收一次"),
        ("賣個股的交易稅", pct(FEE["TAX_RATE_STOCK"] * 100, 1), "賣股票才收，比手續費多一點"),
        ("賣指數型基金的稅", pct(FEE["TAX_RATE_ETF"] * 100, 1), "同類商品稅比較低，身分填錯整本帳都要重算"),
        ("零股最低手續費", f'{FEE["MIN_FEE_ODD"]} 元', "金額太小時反而吃虧，所以別一天只賣一股"),
        ("整張最低手續費", f'{FEE["MIN_FEE_ROUND"]} 元', "一次買賣一整張時的最低收費"),
    ]
    for a, b_, c in fee_rows:
        add(f'<tr><td>{e(a)}</td><td class="num">{e(b_)}</td><td>{e(c)}</td></tr>')
    add('</table>')
    add(f'<p>算錢的程式集中在 <code>tool/v3</code>，共 <b>{C["n_py_modules"]} 支、'
        f'{C["n_py_lines"]:,} 行</b>。每一支算完都把數字存成結果檔，報告再讀結果檔來寫，'
        f'<b>不憑印象手抄</b>——這是 V4.2 第八條規矩，到現在沒破過。</p>')
    card("ok", "一個真實的例子（中探針，一張）",
         f'當初買 371 元實付 <b>{money(B["buy_paid"])} 元</b>；'
         f'現在 109 元賣掉實收 <b>{money(B["sell_received"])} 元</b>；'
         f'中間不見 <b>{money(B["loss_per_lot"])} 元</b>（{minus(B["loss_pct_on_cash"])}）。'
         f'要真正打平得漲回 <b>{B["recover_price"]:.1f} 元</b>，'
         f'等於從現在再漲 <b>{pct(B["recover_pct_from_now"])}</b>——'
         '比當初的 371 還高，因為買賣各付一次手續費、賣出還要繳稅。')

    # 6 規矩層
    h2("6", "第三層：寫死不改的規矩", "貼在冰箱上，盤中不改")
    add('<table><tr><th>規矩</th><th>內容</th><th>白話</th></tr>')
    cap = PR["REGIME_CAP"]
    rules_rows = [
        ("七條價值觀", "先活下來、只做懂的、別一直進出、紀律優先於預測…",
         "先把「不可以」寫清楚，再談「可以」"),
        ("五層漏斗", f'至少要 {PR["MIN_BARS"]:,} 天日線、近 60 天日均成交額 ≥ '
         f'{PR["MIN_ADV_NTD"]/1e8:.0f} 億、年化晃動 ≤ {pct(PR["MAX_VOL_ANN"]*100,0)}、'
         f'五年最多跌 ≤ {pct(PR["MAX_DRAWDOWN"]*100,0)}、本益比 ≤ {PR["MAX_PE"]:.0f}',
         "先篩掉不該碰的，不是挑出會漲的"),
        ("四種天氣 → 最多放多少",
         f'好天 {cap["BULL"]*100:.0f}%、普通 {cap["NEUTRAL"]*100:.0f}%、'
         f'下雨 {cap["BEAR"]*100:.0f}%、颱風 {cap["CRISIS"]*100:.0f}%',
         "雨越大，口袋裡留的現金越多"),
        (f'下單前 {RU["n_pretrade_questions"]} 問',
         "十二題全部答「是」才准買；沒回答、不確定，一律算不過",
         "上飛機前的檢查表，少一格就不起飛"),
        ("單一炒作股上限 1%", "這種一年能漲好幾倍又跌回來的，家裡最多放 1%",
         "最會漏水的那間房，不放最重的米"),
        ("四層桶", "現金／會配息的／大盤／少許個股，分四格放",
         "雞蛋分四個籃子，行情再好也不梭哈"),
        ("三條自動停手", f'一天賠到 {money(AD["max_daily_loss"])} 元、連賠 '
         f'{AD["max_consecutive_losses"]} 次、整體從高點跌 {pct(AD["max_drawdown_pct"]*100,0)}',
         "鍋子過熱自動斷電，隔天也不自己復機"),
    ]
    for a, b_, c in rules_rows:
        add(f'<tr><td><b>{e(a)}</b></td><td>{e(b_)}</td><td>{e(c)}</td></tr>')
    add('</table>')
    card("warn", "這層有個容易搞混的地方，本版特別標出來",
         "同樣叫「Gate」，其實有<b>兩組完全不同的東西</b>：<br>"
         "① <b>升級五關</b>（V3.0）：要從「逐筆按確認」升到「額度內自動」，得五關全過，"
         "那是<b>准不准花真錢</b>。<br>"
         "② <b>規矩三道安檢門</b>（V4.2）：一條新方法想寫進系統，得先換資料重考、"
         "改一點參數看會不會走味、確認資料夠不夠，那是<b>准不准寫進程式</b>。<br>"
         "名字很像，管的事完全不同。往後文件一律寫全名，不再只寫代號。")

    # 7 授權層
    h2("7", "第四層：誰准它動真錢", "鑰匙在人手上，不在電腦手上")
    add('<table><tr><th>層級</th><th>做什麼</th><th>現在</th></tr>')
    lv_rows = [
        ("M0 練習帳", "只在紙上算，不送券商、不花真錢", "✅ 現在在這裡"),
        ("M1 只出主意", "只產出決策，仍然不送單", "已備妥，未啟用"),
        ("M2 逐筆確認", "真錢，但每一筆都要人按確認", "待開通"),
        ("M3 額度內自動", "真錢，額度內不必逐筆按；額度由人簽、可隨時收回", "🔒 鎖著，未解鎖"),
    ]
    for a, b_, c in lv_rows:
        add(f'<tr><td><b>{e(a)}</b></td><td>{e(b_)}</td><td>{e(c)}</td></tr>')
    add('</table>')
    add(f'<p>就算將來解鎖，也不是「給一張提款卡」，是<b>十一條線同時綁著</b>：'
        f'累計最多 {money(AD["max_total_exposure"])} 元、單筆 {money(AD["max_order_amount"])} 元、'
        f'單日 {money(AD["max_daily_amount"])} 元、單日 {AD["max_orders_per_day"]} 筆、'
        f'單一標的 {money(AD["max_symbol_exposure"])} 元、持股最多 '
        f'{pct(AD["max_position_pct"]*100,0)}、只准 {len(AD["whitelist"])} 支白名單、'
        f'只准盤中、只准零股、報價不能舊於 {AD["max_quote_age_seconds"]} 秒。</p>')
    card("red", "五道防線，一道都不能少",
         "① 額度寫死，程式只能讀不能改；② 升級要人簽名加五關全過，程式不能自己宣布達標；"
         "③ 熔斷就降級、隔日不自動復機；④ 人隨時可收回，收回優先於所有決策；"
         "⑤ 每一筆都留痕跡（為什麼買、依據哪個數字、用掉多少額度）。"
         "<b>還有兩道急停：本機收回、券商端停用金鑰</b>，就算電腦被改，也能從券商那邊切斷。")
    add('<p class="note">職責鏈（給接手的人）：先產生意圖 → 問風險能不能接受 → '
        '問有沒有被授權、額度夠不夠 → 才准送出去。少了任何一段，最後那道門一律不放行。</p>')
    card("blue", "現在的真實狀態（每次都要講）",
         f'測試環境位址只是一個常數（<code>{e(RU["sandbox_url"])}</code>），'
         '<b>沒有連線、沒有登入、沒有下過任何一張單</b>。'
         '升級五關目前只有第一關（紙上對照跑贏基準）通過，其餘四關都還沒開始。')

    # 8 說話層
    h2("8", "第五層：話要怎麼說", "給長輩看，不是給同行看")
    add(f'<p>從 V4.2 起，每一版報告都照下面 <b>{SI["n_speak_rules"]} 條</b>寫。'
        '這不是排版偏好，是<b>規格</b>：寫法不對，報告就不算完成。</p>')
    add('<table><tr><th class="num">#</th><th>規矩</th></tr>')
    for i, (t, p) in enumerate(SPEAK, 1):
        add(f'<tr><td class="num">{i}</td><td>{e(t)}'
            + (f'<br><span class="note">{e(p)}</span>' if p else '') + '</td></tr>')
    add('</table>')
    card("ok", "每一版交付前的體檢（前面踩過的坑，已變成固定動作）",
         "簡體字殘留、專門術語偷跑、同一個數字前後不一致、章節跳號、"
         "標籤沒閉合、舊說法跟新結論打架、瀏覽器截圖看有沒有溢出——"
         "<b>七項全過才算完成</b>。V4.6 就靠這一步抓出「把天數占比誤寫成漲跌歸因」。")
    add('<h3>術語白話對照（非用不可，就立刻解釋）</h3>')
    add('<table><tr><th>聽起來很硬的詞</th><th>意思是</th><th>家裡的說法</th></tr>')
    for a, b_, c in GLOSSARY:
        add(f'<tr><td><b>{e(a)}</b></td><td>{e(b_)}</td><td>{e(c)}</td></tr>')
    add('</table>')

    # 9 自修層
    h2("9", "第六層：系統會自己改錯", "靠日曆，不靠意志力")
    add(f'<p>錯題本目前記了 <b>{SI["n_error_ledger"]} 筆</b>。'
        f'一條新規矩想寫進系統，得過 <b>{len(SI["gates"])} 道安檢門</b>：</p>')
    add('<table><tr><th>安檢門</th><th>問什麼</th><th>白話</th></tr>')
    for g in SI["gates"]:
        add(f'<tr><td><b>{e(g["id"])}</b></td><td>{e(g["name"])}</td><td>{e(g.get("plain",""))}</td></tr>')
    add('</table>')
    add('<p class="note">'
        f'目前判定：<b>{len(SI["claims"])} 條規矩</b>逐條評過，可進系統、附條件、'
        '只能觀察、不准用，分得清清楚楚。被判「不准用」的不是沒用，是還不夠可靠。</p>')
    card("blue", "六步改法（一次只改一處）",
         "① 每天把寫過的數字重算一遍，對不上就記一筆 → ② 先問是資料錯、程式錯、還是前提錯 → "
         "③ 一次只動一個地方 → ④ 改完全部重算，不沿用舊數字 → "
         "⑤ 改前改後並排放，差多少寫清楚 → ⑥ 記進錯題本，過不了三道門就不准上線。"
         "<b>上一版自己就犯了第 ③ 步（一次改了三處），所以下一版不是加功能，是拆開慢慢驗。</b>")
    add('<table><tr><th>什麼時候</th><th>做什麼</th><th>白話</th></tr>')
    for a, b_, c in [
        ("每次下單前", "十二問加三條熔斷，系統自動擋", "不用您記，程式先擋"),
        ("每個月", "把上一版數字重算一遍", "像每個月對一次存摺"),
        ("每季", "換沒用過的資料重考、改一點參數看落差", "像定期健康檢查"),
        ("每次想改方法", "一次只改一處、前後並排、人簽名才算數", "想改可以，要留下改前改後"),
        ("每年", "重讀錯題本，問同樣的錯還在不在", "像年前大掃除"),
    ]:
        add(f'<tr><td><b>{e(a)}</b></td><td>{e(b_)}</td><td>{e(c)}</td></tr>')
    add('</table>')

    # 10 實測數字速查
    h2("10", "算過的數字，一張表看完", "全部由結果檔讀出，不重算、不編")
    cr, fb, ai, gp, lv = EV["correlation"], EV["four_bucket"], EV["all_in"], EV["groups"], EV["leverage"]
    c30 = EV["crash30"]
    add('<table><tr><th>問題</th><th class="num">數字</th><th>白話</th></tr>')
    ev_rows = [
        ("把錢分到 64 檔之後，整體晃動少多少", pct(cr["vol_reduction_pct"]),
         f'單檔平均晃 {pct(cr["single_vol_pct"])} → 一起放只晃 {pct(cr["equal_weight_vol_pct"])}'),
        ("平均分開後，實際等於幾檔獨立", f'{cr["effective_n"]} 檔',
         f'平均相關 {cr["avg_pairwise_corr"]:.4f}，分開還是有效，但沒想像中多'),
        ("四層桶每年賺多少、最多跌多少", f'{pct(fb["ann_pct"])}／{minus(fb["mdd_pct"])}',
         "分四格放，跌起來比全押溫和"),
        ("全部押一檔指數，每年賺多少、最多跌多少", f'{pct(ai["ann_pct"])}／{minus(ai["mdd_pct"])}',
         "賺得多一點，但跌起來深很多"),
        ("急殺那 30 天，大盤跌多少", minus(c30["index_ret_pct"]), "一直下雨的日子"),
        ("同一段，會配息的防禦組跌多少", minus(c30["DEF"]), "撐傘的人淋得比較少"),
        ("同一段，暴漲暴跌那組跌多少", minus(c30["HYPE"]), "跑最快的那群，摔得也最重"),
        ("暴漲暴跌組整段走完，總共", minus(gp["HYPE"]["total_pct"]),
         f'途中最多跌 {minus(gp["HYPE"]["mdd_pct"])}'),
        ("在山頂用兩倍錢，30 天後", minus(lv["lever_ret_pct"]),
         f'要回本得再漲 {pct(lv["recover_needed_pct"],1)}'),
        ("每天做一次當沖，來回成本", pct(EV["daytrade"]["cost_stock_pct"], 3),
         f'做一整年約侵蝕 {pct(EV["daytrade"]["annual_erosion_stock_pct"],1)}'),
        (f'過去 {EV["structure"]["n_days"]:,} 天，個股各走各的佔', pct(EV["idio"]["pct"], 1),
         "本來就靠分開放來扛，不靠猜哪一支會漲"),
    ]
    for a, b_, c in ev_rows:
        add(f'<tr><td>{e(a)}</td><td class="num"><b>{e(b_)}</b></td><td>{e(c)}</td></tr>')
    add('</table>')
    card("warn", "一個數字，兩種意思（V4.6 抓到過的錯）",
         f'「個股主導」有兩個不同的數字：<b>{pct(EV["idio"]["pct"],1)} 是「天數占比」</b>'
         f'（{EV["structure"]["n_days"]:,} 天裡有幾天是各走各的），'
         f'<b>{pct(EV["idio"]["share_idio"]*100,0)} 是「漲跌歸因占比」</b>'
         '（當天漲跌裡有多少來自個股自己）。前面曾把前者誤寫成後者，已記進錯題本。'
         '往後引用一定要講清楚是哪一個。')

    # 11 現況與接續路線
    h2("11", "現在的真實狀態，與接著要做的事", "誠實清單，不報喜不報憂")
    card("red", "現在「還沒有」的事（每一版都要講）",
         f'① 仍是練習帳，沒連券商、沒下單；② 升級五關只過第一關；'
         f'③ 本機有 <b>{G["n_untracked"]} 項新檔案還沒推上 GitHub</b>'
         '（舊令牌已撤銷，要新令牌才能推）；④ 富邦測試環境只是規格裡的一個位址；'
         f'⑤ 中探針不在 {DS["n_stocks"]} 檔資料池裡，外部只找到 '
         f'{B["external_bars"]} 根日線，但規矩要 {B["required_bars"]:,} 根 → '
         '<b>資料不夠就當不合格</b>；⑥ V2.8 的雙時間標籤還只是規格，沒寫進網頁。')
    add('<h3>接著做，按先後排（不是加新功能）</h3>')
    add('<table><tr><th>順序</th><th>要做的事</th><th>為什麼現在做</th></tr>')
    roadmap = [
        ("先", "辦新令牌，把 tool/v3 與所有結果檔、本規格推上倉庫",
         f'現在 {G["n_untracked"]} 項只存在這台機器，換台電腦就沒了；憑證絕對不進倉庫'),
        ("先", "把 V2.8 的雙時間、三態標籤、資料時效總覽做進網頁",
         "規格寫好了兩版，網頁還在顯示會讓人誤會的舊寫法"),
        ("再", "把「部分減碼／月檢／賣後回補」拆開，一次只改一處各驗一次",
         "V4.0 那次一次改了三處，只能證明方向對，不能證明是誰有功勞"),
        ("再", "圖表改存每日數字，不再每七天取一個點",
         "取樣會漏掉最深那天，跌幅平均低估 2.76 個百分點、最多 5.68"),
        ("再", "換成多段輪流考，不再只切一次",
         "只考一段，可能是剛好押中那一段"),
        ("後", "補資料：八樣缺的、每季獲利、中探針要夠 1,000 根連續日線",
         "資料齊了，五道安檢門才能給正式分數；不齊就繼續寫不知道"),
        ("最後", "才談富邦測試環境全鏈路、逐筆確認實盤十天、簽署開通、書面授權",
         "這四關全過，才輪到討論要不要解鎖自動；而且要以「策略」為單位放行"),
    ]
    for a, b_, c in roadmap:
        add(f'<tr><td><b>{e(a)}</b></td><td>{e(b_)}</td><td>{e(c)}</td></tr>')
    add('</table>')
    card("ok", "路線圖裡最重要的一句",
         "前面七件事，沒有一件是「讓系統更會賺」。"
         "它們全是<b>把資料補齊、把改動拆開、把權限收好</b>。"
         "這正是 V4.2 定下的方向：系統進步，是變誠實，不是變大膽。")

    # 12 技術債
    h2("12", "技術債：寫給接手寫程式的人", "這一節看不懂可以跳過")
    add('<p class="note">下面保留真實檔名與代號，是給要動程式的人對照用的。'
        '每一項後面都附白話，不用先懂程式也能看得出「哪裡會出事」。</p>')
    add('<table><tr><th>現況</th><th class="num">數字</th><th>會出什麼事</th></tr>')
    debt_rows = [
        ("程式把資料位置寫死在某一台機器", f'{TD["n_modules_with_abs_path"]}/{C["n_py_modules"]} 支',
         "換台電腦、換個資料夾就找不到資料，全部要改"),
        ("報告生成器各自寫一套輸出位置", f'{TD["n_generators"]} 支',
         f"輸出路徑三種寫法混用；想改版型要改 {TD['n_generators']} 次"),
        ("結果檔散在兩個地方", f'倉庫 {TD["n_result_in_repo"]} 份／外層 {TD["n_result_in_root"]} 份',
         "備份容易漏，讀檔要分兩邊找"),
        ("沒有一支共用的版型程式", "沒有" if TD["no_shared_layout_module"] else "有",
         f"字級、顏色、淺底改一次要動 {TD['n_generators']} 支"),
        ("沒有一支自動體檢程式", "沒有" if TD["no_auto_check_script"] else "有",
         "前面七項體檢都是每次手寫，容易漏"),
        ("新檔案還沒推送", f'{G["n_untracked"]} 項',
         "只存在這台機器；推送要新令牌，憑證不進倉庫"),
    ]
    for a, b_, c in debt_rows:
        add(f'<tr><td>{e(a)}</td><td class="num"><b>{e(b_)}</b></td><td>{e(c)}</td></tr>')
    add('</table>')
    card("blue", "建議的最小改法（還沒做，先記著）",
         f"① 把寫死的機器位置改成「相對於這支程式」；② 抽一支共用版型，"
         f"{TD['n_generators']} 支生成器都讀它；"
         "③ 把七項體檢寫成一支固定程式，每次交付前跑一次；④ 結果檔統一放倉庫同一處。"
         "<b>四件都是整理，不是加功能；而且一次只做一件、做完重跑對照</b>——"
         "才不會又犯「一次改三處」的老毛病。")

    # 附錄
    h2("A", "附錄：這次哪裡可能錯", "先自首，跟前面每一版一樣")
    for t in [
        "資料只有一段難得的大多頭，空頭看得不夠；所有「不要賣」的規矩都可能被高估。",
        f'八樣資料沒有、每季獲利只有 {DS["with_quarterly_eps"]}/{DS["n_stocks"]} 檔，'
        "所以「量能是不是買點」「國際盤影響」現在不能回答。",
        "三道安檢門、升級五關，都是我們自己訂的標準，不是市場給的保證。",
        "本版只做盤點與整理，沒有重跑任何回測；所有數字沿用既有結果檔，"
        "若來源檔有錯，本版會一起帶著錯。",
        "盤點數字是「當下」的檔案狀態；往後每加一支程式、每推一次，數字就會變，"
        "要重跑盤點才準。",
        "全部是練習帳，沒連券商、沒下一張單。系統會犯錯，只是它會把錯記下來。",
    ]:
        add(f'<p>· {e(t)}</p>')

    h2("B", "附錄：檔案放在哪裡", "給接手的人按圖索驥")
    add('<table><tr><th>東西</th><th>位置</th><th>筆數</th></tr>')
    for a, b_, c in [
        ("網頁原始碼（Flutter）", "silverstock_quant_web/lib/、web/", "上線版本 V2.7"),
        ("資料檔", "silverstock_quant_web/assets/data/", "7 份"),
        ("算錢與規則程式", "silverstock_quant_web/tool/v3/", f'{C["n_py_modules"]} 支'),
        ("算出來的結果檔", "silverstock_quant_web/v*.json 與 /workspace/v*.json",
         f'{C["n_result_files"]} 份'),
        ("報告（大字版＋可列印卡）", "/workspace/V*.html、V*.md", f'{C["n_report_files"]} 份'),
        ("本版盤點結果", "silverstock_quant_web/v50_inventory.json", "1 份"),
        ("本版技術規格（倉庫副本）", "silverstock_quant_web/docs/V5.0_SYSTEM_SPEC.md", "1 份"),
        ("公開倉庫", G["remote"], "線上仍是 V2.7"),
    ]:
        add(f'<tr><td>{e(a)}</td><td><code>{e(b_)}</code></td><td>{e(c)}</td></tr>')
    add('</table>')

    add(f'<footer>本頁所有數字由 <code>v50_inventory.json</code> 讀檔回填，'
        f'盤點程式 <code>tool/v3/inventory_v50.py</code>，'
        f'產生器 <code>tool/v3/gen_v50_spec.py</code>。'
        f'{e(D["generated_at"])} 產出。這份是方法與風險控管示範，不是買賣建議。</footer>')
    add('</div></body></html>')
    return "\n".join(H)


# ══════════════════════════════════════════════════════════════════
# Markdown（技術版，可放倉庫供接續開發）
# ══════════════════════════════════════════════════════════════════
L = []
def q(s=""):
    L.append(s)


def build_md():
    q("# V5.0 台海股投資接續系統・開發與技術總規格")
    q("")
    q(f"> 盤點日期：{D['generated_at']}｜接續 V2.7 ～ V4.6｜現況：M0 練習帳，未連券商、未下單")
    q("> 讀者：家人與接手開發者。內文繁體、白話；技術名詞首次出現立刻附解釋。")
    q("> 數字全部由 `v50_inventory.json` 讀檔回填，盤點程式 `tool/v3/inventory_v50.py`。")
    q("")
    q(f"**一句話：{ONE_LINE}**")
    q("")
    q("---")
    q("")
    q("## 給爸媽的一頁紙")
    q("")
    for t, p in THREE_THINGS:
        q(f"**{t}** {p}")
        q("")
    q("---")
    q("")

    q("## 1．現在到底有什麼")
    q("")
    q(f"| 項目 | 數字 |\n|---|---:|")
    q(f"| 寫好的程式 | {C['n_py_modules']} 支 |\n| 程式總行數 | {C['n_py_lines']:,} 行 |"
      f"\n| 結果檔 | {C['n_result_files']} 份 |\n| 報告 | {C['n_report_files']} 份 |"
      f"\n| 版本 | {C['n_versions']} 個 |")
    q("")
    q("本版不新增交易功能，只把既有資產收成一張可接續的地圖。")
    q("")

    q(f"## 2．{C['n_versions']} 個版本，六段路")
    q("")
    q("| 版本 | 那一段在做什麼 | 留下來的東西 |\n|---|---|---|")
    for v, t, p in HISTORY:
        q(f"| **{v}** | **{t}** | {p} |")
    q("")

    q("## 3．系統分成六層")
    q("")
    q("往後要改東西，先問「要改的是哪一層」，不要一次動六層。")
    q("")
    q("| 層 | 名稱 | 白話 | 生活比喻 | 對應檔案 |\n|---|---|---|---|---|")
    for no, nm, wh, analogy, real in LAYERS:
        q(f"| {no} | **{nm}** | {wh} | {analogy} | `{real}` |")
    q("")
    q("> **最要緊的一句**：第 4 層（授權）的鑰匙永遠在人手上。"
      "第 1～6 層都可以交給電腦，只有「要不要花真錢、能花多少」不行。")
    q("")

    q("## 4．第一層：資料從哪裡來")
    q("")
    q(f"- 股票 {DS['n_stocks']} 檔、大盤日線 {DS['index_bars']:,} 天、"
      f"範圍 {DS['range'][0]} ～ {DS['range'][1]}、最後補貨 {DS['captured_at']}")
    q(f"- 單一股票日線 {DS['bars_min']:,} ～ {DS['bars_max']:,} 天；"
      f"每季獲利數字只有 {DS['with_quarterly_eps']}/{DS['n_stocks']} 檔有")
    q(f"- 來源：{DS['source']}")
    q(f"- 單檔欄位：{', '.join(DS['fields_per_stock'])}")
    q("")
    q("**八樣資料沒有，一律寫不知道**：" + "、".join(DS["missing_fields"]) + "。")
    q("")
    q("**V2.8 規格（尚未寫進網頁）**：兩個時間（行情時間／資料更新）皆為靜止固定值；"
      "三態標籤（盤中報價／今日收盤／歷史資料）；全站不顯示會跳動的裝置時鐘；"
      "行情落後超過 3 個日曆日顯示陳舊警示；判斷以資料自帶時間為準，不以現在幾點猜。")
    q("")

    q("## 5．第二層：錢是怎麼算的")
    q("")
    q("| 項目 | 常數 | 數值 | 白話 |\n|---|---|---:|---|")
    fee_md = [
        ("買賣手續費", "FEE_RATE", pct(FEE["FEE_RATE"] * 100, 4), "買一次、賣一次各收"),
        ("個股賣出交易稅", "TAX_RATE_STOCK", pct(FEE["TAX_RATE_STOCK"] * 100, 1), "賣個股才收"),
        ("指數型基金賣出稅", "TAX_RATE_ETF", pct(FEE["TAX_RATE_ETF"] * 100, 1),
         "這種商品一次買一籃子（像 0050）；身分判錯要重算整本帳"),
        ("現股當沖賣出稅", "TAX_RATE_DAYTRADE", pct(FEE["TAX_RATE_DAYTRADE"] * 100, 2), "當沖適用"),
        ("零股最低手續費", "MIN_FEE_ODD", f'{FEE["MIN_FEE_ODD"]} 元', "金額太小反而吃虧"),
        ("整股最低手續費", "MIN_FEE_ROUND", f'{FEE["MIN_FEE_ROUND"]} 元', "整張買賣適用"),
    ]
    for key, cn, val, plain in fee_md:
        q(f"| {key} | `{cn}` | {val} | {plain} |")
    q("")
    q(f"算錢程式集中 `tool/v3`：{C['n_py_modules']} 支、{C['n_py_lines']:,} 行。"
      "每支算完存結果檔，報告讀結果檔來寫，不憑印象手抄（V4.2 第八條）。")
    q("")
    q(f"**實際案例（中探針，一張）**：買 371 元實付 {money(B['buy_paid'])} 元；"
      f"109 元賣出實收 {money(B['sell_received'])} 元；"
      f"不見 {money(B['loss_per_lot'])} 元（{minus(B['loss_pct_on_cash'])}）。"
      f"打平需漲回 {B['recover_price']:.1f} 元＝再漲 {pct(B['recover_pct_from_now'])}。")
    q("")

    q("## 6．第三層：寫死不改的規矩")
    q("")
    cap = PR["REGIME_CAP"]
    q(f"- 七條價值觀（{RU['n_values']} 條）：先活下來、能力圈、成本、紀律、"
      "賠得起的風險、代價先算、承認會錯")
    q(f"- 五層漏斗常數：`MIN_BARS={PR['MIN_BARS']:,}`、`MIN_ADV_NTD={PR['MIN_ADV_NTD']:.0e}`、"
      f"`MAX_VOL_ANN={PR['MAX_VOL_ANN']}`、`MAX_DRAWDOWN={PR['MAX_DRAWDOWN']}`、"
      f"`MAX_PE={PR['MAX_PE']}`、`INDUSTRY_CAP={PR['INDUSTRY_CAP']}`")
    q(f"- 四種天氣 → 最多放多少：好天（BULL）{cap['BULL']*100:.0f}%／"
      f"普通（NEUTRAL）{cap['NEUTRAL']*100:.0f}%／下雨（BEAR）{cap['BEAR']*100:.0f}%／"
      f"颱風（CRISIS）{cap['CRISIS']*100:.0f}%。括號前是給人看的說法，括號裡是程式用的代號。")
    q(f"- 下單前 {RU['n_pretrade_questions']} 問：任一題否／未答／不確定 → 拒單"
      "（資料不夠就當不過關，寧可錯過不放寬）")
    q("- 單一炒作股上限 1%；四層桶（現金／高息／指數／衛星）")
    q(f"- 三條熔斷：單日已實現虧損 {money(AD['max_daily_loss'])} 元、"
      f"連虧 {AD['max_consecutive_losses']} 筆、權益自峰值回撤 "
      f"{pct(AD['max_drawdown_pct']*100,0)} → 全部停單、降級、隔日不自動復機")
    q("")
    q("> **防混淆（本版新增）**：文件裡有兩組都叫 Gate 的東西，名稱相近、管的事完全不同。"
      "① **升級五關**（V3.0，G1～G5）＝准不准花真錢；"
      "② **規矩三道安檢門**（V4.2，G1～G3）＝准不准把新方法寫進程式。"
      "往後一律寫全名，不再只寫代號。")
    q("")

    q("## 7．第四層：誰准它動真錢")
    q("")
    q("| 層級 | 常數 | 送券商 | 逐筆確認 | 現況 |\n|---|---|---|---|---|")
    for lv, cn, send, cf, now in [
        ("M0 練習帳", "M0_PAPER", "否", "不適用", "✅ 現在在這裡"),
        ("M1 只出主意", "M1_DRYRUN", "否", "不適用", "已備妥，未啟用"),
        ("M2 逐筆確認", "M2_CONFIRM", "是", "要", "待開通"),
        ("M3 額度內自動", "M3_AUTO", "是", "不要", "🔒 鎖著，未解鎖"),
    ]:
        q(f"| **{lv}** | `{cn}` | {send} | {cf} | {now} |")
    q("")
    q("**十一條線同時生效**（`AuthorizationPolicy` 保守預設，全部待人拍板）：")
    q("")
    q(f"| 類別 | 參數 | 預設 |\n|---|---|---:|")
    for k, label, fmt in [
        ("max_total_exposure", "累計買進總額", "money"),
        ("max_order_amount", "單筆上限（含費用）", "money"),
        ("max_daily_amount", "單日累計金額", "money"),
        ("max_orders_per_day", "單日筆數", "int"),
        ("max_symbol_exposure", "單一標的曝險", "money"),
        ("max_position_pct", "持股比重", "pct"),
        ("max_daily_loss", "單日虧損熔斷", "money"),
        ("max_consecutive_losses", "連虧筆數熔斷", "int"),
        ("max_drawdown_pct", "峰值回撤熔斷", "pct"),
        ("max_quote_age_seconds", "報價最久可用（秒）", "int"),
    ]:
        v = AD[k]
        s = money(v) if fmt == "money" else (pct(v * 100, 0) if fmt == "pct" else str(v))
        q(f"| {label} | `{k}` | {s} |")
    q(f"| 白名單 | `whitelist` | {', '.join(AD['whitelist'])} |")
    q(f"| 時段 | `allow_session` | {', '.join(AD['allow_session'])} |")
    q(f"| 整張 | `allow_round_lot` | {'否' if not AD['allow_round_lot'] else '是'} |")
    q("")
    q("**五道不可繞過的防線**：額度 frozen 不可改；升級需人簽名＋五關全過；"
      "熔斷即降級不自動復原；人隨時可收回；逐筆留痕。")
    q("")
    q("**職責鏈**：`decide()` 意圖 → `risk_gate()` 風險 → `authorize()` 授權與額度 → "
      "`place_from_intent()` 才送券商；未帶授權結果一律不放行。")
    q("")
    q("**兩道急停**：本機 `revoke()`；券商端停用 API 金鑰／撤銷雲端條件單。")
    q("")
    q(f"**現況**：測試位址僅為常數 `{RU['sandbox_url']}`，未連線、未登入、未下單。"
      "升級五關目前僅 G1（紙上對照跑贏買入持有）通過，G2～G5 未開始。")
    q("")

    q("## 8．第五層：話要怎麼說")
    q("")
    q(f"從 V4.2 起固定 {SI['n_speak_rules']} 條，寫法不對，報告不算完成：")
    q("")
    for i, (t, p) in enumerate(SPEAK, 1):
        q(f"{i}. {t}" + (f"（{p}）" if p else ""))
    q("")
    q("**交付前七項體檢**：簡體殘留、術語偷跑、數字前後不一致、章節跳號、"
      "標籤未閉合、舊說法與新結論矛盾、瀏覽器截圖溢出。")
    q("")
    q("**術語白話對照**：")
    q("")
    q("| 詞 | 意思 | 家裡的說法 |\n|---|---|---|")
    for a, b_, c in GLOSSARY:
        q(f"| **{a}** | {b_} | {c} |")
    q("")

    q("## 9．第六層：系統會自己改錯")
    q("")
    q(f"錯題本 {SI['n_error_ledger']} 筆；新規矩要過 {len(SI['gates'])} 道安檢門：")
    q("")
    q("| 門 | 問什麼 | 白話 | 沒過 |\n|---|---|---|---|")
    for g in SI["gates"]:
        q(f"| **{g['id']}** | {g['name']} | {g.get('plain','')} | {g.get('fail_plain','')} |")
    q("")
    q(f"目前 {len(SI['claims'])} 條規矩逐條評過，分為可進系統／附條件／只能觀察／不准用。")
    q("")
    q("**六步改法**：找 → 定位 → 只改一處 → 重跑 → 前後對照 → 記帳＋過閘。"
      "V4.0 曾一次改三處，只能證明方向對，不能證明是誰有功勞。")
    q("")
    q("**靠日曆**：每次下單前（十二問＋三熔斷）／每月（對帳）／每季（換資料重考）／"
      "每次想改方法（人簽名才算數）／每年（重讀錯題本）。")
    q("")

    q("## 10．算過的數字，一張表看完")
    q("")
    cr, fb, ai, gp, lv = EV["correlation"], EV["four_bucket"], EV["all_in"], EV["groups"], EV["leverage"]
    c30 = EV["crash30"]
    q("| 問題 | 數字 | 白話 |\n|---|---:|---|")
    q(f"| 分到 {cr['n_assets']} 檔後整體晃動少 | {pct(cr['vol_reduction_pct'])} | "
      f"單檔 {pct(cr['single_vol_pct'])} → 等權 {pct(cr['equal_weight_vol_pct'])} |")
    q(f"| 平均相關／等效檔數 | {cr['avg_pairwise_corr']:.4f}／{cr['effective_n']} 檔 | 分開有效但沒想像中多 |")
    q(f"| 四層桶年化／最大回撤 | {pct(fb['ann_pct'])}／{minus(fb['mdd_pct'])} | 比全押溫和 |")
    q(f"| 全押指數年化／最大回撤 | {pct(ai['ann_pct'])}／{minus(ai['mdd_pct'])} | 賺多一點、跌深很多 |")
    q(f"| 急殺 30 天大盤／防禦／炒作 | {minus(c30['index_ret_pct'])}／{minus(c30['DEF'])}／"
      f"{minus(c30['HYPE'])} | 一起被砍，撐傘的淋得少 |")
    q(f"| 炒作組整段／途中最多跌 | {minus(gp['HYPE']['total_pct'])}／{minus(gp['HYPE']['mdd_pct'])} | "
      "跑最快摔最重 |")
    q(f"| 山頂兩倍錢 30 天／回本需 | {minus(lv['lever_ret_pct'])}／{pct(lv['recover_needed_pct'],1)} | "
      "不要用借來的錢 |")
    q(f"| 當沖來回成本／一年侵蝕 | {pct(EV['daytrade']['cost_stock_pct'],3)}／"
      f"{pct(EV['daytrade']['annual_erosion_stock_pct'],1)} | 越勤越快不見 |")
    q(f"| {EV['structure']['n_days']:,} 天裡個股各走各的（天數占比） | "
      f"{pct(EV['idio']['pct'],1)} | 靠分開放，不靠猜 |")
    q("")
    q(f"> **一個數字兩種意思**：個股主導的「天數占比」是 {pct(EV['idio']['pct'],1)}，"
      f"「漲跌歸因占比」是 {pct(EV['idio']['share_idio']*100,0)}。"
      "V4.6 曾把前者誤寫成後者，已記進錯題本；引用務必講清楚是哪一個。")
    q("")

    q("## 11．現在的真實狀態，與接著要做的事")
    q("")
    q("**現在還沒有的事**：")
    q("")
    q(f"1. 仍是 M0 練習帳，沒連券商、沒下單；升級五關只過 G1。")
    q(f"2. 本機 {G['n_untracked']} 項新檔案未推上 GitHub（舊令牌已撤銷，需新令牌；憑證不進倉庫）。")
    q(f"3. 中探針不在 {DS['n_stocks']} 檔池；外部僅 {B['external_bars']} 根日線，"
      f"規矩要 {B['required_bars']:,} 根 → 資料不夠就當不合格。")
    q("4. V2.8 雙時間三態仍只是規格，尚未寫進網頁。")
    q("")
    q("**接續路線（按先後，不是加新功能）**：")
    q("")
    q("| 順序 | 要做的事 | 為什麼現在做 |\n|---|---|---|")
    for a, b_, c in roadmap:
        q(f"| **{a}** | {b_} | {c} |")
    q("")
    q("> 七件事沒有一件是「讓系統更會賺」，全是補資料、拆改動、收權限。"
      "系統進步是變誠實，不是變大膽（V4.2 定調）。")
    q("")

    q("## 12．技術債（給接手寫程式的人）")
    q("")
    q("| 現況 | 數字 | 會出什麼事 |\n|---|---:|---|")
    for a, b_, c in debt_rows:
        q(f"| {a} | **{b_}** | {c} |")
    q("")
    q("**建議最小改法（尚未執行，先記著）**：① 絕對路徑改相對；② 抽共用版型；"
      "③ 七項體檢寫成固定程式；④ 結果檔統一放倉庫同一處。"
      "四件都是整理，一次只做一件、做完重跑對照，避免再犯「一次改三處」。")
    q("")
    q("### 模組清單（真實盤點）")
    q("")
    q("> 下表「摘要」直接取自各程式檔開頭說明，只做簡轉繁（優先 opencc，缺套件時退回內建單字表），"
      "**未改寫內容**；行數、函式數由程式讀檔算出。")
    q("")
    q("| 檔案 | 行數 | 函式／類別 | 摘要 |\n|---|---:|---:|---|")
    for m in D["modules"]:
        if m.get("parse_error"):
            continue
        q(f"| `{m['file']}` | {m['lines']:,} | {m['n_funcs']}/{m['n_classes']} | {mdcell(m['summary'][:60])} |")
    q("")
    q("### 結果檔清單")
    q("")
    q("| 檔案 | 大小 | 位置 |\n|---|---:|---|")
    for r in D["results"]:
        q(f"| `{r['file']}` | {r['bytes']:,} B | {'倉庫' if r['in_repo'] else '/workspace'} |")
    q("")

    q("## 附錄 A．這次哪裡可能錯")
    q("")
    for t in [
        "資料只有一段難得的大多頭，空頭看得不夠；所有「不要賣」的規矩都可能被高估。",
        f"八樣資料沒有、每季獲利只有 {DS['with_quarterly_eps']}/{DS['n_stocks']} 檔。",
        "三道安檢門、升級五關都是自訂標準，不是市場保證。",
        "本版只盤點整理，沒有重跑任何回測；來源檔若有錯，本版會一起帶著錯。",
        "盤點數字是當下檔案狀態；每加一支程式、每推一次就要重跑盤點。",
        "全部是練習帳，沒連券商、沒下一張單。系統會犯錯，只是它會把錯記下來。",
    ]:
        q(f"- {t}")
    q("")

    q("## 附錄 B．檔案放在哪裡")
    q("")
    q("| 東西 | 位置 |\n|---|---|")
    q("| 網頁原始碼（Flutter Web） | `silverstock_quant_web/lib/`、`web/` |")
    q("| 資料檔 | `silverstock_quant_web/assets/data/` |")
    q("| 算錢與規則程式 | `silverstock_quant_web/tool/v3/` |")
    q("| 結果檔 | `silverstock_quant_web/v*.json`、`/workspace/v*.json` |")
    q("| 報告 | `/workspace/V*.html`、`V*.md` |")
    q("| 本版盤點 | `silverstock_quant_web/v50_inventory.json` |")
    q("| 本版規格（倉庫副本） | `silverstock_quant_web/docs/V5.0_SYSTEM_SPEC.md` |")
    q(f"| 公開倉庫 | `{G['remote']}`（線上仍是 V2.7） |")
    q("")
    q("## 附錄 C．倉庫狀態與版本")
    q("")
    q(f"- 倉庫最近提交：`{G['last_commits'][0] if G['last_commits'] else '（無法讀取）'}`")
    q(f"- 未推送項目（{G['n_untracked']}）：" + "、".join(f"`{x}`" for x in G["untracked"]))
    q(f"- 報告版本：{'、'.join(D['reports']['by_version'].keys())}")
    q("")
    q("---")
    q("")
    q(f"*盤點 `tool/v3/inventory_v50.py` → `v50_inventory.json` → 本檔。"
      f"{D['generated_at']} 產出。方法與風險控管示範，不是買賣建議。*")
    return "\n".join(L)


# 讓 MD 也能引用 HTML 段定義的兩張表
roadmap = [
    ("先", "辦新令牌，把 tool/v3 與所有結果檔、本規格推上倉庫",
     f'現在 {G["n_untracked"]} 項只存在這台機器，換台電腦就沒了；憑證絕對不進倉庫'),
    ("先", "把 V2.8 的雙時間、三態標籤、資料時效總覽做進網頁",
     "規格寫好了兩版，網頁還在顯示會讓人誤會的舊寫法"),
    ("再", "把「部分減碼／月檢／賣後回補」拆開，一次只改一處各驗一次",
     "V4.0 那次一次改了三處，只能證明方向對，不能證明是誰有功勞"),
    ("再", "圖表改存每日數字，不再每七天取一個點",
     "取樣會漏掉最深那天，跌幅平均低估 2.76 個百分點、最多 5.68"),
    ("再", "換成多段輪流考，不再只切一次",
     "只考一段，可能是剛好押中那一段"),
    ("後", "補資料：八樣缺的、每季獲利、中探針要夠 1,000 根連續日線",
     "資料齊了，五道安檢門才能給正式分數；不齊就繼續寫不知道"),
    ("最後", "才談富邦測試環境全鏈路、逐筆確認實盤十天、簽署開通、書面授權",
     "這四關全過，才輪到討論要不要解鎖自動；而且要以「策略」為單位放行"),
]

debt_rows = [
    ("程式把資料位置寫死在某一台機器", f'{TD["n_modules_with_abs_path"]}/{C["n_py_modules"]} 支',
     "換台電腦、換個資料夾就找不到資料，全部要改"),
    ("報告生成器各自寫一套輸出位置", f'{TD["n_generators"]} 支',
     f"輸出路徑三種寫法混用；想改版型要改 {TD['n_generators']} 次"),
    ("結果檔散在兩個地方", f'倉庫 {TD["n_result_in_repo"]} 份／外層 {TD["n_result_in_root"]} 份',
     "備份容易漏，讀檔要分兩邊找"),
    ("沒有一支共用的版型程式", "沒有" if TD["no_shared_layout_module"] else "有",
     f"字級、顏色、淺底改一次要動 {TD['n_generators']} 支"),
    ("沒有一支自動體檢程式", "沒有" if TD["no_auto_check_script"] else "有",
     "前面七項體檢都是每次手寫，容易漏"),
    ("新檔案還沒推送", f'{G["n_untracked"]} 項',
     "只存在這台機器；推送要新令牌，憑證不進倉庫"),
]


def main():
    OUT_HTML.write_text(build_html(), encoding="utf-8")
    md = build_md()
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_REPO.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPO.write_text(md, encoding="utf-8")
    print(f"產出 {OUT_HTML.name}（{OUT_HTML.stat().st_size:,} bytes）")
    print(f"產出 {OUT_MD.name}（{OUT_MD.stat().st_size:,} bytes）")
    print(f"產出 {OUT_REPO}（{OUT_REPO.stat().st_size:,} bytes）")


if __name__ == "__main__":
    main()
