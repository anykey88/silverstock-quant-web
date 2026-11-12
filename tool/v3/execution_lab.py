# -*- coding: utf-8 -*-
"""
V4.0 执行策略实验室
===================
回答泰哥的九个观察，全部用 111 档台股 5 年日线（含息、含成本）实测：

  A. 预定目标价自动买卖「太早出手」→ 卖出后的回补规则，比卖点准不准重要多少
  B. 慢慢建仓 / 慢慢减码 → 分批次数的代价曲线与拐点
  C. 没有交易条件就观察等待 → 空手的价值与踏空代价
  D. 零股测试系统 → 不同下单金额的往返成本与最小有效下单额
  E. 整张当日冲销对冲 → 成本门槛（日线无 high/low，不做日内信号断言）
  F. 触底反弹 / 行情突然反转 → 反转确认信号的滞后成本与假反弹次数

严格纪律：
  - 所有信号只用「当日收盘前」可得的资料，均线/回撤都往回看，无前视。
  - 资料集只有收盘价，没有开/高/低 → 当冲只算成本，不编日内绩效。
  - 每段实验都列换手次数与成本，避免用「没出事」证明「有效」。

运行：cd tool/v3 && python3 execution_lab.py
输出：v40_execution_result.json
"""
import json
import math
import os
import statistics
import bisect

from asset_allocation import (
    load, series_of, total_return_index, mdd, stats,
    FEE, TAX_STOCK, TAX_ETF, CASH_ANNUAL, TRADING_DAYS,
)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "v40_execution_result.json")

TAX_DAY = 0.0015            # 现股当冲卖出交易税（个股 3‰ 减半）
CASH_DAILY = (1 + CASH_ANNUAL) ** (1 / TRADING_DAYS) - 1
COST_BUY = FEE
COST_SELL_ETF = FEE + TAX_ETF
COST_SELL_STOCK = FEE + TAX_STOCK


def idx_of(axis, d, side="left"):
    i = bisect.bisect_right(axis, d) - 1
    return max(0, min(i, len(axis) - 1))


def norm(nav, i0, i1):
    """切段并归一化到 1.0"""
    seg = nav[i0:i1 + 1]
    base = seg[0] if seg[0] > 0 else 1.0
    return [x / base for x in seg]


def run_weighted(seg, decide, fee=FEE, tax=TAX_ETF, cash_daily=CASH_DAILY):
    """通用仓位机：decide(i, w, eq, ctx) -> 目标仓位 w（0~1）。

    用「权重」而非「股数」建模：每日 equity *= 1 + w*r + (1-w)*cash_daily
    调整权重按 |Δw| 扣成本；减仓扣 (fee+tax)，加仓扣 fee。
    这样部分止盈、分批建仓、空手等待都能用同一套成本口径。
    """
    w, eq = 0.0, 1.0
    path, turns, cost_paid = [], 0, 0.0
    ctx = {"entry": None, "sell_i": None, "sell_px": None,
           "post_peak": None, "cycles": 0, "last_trade_i": -999}
    for i in range(len(seg)):
        if i > 0 and seg[i - 1] > 0:
            r = seg[i] / seg[i - 1] - 1.0
            eq *= 1 + w * r + (1 - w) * cash_daily
        if ctx["entry"] is None and w > 0:
            ctx["entry"] = seg[i]
        tw = decide(i, w, eq, ctx)
        tw = max(0.0, min(1.0, tw))
        if abs(tw - w) > 1e-9:
            delta = abs(tw - w)
            c = delta * (fee + (tax if tw < w else 0.0))
            eq *= (1 - c)
            cost_paid += c
            turns += 1
            w = tw
            ctx["last_trade_i"] = i
            if tw > 0 and ctx["entry"] is None:
                ctx["entry"] = seg[i]
            if tw > 0 and ctx["sell_i"] is not None:
                ctx["sell_i"] = None
                ctx["entry"] = seg[i]
            if tw == 0:
                ctx["sell_i"] = i
                ctx["sell_px"] = seg[i]
                ctx["post_peak"] = seg[i]
        if ctx["sell_i"] is not None and i > ctx["sell_i"]:
            ctx["post_peak"] = max(ctx["post_peak"] or seg[i], seg[i])
        path.append(eq)
    st = stats(path, "")
    st["turnovers"] = turns
    st["cost_paid_pct"] = round(cost_paid * 100, 2)
    st["final_w"] = round(w, 2)
    st["nav_slim"] = [round(x, 3) for x in path[::7]]
    return st, path


