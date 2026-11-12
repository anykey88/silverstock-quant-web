#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
case_6217_one_lot.py — V4.5「只有一張，除了認賠賣出還有什麼辦法」試算（6217 中探針）

情境（泰哥 2026/11/08 提問）：買在 52 週最高 371 元，只有一張，現在 109 元、
大盤空頭。除了認賠賣出，還有沒有別的辦法「降低損失」？

紀律（延續 V4.2 自檢、V4.3 個案、V4.4 決策）：
  1. 所有錢的數字都真的呼叫 trade_plan_engine 的 buy_cost / sell_proceeds，
     不手抄、不另寫一套比較好看的費率。
  2. 決策真的呼叫 principles.pretrade_check() 跑一次 12 問。
  3. 這檔不在 111 檔回測池，任何「這樣做會賺多少」一律寫「不知道」。
  4. 不知道的事（佔總資產比例、是否融資、家裡一個月開銷、零股實際成交價、
     權證／借券資格）直接寫不知道，不編數字。
  5.  externally 查到的舊價格（2026/09–10 的 156.5 / 162.5 / 165）只拿來說明
     「網路上有人討論過借券」，不拿來算錢，不與 11/06 的 109 混用。

產出：v45_one_lot.json（報告與決策卡的數字全部由此檔回填）
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import trade_plan_engine as E
import principles as P

OUT = ROOT / "v45_one_lot.json"
PREV = json.loads((ROOT / "v44_top_decision.json").read_text(encoding="utf-8"))
V40 = json.loads((ROOT / "v40_execution_result.json").read_text(encoding="utf-8"))
V43 = json.loads((ROOT / "v43_case_6217.json").read_text(encoding="utf-8"))

CFG = E.FeeConfig.for_symbol("6217")   # 個股：賣出證交稅 3‰（ETF 才 1‰）
QTY = 1000                              # 一張 = 1000 股
BUY = 371.00                            # 52 週最高（Yahoo 11/06）
NOW = 109.00                            # 2026/11/06 收盤
SINGLE_CAP_PCT = 1                     # V4.3 炒作股鐵律：單檔上限 1%
CASH_MONTHS = 24                       # V3.8：現金先補 24 個月生活費


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


EPS_Y = find_item(V43, "2025 全年 EPS")["plain"]
EPS_H1 = find_item(V43, "2026 上半年累計 EPS")["plain"]
EPS_TTM = find_item(V43, "近四季 EPS（TTM）")["plain"]
DIV = find_item(V43, "2025 年現金股利")["value"]


