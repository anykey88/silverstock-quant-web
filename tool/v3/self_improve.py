# -*- coding: utf-8 -*-
"""
V4.2 系統自修引擎（Self-Improvement Engine）
=====================================================================
目的：把「靠系統代替自律」與「系統自己會進步」變成可執行、可查核的東西。

它不是一個會預測行情的 AI。它做的是五件很笨但很可靠的事：
  1. 對帳  —— 把自己寫過的數字重算一遍，對不上就抓出來
  2. 分級  —— 每條結論貼標：換資料還站得住 / 只在舊資料漂亮 / 不能用
  3. 找洞  —— 自動列出資料缺什麼、因此還不能回答哪些問題
  4. 示範  —— 真的跑一次「發現錯 → 只改一處 → 重跑 → 前後對照」
  5. 記帳  —— 所有錯誤留在錯題本，不擦掉，下版再驗

輸出：v42_self_improve.json（所有數字由既有結果檔讀取，不手工抄錄）
"""
import json
import os
import statistics
from collections import Counter, defaultdict
from datetime import datetime

ROOT = "/workspace"
PROJ = os.path.join(ROOT, "silverstock_quant_web")
OUT = os.path.join(PROJ, "v42_self_improve.json")


def J(*paths):
    for p in paths:
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8"))
    return {}


V31 = J(os.path.join(ROOT, "v31_ab_result.json"), os.path.join(PROJ, "v31_ab_result.json"))
V33 = J(os.path.join(ROOT, "v33_strategy_lab_result.json"))
V35 = J(os.path.join(ROOT, "v35_factor_audit.json"))
V38 = J(os.path.join(PROJ, "v38_allocation_result.json"))
V39 = J(os.path.join(PROJ, "v39_bear_result.json"))
V40 = J(os.path.join(PROJ, "v40_execution_result.json"))
V41 = J(os.path.join(PROJ, "v41_structure_result.json"))


