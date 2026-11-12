#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
case_6217.py — 用「我們的方法」分析 6217 中探針（V4.3 單一個案）

最重要的立場（延續 V4.2 的自檢規矩）：
  這檔股票【不在】111 檔回測池裡，所以：
    · 含息五年報酬、最大回撤、樣本外檢驗、風險換報酬 → 一律寫「不知道」
    · 以下所有數字都來自外部公開網頁，逐條標日期與來源
    · 判定邏輯直接呼叫 principles.py 的同一組常數與 pretrade_check，
      不另外寫一套對自己寬鬆的規則

產出：v43_case_6217.json（報告的數字全部由此檔回填）
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import principles as P                     # 直接複用既有規則
from market_structure import suggested_layer

OUT = ROOT / "v43_case_6217.json"

# 輸出統一成給長輩看的繁體（單字元對單字元，無歧義才列入）
S2T = str.maketrans(
    "仓买涨后这时动过条测场盘单价费税态状检额续损开资数据网当际个门问题"
    "让记错变会进种组统结论证验实亿万钱确认识别类卫层长辈岁体压帐签断优级纪"
    "赚赔择选减线亏档补卖还来对关应该张",
    "倉買漲後這時動過條測場盤單價費稅態狀檢額續損開資數據網當際個門問題"
    "讓記錯變會進種組統結論證驗實億萬錢確認識別類衛層長輩歲體壓帳簽斷優級紀"
    "賺賠擇選減線虧檔補賣還來對關應該張"
)

# ══════════════════════════════════════════════════════════════════
# 一、證據檔：每一個數字都帶來源與日期，沒有來源的一律不寫
# ══════════════════════════════════════════════════════════════════
SRC = {
    "money": "MoneyDJ 理財網・探針/探針卡同業股價表（報酬計算日 2026/11/02）",
    "yuanta": "元大證券動態報導 6217（2026/11/04 收盤）",
    "luvai": "股譯 luvai 6217 個股頁（2026/11/04 收盤、11/05 盤中）",
    "yahoo": "Yahoo 奇摩股市 6217.TWO（2026/11/06 收盤）",
    "cmoney": "CMoney 理財寶 6217 報價頁（2026/11/05 收盤 118）",
    "cnyes": "鉅亨網盤中速報（2026/11/06）",
    "winvest": "Winvest 6217 公司概況（營收至 2026/09、財報至 2026Q2）",
    "nstock": "nStock 公司小百科 6217（配息/獲利摘要）",
    "udn": "經濟日報・中探針 Q2 自結（2026/07）",
    "disposal": "元大證券處置股公告（2026/05/20–06/02、2026/07/31–08/13 再次處置）",
    "user": "泰哥提供之 2026/11/06 台指收盤 39,701.64",
}

# 價格時間軸（多來源交叉，鏈條自洽：148 → 131 → 118 → 109）
PRICES = [
    {"date": "2026-11-02", "close": 148.00, "src": "money", "note": "近一週 −6.92%、近一月 −16.62%、近二月 −24.30%、今年以來 +189.06%"},
    {"date": "2026-11-04", "close": 131.00, "src": "yuanta", "note": "+2.50 元 / +1.87%，成交量 6,224 張，開 133.5 高 136 低 121"},
    {"date": "2026-11-05", "close": 118.00, "src": "cmoney", "note": "−13 元 / −9.92%，昨收 131；盤中曾見 123.50"},
    {"date": "2026-11-06", "close": 109.00, "src": "yahoo", "note": "−9.00 元 / −7.63%，前收 118，開 106.5，區間 106.5–110.5"},
]

# Yahoo 11/06 區間報酬
HORIZON = [
    ("1 天", -7.63), ("5 天", -28.29), ("1 個月", -37.36),
    ("6 個月", -61.48), ("今年以來", 112.89), ("1 年", 96.40),
]
W52_LOW, W52_HIGH = 45.55, 371.00