def build() -> dict:
    # ── 一、這一張的錢，全部由引擎算 ──────────────────────────────
    b = E.buy_cost(BUY, QTY, CFG)
    s = E.sell_proceeds(NOW, QTY, CFG)
    loss = b.total - s.total
    loss_wan = f"{loss / 10000:.0f} 萬"     # 長輩版用約數，但仍由程式算
    recover_price = PREV["money"]["recover_price"]
    recover_pct = PREV["money"]["recover_pct_from_now"]

    truth = {
        "buy_price": BUY,
        "now_price": NOW,
        "loss_wan": loss_wan,
        "buy_paid": b.total,
        "buy_fee": b.fee,
        "now_value_before_fee": s.amount,
        "sell_received": s.total,
        "sell_fee": s.fee,
        "sell_tax": s.tax,
        "loss": loss,
        "loss_pct_on_cash": PREV["money"]["loss_pct_on_cash"],
        "recover_price": recover_price,
        "recover_pct_from_now": recover_pct,
        "plain": "房子跌價了，不管您賣不賣，它就是跌了。賣掉只是把「帳面上變少」"
                 "換成「存摺裡確定變少」，不會多賠、也不會少賠。",
        "already": f"當初付 {b.total:,.0f} 元，現在這張值 {s.amount:,.0f} 元，"
                   f"真正賣到手 {s.total:,.0f} 元。中間不見的 {loss:,.0f} 元，"
                   "是【已經發生】的事，不是「賣掉才賠」。",
        "sell_role": "認賠賣出只做一件事：把「明天還會不會再跌」這個風險，從您身上拿走。"
                     f"它不會把 {loss_wan}變回來，也不會讓您多賠。所以「除了認賠賣出」"
                     "真正要問的是：有沒有別的方法，也能把這個風險拿走？"
                     "答案是有幾種，但都不是靠把股價變回來。",
    }

    # ── 二、只有一張＝最壞情況已經封頂 ─────────────────────────────
    cap = {
        "worst_more": s.total,
        "worst_more_if_average": None,   # 下面攤平算完再填
        "plain": "只剩一張，最壞就是這張歸零，最多再賠 "
                 f"{s.total:,.0f} 元，不會變成無底洞。這反而是這次唯一做對的事："
                 "買錯了，但沒有把錯放大。",
    }

    # ── 三、最常被想到的「攤平」：真的算一次 ──────────────────────
    b2 = E.buy_cost(NOW, QTY, CFG)                 # 再買一張 @109
    total_paid = b.total + b2.total
    avg_cost = total_paid / (QTY * 2)
    s2 = E.sell_proceeds(NOW, QTY * 2, CFG)       # 攤平後立刻全部賣掉
    loss2 = total_paid - s2.total
    extra_now = loss2 - loss

    drop_px = E.round_to_tick(NOW * 0.90)         # 只是「假如」再跌一成，不是預測
    s_drop_1 = E.sell_proceeds(drop_px, QTY, CFG)
    s_drop_2 = E.sell_proceeds(drop_px, QTY * 2, CFG)
    more_1 = s.total - s_drop_1.total
    more_2 = s2.total - s_drop_2.total

    avg_down = {
        "second_paid": b2.total,
        "total_paid": total_paid,
        "avg_cost": r(avg_cost),
        "sell_all_received": s2.total,
        "loss_if_average": loss2,
        "extra_loss_now": extra_now,
        "drop_price": drop_px,
        "more_loss_1lot": more_1,
        "more_loss_2lots": more_2,
        "per_1dollar_1lot": QTY * 1,
        "per_1dollar_2lots": QTY * 2 * 1,
        "plain": f"再買一張，平均成本從 {BUY:,.0f} 元降到 {avg_cost:,.0f} 元，"
                 "看起來好看；但口袋裡多押了 "
                 f"{b2.total:,.0f} 元進去。股價每跌 1 元，"
                 f"不攤平賠 {QTY:,.0f} 元，攤平後賠 {QTY * 2:,.0f} 元。",
    }
    cap["worst_more_if_average"] = s2.total

    # ── 四、只有一張才做得到的：拆零股、分幾天慢慢退 ──────────────
    once = s.total
    each100 = E.sell_proceeds(NOW, 100, CFG)
    ten_days = each100.total * 10
    one_share = E.sell_proceeds(NOW, 1, CFG)
    min_amount = CFG.min_fee_odd / (CFG.fee_rate * CFG.fee_discount)
    min_shares = math.ceil(min_amount / NOW)
    normal_cost_pct = (s.fee + s.tax) / s.amount * 100
    one_cost_pct = (one_share.fee + one_share.tax) / one_share.amount * 100

    split_odd = {
        "once_received": once,
        "each_100_received": each100.total,
        "ten_days_received": ten_days,
        "diff": once - ten_days,
        "min_amount": r(min_amount),
        "min_shares": min_shares,
        "one_share_received": one_share.total,
        "one_share_fee": one_share.fee,
        "one_share_tax": one_share.tax,
        "one_share_cost_pct": r(one_cost_pct),
        "normal_cost_pct": r(normal_cost_pct),
        "days_if_one_share": QTY,
        "plain": "一張可以拆成零股賣，不必一次砍光。分十天、每天 100 股，"
                 f"合計實收 {ten_days:,.0f} 元，跟一次賣掉的 {once:,.0f} 元"
                 f"只差 {once - ten_days:,.0f} 元——手續費幾乎沒變貴。",
        "warn": f"但不要分太細：每天只賣 1 股，券商手續費最低收 "
                f"{CFG.min_fee_odd} 元，加上稅進位，成本率會從 "
                f"{normal_cost_pct:.2f}% 變成 {one_cost_pct:.2f}%；"
                f"要賣 {QTY:,} 次才賣得完。每次至少賣 {min_shares} 股（成交金額約 "
                f"{min_amount:,.2f} 元）才不吃這個低收。",
        "honest": "要誠實：分批退不會讓您多拿回錢，它換到的是「不必賭今天是不是最低點」。"
                  "而且零股實際成交價可能跟整張差一點、盤後零股一天只配一次也不一定成交，"
                  "這部分我們沒有資料，不知道。下跌段分批減碼也沒有對應實測，只給做法、不給報酬數字。",
    }

    # ── 五、佔比分支：這一題最關鍵的「不必認賠」合法出路 ──────────
    branch = {
        "cap_pct": SINGLE_CAP_PCT,
        "small": {
            "title": "如果這一張不到您全部資產的 1%",
            "do": "留著、絕不加碼、每個月底看一次三件事就好。"
                  "這不是硬拗，是 V4.3 原本就寫好的規則。",
            "plain": "就像家裡留了一個小抽屜放舊東西，不佔地方，不必今天清掉。",
        },
        "large": {
            "title": "如果這一張超過 1%",
            "do": f"按日降一點，降到只佔 {SINGLE_CAP_PCT}% 以內就停；"
                  "退出來的錢先補滿 24 個月生活費，再看會配息的地方。",
            "plain": "不是認賠，是把會讓您睡不著的那一部分，慢慢搬回安全的地方。",
        },
        "next_hint": "接下來幾節是給「確定要降」的人看的；"
                     "如果答案是不到 1%，看完後面「靠日曆」那一節就可以收起來了。",
        "unknown": "您還沒告訴我全部資產多少，所以我不知道這一張是 1% 還是 10%。"
                   "不知道就不硬湊張數，先回答這個問題再決定要不要賣。",
    }

    # ── 六、其餘辦法逐條判定（有數字的用既有實測／法條，其餘寫不知道）──
    dt = V40["daytrade"]
    options = [
        {
            "group": "真的有用",
            "name": "先問「這一張佔家裡多少錢」",
            "verdict": "可以做",
            "plain": f"先看這張佔家裡多少錢，再決定要不要賣。{branch['small']['do']}"
                     f"若是超過 {SINGLE_CAP_PCT}%，才照日曆慢慢降。",
            "number": f"上限 {SINGLE_CAP_PCT}%；不知道佔比就先不要動",
        },
        {
            "group": "真的有用",
            "name": "要退，就拆零股分幾天退",
            "verdict": "可以做",
            "plain": split_odd["plain"],
            "number": f"一次賣 {once:,.0f} 元；分十天 {ten_days:,.0f} 元；差 {once - ten_days:,.0f} 元",
        },
        {
            "group": "真的有用",
            "name": "把這次寫進規矩，交給系統",
            "verdict": "可以做",
            "plain": f"唯一能把這 {loss_wan}「換回價值」的地方，不是這張股票，"
                     "是讓下次不要再用同一種方式賠一次。三條寫死：買進當下就掛停損、"
                     "單檔最多 1%、看到「跌很多想買」自動擋下來。",
            "number": f"同樣的錯若買十張，是 {PREV['money']['loss_10lots_now']:,.0f} 元",
        },
        {
            "group": "看起來有用，其實沒有",
            "name": "再買一張攤平，把成本降下來",
            "verdict": "不要做",
            "plain": f"平均成本好看，但口袋裡多押了 {b2.total:,.0f} 元；"
                     f"股價每跌 1 元，從賠 {QTY:,.0f} 元變成賠 {QTY * 2:,.0f} 元。"
                     "完整數字在「攤平算給你看」那一節，這裡只給結論：不要做。",
            "number": f"平均成本 {avg_cost:,.0f} 元，但總投入變 {total_paid:,.0f} 元",
        },
        {
            "group": "看起來有用，其實沒有",
            "name": "放著等回本",
            "verdict": "不要當辦法",
            "plain": f"要漲到 {recover_price:,.1f} 元才回到當初付出去的錢，等於從 "
                     f"{NOW:,.0f} 再漲 {recover_pct:.2f}%。{EPS_Y}、{EPS_H1}、"
                     f"{EPS_TTM}；現金股利 {DIV}，沒有東西幫您墊著。"
                     "要等多久、會不會回來，不知道。",
            "number": f"回本要再漲 {recover_pct:.2f}%",
        },
        {
            "group": "看起來有用，其實沒有",
            "name": "當天買賣來回賺差價（當沖）",
            "verdict": "不要做",
            "plain": "來回一次成本 0.435%，每天做一次、一年會把錢磨掉將近三分之二。"
                     "而且它的來回不會改掉您手上這一張的成本，只是另外再賭一次；"
                     "我們的資料也沒有當天開高低價，任何「勝率」都是編的。",
            "number": f"來回成本 {dt['cost_stock_pct']}%；一年侵蝕 {dt['annual_erosion_stock_pct']}%",
        },
        {
            "group": "看起來有用，其實沒有",
            "name": "認賠賣掉，拿去抵所得稅",
            "verdict": "不成立",
            "plain": "台灣上市櫃股票的證券交易所得目前停徵所得稅，"
                     "反過來，交易損失也【不能】拿去抵一般所得。別把這條當成降低損失的方法。"
                     "法規細節請跟會計師或券商確認。",
            "number": "所得稅法第 4 條之 1",
        },
        {
            "group": "看起來有用，其實沒有",
            "name": "留著領股息、或等股東會紀念品",
            "verdict": "不成立",
            "plain": f"現金股利 {DIV}，本來就沒有息可領。"
                     f"紀念品是一包米或一個杯子，領了很開心，但不會把 {loss_wan}補回來——"
                     "就像房子跌價了，管理員送您一袋米，房價還是跌了。",
            "number": f"現金股利 {DIV}",
        },
        {
            "group": "看起來有用，其實沒有",
            "name": "把股票借出去領利息",
            "verdict": "不是辦法",
            "plain": "網路上確實有人討論這檔借券領利息，但那是論壇貼文、沒有官方利率，"
                     "而且一張能不能借、能領多少、稅怎麼算，我都不知道。"
                     "更關鍵的是：股票借出去還是您的，股價跌照樣賠，風險一點沒少。",
            "number": "不知道（資料不夠，不編利率）",
        },
        {
            "group": "看起來有用，其實沒有",
            "name": "放空、買認售權證或用選擇權對沖",
            "verdict": "不知道，也不准",
            "plain": "這檔不在我們的資料池，沒有借券成本、沒有權證清單、也沒有個股選擇權資料，"
                     "所以「划不划算」算不出來，一律寫不知道。而且這是【開一個新賭局】："
                     "要另開信用帳戶、要付權利金、會到期歸零，只有一張的規模完全不划算。",
            "number": "不知道（資料不夠，依規矩不准放行）",
        },
        {
            "group": "看起來有用，其實沒有",
            "name": "現在才補掛停損單",
            "verdict": "已經來不及",
            "plain": "原本那條「−15% 無條件砍」要在【買進當下】就交給券商託管。"
                     f"現在股價 {NOW:,.0f} 元，事後補掛 "
                     f"{PREV['money']['stop_price']:.1f} 元永遠不會觸發，等於沒掛。"
                     "保險要在出事之前買，出事之後才買，保險公司不賠。",
            "number": f"當初該在 {PREV['money']['stop_price']:.1f} 元出場",
        },
        {
            "group": "最急的一件事",
            "name": "如果是融資買的，先打電話問維持率",
            "verdict": "先辦",
            "plain": "借錢買的話，券商追繳比股價更急：會被強迫賣在您不能選的日子。"
                     "這題您還沒回答，所以我不敢往下算。先問營業員「這筆是不是融資、維持率多少」。",
            "number": "不知道（要問券商）",
        },
    ]

    # ── 七、真的再跑一次 12 問，問的是「現在攤平準不準」 ──────────
    answers = {f"Q{i}": None for i in range(1, 13)}
    answers["Q9"] = False    # 公司最近四季合起來賠錢
    answers["Q11"] = False   # 是因為「跌很多」才想買
    chk = P.pretrade_check(answers, regime_state="BEAR", position_pct=0.0)
    pretrade = {
        "purpose": "真的跑一次 12 問，問的是「現在再買一張攤平，準不準」。",
        "ok": chk["ok"],
        "issue_n": len(chk["issues"]),
        "issues": chk["issues"],
        "plain": f"12 問全數過不了（不過 {len(chk['issues'])} 題）→ 今天不准下任何「買」的單。",
    }

    # ── 八、錯題本與行事曆 ────────────────────────────────────────
    wrongbook = [
        {
            "rule": "停損要【買進當下】就掛，不能事後補",
            "evidence": f"371 買、−15% 該在 {PREV['money']['stop_price']:.1f} 元出場；"
                        f"現在 {NOW:,.0f} 元，每張少拿 {PREV['money']['saved_per_lot_if_stopped']:,.0f} 元。",
        },
        {
            "rule": "單檔最多 1%，買錯也不准加碼",
            "evidence": f"只有一張，最壞再賠 {s.total:,.0f} 元就到底；"
                        f"攤平一張，最壞變成再賠 {s2.total:,.0f} 元。",
        },
        {
            "rule": "看到「比之前便宜很多」自動擋下來",
            "evidence": f"12 問第 11 題專門擋這件事；要回到當初實付得再漲 {recover_pct:.2f}%。",
        },
    ]
    actions = [
        {"when": "今天（11/08 週日，休市）",
         "do": "不下任何單。先回答底下三個問題；若是融資買的，先打電話問券商維持率。"},
        {"when": "回答完之後",
         "do": "佔比不到 1% → 留著觀察就好，不必急著認賠；超過 1% → 才照日曆一天降一點，降到 1% 以內就停。"},
        {"when": "真的要退的那幾天",
         "do": f"可拆零股，每次至少 {min_shares} 股，別一天只賣 1 股；退出來的錢先補滿 {CASH_MONTHS} 個月生活費。"},
        {"when": "每個月底只看一次",
         "do": "站不站得回半年平均價、公司連續兩季有沒有開始賺錢、股息是不是不再掛零。三樣都成立，也只是放回觀察名單。"},
        {"when": "每一筆都記一筆",
         "do": "當初是照哪一條買的？那條現在還成立嗎？這是給系統的錯題本，不是責備自己。"},
    ]

    return {
        "version": "V4.5",
        "case": "6217 中探針・只有一張・買在最高點 371 元",
        "question": "除了認賠賣出，還有什麼辦法降低損失？",
        "asof": PREV["asof"],
        "next_trading_day": PREV["next_trading_day"],
        "one_line": f"已經賠的 {loss_wan}沒有辦法變回來；能做的只有三件事：別讓它變大、別為它再賠一次、讓這次的教訓換回下次少賠。",
        "truth": truth,
        "cap": cap,
        "branch": branch,
        "average_down": avg_down,
        "split_odd": split_odd,
        "options": options,
        "pretrade": pretrade,
        "wrongbook": wrongbook,
        "actions": actions,
        "opportunity": {
            "formula": f"{s.total:,.0f} 元 ÷ 家裡一個月開銷 ＝ 幾個月的生活費",
            "plain": "錢卡在這裡，就沒有放在別的地方。這筆錢等於家裡幾個月的開銷，"
                     "我不知道您家一個月花多少，請自己除一下，比看股價更實在。",
        },
        "unknown": [
            "這一張佔您全部資產百分之幾（不知道 → 不知道該不該賣）",
            "是不是融資買的、維持率多少（不知道 → 追繳風險算不出來）",
            "實際成交價是不是 371 元（不是 → 上面每個金額都要重算）",
            "家裡一個月開銷多少（不知道 → 機會成本只能給公式）",
            "零股實際成交價與整張差多少、盤後零股能不能成交（資料不夠）",
            "這檔有沒有權證／個股選擇權、借券利率與一張能否出借（資料不夠）",
            "含息五年報酬、最大回撤、年化波動、正式評分（不在 111 檔池，一律不編）",
            "下週會漲還是會跌（不知道，也不該拿來當決策依據）",
        ],
        "sources": [
            "既有 v44_top_decision.json（V4.4 決策試算：一張的實付、實收、回本價、停損價）",
            "既有 v40_execution_result.json（V4.0 實測：當沖來回成本 0.435%、一年侵蝕 66.7%）",
            "既有 v43_case_6217.json（V4.3：基本面數字由該檔回填；不在 111 檔回測池）",
            "trade_plan_engine.py（富邦營業員 2026/11/05 回覆費率：買賣 1.425‰、個股賣出稅 3‰、零股低收 1 元、整股 20 元）",
            "所得稅法第 4 條之 1；總統府公報第 7044-2 號（101/08/08）；勤業眾信／中央社 2024/02/20；中時 2024/07/09（上市櫃證交所得停徵、損失不得自所得額減除）",
            "CMoney 股市爆料同學會、MoneyDJ（僅用來確認「網路上有人討論 6217 借券」；貼文裡的價格是 2026/09–10 舊價，不與 11/06 收盤價混用，也不拿來算錢）",
        ],
        "auto": PREV["auto"],
        "disclaimer": "這是方法示範與風險控管，不是買賣建議；系統仍在 M0 模擬盤，沒有連線、沒有下單。",
    }


if __name__ == "__main__":
    d = build()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    t, a, sp = d["truth"], d["average_down"], d["split_odd"]
    print(f"產出 {OUT.name}（{OUT.stat().st_size:,} bytes）")
    print(f"一張：付 {t['buy_paid']:,.0f} → 實收 {t['sell_received']:,.0f}，賠 {t['loss']:,.0f}")
    print(f"攤平：平均成本 {a['avg_cost']:,.0f}，總投入 {a['total_paid']:,.0f}，"
          f"現在多賠 {a['extra_loss_now']:,.0f}，再跌一成多賠 {a['more_loss_2lots']:,.0f}")
    print(f"零股：一次 {sp['once_received']:,.0f}，分十天 {sp['ten_days_received']:,.0f}，"
          f"差 {sp['diff']:,.0f}；每次至少 {sp['min_shares']} 股")
    print(f"12 問：不過 {d['pretrade']['issue_n']} 題，ok={d['pretrade']['ok']}")