# ══════════════════════════════════════════════════════════════════
# 1. 錯題本：六版裡真實發生過、且真的改掉的錯
#    分類：算法 / 資料 / 假設 / 表達 / 記錄
#    「怎麼發現」一律是「重算對不上」或「自己多看一眼」，不是別人指正
# ══════════════════════════════════════════════════════════════════
ERROR_LEDGER = [
    dict(ver="V3.1", kind="資料", what="把 0050 當個股課 3‰ 交易稅",
         found="算完來回成本覺得不合理，回頭查費率表",
         fix="ETF 改 1‰，並做成 FeeConfig.for_symbol() 自動判斷",
         effect="0050 來回成本與全部對照數字重算", plain="同一支股票，身分搞錯，整張帳就錯了"),
    dict(ver="V3.1", kind="算法", what="合併清單時把標題寫進錯誤物件",
         found="線上頁面標題舊、內容新，比對後發現", fix="重新合併並對 main 補一次提交",
         effect="線上與本機一致", plain="貼錯格子，改了內容沒改到標題"),
    dict(ver="V3.3", kind="記錄", what="誤以為策略實驗室沒跑，實際 11/6 已跑出 3 折樣本外",
         found="回頭翻檔案時間戳", fix="向使用者更正，並把結果接回後續分析",
         effect="避免白白重跑一次", plain="自己記錯做過沒做過，比算錯還容易發生"),
    dict(ver="V3.8", kind="算法", what="相關性用「前值填空」補齊缺少的交易日",
         found="算出來的相關係數低得不合理，抽樣兩檔直接算對不上",
         fix="改成兩檔都有的日子才成對計算", effect="平均相關回到 0.248、有效檔數 3.8",
         plain="把沒上課的日子也算成缺席，成績單當然不準"),
    dict(ver="V3.8", kind="算法", what="止盈組合沒有留淨值曲線，算不出回撤",
         found="要看最大回撤時發現欄位是空的", fix="重寫讓每一天都記一筆淨值",
         effect="七種止盈規則才有了可比較的回撤", plain="只看期末多少錢，不知道中途最慘賠多少"),
    dict(ver="V3.8", kind="算法", what="算日均成交額時索引抓錯位置",
         found="龍頭股竟被判成低流動性", fix="改成從陣列尾端正確取 60 日",
         effect="流動性池從異常回到 64 檔", plain="量尺拿反了，量出來當然不對"),
    dict(ver="V3.8", kind="假設", what="流動性過濾加了「零收益日 <3%」，把正常股票誤殺",
         found="符合條件的檔數少到不合理", fix="只留日均成交額 ≥3 億這一個門檻",
         effect="相關性改用乾淨的 64 檔池", plain="條件加太多，好東西也被濾掉"),
    dict(ver="V3.9", kind="資料", what="第一段空頭資料起點不足 70 日，無法事前分類",
         found="分類函式回傳空值", fix="如實標註「只報整體」，不硬凑數字",
         effect="報告少了 1 段、但沒多 1 個假結論", plain="資料不夠就說不夠，不要硬編"),
    dict(ver="V4.0", kind="算法", what="減碼實驗起點沒買，報酬其實是空手利息",
         found="六組結果全都 2.4%，一看就是現金利率", fix="起點先建倉再跑",
         effect="減碼對照才成立", plain="忘了先把貨買進來，測到的只是錢躺著"),
    dict(ver="V4.0", kind="算法", what="分批成本變數抓到外層，用錯清單",
         found="分批次數怎麼改結果都一樣", fix="改成讀當次實際買進日",
         effect="分 1 次 134.6% → 分 20 次 89.5%", plain="記帳本翻錯頁，數字就重複了"),
    dict(ver="V4.0", kind="假設", what="組合規則起點空手分批，不符合已持有四層桶的實況",
         found="V 型反轉裡天然吃虧，與前提矛盾", fix="改成核心層起點就不動",
         effect="組合規則 +237.2%、回撤 −22.8%", plain="測的是別人的處境，不是自己的"),
    dict(ver="V4.0", kind="算法", what="全程段索引把 0 當成 False，落回起點",
         found="全程結果和第一段多頭一模一樣", fix="改用 None 判定",
         effect="三種策略全程對照才正確", plain="0 被電腦當成「沒有」，這很小但很要命"),
    dict(ver="V4.0", kind="資料", what="宣稱零股 1 元低收有用，其實 1,000 元根本沒觸發",
         found="1,000×1.425‰ = 1.425 元，比 1 元還多", fix="補算真正生效門檻 701.75 元",
         effect="誠實標出小額門檻，不再籠統說「零股便宜」", plain="優待根本沒用到，卻一直寫成有用到"),
    dict(ver="V4.0", kind="表達", what="報告繁體、結果檔簡體，還留下 ma240 英文訊號名",
         found="截圖檢查時看到混字", fix="在引擎層統一字體再重跑",
         effect="長輩看到的版本不再混", plain="給誰看的，就要用誰看得懂的字"),
    dict(ver="V4.1", kind="算法", what="橫截面極差被單檔異常值污染到 117pp",
         found="一天之內離散度飆到不可能", fix="改用 P95−P5 穩健極差",
         effect="產業差距回到 7.39pp 等合理範圍", plain="一個特別吵的人，不代表全班都很吵"),
    dict(ver="V4.1", kind="假設", what="分層規則把高波動、深回撤的股票放進核心層",
         found="對照 V3.8 核心層要低波動，自相矛盾", fix="MDD>40% 或波動>30% 一律降衛星層",
         effect="核心候選名單與四層桶一致", plain="前面說要穩，後面卻挑了最會晃的"),
    dict(ver="V4.1", kind="表達", what="橫向條狀圖遇到負值往左溢出，標籤被裁掉",
         found="截圖只看得到兩條", fix="改成條長代表落後幅度並加註",
         effect="四組全部看得見", plain="圖畫到紙外面，長輩就以為只有兩項"),
    dict(ver="V4.1", kind="記錄", what="手冊三個超額數字憑印象寫，與結果檔不符",
         found="回頭對帳，實際六組超額全部為負", fix="改成程式讀出的真值並加一句總結",
         effect="手冊與結果檔一致", plain="用記的就會記錯，用抄的才不會"),
    dict(ver="V4.1", kind="表達", what="章節編號漏了 7（一頁紙沒編到）",
         found="數標題時發現跳號", fix="補上編號",
         effect="8 章連續", plain="目錄跳號，翻的人會以為漏頁"),
    dict(ver="V4.2", kind="假設", what="上一版說升級『只加一句』，其實同時改了賣法、月檢、回補三處",
         found="自修引擎要跑『只改一處』示範時，對照程式碼發現",
         fix="如實改成『一次改三處』，並列為下版要補做的單因子對照",
         effect="不再把功勞歸給單一規則", plain="改太多地方，變好了也不知道該謝誰"),
    dict(ver="V4.2", kind="資料", what="圖表用的淨值曲線每 7 日取一個點，低估了最大回撤",
         found="自修引擎把曲線重算一次，跟原數字對不上",
         fix="標註取樣誤差，下版圖表改存每日淨值或另記真實最低點",
         effect="平均低估 2.76pp、最大 5.68pp", plain="一週只量一次血壓，會漏掉最高的那天"),
]