# ══════════════════════════════════════════════════════════════════
# A. 「太早出手」：静态止盈卖出后，回补规则能救回多少
# ══════════════════════════════════════════════════════════════════
def exit_reentry(seg, trigger, mode, param=20):
    """起点满仓；相对「本轮进场价」涨到 +trigger 就卖出（预定目标价自动卖）。

    mode:
      never      卖出后永不回补（泰哥描述的痛点）
      after_N    卖出后第 N 日无条件回补
      dip_Y      卖出后回档 Y% 回补（等回头，最常见的错误）
      newhigh_N  卖出后 N 日内创「卖出后新高」回补（趋势确认）
      ladder     不一次卖：+trigger 卖 1/4，+2*trigger 再卖 1/3
      repeat     可反复执行「卖出→N 日回补」，上限 3 轮，用来看换手成本
    """
    def decide(i, w, eq, ctx):
        if i == 0:
            ctx["entry"] = seg[0]
            ctx["steps"] = set()
            return 1.0
        px = seg[i]
        basis = ctx["entry"] or seg[0]
        gain = px / basis - 1.0

        # 卖出触发
        if w > 0 and ctx["sell_i"] is None:
            if mode == "ladder":
                if 0 not in ctx["steps"] and gain >= trigger:
                    ctx["steps"].add(0)
                    return max(0.0, w - 0.25)
                if 1 not in ctx["steps"] and gain >= 2 * trigger:
                    ctx["steps"].add(1)
                    return max(0.0, w - 1 / 3)
                return w
            if gain >= trigger:
                return 0.0

        # 空手后的回补判断
        if w == 0 and ctx["sell_i"] is not None:
            k = i - ctx["sell_i"]
            if mode == "never":
                return 0.0
            if mode in ("after_N", "repeat") and k >= param:
                if mode == "repeat":
                    ctx["cycles"] = ctx.get("cycles", 0) + 1
                    if ctx["cycles"] >= 3:
                        return 0.0
                return 1.0
            if mode == "dip_Y" and px / (ctx["sell_px"] or px) - 1 <= -param:
                return 1.0
            if mode == "newhigh_N" and 0 < k <= param and px >= (ctx["post_peak"] or px):
                return 1.0
        return w

    return run_weighted(seg, decide, tax=TAX_ETF)[0]


def experiment_a(navs, axis, periods):
    bulls = [p for p in periods if p["direction"] == "多頭"]
    out = []
    for p in bulls:
        i0, i1 = idx_of(axis, p["start"]), idx_of(axis, p["end"])
        seg = norm(navs["0050"], i0, i1)
        bh = run_weighted(seg, lambda i, w, eq, ctx: 1.0, tax=TAX_ETF)[0]
        rows = [{"rule": "买入持有（对照）", **{k: bh[k] for k in
                ("total_pct", "ann_pct", "mdd_pct", "calmar", "turnovers", "cost_paid_pct")}}]
        for trig in (0.10, 0.20, 0.30):
            variants = [
                ("never", 0), ("after_N", 20), ("after_N", 60),
                ("dip_Y", 0.05), ("dip_Y", 0.10), ("newhigh_N", 20),
                ("repeat", 20), ("ladder", 0),
            ]
            for mode, prm in variants:
                r = exit_reentry(seg, trig, mode, prm)
                rows.append({
                    "trigger_pct": round(trig * 100), "mode": mode, "param": prm,
                    "rule": f"+{round(trig*100)}% 賣 / {mode} {prm if prm else ''}".strip(),
                    **{k: r[k] for k in ("total_pct", "ann_pct", "mdd_pct", "calmar",
                                          "turnovers", "cost_paid_pct")},
                    "gap_vs_bh_pp": round(r["total_pct"] - bh["total_pct"], 2),
                })
        out.append({"start": p["start"], "end": p["end"],
                    "index_ret_pct": p["index_ret_pct"],
                    "bh_total_pct": bh["total_pct"], "rows": rows})
    return out