# 月營收年增率（Winvest）：用來對照「營收減速」與股價
REV_YOY = [
    ("2026/01", 55.74), ("2026/02", 42.94), ("2026/03", 15.42),
    ("2026/04", 22.24), ("2026/05", 51.18), ("2026/06", 43.91),
    ("2026/07", 27.80), ("2026/08", 23.00), ("2026/09", 0.70),
]

FUNDAMENTALS = [
    {"item": "2025 全年 EPS", "value": "−1.65 元", "src": "winvest", "plain": "去年整年每股賠 1.65 元"},
    {"item": "2026 上半年累計 EPS", "value": "−0.19 元", "src": "winvest", "plain": "今年上半年還是賠錢"},
    {"item": "2026Q2 EPS", "value": "−0.30 元", "src": "winvest", "plain": "第二季又由賺轉賠"},
    {"item": "近四季 EPS（TTM）", "value": "−0.37 元", "src": "yahoo", "plain": "最近一年合計仍是賠"},
    {"item": "本益比", "value": "無（虧損，算不出來）", "src": "yahoo", "plain": "公司沒賺錢，本益比這格是空的"},
    {"item": "2025 年現金股利", "value": "0 元／目前殖利率 0%", "src": "nstock", "plain": "今年沒發股息，完全沒有安全墊"},
    {"item": "近五年平均殖利率", "value": "1.25%", "src": "nstock", "plain": "就算過去有配，也遠低於高股息門檻 3.5%"},
    {"item": "2026 1–9 月累計營收", "value": "34.62 億、年增 29.65%", "src": "winvest", "plain": "生意確實變大，但還沒變成獲利"},
    {"item": "2026/09 單月營收", "value": "3.52 億、月減 16.09%、年增 0.7%", "src": "winvest", "plain": "年增從 55% 一路掉到接近 0"},
    {"item": "2026Q2 營益率／淨利率", "value": "−3.27%／−3.12%", "src": "nstock", "plain": "每做 100 元生意，本業還倒賠 3 元多"},
    {"item": "融資餘額", "value": "12,973 張（2026/10/20）", "src": "winvest", "plain": "很多人在借錢買，跌的時候會被追繳"},
    {"item": "外資買賣超", "value": "10/15–10/20 連 4 日賣超合計 −1,344 張", "src": "winvest", "plain": "大戶連續四天在賣"},
    {"item": "交易所處置紀錄", "value": "2026/05/20–06/02、2026/07/31–08/13（再次處置）", "src": "disposal", "plain": "被交易所點名兩次，等於被記了兩支警告"},
]

# 同產業 11/02 近一個月報酬（V4.1：先看產業，再看個股）
PEERS = [
    {"name": "6217 中探針", "close": 148.0, "m1": -16.62, "ytd": 189.06},
    {"name": "6515 穎崴", "close": 4485.0, "m1": -26.11, "ytd": 59.09},
    {"name": "7856 漢測", "close": 3240.0, "m1": -22.77, "ytd": None},
    {"name": "6223 旺矽", "close": 4655.0, "m1": -12.34, "ytd": 107.60},
]

# ══════════════════════════════════════════════════════════════════
# 二、程式計算（數字不手抄）
# ══════════════════════════════════════════════════════════════════
def computed():
    p0, p_last = PRICES[0]["close"], PRICES[-1]["close"]
    return {
        "last_close": p_last,
        "last_date": PRICES[-1]["date"],
        "drop_1102_to_1106_pct": round((p_last / p0 - 1) * 100, 2),
        "drop_1104_to_1106_pct": round((p_last / PRICES[1]["close"] - 1) * 100, 2),
        "drop_from_52w_high_pct": round((p_last / W52_HIGH - 1) * 100, 2),
        "rise_from_52w_low_to_high_pct": round((W52_HIGH / W52_LOW - 1) * 100, 1),
        "recover_to_high_pct": round((W52_HIGH / p_last - 1) * 100, 1),
        "w52_low": W52_LOW, "w52_high": W52_HIGH,
        "horizon": [{"label": a, "pct": b} for a, b in HORIZON],
        "rev_yoy": [{"month": a, "yoy_pct": b} for a, b in REV_YOY],
        "rev_yoy_first": REV_YOY[0][1], "rev_yoy_last": REV_YOY[-1][1],
        "rev_yoy_slowdown_pp": round(REV_YOY[-1][1] - REV_YOY[0][1], 2),
        "peers": PEERS,
        "peers_m1_avg_pct": round(sum(x["m1"] for x in PEERS) / len(PEERS), 2),
        "prices": PRICES,
        "fundamentals": FUNDAMENTALS,
        "sources": SRC,
        "note": "以上全部為外部公開網頁資料，非 111 檔回測池；不同來源報酬基準日不同，不可混合計算。",
    }