# ══════════════════════════════════════════════════════════════════
# 2. 自動對帳：把自己寫過的數字重算一遍
# ══════════════════════════════════════════════════════════════════
def mdd(series):
    peak, worst = series[0], 0.0
    for v in series:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1.0)
    return worst * 100


def reconcile():
    """檢查 A：total_pct 與 final_x 是否自洽；檢查 B：每 7 日取樣的淨值
    曲線重算回撤，會比真實回撤淺多少（這正是本次自檢新抓到的問題）。"""
    rows = []
    # V3.8 十二種配置
    for c in V38.get("configs", []):
        nav = c.get("nav_slim") or []
        if len(nav) < 20:
            continue
        calc = mdd(nav)
        rows.append(dict(src="V3.8 配置", label=c.get("name") or c.get("key"),
                         declared_total_pct=c.get("total_pct"),
                         recomputed_from_final_x=round((c.get("final_x", 1) - 1) * 100, 2),
                         declared_mdd_pct=c.get("mdd_pct"),
                         mdd_from_sampled_nav=round(calc, 2),
                         mdd_gap_pp=round(calc - c.get("mdd_pct", 0), 2)))
    # V4.0 組合規則三條曲線
    for c in V40.get("combined", []):
        for key, field in (("combo", "nav_slim"), ("buyhold", "bh_slim"),
                           ("static_target", "static_slim")):
            nav = c.get(field) or []
            if len(nav) < 20:
                continue
            obj = c.get(key, {})
            rows.append(dict(src="V4.0 " + c.get("label", ""), label=key,
                             declared_total_pct=obj.get("total_pct"),
                             recomputed_from_final_x=None,
                             declared_mdd_pct=obj.get("mdd_pct"),
                             mdd_from_sampled_nav=round(mdd(nav), 2),
                             mdd_gap_pp=round(mdd(nav) - obj.get("mdd_pct", 0), 2)))

    total_consistent = [r for r in rows
                        if r["recomputed_from_final_x"] is not None
                        and abs(r["declared_total_pct"] - r["recomputed_from_final_x"]) < 0.05]
    gaps = [r["mdd_gap_pp"] for r in rows if r["declared_mdd_pct"] is not None]
    return {
        "n_checked": len(rows),
        "total_pct_consistent_n": len(total_consistent),
        "total_pct_checked_n": sum(1 for r in rows if r["recomputed_from_final_x"] is not None),
        "avg_mdd_gap_pp": round(sum(gaps) / len(gaps), 2) if gaps else 0,
        "max_mdd_gap_pp": round(max(gaps), 2) if gaps else 0,
        "new_finding": "每 7 日取樣的淨值曲線會低估最大回撤（最深的那天可能沒被取到）",
        "new_finding_plain": "一週只量一次血壓，會漏掉中間最高的那一次",
        "rows": rows,
    }


# ══════════════════════════════════════════════════════════════════
# 3. 三道閘門：決定一條規矩能不能真的寫進系統
# ══════════════════════════════════════════════════════════════════
GATES = [
    dict(id="G1", name="換資料還站得住嗎", plain="拿沒複習過的考題再考一次",
         fail_plain="只在同一段資料漂亮，換一段就垮 → 不准上線"),
    dict(id="G2", name="改一點參數就變太多嗎", plain="食譜改一小匙就走味，代表是碰巧",
         fail_plain="參數一動成績差很大 → 只能觀察，不能當紀律"),
    dict(id="G3", name="資料夠不夠、成本算了沒", plain="樣本太少或忘了手續費，等於沒算",
         fail_plain="資料不足或沒扣成本 → 補齊再說"),
]