# ══════════════════════════════════════════════════════════════════
# B. 分批建仓 / 分批减码：次数的代价曲线
# ══════════════════════════════════════════════════════════════════
def dca_experiment(navs, axis, crash_start, crash_end, hold_days=250):
    """在急杀段分 k 次建仓，持有到低点后 250 日。
    mode: time（时间等分）/ dip（每跌 X% 加码，金字塔）"""
    i0 = idx_of(axis, crash_start)
    ie = idx_of(axis, crash_end)
    i1 = min(len(axis) - 1, ie + hold_days)
    seg = norm(navs["0050"], i0, i1)
    crash_len = ie - i0
    out = []
    for k in (1, 2, 3, 5, 10, 20):
        for mode in ("time", "dip"):
            if mode == "time":
                buy_days = {min(crash_len, round(crash_len * (j + 1) / k)) for j in range(k)}
            else:
                # 每相对起点跌 3% 买一次，最多 k 次
                buy_days = set()
                step = 0.03
                for i in range(crash_len + 1):
                    lvl = seg[i] / seg[0] - 1
                    if lvl <= -step * len(buy_days) and len(buy_days) < k:
                        buy_days.add(i)
                if 0 not in buy_days and k == 1:
                    buy_days.add(0)
            inc = 1.0 / k

            def decide(i, w, eq, ctx, bd=buy_days, inc=inc):
                if i in bd and w < 1 - 1e-9 and i <= crash_len:
                    return min(1.0, w + inc)
                return w

            r, path = run_weighted(seg, decide, tax=TAX_ETF)
            # 平均建仓成本（相对起点价）
            costs = [seg[i] for i in sorted(buy_days)]
            out.append({
                "k": k, "mode": mode,
                "total_pct": r["total_pct"], "mdd_pct": r["mdd_pct"],
                "calmar": r["calmar"], "turnovers": r["turnovers"],
                "cost_paid_pct": r["cost_paid_pct"],
                "avg_entry_vs_start_pct": round((sum(costs) / len(costs) / seg[0] - 1) * 100, 2) if costs else 0,
                "final_w": r["final_w"],
            })
    return {"start": crash_start, "end": crash_end,
            "hold_days": hold_days, "crash_bars": crash_len, "rows": out}


def scale_out_experiment(navs, axis, bull_start, bull_end):
    """多头段分批减码：从 +30% 起分 k 次减到空手，对比一次清与不卖。"""
    i0, i1 = idx_of(axis, bull_start), idx_of(axis, bull_end)
    seg = norm(navs["0050"], i0, i1)
    bh = run_weighted(seg, lambda i, w, eq, ctx: 1.0, tax=TAX_ETF)[0]
    out = [{"k": 0, "rule": "不減碼（對照）", **{x: bh[x] for x in
            ("total_pct", "mdd_pct", "calmar", "turnovers", "cost_paid_pct")}}]
    for k in (1, 2, 3, 5, 10):
        trig_lo, trig_hi = 0.30, 1.20
        done = set()

        def decide(i, w, eq, ctx, k=k, done=done):
            if i == 0:
                return 1.0
            if w <= 0:
                return 0.0
            lvl = seg[i] / seg[0] - 1
            for j in range(k):
                t = trig_lo + (trig_hi - trig_lo) * j / max(1, k - 1)
                if j not in done and lvl >= t:
                    done.add(j)
                    return max(0.0, w - 1.0 / k)
            return w

        r, _ = run_weighted(seg, decide, tax=TAX_ETF)
        out.append({"k": k, "rule": f"分 {k} 次減碼",
                    **{x: r[x] for x in ("total_pct", "mdd_pct", "calmar",
                                          "turnovers", "cost_paid_pct")},
                    "final_w": r["final_w"]})
    return {"start": bull_start, "end": bull_end, "rows": out}


