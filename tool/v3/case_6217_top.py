#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
case_6217_top.py — V4.4「買在最高點」決策試算（6217 中探針）

情境：買在 52 週最高 371 元，現在 2026/11/06 收盤 109 元、大盤空頭。
最重要的紀律（延續 V4.2 自檢、V4.3 個案）：
  1. 所有錢的數字都真的呼叫 trade_plan_engine 的 buy_cost / sell_proceeds /
     tick_size，不手抄、不自己另寫一套比較好看的費率。
  2. 決策真的呼叫 principles.pretrade_check() 跑一次 12 問。
  3. 這檔不在 111 檔回測池，任何「這樣做會賺多少」一律寫「不知道」。
  4. 不知道的事（買幾張、總資產多少、是否融資、佔比多少）直接寫不知道，
     只給「比例」與「做法」，不給假張數。

產出：v44_top_decision.json（報告與決策卡的數字全部由此檔回填）
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

OUT = ROOT / "v44_top_decision.json"

CFG = E.FeeConfig.for_symbol("6217")   # 個股：賣出證交稅 3‰（ETF 才 1‰）
QTY = 1000                              # 一張 = 1000 股
BUY = 371.00                            # 52 週最高（Yahoo 11/06）
NOW = 109.00                            # 2026/11/06 收盤（Yahoo、元大、鉅亨交叉）
DAY_LOW = 106.50                        # 11/06 當日最低（元大、Yahoo）
STOP_RATE = 0.15                        # 我們寫死的炒作股鐵律：−15% 無條件砍
BATCH_DAYS = 10                         # 分 10 個交易日、每天賣 1/10


def _r(x, n=2):
    return round(x, n)


def recover_price() -> float:
    """要賣在多少錢，實收才補得回當初 371 買進的實付（含買賣來回成本）。"""
    target = E.buy_cost(BUY, QTY, CFG).total
    p = NOW
    step = E.tick_size(p)
    while p < 2000:
        if E.sell_proceeds(p, QTY, CFG).total >= target:
            return _r(p, 2)
        p = round(p + step, 4)
        step = E.tick_size(p)
    raise RuntimeError("找不到回本價")