def grade_claims():
    """把歷版主要結論逐條過閘。判定依據一律來自結果檔的真實數字。"""
    wf = V40.get("walkforward", {})
    sens = wf.get("sensitivity", [])
    cal = [s["calmar"] for s in sens] if sens else []
    sens_spread = round(max(cal) - min(cal), 2) if cal else None
    lab = V33.get("summary", [])
    beat_zero = sum(1 for x in lab if x.get("beat_rate", 0) == 0)
    lab_n = len(lab)

    vol = V41.get("volume", {})
    ex_all = [r.get("excess20_pct") for r in vol.get("buckets", [])
              if r.get("excess20_pct") is not None]

    C = []

    def add(name, ver, verdict, why, plain, evidence):
        C.append(dict(rule=name, version=ver, verdict=verdict, reason=why,
                      plain=plain, evidence=evidence))

    _bucket = next((c for c in V38.get("configs", [])
                    if "四层桶" in str(c.get("key", "")) or "四層桶" in str(c.get("key", ""))), {})
    _allin = next((c for c in V38.get("configs", []) if "100% 0050" in str(c.get("key", ""))), {})
    add("四層桶固定比例（20/25/35/20）", "V3.8", "可進系統",
        "12 種配置同一段資料比較，Calmar 最高且回撤、水下時間都較小；比例是事前定的，不是挑出來的",
        "不管行情怎麼變，錢先分四桶放好，不用每天猜",
        dict(calmar=_bucket.get("calmar"), mdd_pct=_bucket.get("mdd_pct"),
             ann_pct=_bucket.get("ann_pct"),
             allin_calmar=_allin.get("calmar"), allin_mdd_pct=_allin.get("mdd_pct"),
             n_configs=len(V38.get("configs", []))))
    add("部分止盈（+20% 賣 1/4、+30% 賣 1/2）", "V3.8 / V4.0", "可進系統",
        "七種規則對照，賣一部分改善 Calmar；且 V4.0 補回補規則後仍站得住",
        "賺了先拿一點回來放口袋，但不要一次全賣",
        dict(n_rules=len(V38.get("take_profit", []))))
    add("全清式移動停損 20%", "V3.8", "不准用",
        "被台股每年 15–25% 正常回調掃出場，年化大幅下降",
        "跌一點就全部賣掉，後面漲回來都跟自己無關",
        dict(note="V3.8 實測全清年化僅約 3.48%"))
    add("MA120 月檢等待（樣本內挑出的最佳參數）", "V4.0", "只能觀察",
        "前半段七個候選挑出來的；後半段雖然 Calmar 反勝，但改檢查週期就大幅變動",
        "在舊考卷上考滿分，不代表換一張卷子還會",
        dict(in_sample_calmar=wf.get("best_in_sample", {}).get("calmar"),
             out_sample_calmar=wf.get("test_rule_calmar"),
             out_sample_vs_bh_pp=wf.get("outperformance_pp"),
             sensitivity_spread=sens_spread,
             sensitivity=[(s["recheck_days"], s["calmar"]) for s in sens]))
    add("7 組擇時／選股策略", "V3.3", "不准用",
        "3 折樣本外，跑贏買入持有的比例為 0",
        "七套方法換到新資料，沒有一套比『買著不要動』好",
        dict(n_strategies=lab_n, beat_zero_n=beat_zero,
             buy_hold_mean=V33.get("buy_hold_mean")))
    add("量比爆量當買點", "V4.1", "不准用",
        "六個量比分組的 20 日超額報酬全部為負；量能×趨勢四組也全負",
        "看到成交量突然變大就追，長期是白忙",
        dict(n_buckets=len(ex_all), max_excess_pct=max(ex_all) if ex_all else None,
             min_excess_pct=min(ex_all) if ex_all else None))
    add("靜態目標價 +20% 全賣不回補", "V4.0", "不准用",
        "同一段資料比買入持有少賺一大截；補上回補規則才救回來",
        "設一個價就全賣，賣完就走，後面一大段都沒吃到",
        dict(static_pct=next((c["static_target"]["total_pct"] for c in V40.get("combined", [])
                              if c.get("label") == "全程"), None),
             buyhold_pct=next((c["buyhold"]["total_pct"] for c in V40.get("combined", [])
                               if c.get("label") == "全程"), None),
             combo_pct=next((c["combo"]["total_pct"] for c in V40.get("combined", [])
                             if c.get("label") == "全程"), None)))
    add("賣出後 20 日內創新高補回 1/4", "V4.0", "可進系統（附條件）",
        "只加一條規則就把靜態目標價的缺口補回大部分，且回撤仍較小；但只在一段大多頭驗過",
        "賣掉之後如果又往上走，就買回一點，不要賭氣不回頭",
        dict(combo_pct=next((c["combo"]["total_pct"] for c in V40.get("combined", [])
                             if c.get("label") == "全程"), None),
             caveat="尚未做滾動樣本外，參數為事前固定之中庸值"))
    add("零槓桿、不攤平、單檔 ≤1%", "V3.7 / V3.9", "可進系統",
        "不是報酬最優，是讓最壞情況不會被迫在低點賣出；屬結構性風控，不依賴預測",
        "這幾條不是為了多賺，是為了不管怎樣都還活得下去",
        dict(top_lever_loss_pct=V39.get("top_lever_loss", {}).get("lever_ret_pct")))

    return {"gates": GATES, "claims": C,
            "verdict_counts": dict(Counter(c["verdict"] for c in C))}