# ══════════════════════════════════════════════════════════════════
# 三、第一關：真的呼叫 screen()，看系統怎麼判「資料不足」
# ══════════════════════════════════════════════════════════════════
def real_funnel():
    """造一個只含 6217、只放外部可取得價格點的迷你 snapshot，
    直接餵給 principles.screen()。它會因為歷史不足 1000 根而判 fail。"""
    mini = {"stocks": {"6217": {
        "name": "中探針", "industry": "電子零組件",
        "closes": [x["close"] for x in PRICES],
        "volumes": [6224, 6224, 3331, 4145],
        "latest": [0, 0.0, None],
    }}}
    picks, final = P.screen(mini)
    p = picks[0]
    return {
        "method": "直接呼叫 principles.screen()（與選股漏斗同一組常數）",
        "bars_available": len(mini["stocks"]["6217"]["closes"]),
        "min_bars_required": P.MIN_BARS,
        "passed": p.passed,
        "fail_reason": [x.replace("历史", "歷史").replace("不足", "不夠") for x in p.fail_reason],
        "final_n": len(final),
        "plain": "系統第一關就擋下來：我們規定至少要有 4 年日線，"
                 "這檔在資料池裡一格都沒有。不是算出來不好，是根本不准算。",
    }


# ══════════════════════════════════════════════════════════════════
# 四、人工輔助核對：若用外部資料，五關各過不了哪一關
#    （明確標「代理值」，不冒充回測）
# ══════════════════════════════════════════════════════════════════
def funnel_checks():
    c = computed()
    adv_proxy = round(8290 * 1000 * 130 / 1e8, 2)   # 20日均量 × 約價 → 億元
    rows = [
        {
            "gate": "① 流動性：近 60 日日均成交額 ≥ 3 億",
            "threshold": "≥ 3 億元", "observed": f"約 {adv_proxy} 億元（20 日均量 8,290 張估算）",
            "status": "pass", "proxy": True,
            "plain": "買得到也賣得掉，但這是炒作帶出來的量，不是穩定的量。",
        },
        {
            "gate": "② 年線：股價要站在 240 日均線之上",
            "threshold": "站上年線", "observed": "11/04 已跌破半年低、連 5 天下跌；6 個月 −61.48%",
            "status": "fail", "proxy": True,
            "plain": "像溜滑梯一路往下，連比較長的平均線都站不回去。",
        },
        {
            "gate": "③ 回撤：五年最大回撤 ≤ 55%",
            "threshold": "≤ 55%", "observed": f"52 週高 {W52_HIGH} → 109，{c['drop_from_52w_high_pct']}%（僅一年）",
            "status": "fail", "proxy": True,
            "plain": "我們給的是「五年最多賠 55%」，它「一年」就賠掉七成，門檻直接破表。",
        },
        {
            "gate": "④ 估值：本益比 ≤ 40 且為正",
            "threshold": "≤ 40 倍", "observed": "無本益比（近四季虧損）；殖利率 0%",
            "status": "fail", "proxy": True,
            "plain": "公司還在賠錢，這格根本填不出數字；也沒配股息可以墊著。",
        },
        {
            "gate": "⑤ 波動：年化波動 ≤ 45%",
            "threshold": "≤ 45%", "observed": "無日線可算年化；但 5 天 −28.29%、單日 −9.92%、振幅 6.87%",
            "status": "unknown", "proxy": True,
            "plain": "這一格我們誠實寫「算不出來」。但光看這幾天，就已經不像能放核心的東西。",
        },
    ]
    passed = sum(1 for r in rows if r["status"] == "pass")
    return {
        "rows": rows, "passed_n": passed, "total_n": len(rows),
        "fail_closed": True,
        "plain": "五關裡確定過關的只有 1 關（流動性），另外 3 關明確不過、1 關資料不足。"
                 "按「資料不夠就當不合格」這條規矩，資料不足也算不過 → 結論就是不准放行。",
        "disclaimer": "此表為「外部資料人工核對」，不是回測結果；門檻值取自 principles.py 常數。",
    }