def build() -> dict:
    # ── 一、一張股票的錢，全部由引擎算 ───────────────────────────
    b = E.buy_cost(BUY, QTY, CFG)
    s = E.sell_proceeds(NOW, QTY, CFG)
    loss = b.total - s.total

    # 停損價：371 × 0.85 = 315.35，台股 100–500 元跳 0.5 元，保守往下取
    tick = E.tick_size(BUY)
    stop_px = math.floor(BUY * (1 - STOP_RATE) / tick) * tick
    stop_s = E.sell_proceeds(stop_px, QTY, CFG)

    rp = recover_price()
    rp_s = E.sell_proceeds(rp, QTY, CFG)

    # ── 二、一次賣 10 張 vs 分 10 天每天賣 1 張（只比成本，不比報酬）──
    once = E.sell_proceeds(NOW, QTY * 10, CFG)
    each = E.sell_proceeds(NOW, QTY, CFG)
    split = each.total * BATCH_DAYS
    split_diff = once.total - split

    # ── 三、剩下部位若跌破 11/06 低點就清掉，能拿回多少（客觀價，不預測）──
    line_s = E.sell_proceeds(DAY_LOW, QTY, CFG)

    # ── 四、真的跑一次 12 問：現在想「攤平／加碼」準不準 ──────────
    ans = {qid: None for qid, _ in P.PRETRADE_QUESTIONS}
    ans["Q9"] = False     # 公司近四季賠錢 → 明確否
    ans["Q11"] = False    # 因為「跌很多」才想買 → 明確否（伸手接刀）
    chk = P.pretrade_check(ans, "BEAR", 0.0)

    money = {
        "buy_price": BUY,
        "now_price": NOW,
        "qty_per_lot": QTY,
        "buy_paid": _r(b.total, 0),
        "buy_fee": b.fee,
        "sell_received": _r(s.total, 0),
        "sell_fee": s.fee,
        "sell_tax": s.tax,
        "loss_per_lot": _r(loss, 0),
        "loss_pct_on_cash": _r(-loss / b.total * 100, 2),
        "loss_pct_on_price": _r((NOW / BUY - 1) * 100, 2),
        "left_per_100w": _r(s.total / b.total * 100, 1),
        "left_of_100w_ntd": _r(1_000_000 * s.total / b.total, 0),
        "price_left_per_100w": _r(NOW / BUY * 100, 1),
        "recover_price": rp,
        "recover_pct_from_now": _r((rp / NOW - 1) * 100, 2),
        "recover_price_pct_from_buy": _r((rp / BUY - 1) * 100, 2),
        "recover_check_received": _r(rp_s.total, 0),
        "stop_price": _r(stop_px, 2),
        "stop_received": _r(stop_s.total, 0),
        "stop_loss_if_done": _r(b.total - stop_s.total, 0),
        "stop_loss_pct": _r(-(b.total - stop_s.total) / b.total * 100, 2),
        "saved_per_lot_if_stopped": _r(stop_s.total - s.total, 0),
        "saved_10lots_if_stopped": _r((stop_s.total - s.total) * 10, 0),
        "once_10lots_received": _r(once.total, 0),
        "split_10days_received": _r(split, 0),
        "split_cost_diff": _r(split_diff, 0),
        "split_each_day_received": _r(each.total, 0),
        "day_low": DAY_LOW,
        "day_low_received": _r(line_s.total, 0),
        "loss_10lots_now": _r(loss * 10, 0),
        "fee_note": "手續費買賣各 1.425‰、賣出證交稅 3‰（個股）、費用無條件進位到元；整股單筆低收 20 元。實際以券商交割單為準。",
    }

    m = money  # 以下所有結論文字的數字，一律由 money 回填，不手抄

    return {
        "version": "V4.4",
        "batch_days": BATCH_DAYS,
        "single_stock_cap_pct": 1,
        "cash_months": 24,
        "case": "6217 中探針・買在最高點 371 元",
        "asof": "2026-11-08（資料最新至 2026/11/06 收盤；11/07、11/08 週末休市）",
        "next_trading_day": "2026-11-09（週一，以券商行事曆為準）",
        "one_line": "買在最高點，現在不是問「要不要認賠」，是問「怎麼把剩下的錢，慢慢搬回安全的地方」。",
        "market": {
            "state": "空頭（一直在跌的日子）",
            "taiex_close": 39701.64,
            "taiex_drawdown_pct": -20.31,
            "position_cap_pct": int(P.REGIME_CAP["BEAR"] * 100),
            "cap_note": P.REGIME_NOTE["BEAR"],
            "last_day": {
                "date": "2026-11-06", "close": NOW, "change": -9.00, "change_pct": -7.63,
                "open": 106.50, "high": 110.50, "low": DAY_LOW, "volume_lots": 4151,
            },
            "four_days": [
                {"date": "11/02", "close": 148.00}, {"date": "11/04", "close": 131.00},
                {"date": "11/05", "close": 118.00}, {"date": "11/06", "close": 109.00},
            ],
            "four_day_drop_pct": -26.35,
            "ma": [
                {"name": "5 日平均價", "value": 127.9}, {"name": "20 日平均價", "value": 164.1},
                {"name": "60 日平均價", "value": 167.8}, {"name": "120 日平均價（半年）", "value": 199.0},
            ],
            "ma_plain": "四條平均價全部在 109 元上面，等於「過去五天、一個月、一季、半年買的人，統統套牢」。",
            "peers_1m_avg_pct": -19.46,
            "peers_plain": "同業近一個月平均也跌 19.46%，不是這家公司單獨出事，是整群一起被砍。",
            "margin_lots": 12973,
            "margin_plain": "還有很多人借錢買，跌的時候會被追繳、被迫賣，越跌越賣。",
            "volume_rule": "成交量只拿來確認，不拿來找買點。前面實測六種量能分組，超額報酬全部是負的。",
            "v41_ref": {
                "crash_up_days_pct": 39.8,
                "crash_up_total": "急殺那段，平均每天有 39.8% 的股票上漲，但整段下來 111 檔只有 4 檔是漲的。",
                "plain": "反彈天天有，但整體還是往下。所以不要「等反彈一點再賣」。",
            },
        },
        "money": money,
        "verdict": {
            "headline": "不加碼、不攤平、不等回本；從下一個交易日開始，按日分批，"
                        "把這檔慢慢降到「只佔總資產 1% 以內」就停。",
            "why_not_wait": f"從 {NOW:.0f} 回到當初買進的實付，要漲到 {m['recover_price']:.1f} 元，"
                            f"等於再漲 {m['recover_pct_from_now']:.2f}%。公司還在賠錢、今年股息 0 元，沒有東西幫您墊著。",
            "why_not_average": "「比最高點便宜七成」不是買的理由。就像房子還在往下掉，不會因為比上個月便宜就再買一間。",
            "why_not_all_at_once": "急殺當天一次砍光，是情緒不是方法；但也不要等反彈。"
                                  "解法是交給日曆：分幾天、每天降一點，不看盤、不改。",
            "day_by_day": {
                "rule": "方向只有一個：降到這檔只佔總資產 1% 以內就停，不是全部賣光、也不是留著等回本。",
                "unknown": "「每次要賣幾張」要等您回答第 8 節那四個問題（有幾張、總資產多少）才算得出來。"
                           "資料不夠，這裡只給方向與節奏，不給張數——不硬湊一個每天十分之一給您。",
                "plain": "就像搬一堆重在身上的東西，不必一天搬完，也不必指定每天搬幾公斤；"
                         "每天搬一點、搬到剩下不壓身就好。",
            },
            "stop_order_expired": {
                "truth": f"我們原本那條「−15% 無條件砍」是要在【買進當下】就交給券商託管。"
                         f"現在股價已經 {NOW:.0f} 元，事後補掛 {m['stop_price']:.1f} 元永遠不會觸發，等於沒掛。",
                "plain": "保險要在出事之前買。出事之後才買，保險公司不賠。",
                "fix": "現在能補的只有兩件事：① 把「不准加碼、不准攤平」寫死；"
                       "② 不要再補掛新的價格條件單（那會跟「分批降」打架），"
                       "改由「照表按日分批」＋三條自動停手規則接管，"
                       "並把「停損要買進當下就掛」記進錯題本。",
            },
        },
        "actions": [
            {"when": "今天（11/08 週日，休市）", "do": "不下任何單。把這張卡印出來，回答底下四個問題；打電話問券商「這筆是不是融資、維持率多少」。"},
            {"when": "下一個交易日 11/09 起", "do": "按日分批、每天降一點，降到這檔只佔總資產 1% 以內就停；不管當天漲跌、不看新聞、不改方向。每次賣幾張，等四個問題有答案再算。"},
            {"when": "每次賣完當天", "do": "退出來的錢先放回現金，補到 24 個月生活費；滿了之後才放到會配息的地方。不要馬上換別支股票。"},
            {"when": "每個月底只看一次", "do": "看三件事：站不站得回半年平均價、公司連續兩季有沒有開始賺錢、股息是不是不再掛零。三樣都成立，也只是放回觀察名單，不是可以買。"},
            {"when": "每一筆賣出都記一筆", "do": "寫下：當初是照哪一條買的？那條現在還成立嗎？這是給系統的錯題本，不是責備自己。"},
        ],
        "questions_for_user": [
            "這檔當初實際買了幾張？（不知道 → 只能給比例，不能給張數）",
            "買進的實際成交價是多少？（若不是 371，上面每一個金額都要重算）",
            "這檔佔您全部資產的百分之幾？（不知道 → 算不出 1% 是幾張）",
            "是不是用融資買的？（若是，追繳比股價更急，要先問券商維持率）",
        ],
        "pretrade": {
            "purpose": "真的跑一次 12 問，問的是「現在想攤平／加碼，準不準」。",
            "ok": chk["ok"],
            "issue_n": len(chk["issues"]),
            "issues": chk["issues"],
            "key_fails": [
                "第 9 題：公司最近一年合起來是賠錢的 → 不過",
                "第 11 題：是因為「跌很多」才想買 → 不過（這叫伸手接刀）",
                f"其餘 {len(chk['issues']) - 2} 題資料不夠或沒回答，依規矩一律算不過關",
            ],
            "plain": f"12 問全數過不了（不過 {len(chk['issues'])} 題）→ 今天不准下任何「買」的單。",
        },
        "auto": {
            "status": "M0 模擬盤，未連富邦、未下任何單（與前幾版相同）",
            "whitelist": "這檔不進自動化白名單",
            "can": ["只掛「停損」與「不准加碼」，不掛「加碼」、不掛「抄底」", "三條自動停手（一天賠到 300 元、連賠 3 次、整體從高點跌 8%）永遠最優先"],
            "cannot": ["不設「跌到 XX 元自動買進」（那正是接刀）", "不設「反彈就補回」（那條只給會配息的核心持股）", "不開當沖對沖：前面實測來回成本 0.435%、每天做一次一年侵蝕 66.7%"],
            "plain": "自動交易在這裡是幫您踩煞車，不是幫您找買點。",
        },
        "wrongbook": [
            {"lesson": "停損要「買進當下」就掛，不能事後補",
             "evidence": f"{BUY:.0f} 買、−15% 該在 {m['stop_price']:.1f} 元出場；現在 {NOW:.0f} 元，"
                         f"每張少拿 {m['saved_per_lot_if_stopped']:,.0f} 元。"},
            {"lesson": "「等回本」不是策略",
             "evidence": f"要漲 {m['recover_pct_from_now']:.2f}% 才回到當初實付，而公司近四季仍虧損、股息 0 元。"},
            {"lesson": "不要用「便宜很多」當買點",
             "evidence": "12 問第 11 題專門擋這件事；V4.1 急殺段實測：天天有反彈，整段卻只有 4/111 上漲。"},
            {"lesson": "分批是為了讓人撐得住，不是為了賣到好價錢",
             "evidence": f"分 {BATCH_DAYS} 天賣跟一次賣，10 張只差 {m['split_cost_diff']:,.0f} 元手續費；"
                         "但下跌段分批減碼沒有對應實測，所以只給做法不給報酬數字。"},
        ],
        "unknown": [
            "實際買幾張、成交價、佔總資產比例、是否融資、融資維持率",
            "這檔的含息五年報酬、最大回撤、年化波動、正式評分（不在 111 檔池，一律不編）",
            "分批減碼在下跌段「會比一次賣少賠多少」——沒有對應實測，不知道",
            "下週會漲還是會跌——不知道，也不該拿來當決策依據",
        ],
        "sources": [
            "Yahoo 奇摩股市 6217.TWO（2026/11/06 收盤 109.00、52 週 45.55–371.00）",
            "元大證券動態報導 6217（2026/11/06 收盤 109.00、量 4,151 張、開 106.5 高 110.5 低 106.5）",
            "鉅亨網盤中速報（2026/11/06，加權指數 −4.18%、測試介面概念領跌 −7.66%）",
            "台股技術指標網站 6217（2026/11/06，5 / 20 / 60 / 120 日平均價、殖利率 0%）",
            "泰哥提供之 2026/11/06 台指收盤 39,701.64",
            "V4.3 結果檔 v43_case_6217.json（基本面、同業、五道安檢門、處置紀錄）",
        ],
        "disclaimer": "這是方法示範與風險控管，不是買賣建議；系統仍在模擬盤，沒有連線、沒有下單。",
    }


def main():
    d = build()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    m = d["money"]
    print(f"產出 {OUT.name}（{OUT.stat().st_size:,} bytes）")
    print("\n一句話：", d["one_line"])
    print(f"\n一張 371 買進實付 {m['buy_paid']:,.0f} 元 → 109 賣出實收 {m['sell_received']:,.0f} 元")
    print(f"  每張賠 {m['loss_per_lot']:,.0f} 元（{m['loss_pct_on_cash']}%）｜10 張賠 {m['loss_10lots_now']:,.0f} 元")
    print(f"  回本價 {m['recover_price']} 元 = 從 109 再漲 {m['recover_pct_from_now']}%")
    print(f"  若當初 −15% 在 {m['stop_price']} 出場，每張可少賠 {m['saved_per_lot_if_stopped']:,.0f} 元")
    print(f"  分 10 天賣 vs 一次賣（10 張）只差 {m['split_cost_diff']:,.0f} 元")
    print(f"\n12 問：ok={d['pretrade']['ok']}、不過 {d['pretrade']['issue_n']} 題 → 不准買")


if __name__ == "__main__":
    main()