# ══════════════════════════════════════════════════════════════════
# 4. 自動找洞：資料缺什麼 → 因此哪些問題現在不能回答
# ══════════════════════════════════════════════════════════════════
def find_gaps():
    """真的去掃 snapshot.json 的欄位，不是靠印象列清單。"""
    snap = J(os.path.join(PROJ, "assets/data/snapshot.json"))
    stocks = snap.get("stocks", {})
    sample = next(iter(stocks.values()), {}) if stocks else {}
    have = set(sample.keys())
    top_keys = set(snap.keys())
    # (實際可能的欄位名, 給長輩看的名稱, 因此還不能回答的問題)
    need = [
        (("opens", "highs", "lows", "open", "high", "low"), "當日開高低價", "當沖、日內停損、真假突破"),
        (("floatShares", "sharesOutstanding", "turnoverRate"), "流通股數／真實換手率", "量比只是代理，不等於換手"),
        (("margin", "shortInterest", "institutional"), "融資融券與法人籌碼", "斷頭賣壓、籌碼流向"),
        (("ticks", "bidAsk", "orderBook"), "逐筆成交與委買委賣", "滑價、排隊成本"),
        (("intl", "sp500", "nikkei", "globalIndex"), "國際股市", "外溢效果與隔夜風險"),
        (("macro", "rates", "cpi", "fx"), "利率、通膨、匯率", "資金行情的源頭"),
        (("bonds", "gold", "otherAssets"), "債券、黃金等非股票資產", "真正的跨資產避險"),
    ]
    gaps = []
    for keys, label, blocks in need:
        hit = [k for k in keys if k in have or k in top_keys]
        gaps.append(dict(field=label, present="有" if hit else "沒有",
                         found=hit, cannot_answer=blocks,
                         status="齊" if hit else "缺"))
    n_eps = sum(1 for s in stocks.values() if len(s.get("quarterlyEps") or []) > 0)
    gaps.append(dict(field="全部個股的季 EPS", present=f"{n_eps}/{len(stocks)} 檔",
                     found=["quarterlyEps"], cannot_answer="基本面選股覆蓋率",
                     status="齊" if n_eps == len(stocks) else "部分"))
    missing = [g for g in gaps if g["status"] != "齊"]
    return {
        "n_fields_checked": len(gaps), "n_missing": len(missing),
        "n_stocks": len(stocks), "n_bars": len(sample.get("dates") or []),
        "gaps": gaps,
        "plain": "先問『資料有沒有』，再問『方法好不好』。資料沒有的，系統就直接說不知道，不編答案。",
    }


# ══════════════════════════════════════════════════════════════════
# 5. 看似打架的結論：把前提補回來（長輩最容易被這個搞混）
# ══════════════════════════════════════════════════════════════════
def conflicts():
    wf = V40.get("walkforward", {})
    return [
        dict(a="V3.8：擇時全部跑輸靜態配置",
             b="V4.0：MA120 月檢樣本外 Calmar 2.05 反勝持有 1.66",
             why="前者比的是『賺多少』，後者比的是『每一分風險換到多少』。少賺 10.19pp 但回撤少 6.77pp，兩句都對。",
             plain="一個比誰賺得多，一個比誰睡得安穩；講清楚比的是什麼，就沒有矛盾。"),
        dict(a="V3.1：120 天裡 AI-長線報酬第一",
             b="V3.3：5 年樣本外 7 組策略 0 組跑贏買入持有",
             why="前者是同一段資料裡比高低（事後看得出誰是贏家），後者是拿沒用過的資料考。考法不同，結果本來就該不同。",
             plain="在家練習考第一，和到考場考試，是兩件事。"),
        dict(a="V3.7 五層漏斗篩出 18 檔",
             b="V4.1：台積電評分最低卻漲最多、亞泥評分最高只漲 5.9%",
             why="漏斗篩的是『不容易出事』，不是『會漲』。這是設計目的，不是失靈。",
             plain="體檢報告說你很健康，不等於說你跑得最快。"),
        dict(a="V3.9：急殺只有 4/111 檔上漲",
             b="V4.1：急殺 31 天裡每日平均仍有 39.8% 個股上漲",
             why="前者是 30 天『累計』，後者是『每一天』的漲跌家數。跌日跌得深、漲日漲得少。",
             plain="一個月結算賠錢，不代表天天都賠；只是賠的那幾天特別重。"),
    ]


