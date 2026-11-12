#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
case_6217_largest.py — V4.6「中探針是我最大的資產」試算（6217 中探針）

情境（泰哥 2026/11/08 補上一句）：前面問「只有一張，除了認賠還有什麼辦法」，
現在補上關鍵事實——【這檔是家裡最大的一筆資產】。

這一版只處理「新事實改變了什麼」，不重算 V4.5 那 12 條辦法（結論沒變）。

紀律（延續 V4.2 自檢、V4.3 個案、V4.4 / V4.5 決策）：
  1. 一張的錢真的呼叫 trade_plan_engine 的 buy_cost / sell_proceeds。
  2. 所有引用的實測數字（炒作組、急殺、分散、四層桶、市場結構）
     一律由既有結果檔讀出，不手抄、不憑印象。
  3. 不知道的事（總資產、佔比、一個月開銷、是否融資、其他資產是什麼）
     直接寫「不知道」，不編總資產、不編該賣幾股。
  4. 12 問是【買進閘門】，不是【持有閘門】；這一版明說用途，不拿來判「要不要賣」。
  5. 上一版「最壞已封頂，算是做對一件事」的安慰，因新事實要收回一半，記進錯題本。
  6. 全文手寫繁體，不做簡繁自動轉換；負數一律改寫成白話的「跌／少／賠」。

產出：v46_largest_asset.json（報告與決策卡的數字全部由此檔回填）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import trade_plan_engine as E
import principles as P

OUT = ROOT / "v46_largest_asset.json"
V45 = json.loads((ROOT / "v45_one_lot.json").read_text(encoding="utf-8"))
V44 = json.loads((ROOT / "v44_top_decision.json").read_text(encoding="utf-8"))
V43 = json.loads((ROOT / "v43_case_6217.json").read_text(encoding="utf-8"))
V38 = json.loads((ROOT / "v38_allocation_result.json").read_text(encoding="utf-8"))
V39 = json.loads((ROOT / "v39_bear_result.json").read_text(encoding="utf-8"))
V41 = json.loads((ROOT / "v41_structure_result.json").read_text(encoding="utf-8"))

CFG = E.FeeConfig.for_symbol("6217")   # 個股：賣出證交稅 3‰（ETF 才 1‰）
QTY = 1000                              # 一張 = 1000 股
BUY = 371.00                            # 52 週最高（Yahoo 11/06）
NOW = 109.00                            # 2026/11/06 收盤
CAP_PCT = 1.0                           # V4.3 炒作股鐵律：單檔上限 1%
CASH_MONTHS = 24                        # V3.8：現金先補 24 個月生活費
EXAMPLE_TOTALS = (300_000, 500_000, 1_000_000)     # 都假設它是家裡最重的一格，不是使用者的資產


def r(x, n=2):
    return round(x, n)


def find_item(obj, name):
    """從 V4.3 結果檔找回同一筆基本面數字，不手抄。"""
    if isinstance(obj, dict):
        if obj.get("item") == name:
            return obj
        for v in obj.values():
            got = find_item(v, name)
            if got:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = find_item(v, name)
            if got:
                return got
    return None


def down(x, n=2):
    """長輩版：負數一律改成白話「跌 X%」，不出現負號。"""
    return f"{abs(x):.{n}f}%"