# ══════════════════════════════════════════════════════════════════
# 五、V3.9 分組：對照已實測的炒作組特徵
# ══════════════════════════════════════════════════════════════════
def hype_classify():
    c = computed()
    bear = json.loads((ROOT / "v39_bear_result.json").read_text(encoding="utf-8"))
    gp = bear["group_paths"]["groups"]
    hype_ref = gp.get("HYPE", {})
    checks = [
        {"feature": "短時間暴漲", "ours": "今年以來 +112.89%（11/06）；11/02 口徑 +189.06%",
         "ref": f"V3.9 炒作組在 2025/04 後多頭 +115.5%", "hit": True},
        {"feature": "隨後急殺", "ours": f"6 個月 −61.48%、1 個月 −37.36%、5 天 −28.29%",
         "ref": f"V3.9 炒作組 30 天急殺 −28.98%", "hit": True},
        {"feature": "深回撤", "ours": f"52 週高 371 → 109，{c['drop_from_52w_high_pct']}%",
         "ref": f"V3.9 炒作組全程最大回撤 −45.3%", "hit": True},
        {"feature": "平時冷、偶爾爆量", "ours": "11/05 量比 0.22（極縮）；但曾被列處置股兩次",
         "ref": "V4.1 實測炒作組平均量比 1.07 低於防禦組 1.12，但爆量日 3.7% > 2.7%", "hit": True},
        {"feature": "基本面跟不上", "ours": "近四季虧損、殖利率 0%、9 月營收年增僅 +0.7%",
         "ref": "V3.9 防禦組靠配息與低波動；炒作組沒有這層墊", "hit": True},
    ]
    return {
        "group": "HYPE 炒作組（且比樣本裡的 5 檔更極端）",
        "checks": checks,
        "hit_n": sum(1 for x in checks if x["hit"]), "total_n": len(checks),
        "hype_ref": {"n": hype_ref.get("n"), "total_pct": hype_ref.get("total_pct"),
                     "mdd_pct": hype_ref.get("mdd_pct")},
        "plain": "五個特徵全中。它不是「基本面股跌下來」，它本來就是炒作股，"
                 "而現在正在走我們實測過的那一段：把前面暴漲的全程吃掉。",
    }