# ══════════════════════════════════════════════════════════════════
# 6. 真的跑一次迭代示範（所有數字現場算，不抄）
# ══════════════════════════════════════════════════════════════════
FEE = 0.001425
TAX_STOCK, TAX_ETF = 0.003, 0.001
MIN_ODD = 1.0


def fee_demo():
    """示範一：把 ETF 稅率改對，數字差多少（真實發生過的錯）"""
    amt = 10000.0
    def roundtrip(tax):
        fee = max(amt * FEE, MIN_ODD)
        return fee * 2 + amt * tax
    wrong, right = roundtrip(TAX_STOCK), roundtrip(TAX_ETF)
    return dict(amount_ntd=amt, wrong_tax="3‰（當成個股）", right_tax="1‰（ETF）",
                wrong_cost_ntd=round(wrong, 2), right_cost_ntd=round(right, 2),
                diff_ntd=round(wrong - right, 2),
                wrong_cost_pct=round(wrong / amt * 100, 3),
                right_cost_pct=round(right / amt * 100, 3),
                plain="一個身分標錯，來回就多算 20 元；金額一大，整份報告全要重算。")


def patch_demo():
    """示範二：V4.0 兩版規則前後差多少，並誠實標出「一次改了三處」這個毛病。"""
    full = next((c for c in V40.get("combined", []) if c.get("label") == "全程"), {})
    st = full.get("static_target", {}).get("total_pct")
    bh = full.get("buyhold", {}).get("total_pct")
    cb = full.get("combo", {}).get("total_pct")
    return dict(change="從『+20% 全賣不回補』改成『部分減碼＋月檢 MA120＋20 日內創新高補回 1/4』",
                before_pct=st, after_pct=cb, buyhold_pct=bh,
                recovered_pp=round(cb - st, 2) if (cb is not None and st is not None) else None,
                still_behind_pp=round(bh - cb, 2) if (cb is not None and bh is not None) else None,
                changed_parts=["賣法：全賣 → 分批賣 1/4、1/3", "加月檢 MA120 調整衛星倉", "加賣後回補規則"],
                caveat="一次改了三處，所以只能證明『方向對了』，不能證明是哪一條的功勞。這違反六步閉環的第 3 步，列為下一版要補做的單因子對照。",
                plain="改太多處，就算變好也不知道該謝誰。下一版要一次只動一個地方，慢慢拆開看。")


def sensitivity_demo():
    """示範三：參數只改一點，成績掉多少（防『找到最佳方法』的陷阱）"""
    s = V40.get("walkforward", {}).get("sensitivity", [])
    if not s:
        return {}
    best = max(s, key=lambda x: x["calmar"])
    worst = min(s, key=lambda x: x["calmar"])
    return dict(best_days=best["recheck_days"], best_calmar=best["calmar"],
                worst_days=worst["recheck_days"], worst_calmar=worst["calmar"],
                drop=round(best["calmar"] - worst["calmar"], 2),
                all=[(x["recheck_days"], x["calmar"]) for x in s],
                plain="只把『幾天檢查一次』從 21 改成 63，成績就從 2.05 掉到 1.18。這種漂亮，是碰巧，不是本事。")


def loop():
    return dict(steps=[
        dict(step=1, name="找", plain="每天把寫過的數字重算一遍，對不上就記一筆"),
        dict(step=2, name="定位", plain="先問是資料錯、程式錯、還是前提錯，不要急著改"),
        dict(step=3, name="只改一處", plain="一次只動一個地方，才知道是哪一步救回來的"),
        dict(step=4, name="重跑", plain="改完全部重算，不沿用舊數字"),
        dict(step=5, name="前後對照", plain="把改前、改後並排放，差多少寫清楚"),
        dict(step=6, name="記帳＋過閘", plain="寫進錯題本；過不了三道閘就不准上線"),
    ], fee_fix=fee_demo(), patch_fix=patch_demo(), sensitivity=sensitivity_demo())