def build() -> dict:
    # ── 一、這一張的錢，全部由引擎算 ──────────────────────────────
    b = E.buy_cost(BUY, QTY, CFG)
    s = E.sell_proceeds(NOW, QTY, CFG)
    loss = b.total - s.total
    loss_wan = f"{loss / 10000:.0f} 萬"

    div = find_item(V43, "2025 年現金股利")["value"]
    eps_ttm = find_item(V43, "近四季 EPS（TTM）")["plain"]

    # ── 二、既有實測數字，一律讀檔 ────────────────────────────────
    hype = V43["hype"]["hype_ref"]                       # n / total_pct / mdd_pct
    crash = min((p for p in V39["period_stats"] if p["direction"] == "空頭"),
                key=lambda p: p["index_ret_pct"])        # 30 天急殺那一段
    corr = V38["correlation"]                            # 等效檔數、波動降低
    cfg_by_key = {c["key"]: c for c in V38["configs"]}
    four = next(c for k, c in cfg_by_key.items() if "四" in k and "桶" in k)
    all_in = next(c for k, c in cfg_by_key.items() if "100%" in k and "持有" in k)
    struct_states = {st["state"]: st["pct"] for st in V41["structure"]["states"]}
    idio_pct = struct_states["個股主導"]     # 這是「天數占比」，不是漲跌歸因占比
    n_days = V41["structure"]["n_days"]

    # ── 三、新事實改變了什麼 ──────────────────────────────────────
    what_changed = [
        {
            "before": f"上一版說：這張不到全部資產 {CAP_PCT:.0f}% 的話，本來就不用急著賣。",
            "after": "這條退路現在用不上了。",
            "why": "您說它是【最大的一筆】，那就幾乎可以確定遠遠超過 1% 那格；"
                   "精確幾 % 我還是不知道，但方向已經確定。",
        },
        {
            "before": "上一版說：不知道佔比，所以只給方向、不給張數。",
            "after": "方向確定：把這檔降到只佔 1% 以內就停。",
            "why": "不是今天新改的規矩，是 V4.3 就寫好的；今天只是確認它該被執行。",
        },
        {
            "before": f"上一版說：只有一張、最壞再賠 {s.total:,.0f} 元就到底，算是做對一件事。",
            "after": "這句安慰要收回一半。",
            "why": f"數學上確實封頂了，但封頂的那一筆，正好是家裡最重的一袋米。"
                   f"不是無底洞，可是再掉下去會很痛：最壞還會再不見 {s.total:,.0f} 元。",
        },
        {
            "before": "上一版把 12 條辦法逐一算過一遍。",
            "after": "結論沒變，這一版不重算。",
            "why": "攤平、等回本、當沖、抵稅、領息、借券、放空、補掛停損，"
                   "答案都還是「不成立」或「不知道」。重複貼一次只是灌水。",
        },
    ]

    # ── 四、最容易記錯的地方：最大，是當初的記法 ──────────────────
    shrink = (NOW / BUY - 1) * 100
    size_trap = {
        "then_value": BUY * QTY,
        "now_value": NOW * QTY,
        "buy_paid": b.total,
        "sell_received": s.total,
        "shrink_pct": r(shrink),
        "shrink_down": down(shrink),
        "plain": f"買進當時，這一張在帳面上值 {BUY * QTY:,.0f} 元，確實是家裡最重的一格；"
                 f"現在只剩 {NOW * QTY:,.0f} 元，真正賣到手 {s.total:,.0f} 元，"
                 f"等於自己縮掉了 {down(shrink)}。人很容易用【買進當時的份量】記著它，"
                 "所以會覺得「我最大的資產還在」——其實錢早就不見了。",
        "analogy": "就像一袋米當初買來是滿的，現在只剩袋底一點；"
                   "我們還記得它當初扛起來有多重，不能拿那個重量當今天的重量。",
    }

    # ── 五、兩個袋子：該追的是哪一個 ──────────────────────────────
    two_piles = {
        "gone": loss,
        "left": s.total,
        "gone_wan": loss_wan,
        "plain": f"現在要看的是兩個袋子：一個是已經不見的 {loss:,.0f} 元（追不回來），"
                 f"另一個是還留在裡面的 {s.total:,.0f} 元（還守得住）。"
                 f"「最大資產」這句話真正提醒我們的，是【後面這袋】不能再跟著縮下去，"
                 "不是叫人去把前面那袋變回來。",
        "analogy": "米缸破了，別蹲在地上撿已經灑出去的米；先把缸裡剩下的倒到乾的桶子裡。",
    }

    # ── 六、為什麼「最大的一筆壓在這一格」特別危險 ────────────────
    concentration = {
        "refs": [
            {"lab": "這類暴漲暴跌的股票，整段走完", "val": f"倒賠 {down(hype['total_pct'])}",
             "note": f"我們資料池裡同一組 {hype['n']} 檔，四年多下來的結果"},
            {"lab": "同一組，途中最多", "val": f"跌 {down(hype['mdd_pct'])}",
             "note": "差不多快腰斬"},
            {"lab": f"急殺那 {crash['bars']} 天，大盤", "val": f"跌 {down(crash['index_ret_pct'])}",
             "note": "整個市場一起被砍"},
            {"lab": "同一段，這類股票", "val": f"跌 {down(crash['HYPE'])}",
             "note": f"同時間會配息、比較穩的那組只跌 {down(crash['DEF'])}"},
            {"lab": f"把錢分到 {corr['n_assets']} 檔之後，整體晃動", "val": f"少了 {down(corr['vol_reduction_pct'])}",
             "note": f"看起來很多檔，其實只等於 {corr['effective_n']} 檔各自獨立"},
            {"lab": "四層桶（現金／高息／指數／衛星分開放）最多", "val": f"跌 {down(four['mdd_pct'])}",
             "note": "現金那一層在空頭裡是唯一確定有效的"},
            {"lab": "全部押在同一檔指數，最多", "val": f"跌 {down(all_in['mdd_pct'])}",
             "note": "還不是這檔個股，是相對穩的指數"},
        ],
        "idio_pct": idio_pct,
        "plain": "這次真正的錯，不是「選錯股票」，是【家裡最大的一筆錢放在同一格】——"
                 f"這是「錢要怎麼分開放」的問題，不是選股的問題。前面實測也說過：過去 {n_days:,} 天裡，"
                 f"有 {idio_pct:.1f}% 的日子是個股自己各走各的、不是整盤一起動，"
                 "本來就該靠分開放來扛，而不是靠猜哪一支會漲。",
        "analogy": "把所有家當放進同一間房，偏偏那間又是最會漏水的；"
                   "問題不在「這間房的東西好不好」，在「為什麼全部都放這間」。",
    }

    # ── 七、1% 那格有多小：給一把可以自己套用的尺 ────────────────
    examples = []
    for total in EXAMPLE_TOTALS:
        now_pct = s.total / total * 100
        target = total * CAP_PCT / 100
        move = max(0.0, s.total - target)
        examples.append({
            "total": total,
            "now_pct": r(now_pct),
            "target": target,
            "move": move,
            "move_pct_of_lot": r(move / s.total * 100, 1),
        })
    ruler = {
        "cap_pct": CAP_PCT,
        "applies_to": "這類會暴漲又暴跌的炒作股",
        "examples": examples,
        "formula": f"{CAP_PCT:.0f}% 的上限 ＝ 全部資產 × 0.01；要搬走的 ＝ "
                   f"{s.total:,.0f} 元 − 這個上限（若上限比這張還大，就不用搬）。",
        "caveat": "上面三行都假設它是家裡最重的一格，但只是【舉例換算】，不是您的資產，"
                  "也不是叫您明天搬走九成。列出來是讓您看見 1% 這格有多小，"
                  "所以才要分幾天、慢慢搬，不是一次砍光。",
        "honest": "我不知道您全部資產多少，就算不出「該留幾股、每次賣幾股」。"
                  "不知道就不硬湊；等您給一個大概數字，這張表立刻能算出真正的張數。",
        "not_all_stocks": f"補一句怕誤會：{CAP_PCT:.0f}% 是這類炒作股專用的規矩，"
                          f"不是每一支股票都只能放 {CAP_PCT:.0f}%。會配息、波動小的核心持股，規矩不一樣。",
    }

    # ── 八、最急的兩件事 ──────────────────────────────────────────
    urgent = [
        {
            "title": f"家裡 {CASH_MONTHS} 個月的生活費，現在還在不在？",
            "why": "既然這檔是最大的一筆，當初很可能就是把預備的錢押進去了。"
                   "先把生活費補回來，比股價明天漲跌重要得多。",
            "formula": f"{s.total:,.0f} 元 ÷ 家裡一個月開銷 ＝ 幾個月的米",
            "plain": "我不知道您家一個月花多少，請自己除一下；"
                     "這個數字比看盤還實在，因為它決定「能不能等」。",
        },
        {
            "title": "這筆是不是融資買的？維持率多少？",
            "why": "借錢買的話，券商追繳比股價更急，會被強迫賣在您不能選的日子。",
            "plain": "打一通電話給營業員就問得到。這題沒回答，我不敢往下算。",
        },
    ]

    # ── 九、真的再跑一次 12 問，但明說它是買進閘門 ────────────────
    answers = {f"Q{i}": None for i in range(1, 13)}
    answers["Q9"] = False     # 公司最近四季合起來賠錢
    answers["Q11"] = False    # 是因為「跌很多」才想買
    chk = P.pretrade_check(answers, regime_state="BEAR", position_pct=0.0)
    pretrade = {
        "purpose": "現在最危險的動作，是有人勸您「既然是最大資產，再補一點把成本降下來」。"
                   "所以真的再跑一次 12 問，問的是「現在再加錢，準不準」。",
        "ok": chk["ok"],
        "issue_n": len(chk["issues"]),
        "key_fails": [
            "第 9 題：公司最近一年合起來是賠錢的 → 不過",
            "第 11 題：是因為「跌很多」才想買 → 不過（這叫伸手接刀）",
            f"其餘 {len(chk['issues']) - 2} 題資料不夠或沒回答，依規矩一律算不過關",
        ],
        "plain": f"12 問全數過不了（不過 {len(chk['issues'])} 題）→ 今天不准下任何「買」的單。",
        "honest": "這道閘門只管【要不要再買】，不能拿來判【要不要賣】。"
                  "上一版已經跑過一次，這裡再跑，是因為新事實讓「再加錢」變得特別危險；"
                  "不是把買進規矩拿來冒充賣出建議。",
    }

    # ── 十、錯題本（系統自修）────────────────────────────────────
    wrongbook = [
        {
            "rule": "最大的一筆錢放在同一檔，是錢怎麼分的問題，不是選股的問題",
            "evidence": f"分散到 {corr['n_assets']} 檔後晃動少 {down(corr['vol_reduction_pct'])}；"
                        f"這類炒作組全程倒賠 {down(hype['total_pct'])}、最多跌 {down(hype['mdd_pct'])}；"
                        f"四層桶最多跌 {down(four['mdd_pct'])}，全押一檔最多跌 {down(all_in['mdd_pct'])}。",
        },
        {
            "rule": "上一版的安慰要收回一半：封頂不等於不痛",
            "evidence": f"最壞確實只再賠 {s.total:,.0f} 元就到底，但它同時是家裡最重的一袋米；"
                        f"已不見的 {loss:,.0f} 元也是從「最大」那一格不見的。",
        },
        {
            "rule": "用買進當時的份量記一檔股票，會誤判今天的大小",
            "evidence": f"當初市值 {BUY * QTY:,.0f} 元 → 現在 {NOW * QTY:,.0f} 元，"
                        f"自己縮了 {down(shrink)}，但口裡還叫它「最大資產」。",
        },
        {
            "rule": "規則不能拿來套不同的問題",
            "evidence": "12 問是買進閘門；這一版明說用途，不拿它判「要不要賣」，"
                        "避免為了給答案而誤用規則。",
        },
        {
            "rule": "停損要【買進當下】就掛，不能事後補",
            "evidence": f"{BUY:,.0f} 買、當天就該掛 {V44['money']['stop_price']:.1f} 元的停損；"
                        f"現在 {NOW:,.0f} 元，每張少拿 {V44['money']['saved_per_lot_if_stopped']:,.0f} 元。",
        },
    ]

    # ── 十一、行事曆 ──────────────────────────────────────────────
    actions = [
        {"when": "今天（11/08 週日，休市）",
         "do": "不下任何單。拿一張紙寫三個數字：這張現在值多少、家裡全部資產大概多少、"
               "家裡一個月開銷多少。寫不出精確值也沒關係，先有個大概。"},
        {"when": "今天，順手打一通電話",
         "do": f"問營業員「這筆是不是融資、維持率多少」，順便確認實際成交價是不是 {BUY:,.0f} 元。"},
        {"when": "下一個交易日 11/09 起",
         "do": "照日曆、一天搬一點，搬到這檔不再是家裡最重的那一格、只佔 1% 以內就停；"
               "不管當天漲跌、不看新聞、不改方向。每次搬幾股，等上面三個數字有答案再算。"},
        {"when": "每次搬完當天",
         "do": f"錢先放回現金，補滿 {CASH_MONTHS} 個月生活費；滿了之後才放到會配息的地方。"
               f"不要馬上換別支股票。若拆零股，每次至少 {V45['split_odd']['min_shares']} 股，"
               "別一天只賣 1 股。"},
        {"when": "每個月底只看一次",
         "do": "看三件事：站不站得回半年平均價、公司連續兩季有沒有開始賺錢、股息是不是不再掛零。"
               "三樣都成立，也只是放回觀察名單，不是可以買。"},
        {"when": "每一筆都記一筆",
         "do": "當初是照哪一條買的？那條現在還成立嗎？這是給系統的錯題本，不是責備自己。"},
    ]

    # ── 十二、建議加的新閘門（還沒上線）───────────────────────────
    upgrade = {
        "title": "建議加一道新閘門，但還沒寫進系統",
        "rule": "買進當下先問：這一筆會不會變成家裡最大的一筆？會 → 直接擋下來。",
        "why": "這次的錯，靠「事後叫人別攤平」擋不住；要在按下買進之前就擋。"
               "這正是您說的「靠系統，不靠自律」。",
        "status": "先記在錯題本，等 M0 模擬盤驗證過才准進規則；現在【不算已上線】。",
    }

    unknown = [
        "全部資產大概多少、這檔精確佔幾 %（只知道「最大」，仍算不出該留幾股）",
        "其他資產是什麼（現金、房產、還是別的股票）→ 這決定搬出來的錢放哪裡",
        f"家裡一個月開銷多少（不知道 → {CASH_MONTHS} 個月生活費只能給公式）",
        "是不是融資買的、維持率多少（不知道 → 追繳風險算不出來）",
        f"實際成交價是不是 {BUY:,.0f} 元（不是 → 上面每個金額都要重算）",
        "這檔的含息五年報酬、最大回撤、正式評分（不在 111 檔池，一律不編）",
        "分批減碼在下跌段「會比一次賣少賠多少」——沒有對應實測，不知道",
        "下週會漲還是會跌——不知道，也不該拿來當決策依據",
    ]

    sources = [
        "泰哥 2026/11/08 補充：「中探針股票是我的最大資產」（本版唯一新事實）",
        "既有 v45_one_lot.json（V4.5：一張的 12 條辦法與零股門檻，結論未改）",
        "既有 v44_top_decision.json（V4.4：回本價、停損價、市場狀態）",
        "既有 v43_case_6217.json（V4.3：炒作組特徵、股息、單檔 1% 上限、不在回測池）",
        "既有 v38_allocation_result.json（V3.8：相關性、等效檔數、四層桶與全押的最大回撤）",
        "既有 v39_bear_result.json（V3.9：急殺 30 天各組跌幅、炒作組全程報酬與回撤）",
        "既有 v41_structure_result.json（V4.1：個股主導佔比）",
        "trade_plan_engine.py（富邦營業員 2026/11/05 回覆費率：買賣 1.425‰、個股賣出稅 3‰、"
        "零股低收 1 元、整股 20 元）",
    ]

    return {
        "version": "V4.6",
        "case": "6217 中探針・它是家裡最大的一筆資產",
        "question": "補上一句「它是我最大資產」之後，前面的結論要怎麼改？",
        "asof": "2026-11-08（資料最新至 2026/11/06 收盤；11/07、11/08 週末休市）",
        "next_trading_day": "2026-11-09（週一，以券商行事曆為準）",
        "one_line": "現在知道了最重要的一件事：家裡最大的一筆錢，放在最會跌的那一格。"
                    "接下來不是追回已經不見的錢，是先把還剩下的那一袋，慢慢搬回乾的地方。",
        "new_fact": "這檔是家裡最大的一筆資產（泰哥 2026/11/08 補充）",
        "cash_months": CASH_MONTHS,
        "truth": {
            "buy_price": BUY,
            "now_price": NOW,
            "buy_paid": b.total,
            "buy_fee": b.fee,
            "now_value_before_fee": s.amount,
            "sell_received": s.total,
            "sell_fee": s.fee,
            "sell_tax": s.tax,
            "loss": loss,
            "loss_wan": loss_wan,
            "loss_down": down(V44["money"]["loss_pct_on_cash"]),
            "recover_price": V44["money"]["recover_price"],
            "recover_pct": V44["money"]["recover_pct_from_now"],
            "dividend": div,
            "eps_ttm": eps_ttm,
        },
        "what_changed": what_changed,
        "size_trap": size_trap,
        "two_piles": two_piles,
        "concentration": concentration,
        "ruler": ruler,
        "urgent": urgent,
        "pretrade": pretrade,
        "wrongbook": wrongbook,
        "actions": actions,
        "upgrade": upgrade,
        "unknown": unknown,
        "sources": sources,
        "auto": V45["auto"],   # 沿用既有結果檔，不重抄 0.435% / 66.7% 等實測數字
        "disclaimer": "這是方法示範與風險控管，不是買賣建議；系統仍在 M0 模擬盤，沒有連線、沒有下單。",
    }


if __name__ == "__main__":
    d = build()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"產出 {OUT.name}（{OUT.stat().st_size:,} bytes）")
    print("一句話:", d["one_line"])
    print("改變:", len(d["what_changed"]), "項")
    print("實測引用:", len(d["concentration"]["refs"]), "筆；換算例子:", len(d["ruler"]["examples"]))
    print("12 問：不過", d["pretrade"]["issue_n"], "題，ok=", d["pretrade"]["ok"])
    print("錯題本:", len(d["wrongbook"]), "條；不知道:", len(d["unknown"]), "項")