# ══════════════════════════════════════════════════════════════════
# 六、V3.8 分層 + V4.0 狀態機 + 12 問拒單
# ══════════════════════════════════════════════════════════════════
def layer_and_pretrade():
    c = computed()
    # 用外部代理值造一個 Pick，餵給 V4.1 的 suggested_layer
    p = P.Pick(
        sid="6217", name="中探針", industry="電子零組件",
        close=c["last_close"], ret5y_pct=None,
        mdd_pct=c["drop_from_52w_high_pct"], vol_pct=None,
        adv_yi=round(8290 * 1000 * 130 / 1e8, 2), pe=None,
        yield_pct=0.0, above_ma240=False,
        passed=False, fail_reason=["資料不足", "跌破年線", "回撤過深", "估值不合格"],
    )
    layer, why = suggested_layer("6217", {"industry": "電子零組件"}, p, "HYPE")

    bear = json.loads((ROOT / "v39_bear_result.json").read_text(encoding="utf-8"))
    latest = bear["latest"]
    state = latest["state"]

    # 12 問：誠實作答（不是為了通過而填）
    answers = {
        "Q1": True, "Q2": None, "Q3": None, "Q4": None, "Q5": None,
        "Q6": None, "Q7": None, "Q8": None, "Q9": False,   # 近四季虧損
        "Q10": None, "Q11": False,                        # 就是因為「跌很多」才想買
        "Q12": None,
    }
    chk = P.pretrade_check(answers, state, 0.01)
    return {
        "layer": layer, "layer_reason": why,
        "single_stock_cap_pct": 1.0,
        "regime": {"state": state, "last": latest["last"], "date": latest["date"],
                   "drawdown_pct": latest["drawdown_pct"], "vol20_pct": latest["vol20_pct"],
                   "position_cap_pct": round(P.REGIME_CAP[state] * 100),
                   "note": "現金也是一種仓位；只留能領息的核心，反彈不追、破線減碼"},
        "pretrade": {"ok": chk["ok"], "issue_n": len(chk["issues"]),
                     "issues": chk["issues"],
                     "key_fails": ["第 9 題：公司最近一年合起來是賠錢的 → 不過",
                                   "第 11 題：是因為『跌很多』才想買 → 不過（這叫伸手接刀）",
                                   "其餘 9 題資料不夠，依規矩一律算不過關"]},
        "plain": "系統判定：這檔只能放最外面那一小格（最多總資產的 1%），"
                 "而且現在是空頭、12 問有 11 題過不了 → 今天不准下單。",
    }


# ══════════════════════════════════════════════════════════════════
# 七、V4.1 量能與市場結構
# ══════════════════════════════════════════════════════════════════
def structure_check():
    c = computed()
    v41 = json.loads((ROOT / "v41_structure_result.json").read_text(encoding="utf-8"))
    bl = v41["volume"]["buckets"]
    def find(prefix):
        return next((b["excess20_pct"] for b in bl if b["bucket"].startswith(prefix)), None)
    return {
        "volume_ratio_1105": 0.22, "avg_vol_20d_lots": 8290,
        "volume_rule": "成交量只拿來確認，不拿來找買點；若今天突然比最近 20 天平均多一倍量、"
                        "又跌破近一個月平均價，就把仓位縮小、停損往前移",
        "volume_ratio_plain": "量比＝今天的成交量 ÷ 最近 20 天的平均成交量；0.22 代表今天只有平常的兩成",
        "v41_ref": {
            "extreme_low_excess_pct": find("①"),
            "burst_excess_pct": find("⑥"),
            "all_six_negative": True,
        },
        "market_state": "指數主導／齊跌 + 產業齊跌（兩層同時發生）",
        "evidence": [
            "11/06 加權指數盤中 −4.18%～−4.74%，收 39,701.64（泰哥提供）",
            "11/06 測試介面概念領跌 −7.66%：健策 −9.99%、順德 −9.12%、中探針 −8.9%",
            f"同業近一個月平均 {c['peers_m1_avg_pct']}%（穎崴 −26.11%、漢測 −22.77%、旺矽 −12.34%）",
            "融資餘額 12,973 張 → 跌時有追繳賣壓，會自己越跌越賣",
        ],
        "order": "先看指數與上漲家數 → 再看產業差距 → 兩者都平靜才輪到選股",
        "plain": "今天不是『這家公司出事』，是整個測試介面族群一起被砍，連大盤也在跌。"
                 "照 V4.1 的判別順序，這種日子該做的是調總仓位，不是挑哪一支比較便宜。",
    }