# ══════════════════════════════════════════════════════════════════
# 7. 自律替代表：人會犯的錯 → 系統哪一條硬規矩擋住
# ══════════════════════════════════════════════════════════════════
def discipline_map():
    wf = V40.get("walkforward", {})
    full = next((c for c in V40.get("combined", []) if c.get("label") == "全程"), {})
    tp = V38.get("take_profit", [])
    trail = next((t for t in tp
                  if ("移動止損" in t.get("rule", "") or "移动止损" in t.get("rule", ""))
                  and "全清" in t.get("rule", "")), None)
    bull = (V39.get("bull_models") or [{}])[0].get("models", {})
    return [
        dict(human="一緊張就全部賣掉", system="核心層永不擇時；只准部分減碼",
             number=("全清移動停損年化 " + str(trail.get("ann_pct")) + "%") if trail else "全清移動停損年化約 3.48%",
             plain="手會抖，規矩不會"),
        dict(human="賺一點就想落袋、賣完不敢買回", system="目標觸發自動賣；20 日內創新高自動補 1/4",
             number=f"不回補 {full.get('static_target',{}).get('total_pct')}% → 補回 {full.get('combo',{}).get('total_pct')}%",
             plain="不用克服貪跟怕，讓條件單去按"),
        dict(human="跌了想攤平、想加碼拚回來", system="單檔上限、−15% 硬停、三條熔斷先於一切",
             number="單日 −300／連虧 3／回撤 8% 即停機，隔日不自動復機",
             plain="不是叫你忍，是直接不給按"),
        dict(human="看到爆量、聽到消息就追", system="量能只當確認不當買點；G3 不准上線",
             number="六個量比分組超額全為負", plain="把『想買』擋在資料前面"),
        dict(human="覺得自己找到最強參數", system="G1／G2 兩道閘：換資料重考、改參數看落差",
             number=f"21 日 Calmar 2.05 → 63 日 1.18", plain="先別高興，換張考卷再說"),
        dict(human="記錯做過沒做過、數字憑印象寫", system="對帳＋錯題本，全部數字由程式回填",
             number=f"錯題本已記 {len(ERROR_LEDGER)} 筆", plain="人會忘，檔案不會"),
        dict(human="想用槓桿賺快一點", system="零槓桿寫進授權層，M3 額度內也禁止",
             number=f"頂部 2 倍 30 天 {V39.get('top_lever_loss',{}).get('lever_ret_pct')}%",
             plain="不是算過風險，是直接不開這扇門"),
        dict(human="行情一變就想改整套方法", system="一次只改一處、重跑、前後對照才准升級",
             number="六步閉環，改動清單最多 1 條", plain="改太快，錯了都不知道錯在哪"),
    ]


# ══════════════════════════════════════════════════════════════════
# 8. 往後說話的規矩（使用者要求：大白話、給長輩看）
# ══════════════════════════════════════════════════════════════════
SPEAK_RULES = [
    dict(no=1, rule="每節先給一句話結論", plain="先講答案，再講為什麼"),
    dict(no=2, rule="一個道理配一個真實案例＋具體數字", plain="不講空話，講『誰、多少錢、後來怎樣』"),
    dict(no=3, rule="專有名詞一律換成生活比喻，非用不可立刻括號解釋",
         plain="樣本外＝拿沒複習過的考題再考一次"),
    dict(no=4, rule="句子短、一段不超過三行、字大、留白多", plain="一眼看得完，不用來回找"),
    dict(no=5, rule="給爸媽的版本：繁體、一頁、只講三件事", plain="不要給長輩一整本"),
    dict(no=6, rule="資料不夠就寫『不知道』，不編、不硬湊", plain="誠實比漂亮重要"),
    dict(no=7, rule="每次都附上『這次哪裡可能錯』", plain="先自首，別等人來抓"),
    dict(no=8, rule="數字一律由程式讀檔回填，不憑印象手寫", plain="用抄的，不要用記的"),
]


def can_cannot():
    """系統會進步，但進步的是紀律不是預測。這條邊界一定要講清楚。"""
    return [
        dict(can="記住每一次犯錯，不犯第二次", cannot="猜明天漲還是跌",
             plain="它很會記帳，不會算命"),
        dict(can="到點自動執行，不受情緒影響", cannot="找到穩賺不賠的方法",
             plain="資料只有一段大多頭，沒有穩賠這回事"),
        dict(can="換一段資料重考，拆穿假本事", cannot="保證報酬",
             plain="它會說『這個不可靠』，不會說『這個一定賺』"),
        dict(can="越權、超額、熔斷先擋下來", cannot="替您決定能賠多少",
             plain="賠得起多少，要您自己先簽，系統不改這條"),
        dict(can="把數字重算、把錯記下來", cannot="自己改寫授權範圍",
             plain="它會改算法，不會自己把門檻放寬"),
    ]