# ══════════════════════════════════════════════════════════════════
# C. 「没有条件就观察等待」：空手的价值与代价
# ══════════════════════════════════════════════════════════════════
def waiting_experiment(navs, axis, periods):
    """每月检查一次状态（避免频繁），信号只用截至当日收盘的资料。"""
    px = navs["0050"]
    n = len(axis)
    ma = {}
    for win in (60, 120, 240):
        vals = []
        s = 0.0
        for i in range(n):
            s += px[i]
            if i >= win:
                s -= px[i - win]
            vals.append(s / min(i + 1, win))
        ma[win] = vals
    # 252 日滚动高点
    hh = [max(px[max(0, i - 251):i + 1]) for i in range(n)]

    def run(kind, th, recheck=21):
        def decide(i, w, eq, ctx):
            if i % recheck != 0:
                return w
            if kind.startswith("ma"):
                win = int(kind[2:])
                ok = px[i] >= ma[win][i]
            else:  # drawdown
                ok = px[i] / hh[i] - 1 > -th
            return 1.0 if ok else 0.0
        r, path = run_weighted(norm(px, 0, n - 1), decide, tax=TAX_ETF)
        # 空手天数（用 path 无法反推，另算）
        idle = 0
        last_w = 1.0
        for i in range(n):
            if i % recheck == 0:
                if kind.startswith("ma"):
                    last_w = 1.0 if px[i] >= ma[int(kind[2:])][i] else 0.0
                else:
                    last_w = 1.0 if px[i] / hh[i] - 1 > -th else 0.0
            if last_w == 0:
                idle += 1
        r["idle_pct"] = round(idle / n * 100, 1)
        return r

    out = []
    bh = run_weighted(norm(px, 0, n - 1), lambda i, w, eq, ctx: 1.0, tax=TAX_ETF)[0]
    out.append({"rule": "全程持有（對照）", **{x: bh[x] for x in
                ("total_pct", "ann_pct", "mdd_pct", "calmar", "turnovers", "cost_paid_pct")},
                "idle_pct": 0.0})
    for kind in ("ma60", "ma120", "ma240"):
        r = run(kind, 0)
        out.append({"rule": f"跌破 {kind[2:]} 日均線即空手（月檢）",
                    **{x: r[x] for x in ("total_pct", "ann_pct", "mdd_pct", "calmar",
                                          "turnovers", "cost_paid_pct", "idle_pct")}})
    for th in (0.08, 0.15, 0.20, 0.25):
        r = run("dd", th)
        out.append({"rule": f"回撤 >{th*100:.0f}% 即空手（月檢）",
                    **{x: r[x] for x in ("total_pct", "ann_pct", "mdd_pct", "calmar",
                                          "turnovers", "cost_paid_pct", "idle_pct")}})
    # 各空头 / 急杀段的表现
    seg_perf = []
    for p in periods:
        i0, i1 = idx_of(axis, p["start"]), idx_of(axis, p["end"])
        seg = norm(px, i0, i1)
        bh_s = run_weighted(seg, lambda i, w, eq, ctx: 1.0, tax=TAX_ETF)[0]
        # ma240 版本
        def d(i, w, eq, ctx, i0=i0):
            if i % 21 != 0:
                return w
            j = i0 + i
            return 1.0 if px[j] >= ma[240][j] else 0.0
        w_s = run_weighted(seg, d, tax=TAX_ETF)[0]
        seg_perf.append({"direction": p["direction"], "start": p["start"], "end": p["end"],
                         "index_ret_pct": p["index_ret_pct"],
                         "hold_pct": bh_s["total_pct"], "wait_pct": w_s["total_pct"],
                         "saved_pp": round(w_s["total_pct"] - bh_s["total_pct"], 2)})
    return {"rows": out, "segments": seg_perf}


# ══════════════════════════════════════════════════════════════════
# D. 零股成本精算
# ══════════════════════════════════════════════════════════════════
def odd_lot_cost():
    rows = []
    for amt in (1000, 2000, 3000, 5000, 10000, 20000, 30000, 50000, 100000):
        for is_etf in (True, False):
            mf = 1  # 零股最低手续费 1 元
            fee_buy = max(amt * FEE, mf)
            # 假设平进平出
            fee_sell = max(amt * FEE, mf)
            tax = amt * (TAX_ETF if is_etf else TAX_STOCK)
            total = fee_buy + fee_sell + tax
            be = total / (amt + fee_buy)  # 需涨多少才打平（相对买价）
            rows.append({
                "amount": amt, "kind": "ETF" if is_etf else "个股",
                "fee_each": round(fee_buy, 2), "tax": round(tax, 2),
                "roundtrip_cost": round(total, 2),
                "cost_pct": round(total / amt * 100, 3),
                "breakeven_pct": round(be * 100, 3),
                "min_fee_binding": fee_buy <= mf + 1e-9,
            })
    # 小额档：找出「最低手续费 1 元」真正开始绑定的门槛
    small_rows = []
    for amt in (200, 300, 500, 700, 702, 800, 1000):
        fee = max(amt * FEE, 1)
        tax = amt * TAX_STOCK
        total = fee * 2 + tax
        small_rows.append({"amount": amt, "fee_each": round(fee, 2),
                           "tax": round(tax, 2), "roundtrip_cost": round(total, 2),
                           "cost_pct": round(total / amt * 100, 3),
                           "breakeven_pct": round(total / (amt + fee) * 100, 3),
                           "min_fee_binding": fee <= 1 + 1e-9})
    # 整张对照（2330 现价约 2405 → 一张约 240 万）
    round_rows = []
    for amt in (100000, 500000, 1000000, 2400000):
        fee = max(amt * FEE, 20)
        tax = amt * TAX_STOCK
        total = fee * 2 + tax
        round_rows.append({"amount": amt, "fee_each": round(fee, 2),
                           "tax": round(tax, 2), "roundtrip_cost": round(total, 2),
                           "cost_pct": round(total / amt * 100, 3),
                           "breakeven_pct": round(total / (amt + fee) * 100, 3),
                           "min_fee_binding": fee <= 20 + 1e-9})
    # 要验证一个策略需要几笔（简单 power：单笔净期望 / 单笔波动）
    power = []
    for edge in (0.005, 0.01, 0.02):
        for sd in (0.02, 0.03, 0.05):
            n = (1.96 * sd / edge) ** 2 if edge > 0 else 0
            power.append({"edge_pct": round(edge * 100, 2), "sd_pct": round(sd * 100, 1),
                          "trades_needed_95": math.ceil(n)})
    return {"odd_rows": rows, "small_rows": small_rows,
            "min_fee_threshold_ntd": round(1 / FEE, 2),
            "round_rows": round_rows, "power": power,
            "fee_rate_pct": round(FEE * 100, 4),
            "tax_stock_pct": round(TAX_STOCK * 100, 3),
            "tax_etf_pct": round(TAX_ETF * 100, 3)}