# ═════════════════════════════════════════════════====════════════
# 八、三種人、三套做法
# ══════════════════════════════════════════════════════════════════
def scenarios():
    c = computed()
    return [
        {
            "who": "① 還沒買的人", "verdict": "不進場",
            "steps": [
                "今天不做任何動作，放現金就好（V3.9：空頭裡現金是唯一確定有效的）",
                "不要因為『從 371 跌到 109、便宜很多』就買——買之前那 12 道問題裡，專門有一題在擋這件事",
                "想看的話，只放進觀察名單，等第九節三個條件全部成立再談",
            ],
            "plain": "就像房子還在往下掉，別因為『比上個月便宜三成』就伸手去接。",
        },
        {
            "who": "② 已經小額持有（≤1%）", "verdict": "按炒作股鐵律執行，不加碼",
            "steps": [
                "單檔上限 1%，永遠不加碼、不攤平",
                "從買進成本算 −15% 無條件砍，交給券商條件單托管（不靠自己盯盤）",
                "現在是空頭，前面實測的當下動作是：符合炒作組特徵的持倉優先減",
                "不要套用前面講的『賣掉後又往上走就買回一點』——那條只給核心持股用，這檔不適用",
            ],
            "plain": "這一格本來就是『賠光也不影響生活』的錢，規則寫好就交給機器，不要改。",
        },
        {
            "who": "③ 已經重倉套牢", "verdict": "最難，但方向只有一個：慢慢降下來",
            "steps": [
                f"先承認一件事：等回本不是策略。從 {W52_HIGH:.0f} 跌到 {c['last_close']:.0f}，"
                f"要回到 {W52_HIGH:.0f} 得漲 +{c['recover_to_high_pct']:.0f}%",
                "不攤平、不加碼、不借錢補；融資 12,973 張代表別人正在被追繳，不要跟著進去",
                "不要在跌停日一次全砍（那是情緒），改成按日分批降到 ≤1%，退出的錢回填 L0 現金（24 個月生活費）",
                "再依 V3.8 順序：L0 補滿 → L1 高股息做現金流 → 才談其他",
                "每一筆都記進錯題本：當初是依哪一條買的？那條現在還成立嗎？",
            ],
            "plain": "這不是『認賠』，是『把會讓您睡不著的那部分，慢慢搬回安全的地方』。"
                     "一次搬完會很痛，分幾次搬，人才撐得住。",
            "honest": "要誠實：前面實測『分 10 次減碼』在大多頭裡少賺很多（76.7% vs 197.7%），"
                      "但那是上漲段；下跌段分批減是為了活下來，不是為了賺最多。這段樣本沒有對應實測，"
                      "所以只給方向，不給報酬數字。",
        },
    ]


def reentry_conditions():
    return {
        "title": "什麼時候才『重新拿出來看』（三個要同時成立）",
        "conditions": [
            {"no": 1, "text": "月檢站回 120 日均線（半年線），而且不是單日跳一下",
             "plain": "不是看今天紅棒，是每個月底看一次，連續站穩才算"},
            {"no": 2, "text": "連續兩季 EPS 由負轉正，且殖利率不再是 0",
             "plain": "公司真的開始賺錢、也願意發股息，才有基本面可依"},
            {"no": 3, "text": "波動收斂到 30% 以下，且大盤脫離空頭",
             "plain": "雲霄飛車先停下來，外面的風雨也停了，再談上車"},
        ],
        "gate": "三條都成立也只是『可以放進觀察名單』，不是『可以買』；"
                "買之前還要再跑一次 12 問與五層漏斗。",
    }


def auto_trading():
    return {
        "status": "M0 模擬盤，未連富邦、未下任何單（與前幾版相同）",
        "whitelist": "這檔不進自動化白名單",
        "allowed_orders": [
            "只掛『停損』，不掛『加碼』、不掛『抄底』",
            "−15% 停損（以買進成本為準）交券商雲端條件單托管",
            "單檔最多 1%、一天最多幾筆先寫死；三條自動停手規則（一天賠到 300 元、"
                          "連賠 3 次、整體從高點跌 8%）永遠最優先",
        ],
        "not_allowed": [
            "不設『跌到 XX 元自動買進』（那正是接刀）",
            "不設『反彈就補回』（V4.0 那條只給核心層）",
            "不開當沖對沖：V4.0 實測來回成本 0.435%、每天做一次一年侵蝕 66.7%，"
            "且我們資料沒有開高低價，任何日內勝率都是編的",
        ],
        "plain": "自動交易在這裡的角色是『幫您踩煞車』，不是『幫您找買點』。",
    }