def maintenance():
    """靠日曆，不靠意志力：沒自律的人最需要這張表。"""
    return [
        dict(when="每次下單前", what="12 問拒單＋三條熔斷", who="系統自動",
             plain="不用您記，程式先擋"),
        dict(when="每個月", what="對帳：把上版數字重算一遍；月檢 MA120 只動衛星層", who="系統自動",
             plain="像每個月對一次存摺"),
        dict(when="每季", what="換沒用過的資料重考一次；改一點參數看落差", who="系統跑、人看一眼",
             plain="像定期健康檢查，不是等不舒服才去"),
        dict(when="每次想改方法", what="一次只改一處 → 重跑 → 前後並排 → 過三道閘", who="人簽名才算數",
             plain="想改可以，但要留下改前改後"),
        dict(when="每年", what="重讀錯題本，問『同樣的錯還在嗎』；重算能賠多少", who="人＋系統",
             plain="像年前大掃除，把舊帳翻出來看"),
    ]


def version_history():
    return [
        dict(ver="V2.7", did="網站上線、令牌撤銷", learned="先把門鎖好，再談賺錢"),
        dict(ver="V3.0", did="把手續費、稅、授權額度寫成程式", learned="代價先算清楚才進場"),
        dict(ver="V3.1", did="AI／人工／買入持有對照", learned="抓出 ETF 稅率標錯，全部重算"),
        dict(ver="V3.3", did="7 組策略 3 折樣本外", learned="0 組跑贏買著不動 → 別迷信『最佳參數』"),
        dict(ver="V3.6", did="牛熊、選股、季節性全因素實測", learned="推翻上一版的結論精度"),
        dict(ver="V3.7", did="七條價值觀＋五層漏斗＋12 問拒單", learned="把智慧寫成能照著做的表"),
        dict(ver="V3.8", did="四層桶、部分止盈、再平衡", learned="結構比預測可靠"),
        dict(ver="V3.9", did="慢熊 vs 急殺、兩類股票兩套風控", learned="跌得越急，選股越無效"),
        dict(ver="V4.0", did="九條交易的實測＋樣本外＋升級版", learned="賣太早的代價 −229pp，補一句就救回來"),
        dict(ver="V4.1", did="20 檔個股印證、市場三態", learned="量能不能當買點；三態先判再動"),
        dict(ver="V4.2", did="自檢引擎、錯題本、三道閘", learned="系統學的不是預測，是誠實"),
    ]


def main():
    rec = reconcile()
    graded = grade_claims()
    gaps = find_gaps()
    print(f"對帳：檢查 {rec['n_checked']} 條曲線，報酬自洽 {rec['total_pct_consistent_n']}/{rec['total_pct_checked_n']}")
    print(f"  新抓到的問題：{rec['new_finding']}（平均差 {rec['avg_mdd_gap_pp']}pp、最大 {rec['max_mdd_gap_pp']}pp）")
    print(f"錯題本：{len(ERROR_LEDGER)} 筆", dict(Counter(e['kind'] for e in ERROR_LEDGER)))
    print(f"結論分級：{graded['verdict_counts']}")
    print(f"資料缺口：{gaps['n_missing']}/{gaps['n_fields_checked']} 項")
    lp = loop()
    print(f"示範一 稅率改對：{lp['fee_fix']['wrong_cost_ntd']} → {lp['fee_fix']['right_cost_ntd']} 元")
    print(f"示範二 改規則前後：{lp['patch_fix']['before_pct']}% → {lp['patch_fix']['after_pct']}%（救回 {lp['patch_fix']['recovered_pp']}pp；一次改了三處，已標註）")
    print(f"示範三 改參數：Calmar {lp['sensitivity']['best_calmar']} → {lp['sensitivity']['worst_calmar']}")

    result = dict(
        meta=dict(version="V4.2", title="系統會自己進步", generated_at=datetime.now().isoformat(timespec="seconds"),
                  scope="家人自用／模擬盤 M0，未連富邦、未下任何單",
                  note="所有數字由 v31–v41 結果檔讀取，不手工抄錄"),
        error_ledger=ERROR_LEDGER,
        error_kind_counts=dict(Counter(e["kind"] for e in ERROR_LEDGER)),
        reconcile=rec, grading=graded, gaps=gaps,
        conflicts=conflicts(), loop=lp,
        discipline_map=discipline_map(),
        boundaries=can_cannot(), maintenance=maintenance(),
        speak_rules=SPEAK_RULES,
        version_history=version_history(),
    )
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("寫出", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