# ══════════════════════════════════════════════════════════════════
# E. 当冲成本门槛（不做日内绩效断言）
# ══════════════════════════════════════════════════════════════════
def daytrade_cost(navs, axis):
    px = navs["0050"]
    r = [abs(px[i] / px[i - 1] - 1) for i in range(1, len(px)) if px[i - 1] > 0]
    r_sorted = sorted(r)
    n = len(r_sorted)
    # 个股当冲：买 fee 1.425‰ + 卖 fee 1.425‰ + 当冲税 1.5‰
    cost_stock = FEE * 2 + TAX_DAY
    cost_etf = FEE * 2 + TAX_ETF  # ETF 当冲税仍 1‰（不减半）
    # 一年天天做，光成本吃掉多少
    erode_stock = (1 - (1 - cost_stock) ** TRADING_DAYS) * 100
    erode_etf = (1 - (1 - cost_etf) ** TRADING_DAYS) * 100
    # 打平胜率：赔率 1:1，赚 g% / 亏 g%，扣成本 c
    need = []
    for g in (0.005, 0.01, 0.02, 0.03):
        need.append({"swing_pct": round(g * 100, 1),
                     "breakeven_winrate_pct": round((0.5 + cost_stock / (2 * g)) * 100, 2)})
    # 一张 2330 当冲一次的绝对成本
    one_lot = 2405 * 1000
    return {
        "cost_stock_pct": round(cost_stock * 100, 3),
        "cost_etf_pct": round(cost_etf * 100, 3),
        "annual_erosion_stock_pct": round(erode_stock, 1),
        "annual_erosion_etf_pct": round(erode_etf, 1),
        "one_lot_amount": one_lot,
        "one_lot_cost_ntd": round(one_lot * cost_stock, 0),
        "breakeven_winrate": need,
        "daily_abs_move": {
            "median_pct": round(r_sorted[n // 2] * 100, 2),
            "p75_pct": round(r_sorted[int(n * 0.75)] * 100, 2),
            "p90_pct": round(r_sorted[int(n * 0.90)] * 100, 2),
            "mean_pct": round(sum(r) / n * 100, 2),
            "note": "相邻收盘价变动绝对值，仅作波动量级参考，非日内可捕捉振幅",
        },
        "limitation": "snapshot.json 只有收盘价，无 open/high/low；无法验证任何日内信号或当冲绩效，此处只列成本门槛。",
        "tax_day_pct": round(TAX_DAY * 100, 3),
    }


# ══════════════════════════════════════════════════════════════════
# F. 反转确认：滞后成本与假反弹次数
# ══════════════════════════════════════════════════════════════════
def reversal_experiment(navs, axis, periods):
    px = navs["0050"]
    n = len(px)
    ma20 = [sum(px[max(0, i - 19):i + 1]) / min(i + 1, 20) for i in range(n)]
    ma240 = [sum(px[max(0, i - 239):i + 1]) / min(i + 1, 240) for i in range(n)]
    bears = [p for p in periods if p["direction"] == "空頭"]
    out = []
    for p in bears:
        i0, i1 = idx_of(axis, p["start"]), idx_of(axis, p["end"])
        low_i = min(range(i0, i1 + 1), key=lambda i: px[i])
        end_i = min(n - 1, low_i + 250)
        base = px[low_i]
        # 三种确认信号（从低点往后找首次触发）
        sig = {}
        for name in ("ma20", "ma240", "hold5"):
            hit = None
            for i in range(low_i + 1, min(n - 1, low_i + 120) + 1):
                if name == "ma20" and px[i] > ma20[i]:
                    hit = i
                    break
                if name == "ma240" and px[i] > ma240[i]:
                    hit = i
                    break
                if name == "hold5" and px[i] / base - 1 >= 0.05 and \
                        min(px[max(low_i, i - 10):i + 1]) >= base * 0.999:
                    hit = i
                    break
            sig[name] = hit
        rows = [{"signal": "底部當日單筆（事後，僅作上限）", "lag_days": 0,
                 "entry_vs_low_pct": 0.0,
                 "ret_250_pct": round((px[end_i] / base - 1) * 100, 2)}]
        for name, hit in sig.items():
            if hit is None:
                rows.append({"signal": {"ma20": "站回 20 日均線", "ma240": "站回 240 日年線",
                                        "hold5": "低點反彈 5% 且 10 日不破低"}[name],
                             "lag_days": None, "entry_vs_low_pct": None, "ret_250_pct": None})
                continue
            rows.append({
                "signal": {"ma20": "站回 20 日均線", "ma240": "站回 240 日年線",
                           "hold5": "低點反彈 5% 且 10 日不破低"}[name],
                "lag_days": hit - low_i,
                "entry_vs_low_pct": round((px[hit] / base - 1) * 100, 2),
                "ret_250_pct": round((px[end_i] / px[hit] - 1) * 100, 2),
            })
        # 假反弹：空头段内「5 日涨 ≥5%」后 15 日内又破该起点低点
        fake, last = 0, -99
        for i in range(i0 + 5, i1 + 1):
            if px[i] / px[i - 5] - 1 >= 0.05 and i - last >= 15:
                if any(px[j] < px[i - 5] for j in range(i + 1, min(i1 + 1, i + 16))):
                    fake += 1
                    last = i
        out.append({"start": p["start"], "end": p["end"], "low_date": axis[low_i],
                    "low_px": round(base, 2), "index_ret_pct": p["index_ret_pct"],
                    "fake_rebounds": fake, "rows": rows})
    return out


# ══════════════════════════════════════════════════════════════════
# G. 防过拟合：前半段选参数、后半段验证 + 组合规则实测
# ══════════════════════════════════════════════════════════════════
def _ma_hh(px):
    n = len(px)
    ma = {}
    for win in (60, 120, 240):
        vals, acc = [], 0.0
        for i in range(n):
            acc += px[i]
            if i >= win:
                acc -= px[i - win]
            vals.append(acc / min(i + 1, win))
        ma[win] = vals
    hh = [max(px[max(0, i - 251):i + 1]) for i in range(n)]
    return ma, hh


def _wait_rule(px, ma, hh, i0, i1, kind, th, recheck=21):
    seg = norm(px, i0, i1)

    def decide(i, w, eq, ctx):
        if i != 0 and i % recheck != 0:
            return w
        g = i0 + i
        if kind.startswith("ma"):
            ok = px[g] >= ma[int(kind[2:])][g]
        else:
            ok = px[g] / hh[g] - 1 > -th
        return 1.0 if ok else 0.0

    return run_weighted(seg, decide, tax=TAX_ETF)[0]


def walkforward(navs, axis):
    """诚实的样本外检验：前半段挑出最好的等待参数，后半段才知道有没有用。"""
    px = navs["0050"]
    n = len(px)
    ma, hh = _ma_hh(px)
    split = idx_of(axis, 20240701)
    cands = [("ma60", 0), ("ma120", 0), ("ma240", 0),
             ("dd", 0.08), ("dd", 0.15), ("dd", 0.20), ("dd", 0.25)]
    train = []
    for kind, th in cands:
        r = _wait_rule(px, ma, hh, 0, split, kind, th)
        train.append({"kind": kind, "th": th, "calmar": r["calmar"],
                      "total_pct": r["total_pct"], "mdd_pct": r["mdd_pct"],
                      "turnovers": r["turnovers"]})
    best = max(train, key=lambda x: x["calmar"])
    test = _wait_rule(px, ma, hh, split, n - 1, best["kind"], best["th"])
    bh_test = run_weighted(norm(px, split, n - 1),
                           lambda i, w, eq, ctx: 1.0, tax=TAX_ETF)[0]
    # 参数敏感度：改动检查周期
    sens = []
    for rc in (10, 21, 42, 63):
        r = _wait_rule(px, ma, hh, split, n - 1, best["kind"], best["th"], rc)
        sens.append({"recheck_days": rc, "total_pct": r["total_pct"],
                     "mdd_pct": r["mdd_pct"], "calmar": r["calmar"],
                     "turnovers": r["turnovers"]})
    return {
        "split_date": axis[split], "train_range": [axis[0], axis[split]],
        "test_range": [axis[split], axis[-1]],
        "train_candidates": train,
        "best_in_sample": best,
        "test_rule_pct": test["total_pct"], "test_rule_mdd": test["mdd_pct"],
        "test_rule_calmar": test["calmar"], "test_turnovers": test["turnovers"],
        "test_bh_pct": bh_test["total_pct"], "test_bh_mdd": bh_test["mdd_pct"],
        "test_bh_calmar": bh_test["calmar"],
        "outperformance_pp": round(test["total_pct"] - bh_test["total_pct"], 2),
        "sensitivity": sens,
    }


def combined_rule(px, ma, axis, i0, i1, step1=0.20, step2=0.40,
                  reenter_days=20, off_w=0.40, batch=1 / 3):
    """V4.0 建议规则（参数事前固定的中庸值，不是样本内挑最优）：

      起点满仓 = 核心层永不择时（衔接 V3.8 四层桶）；
      月检 MA120：RISK_OFF 把目标仓位降到 off_w，RISK_ON 分批补回；
      +20% 卖 1/4、+40% 再卖 1/3（部分退出，保留底仓）；
      卖出后 reenter_days 日内创新高回补 1/4 ← 这是 V4.0 最关键的升级。
      对照：买入持有、静态目标价 +20% 全卖不回补。
    """
    seg = norm(px, i0, i1)

    def decide(i, w, eq, ctx):
        if i == 0:
            ctx.update(entry=seg[0], steps=set(), sell_i=None,
                       post_peak=None, target=1.0)
            return 1.0                      # 核心层起点就不动
        g = i0 + i
        pxn = seg[i]
        if i % 21 == 0:                    # 月检，避免频繁
            ok = px[g] >= ma[120][g]
            ctx["target"] = 1.0 if ok else off_w
            if w < ctx["target"] - 1e-9:
                return min(ctx["target"], w + batch)
            if w > ctx["target"] + 1e-9:
                return max(ctx["target"], w - batch)
        basis = ctx["entry"] or seg[0]
        gain = pxn / basis - 1.0
        if w > 0 and ctx["sell_i"] is None:
            if 0 not in ctx["steps"] and gain >= step1:
                ctx["steps"].add(0)
                ctx["sell_i"] = i
                ctx["post_peak"] = pxn
                ctx["target"] = max(0.0, ctx["target"] - 0.25)
                return max(0.0, w - 0.25)
            if 1 not in ctx["steps"] and gain >= step2:
                ctx["steps"].add(1)
                ctx["sell_i"] = i
                ctx["post_peak"] = pxn
                ctx["target"] = max(0.0, ctx["target"] - 1 / 3)
                return max(0.0, w - 1 / 3)
        if ctx["sell_i"] is not None:
            k = i - ctx["sell_i"]
            if 0 < k <= reenter_days and pxn >= (ctx["post_peak"] or pxn):
                ctx["sell_i"] = None
                ctx["steps"].clear()
                ctx["entry"] = pxn
                ctx["target"] = min(1.0, ctx["target"] + 0.25)
                return min(1.0, w + 0.25)
            ctx["post_peak"] = max(ctx["post_peak"] or pxn, pxn)
        return w

    combo, path = run_weighted(seg, decide, tax=TAX_ETF)
    bh, _ = run_weighted(seg, lambda i, w, eq, ctx: 1.0, tax=TAX_ETF)
    static, _ = run_weighted(seg, exit_reentry_decide(seg, step1, "never"), tax=TAX_ETF)
    return {"range": [axis[i0], axis[i1]],
            "combo": {k: combo[k] for k in ("total_pct", "mdd_pct", "calmar",
                                             "turnovers", "cost_paid_pct")},
            "buyhold": {k: bh[k] for k in ("total_pct", "mdd_pct", "calmar", "turnovers")},
            "static_target": {k: static[k] for k in ("total_pct", "mdd_pct", "calmar",
                                                      "turnovers", "cost_paid_pct")},
            "nav_slim": combo["nav_slim"],
            "bh_slim": bh["nav_slim"],
            "static_slim": static["nav_slim"]}


def exit_reentry_decide(seg, trigger, mode, param=20):
    """给 combined_rule 用的简化 decide：静态目标价全卖、不回补"""
    def decide(i, w, eq, ctx):
        if i == 0:
            return 1.0
        if w > 0 and seg[i] / seg[0] - 1 >= trigger:
            return 0.0
        return w
    return decide



def main():
    snap = load()
    axis = snap["index"]["dates"]
    navs, px_map = {}, {}
    for sid, s in snap["stocks"].items():
        px, divs = series_of(s)
        if len(px) < 800:
            continue
        px_map[sid] = px
        navs[sid] = total_return_index(px, divs, axis)
    print(f"可用资产 {len(navs)} 档，交易轴 {axis[0]}–{axis[-1]}（{len(axis)} 日）")

    periods = [
        {"direction": "空頭", "start": 20210601, "end": 20220706, "index_ret_pct": -18.51},
        {"direction": "空頭", "start": 20220706, "end": 20221025, "index_ret_pct": -9.43},
        {"direction": "多頭", "start": 20221025, "end": 20240711, "index_ret_pct": 92.56},
        {"direction": "空頭", "start": 20240711, "end": 20250221, "index_ret_pct": -2.71},
        {"direction": "空頭", "start": 20250221, "end": 20250409, "index_ret_pct": -26.71},
        {"direction": "多頭", "start": 20250409, "end": 20261022, "index_ret_pct": 164.73},
    ]

    print("\nA. 静态目标价卖出后的回补规则…")
    a = experiment_a(navs, axis, periods)
    for blk in a:
        bh = blk["bh_total_pct"]
        print(f"  多头 {blk['start']}–{blk['end']}  买入持有 {bh:+.1f}%")
        for r in blk["rows"][1:]:
            if r["trigger_pct"] == 20:
                print(f"    {r['rule']:<30} {r['total_pct']:>8.1f}%  "
                      f"落后 {r['gap_vs_bh_pp']:>7.1f}pp  换手 {r['turnovers']}")

    print("\nB. 分批建仓 / 减码…")
    dca = dca_experiment(navs, axis, 20250221, 20250409)
    for r in dca["rows"]:
        if r["mode"] == "time":
            print(f"   时间等分 k={r['k']:<3} 期末 {r['total_pct']:>7.1f}%  "
                  f"MDD {r['mdd_pct']:>6.1f}%  均成本 {r['avg_entry_vs_start_pct']:>6.1f}%")
    scale = scale_out_experiment(navs, axis, 20250409, 20261022)
    for r in scale["rows"]:
        print(f"   减码 {r['rule']:<12} 期末 {r['total_pct']:>7.1f}%  MDD {r['mdd_pct']:>6.1f}%")

    print("\nC. 观察等待的价值…")
    wait = waiting_experiment(navs, axis, periods)
    for r in wait["rows"]:
        print(f"   {r['rule']:<28} 全程 {r['total_pct']:>7.1f}%  "
              f"MDD {r['mdd_pct']:>6.1f}%  Calmar {r['calmar']:>5.2f}  空手 {r['idle_pct']:>5.1f}%")

    print("\nG. 样本外检验 + 组合规则…")
    wf = walkforward(navs, axis)
    print(f"   前半段最佳参数 {wf['best_in_sample']['kind']} {wf['best_in_sample']['th']} "
          f"(Calmar {wf['best_in_sample']['calmar']})")
    print(f"   后半段：规则 {wf['test_rule_pct']:+.1f}% / MDD {wf['test_rule_mdd']:.1f}% "
          f"vs 持有 {wf['test_bh_pct']:+.1f}% / MDD {wf['test_bh_mdd']:.1f}% "
          f"→ 超额 {wf['outperformance_pp']:+.1f}pp")
    ma, _ = _ma_hh(navs["0050"])
    combos = []
    for d0, d1, label in ((20221025, 20240711, "多头一"),
                          (20250409, 20261022, "多头二"),
                          (None, None, "全程")):
        c = combined_rule(navs["0050"], ma, axis,
                          idx_of(axis, d0) if d0 else 0,
                          idx_of(axis, d1) if d1 else len(axis) - 1)
        c["label"] = label
        combos.append(c)
        print(f"   {label}: 组合 {c['combo']['total_pct']:+.1f}% / MDD {c['combo']['mdd_pct']:.1f}% "
              f"vs 持有 {c['buyhold']['total_pct']:+.1f}% vs 静态目标价 {c['static_target']['total_pct']:+.1f}%")

    print("\nD. 零股成本 / E. 当冲门槛 / F. 反转确认…")
    odd = odd_lot_cost()
    day = daytrade_cost(navs, axis)
    rev = reversal_experiment(navs, axis, periods)
    print(f"   1,000 元零股个股往返成本 {odd['odd_rows'][1]['cost_pct']}%；"
          f"当冲个股来回 {day['cost_stock_pct']}%、一年复利侵蚀 {day['annual_erosion_stock_pct']}%")
    for x in rev:
        print(f"   空头 {x['start']} 假反弹 {x['fake_rebounds']} 次；"
              f"站回年线滞后 {next((r['lag_days'] for r in x['rows'] if r['signal'].startswith('站回 240')), '-')} 日")

    result = {
        "meta": {
            "title": "V4.0 执行策略实验室",
            "universe": len(navs),
            "range": snap["meta"]["range"],
            "bars": len(axis),
            "note": "含息总报酬、含 1.425‰ 手续费与个股 3‰/ETF 1‰ 交易税；信号无前视",
        },
        "exit_reentry": a,
        "dca": dca,
        "scale_out": scale,
        "waiting": wait,
        "odd_lot": odd,
        "daytrade": day,
        "reversal": rev,
        "walkforward": wf,
        "combined": combos,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"\n已输出 {OUT}")


if __name__ == "__main__":
    main()