def gaps():
    return {
        "in_pool": False, "pool_n": 111,
        "cannot_answer": [
            "含息五年總報酬、最大回撤、年化波動（需要 111 檔池的日線）",
            "V3.7 五層漏斗的正式評分與排名（這檔不在池）",
            "V3.9 防禦／中間／炒作三組的樣本外淨值（分組需事前特徵）",
            "任何『這樣做會賺多少』的回測數字",
            "真實換手率、當日開高低價、融資融券逐日、逐筆成交、法人完整動態",
        ],
        "what_we_did": "改用外部公開報價逐條標來源，並把既有方法（門檻常數、12 問、分層規則）"
                       "原封不動套上去做判定，沒有為這檔放寬任何一條。",
        "plain": "資料不夠就寫不知道。這份報告能說的是『該不該碰、碰了怎麼管』，"
                 "不能說的是『會賺多少』。",
    }


def build():
    c = computed()
    return {
        "version": "V4.3", "case": "6217 中探針（C.C.P. Contact Probes）",
        "asof": "2026-11-08（資料最新至 2026/11/06 收盤）",
        "one_line": "這檔不是『便宜了』，是『炒作股正在把前面暴漲還回去』；"
                    "我們的方法在資料不足時直接判不准放行。",
        "computed": c,
        "real_funnel": real_funnel(),
        "funnel_checks": funnel_checks(),
        "hype": hype_classify(),
        "layer_pretrade": layer_and_pretrade(),
        "structure": structure_check(),
        "scenarios": scenarios(),
        "reentry": reentry_conditions(),
        "auto": auto_trading(),
        "gaps": gaps(),
        "speaking": {
            "rule": "先給一句結論 → 每個道理配一個真數字與生活比喻 → 術語立刻換成白話 → 句子短、字大",
            "examples": [
                ("五層漏斗", "五道安檢門，一關沒過就不放行"),
                ("fail-closed", "資料不夠時，一律當作不合格，不放寬"),
                ("HYPE 炒作組", "會暴漲、也會一次把漲幅全還回去的那類"),
                ("年線／半年線", "過去一年／半年的平均價，站上去才算穩"),
                ("處置股", "被交易所點名『這檔太熱、要冷靜一下』"),
                ("融資斷頭", "借錢買的人被追繳，被迫在低點賣，越跌越賣"),
            ],
        },
    }


def main():
    d = build()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2).translate(S2T),
                   encoding="utf-8")
    print(f"產出 {OUT.name}  ({OUT.stat().st_size:,} bytes)")
    print("\n一句話：", d["one_line"])
    rf = d["real_funnel"]
    print(f"\n第一關 真的跑 screen()：可用 {rf['bars_available']} 根 / 需要 {rf['min_bars_required']} 根 "
          f"→ 通過 {rf['passed']}，原因 {rf['fail_reason']}")
    fc = d["funnel_checks"]
    print(f"人工核對五關：確定過 {fc['passed_n']}/{fc['total_n']}")
    for r in fc["rows"]:
        print(f"  [{r['status']:<7}] {r['gate']}")
    h = d["hype"]
    print(f"\n分組：{h['group']}（{h['hit_n']}/{h['total_n']} 特徵命中）")
    lp = d["layer_pretrade"]
    print(f"分層：{lp['layer']}｜單檔上限 {lp['single_stock_cap_pct']}%")
    print(f"市場：{lp['regime']['state']}（{lp['regime']['last']}）｜12 問通過 {lp['pretrade']['ok']}，"
          f"{lp['pretrade']['issue_n']} 題未過")
    print(f"\n資料邊界：在池 {d['gaps']['in_pool']} → 不能回答 {len(d['gaps']['cannot_answer'])} 類問題")


if __name__ == "__main__":
    main()
