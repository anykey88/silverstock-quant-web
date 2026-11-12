# -*- coding: utf-8 -*-
"""
V3.8 资产配置引擎 —— 四层桶 / 风险预算 / 部分止盈 / 再平衡
================================================================
目的：回答「投资不是梭哈」这件事在数学上到底怎么做。
所有数字都用 assets/data/snapshot.json 的真实 5 年日线跑出来，含股息、含交易成本。

七件事：
  1. 相关性 & 有效分散档数   —— 买 20 档台股 ≠ 分散
  2. 估值分位（基本面锚）     —— 用 PE 历史分位调权重，而不是看新闻
  3. 配置矩阵               —— 100/0 到 40/60、波动率目标、regime、四层桶
  4. 再平衡红利             —— 阈值 5pp / 季度 / 不再平衡 的差异
  5. 部分止盈数学           —— 阶梯止盈到底牺牲多少期望、换回多少回撤
  6. 2022 压力测试          —— 大空头年各配置的真实表现
  7. 现金流覆盖             —— 股息能覆盖多少生活费（安全垫的真实来源）

运行：python3 tool/v3/asset_allocation.py
输出：v38_allocation_result.json
"""
import json
import math
import os
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SNAP = os.path.join(ROOT, "assets", "data", "snapshot.json")
OUT = os.path.join(ROOT, "v38_allocation_result.json")

# ── 成本与利率假设（写死，可改但要留痕）────────────────────────────
FEE = 0.001425          # 券商手续费（未打折）
TAX_STOCK = 0.003       # 个股证交税
TAX_ETF = 0.001         # ETF 证交税
CASH_ANNUAL = 0.016     # 一年期定存 / 货币基金
BOND_ANNUAL = 0.025     # 短债 / 投资级债（假设值，非实测）
TRADING_DAYS = 252


# ══════════════════════════════════════════════════════════════════
# 0. 数据装载
# ══════════════════════════════════════════════════════════════════
def load():
    with open(SNAP, encoding="utf-8") as f:
        return json.load(f)


def series_of(stock):
    """把 (dates, closes, dividends) 转成 {date_int: total_return_factor}
    含息：除息日把股息按当日价格再投入（等价于股息再投资）。"""
    dates = stock["dates"]
    closes = stock["closes"]
    divs = stock.get("dividends") or []

    # 股息按「YYYY-MM」索引，落到该月第一个交易日
    div_by_ym = {}
    for ym, amt in divs:
        try:
            div_by_ym[ym] = div_by_ym.get(ym, 0.0) + float(amt)
        except (TypeError, ValueError):
            continue

    px = {}
    for d, c in zip(dates, closes):
        if c and c > 0:
            px[d] = float(c)
    return px, div_by_ym


def aligned(px, axis):
    """沿主轴前值填充，缺失日沿用上一笔收盘价"""
    out, last = [], None
    for d in axis:
        if d in px:
            last = px[d]
        out.append(last)
    # 头部缺口：用第一个有效值回填
    first = next((v for v in out if v is not None), None)
    return [v if v is not None else first for v in out]


def total_return_index(px, div_by_ym, axis):
    """总报酬指数：价格涨跌 + 股息再投入。基准 = 1.0"""
    out, last, nav = [], None, 1.0
    prev_ym = None
    for d in axis:
        p = px.get(d, last)
        if p is None:
            out.append(nav)
            continue
        if last is not None and last > 0:
            nav *= p / last
        last = p
        ym = str(d)[:6]
        ym = f"{ym[:4]}-{ym[4:]}"
        if ym != prev_ym:
            prev_ym = ym
            if ym in div_by_ym:                 # 除息：股息再投入
                nav *= 1.0 + div_by_ym[ym] / p
        out.append(nav)
    return out


# ══════════════════════════════════════════════════════════════════
# 1. 指标
# ══════════════════════════════════════════════════════════════════
def rets(nav):
    return [nav[i] / nav[i - 1] - 1.0 for i in range(1, len(nav)) if nav[i - 1] > 0]


def ann_ret(nav, days):
    if nav[0] <= 0 or days <= 0:
        return 0.0
    return (nav[-1] / nav[0]) ** (TRADING_DAYS / days) - 1.0


def mdd(nav):
    peak, worst = nav[0], 0.0
    for x in nav:
        peak = max(peak, x)
        worst = min(worst, x / peak - 1.0)
    return worst


def ann_vol(nav):
    r = rets(nav)
    return statistics.pstdev(r) * math.sqrt(TRADING_DAYS) if len(r) > 2 else 0.0


def stats(nav, label):
    n = len(nav) - 1
    ar = ann_ret(nav, n)
    md = mdd(nav)
    av = ann_vol(nav)
    return {
        "name": label,
        "final_x": round(nav[-1], 4),
        "total_pct": round((nav[-1] - 1) * 100, 2),
        "ann_pct": round(ar * 100, 2),
        "mdd_pct": round(md * 100, 2),
        "vol_pct": round(av * 100, 2),
        "calmar": round(ar / abs(md), 2) if md < 0 else 0.0,
        "sharpe": round((ar - CASH_ANNUAL) / av, 2) if av > 0 else 0.0,
    }


def rolling_1y(nav, window=252):
    """滚动一年持有的收益分布：最差 5% / 中位 / 最好 5% / 亏损概率"""
    if len(nav) <= window + 5:
        return None
    rs = sorted(nav[i + window] / nav[i] - 1.0 for i in range(len(nav) - window))
    n = len(rs)
    return {
        "n_windows": n,
        "worst_pct": round(rs[0] * 100, 2),
        "p5_pct": round(rs[int(n * 0.05)] * 100, 2),
        "median_pct": round(rs[n // 2] * 100, 2),
        "p95_pct": round(rs[int(n * 0.95)] * 100, 2),
        "best_pct": round(rs[-1] * 100, 2),
        "loss_prob_pct": round(sum(1 for x in rs if x < 0) / n * 100, 1),
    }


def underwater_days(nav, axis):
    """最长水下天数（从高点到重新创新高的最长间隔）"""
    peak, peak_i, longest, cur_start = nav[0], 0, 0, None
    for i, v in enumerate(nav):
        if v >= peak:
            if cur_start is not None:
                longest = max(longest, i - cur_start)
                cur_start = None
            peak, peak_i = v, i
        else:
            if cur_start is None:
                cur_start = peak_i
    if cur_start is not None:
        longest = max(longest, len(nav) - 1 - cur_start)
    return longest


def year_return(nav, axis, year):
    """单年（含息）报酬"""
    idx = [i for i, d in enumerate(axis) if str(d).startswith(str(year))]
    if len(idx) < 2:
        return None
    a, b = idx[0], idx[-1]
    # 年初净值取上一年最后一天
    base = nav[a - 1] if a > 0 else nav[a]
    return round((nav[b] / base - 1) * 100, 2)


# ══════════════════════════════════════════════════════════════════
# 2. 相关性 / 有效分散档数（成对取交集，不用前值填充，避免假低相关）
# ══════════════════════════════════════════════════════════════════
def _ret_map(px):
    ks = sorted(px)
    out = {}
    for i in range(1, len(ks)):
        if px[ks[i - 1]] > 0:
            out[ks[i]] = px[ks[i]] / px[ks[i - 1]] - 1.0
    return out


def _pair_corr(ra, rb, dates):
    a = [ra[d] for d in dates if d in ra and d in rb]
    b = [rb[d] for d in dates if d in ra and d in rb]
    if len(a) < 120:
        return None
    try:
        return statistics.correlation(a, b)
    except statistics.StatisticsError:
        return None


def corr_analysis(px_map, axis, subset=None):
    """px_map: {id: {date: price}}。返回全期相关、熊市相关、有效档数"""
    ids = [k for k in px_map if len(px_map[k]) >= 1000]
    if subset is not None:
        ids = [k for k in ids if k in subset]
    rm = {k: _ret_map(px_map[k]) for k in ids}

    # 市场基准：等权收益，用来定义「下跌日」
    all_dates = sorted(set().union(*[set(rm[k]) for k in ids]))
    mkt = {}
    for d in all_dates:
        vs = [rm[k][d] for k in ids if d in rm[k]]
        if len(vs) > 50:
            mkt[d] = sum(vs) / len(vs)

    down_days = sorted([d for d, v in mkt.items() if v < 0],
                       key=lambda d: mkt[d])[:int(len(mkt) * 0.20)]
    bear_days = [d for d in all_dates if str(d).startswith("2022")]

    def avg_corr(dates):
        pairs, tot = 0, 0.0
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                c = _pair_corr(rm[ids[i]], rm[ids[j]], dates)
                if c is not None:
                    tot += c
                    pairs += 1
        return (tot / pairs, pairs) if pairs else (0.0, 0)

    c_all, n_all = avg_corr(all_dates)
    c_down, _ = avg_corr(down_days)
    c_bear, _ = avg_corr(bear_days)

    n = len(ids)
    enb = n / (1 + (n - 1) * c_all) if n > 1 else 1

    # 分散化效果：等权组合实际波动 / 各档平均波动
    vols = []
    for k in ids:
        r = list(rm[k].values())
        if len(r) > 200:
            vols.append(statistics.pstdev(r) * math.sqrt(TRADING_DAYS))
    avg_vol = sum(vols) / len(vols) if vols else 0
    ew = []
    for d in all_dates:
        vs = [rm[k][d] for k in ids if d in rm[k]]
        if len(vs) > 50:
            ew.append(sum(vs) / len(vs))
    ew_vol = statistics.pstdev(ew) * math.sqrt(TRADING_DAYS) if len(ew) > 100 else 0

    return {
        "n_assets": n,
        "avg_pairwise_corr": round(c_all, 4),
        "corr_down_days": round(c_down, 4),
        "corr_2022": round(c_bear, 4),
        "effective_n": round(enb, 1),
        "diversification_ratio": round(enb / n, 3),
        "avg_single_vol_pct": round(avg_vol * 100, 2),
        "equal_weight_vol_pct": round(ew_vol * 100, 2),
        "vol_reduction_pct": round((1 - ew_vol / avg_vol) * 100, 2) if avg_vol else 0,
    }


# ══════════════════════════════════════════════════════════════════
# 3. 估值分位（基本面锚）
# ══════════════════════════════════════════════════════════════════
def pe_percentile(ps):
    """perSeries 形如 [date, 殖利率, PE, PB]；返回当前 PE 在历史中的分位"""
    pes = [r[2] for r in (ps or []) if len(r) >= 3 and r[2] and r[2] > 0]
    if len(pes) < 12:
        return None
    cur = pes[-1]
    below = sum(1 for x in pes if x <= cur)
    return round(below / len(pes), 3)


def valuation_thermometer(snap):
    """全市场估值温度：每档 PE 分位的中位数 + 各分位分布"""
    rows = []
    for sid, s in snap["stocks"].items():
        p = pe_percentile(s.get("perSeries"))
        pe = s.get("latest")
        cur_pe = pe[2] if pe and len(pe) >= 3 else None
        if p is not None and cur_pe:
            rows.append({"id": sid, "name": s.get("name", ""),
                         "industry": s.get("industry", ""),
                         "pe": round(cur_pe, 2), "pe_pct": p})
    rows.sort(key=lambda r: r["pe_pct"])
    med = statistics.median([r["pe_pct"] for r in rows]) if rows else None
    cheap = [r for r in rows if r["pe_pct"] <= 0.30]
    rich = [r for r in rows if r["pe_pct"] >= 0.70]
    return {
        "n": len(rows),
        "median_pe_pct": round(med, 3) if med is not None else None,
        "cheap_n": len(cheap),
        "rich_n": len(rich),
        "cheap": cheap[:12],
        "rich": rich[-12:],
        "all": rows,
    }


# ══════════════════════════════════════════════════════════════════
# 4. 配置回测引擎
# ══════════════════════════════════════════════════════════════════
def is_quarter_start(d_prev, d):
    """跨季第一天"""
    if d_prev is None:
        return False
    return str(d)[:4] != str(d_prev)[:4] or (int(str(d)[4:6]) - 1) // 3 != (int(str(d_prev)[4:6]) - 1) // 3


def run_config(axis, assets, weights, rebal="quarter", band=0.05, cost=0.0025):
    """资产 = {id: 总报酬净值序列}；weights = {id: w}，现金用 'CASH'
    rebal: 'none' | 'quarter' | 'year' | 'band'
    """
    n = len(axis)
    cash_daily = (1 + CASH_ANNUAL) ** (1 / TRADING_DAYS) - 1
    nav = [1.0]
    w = dict(weights)
    prev_date = None
    turnover_total = 0.0

    for i in range(1, n):
        # 当日各资产收益
        r = {}
        for k in weights:
            if k == "CASH":
                r[k] = cash_daily
            else:
                s = assets[k]
                r[k] = s[i] / s[i - 1] - 1.0 if s[i - 1] > 0 else 0.0
        port_r = sum(w[k] * r[k] for k in w)
        nav.append(nav[-1] * (1 + port_r))

        # 权重漂移
        grown = {k: w[k] * (1 + r[k]) for k in w}
        tot = sum(grown.values())
        w = {k: grown[k] / tot for k in grown}

        # 再平衡判定
        do = False
        if rebal == "quarter" and is_quarter_start(prev_date, axis[i]):
            do = True
        elif rebal == "year" and str(axis[i])[:4] != str(prev_date)[:4]:
            do = True
        elif rebal == "band":
            do = max(abs(w[k] - weights[k]) for k in w) > band

        if do:
            turnover = sum(abs(w[k] - weights[k]) for k in w) / 2
            if turnover > 0:
                turnover_total += turnover
                nav[-1] *= (1 - turnover * cost * 2)   # 卖出+买入两段
            w = dict(weights)
        prev_date = axis[i]

    out = stats(nav, "")
    out["turnover_annual"] = round(turnover_total / (n / TRADING_DAYS), 2)
    out["nav"] = [round(x, 4) for x in nav]
    return out


def run_regime(axis, risk_nav, caps, cost=0.0025, lookback=240):
    """按 TAIEX 状态调仓：BULL/NEUTRAL/BEAR/CRISIS → 仓位上限"""
    n = len(axis)
    cash_daily = (1 + CASH_ANNUAL) ** (1 / TRADING_DAYS) - 1
    nav = [1.0]
    w = caps["BULL"]
    turnover_total = 0.0
    state_counts = {}
    state_now = "BULL"

    for i in range(1, n):
        # 用 T+1 执行 T 日信号（无前视）
        if i >= 260:
            hist = risk_nav[:i]
            last = hist[-1]
            hh = max(hist[-252:])
            dd = last / hh - 1.0
            ma240 = sum(hist[-lookback:]) / lookback
            w20 = hist[-21:]
            rr = [w20[j] / w20[j - 1] - 1 for j in range(1, len(w20))]
            vol20 = statistics.pstdev(rr) * math.sqrt(TRADING_DAYS) if len(rr) > 2 else 0
            if dd <= -0.25 or vol20 >= 0.45:
                state_now = "CRISIS"
            elif dd <= -0.15 or last < ma240:
                state_now = "BEAR"
            elif dd <= -0.08:
                state_now = "NEUTRAL"
            else:
                state_now = "BULL"
        target = caps[state_now]
        state_counts[state_now] = state_counts.get(state_now, 0) + 1

        r_risk = risk_nav[i] / risk_nav[i - 1] - 1.0
        port_r = w * r_risk + (1 - w) * cash_daily
        nav.append(nav[-1] * (1 + port_r))

        if abs(target - w) > 0.001:
            turnover_total += abs(target - w)
            nav[-1] *= (1 - abs(target - w) * cost)
            w = target

    out = stats(nav, "")
    out["turnover_annual"] = round(turnover_total / (n / TRADING_DAYS), 2)
    out["state_days"] = state_counts
    out["nav"] = [round(x, 4) for x in nav]
    return out


def run_voltgt(axis, risk_nav, target=0.15, lo=0.30, hi=0.95, cost=0.0025):
    """波动率目标：仓位 = 目标波动 / 近 20 日实际波动（周频更新）"""
    n = len(axis)
    cash_daily = (1 + CASH_ANNUAL) ** (1 / TRADING_DAYS) - 1
    nav = [1.0]
    w = 0.6
    turnover_total = 0.0

    for i in range(1, n):
        if i >= 25 and i % 5 == 0:
            w20 = risk_nav[i - 20:i + 1]
            rr = [w20[j] / w20[j - 1] - 1 for j in range(1, len(w20))]
            vol = statistics.pstdev(rr) * math.sqrt(TRADING_DAYS) if len(rr) > 2 else target
            new_w = max(lo, min(hi, target / vol)) if vol > 0 else hi
            if abs(new_w - w) > 0.02:
                turnover_total += abs(new_w - w)
                nav[-1] *= (1 - abs(new_w - w) * cost)
                w = new_w
        r_risk = risk_nav[i] / risk_nav[i - 1] - 1.0
        port_r = w * r_risk + (1 - w) * cash_daily
        nav.append(nav[-1] * (1 + port_r))

    out = stats(nav, "")
    out["turnover_annual"] = round(turnover_total / (n / TRADING_DAYS), 2)
    out["nav"] = [round(x, 4) for x in nav]
    return out


def run_valuation_tilt(axis, risk_nav, monthly_pct, cost=0.0025):
    """估值温度调仓：市场 PE 分位越低，股票仓位越高"""
    n = len(axis)
    cash_daily = (1 + CASH_ANNUAL) ** (1 / TRADING_DAYS) - 1
    nav = [1.0]
    w = 0.7
    turnover_total = 0.0
    prev_ym = None

    for i in range(1, n):
        ym = str(axis[i])[:6]
        if ym != prev_ym:
            prev_ym = ym
            pct = monthly_pct.get(ym)
            if pct is not None:
                target = 0.90 if pct <= 0.30 else (0.70 if pct <= 0.70 else 0.50)
                if abs(target - w) > 0.001:
                    turnover_total += abs(target - w)
                    nav[-1] *= (1 - abs(target - w) * cost)
                    w = target
        r_risk = risk_nav[i] / risk_nav[i - 1] - 1.0
        nav.append(nav[-1] * (1 + w * r_risk + (1 - w) * cash_daily))

    out = stats(nav, "")
    out["turnover_annual"] = round(turnover_total / (n / TRADING_DAYS), 2)
    out["nav"] = [round(x, 4) for x in nav]
    return out


# ══════════════════════════════════════════════════════════════════
# 5. 部分止盈数学
# ══════════════════════════════════════════════════════════════════
def take_profit_sim(px, div_by_ym, axis, rules, cash_daily):
    """单档、起始买入 1 元、持有到期末。rules 定义止盈阶梯。
    返回 (终值倍数, 最大回撤, 触发档数, 已卖出比例, 逐日净值序列)"""
    cost = None
    for d in axis:
        if d in px and px[d] > 0:
            cost = px[d]
            break
    if not cost:
        return 1.0, 0.0, 0, 0.0, [1.0] * len(axis)

    shares = 1.0 / cost
    init_shares = shares
    cash = 0.0
    peak = cost
    sold_steps = set()
    history = []
    prev_ym = None
    last_px = cost

    for d in axis:
        p = px.get(d, last_px)
        if p is None or p <= 0:
            history.append(shares * last_px + cash)
            continue
        last_px = p

        ym = f"{str(d)[:4]}-{str(d)[4:6]}"
        if ym != prev_ym:
            prev_ym = ym
            if ym in div_by_ym:
                cash += shares * div_by_ym[ym]

        ret = p / cost - 1.0

        for i, (trigger, frac) in enumerate(rules.get("steps", [])):
            if i not in sold_steps and ret >= trigger and shares > 1e-9:
                sell = shares * frac
                cash += sell * p * (1 - FEE - TAX_STOCK)
                shares -= sell
                sold_steps.add(i)

        ts = rules.get("trail")
        if ts and shares > 1e-9 and (p / peak - 1.0) <= -ts:
            cash += shares * p * (1 - FEE - TAX_STOCK)
            shares = 0.0
            take_profit_sim.exited = True

        peak = max(peak, p)
        history.append(shares * p + cash)
        cash *= (1 + cash_daily)

    final = shares * last_px + cash
    md = mdd(history)
    return final, md, len(sold_steps), 1.0 - shares / init_shares, history


def take_profit_portfolio(px_map, div_map, axis, ids, rules, cash_daily):
    """等权组合（每日再平衡到等权，等价于等权篮子）跑止盈规则"""
    paths = []
    for sid in ids:
        px = px_map.get(sid)
        if not px or len(px) < 1000:
            continue
        f, md, steps, sold, hist = take_profit_sim(px, div_map.get(sid, {}), axis, rules, cash_daily)
        if len(hist) != len(axis):
            continue
        paths.append(hist)
    if not paths:
        return None
    L = min(len(x) for x in paths)
    combo = [sum(p[i] for p in paths) / len(paths) for i in range(L)]
    st = stats(combo, "")
    st["n"] = len(paths)
    st["nav"] = [round(x, 4) for x in combo]
    return st


# ══════════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════════
def main():
    snap = load()
    axis = snap["index"]["dates"]
    n = len(axis)
    print(f"主轴 {n} 个交易日  {axis[0]} → {axis[-1]}")

    cash_daily = (1 + CASH_ANNUAL) ** (1 / TRADING_DAYS) - 1

    # ── 资产净值序列（含息）
    navs = {}
    px_map, div_map = {}, {}
    for sid, s in snap["stocks"].items():
        px, divs = series_of(s)
        if len(px) < 800:
            continue
        px_map[sid] = px
        div_map[sid] = divs
        navs[sid] = total_return_index(px, divs, axis)
    print(f"可用资产 {len(navs)} 档")

    # TAIEX（价格指数，不含息；用 0050 代替含息基准）
    taiex_nav = [x / snap["index"]["closes"][0] for x in snap["index"]["closes"]]
    taiex_nav = taiex_nav[:n]

    # ── 1. 相关性
    # 流动性筛选：日均成交额 ≥3 亿、且价格不僵滞（零收益日 <3%）
    adv, zero_ratio = {}, {}
    for sid, s in snap["stocks"].items():
        if sid not in px_map:
            continue
        c = s.get("closes") or []
        v = s.get("volumes") or []
        k = min(len(c), len(v), 60)
        adv[sid] = sum(v[len(v) - k + i] * 1000 * c[len(c) - k + i] for i in range(k)) / k / 1e8 if k else 0
        r = list(_ret_map(px_map[sid]).values())
        zero_ratio[sid] = sum(1 for x in r if abs(x) < 1e-9) / len(r) if r else 1
    liquid = {k for k in px_map if adv.get(k, 0) >= 3}
    print(f"流动性池 {len(liquid)} 档（日均成交额≥3亿）")

    print("算相关性…")
    cm = corr_analysis(px_map, axis, subset=liquid)
    cm_all = corr_analysis(px_map, axis)
    print(f"  平均两两相关 {cm['avg_pairwise_corr']}  下跌日 {cm['corr_down_days']}  2022 {cm['corr_2022']}")
    print(f"  有效档数 {cm['effective_n']}/{cm['n_assets']}  波动削减 {cm['vol_reduction_pct']}%")

    # ── 2. 估值温度
    print("算估值分位…")
    vt = valuation_thermometer(snap)
    print(f"  中位 PE 分位 {vt['median_pe_pct']}  便宜 {vt['cheap_n']} 档  昂贵 {vt['rich_n']} 档")

    # 月度估值温度序列（用 2330/大盘代理的月度 PE 分位滚动）
    monthly_pct = {}
    ref = snap["stocks"].get("2330", {}).get("perSeries") or []
    pes = [(r[0], r[2]) for r in ref if len(r) >= 3 and r[2] and r[2] > 0]
    for i in range(len(pes)):
        hist = [p for _, p in pes[:i + 1]]
        cur = pes[i][1]
        pct = sum(1 for x in hist if x <= cur) / len(hist)
        ym = pes[i][0].replace("-", "")[:6]
        monthly_pct[ym] = pct

    # ── 3. 配置矩阵
    print("跑配置回测…")
    R = "0050"          # 风险资产：元大台湾50（含息，可交易）
    D = "0056"          # 高股息
    G = "00878"         # 高股息2

    configs = {}

    # 纯股 / 纯债
    configs["A. 100% 0050 买入持有"] = run_config(axis, navs, {R: 1.0}, rebal="none")
    configs["B. 80/20 年度再平衡"] = run_config(axis, navs, {R: 0.8, "CASH": 0.2}, rebal="year")
    configs["C. 70/30 年度再平衡"] = run_config(axis, navs, {R: 0.7, "CASH": 0.3}, rebal="year")
    configs["D. 60/40 年度再平衡"] = run_config(axis, navs, {R: 0.6, "CASH": 0.4}, rebal="year")
    configs["E. 40/60 年度再平衡"] = run_config(axis, navs, {R: 0.4, "CASH": 0.6}, rebal="year")
    # 再平衡频率对比（同一 70/30）
    configs["F. 70/30 不再平衡"] = run_config(axis, navs, {R: 0.7, "CASH": 0.3}, rebal="none")
    configs["G. 70/30 阈值±5pp"] = run_config(axis, navs, {R: 0.7, "CASH": 0.3}, rebal="band", band=0.05)
    configs["H. 70/30 季度再平衡"] = run_config(axis, navs, {R: 0.7, "CASH": 0.3}, rebal="quarter")
    # 四层桶
    configs["I. 四层桶（20现金/25高息/35指数/20卫星）"] = run_config(
        axis, navs,
        {"CASH": 0.20, D: 0.25, R: 0.35, G: 0.20},
        rebal="quarter")
    # 动态
    configs["J. 波动率目标 15%"] = run_voltgt(axis, navs[R])
    configs["K. Regime 调仓"] = run_regime(axis, navs[R],
                                           {"BULL": 0.85, "NEUTRAL": 0.65, "BEAR": 0.40, "CRISIS": 0.20})
    configs["L. 估值温度调仓"] = run_valuation_tilt(axis, navs[R], monthly_pct)

    # 压力测试与分布
    for k, v in configs.items():
        v["y2022"] = year_return(v["nav"], axis, 2022)
        v["y2023"] = year_return(v["nav"], axis, 2023)
        v["y2025"] = year_return(v["nav"], axis, 2025)
        v["y2026"] = year_return(v["nav"], axis, 2026)
        v["roll_1y"] = rolling_1y(v["nav"])
        v["underwater_days"] = underwater_days(v["nav"], axis)
        v["underwater_months"] = round(v["underwater_days"] / 21, 1)
        v["nav_slim"] = v["nav"][::7]
        v["recover_gain_pct"] = round((1 / (1 + v["mdd_pct"] / 100) - 1) * 100, 1)
        v.pop("nav", None)

    rows = sorted(configs.items(), key=lambda kv: -kv[1]["calmar"])
    print("\n{:<40} {:>8} {:>8} {:>8} {:>8} {:>8}".format("配置", "总报酬", "年化", "MDD", "Calmar", "年换手"))
    for k, v in rows:
        print("{:<40} {:>7.1f}% {:>7.2f}% {:>7.1f}% {:>8.2f} {:>8.2f}".format(
            k, v["total_pct"], v["ann_pct"], v["mdd_pct"], v["calmar"], v["turnover_annual"]))

    # ── 4. 部分止盈
    print("\n跑部分止盈实验…")
    pool = [sid for sid, s in snap["stocks"].items()
            if len(s["closes"]) >= 1000 and s.get("industry") != "ETF"]
    bh = take_profit_portfolio(px_map, div_map, axis, pool, {"steps": [], "trail": None}, cash_daily)

    rules_all = [
        ("0. 买入持有（对照）", {"steps": [], "trail": None}),
        ("1. +20% 卖 1/4", {"steps": [(0.20, 0.25)], "trail": None}),
        ("2. +20%卖1/4 / +40%卖1/3", {"steps": [(0.20, 0.25), (0.40, 1 / 3)], "trail": None}),
        ("3. 阶梯 + 移动止损20%", {"steps": [(0.20, 0.25), (0.40, 1 / 3)], "trail": 0.20}),
        ("4. +30% 卖 1/2", {"steps": [(0.30, 0.50)], "trail": None}),
        ("5. 纯移动止损 20%（全清）", {"steps": [], "trail": 0.20}),
        ("6. 纯移动止损 30%（全清）", {"steps": [], "trail": 0.30}),
    ]
    tp = []
    for label, rules in rules_all:
        r = take_profit_portfolio(px_map, div_map, axis, pool, rules, cash_daily)
        if r:
            r["rule"] = label
            r["roll_1y"] = rolling_1y(r["nav"])
            r["underwater_days"] = underwater_days(r["nav"], axis)
            r["underwater_months"] = round(r["underwater_days"] / 21, 1)
            r.pop("nav", None)
            tp.append(r)
            print("  {:<28} 终值 {:.2f}x  年化 {:>6.2f}%  MDD {:>7.2f}%  Calmar {:.2f}".format(
                label, r["final_x"], r["ann_pct"], r["mdd_pct"], r["calmar"]))

    # ── 5. 现金流覆盖
    cashflow = []
    for sid in ["0050", "0056", "00878"]:
        s = snap["stocks"][sid]
        divs = s.get("dividends") or []
        px, _ = series_of(s)
        recent = [d for d in divs if d[0] >= "2025-01"]
        ttm = sum(d[1] for d in recent)
        cur = px[max(px.keys())]
        # 5 年累计股息 / 5 年平均价 = 年均殖利率（更稳，含资本利得不剔除）
        all_div = sum(d[1] for d in divs if d[0] >= "2021-07")
        avg_px = sum(px.values()) / len(px)
        cashflow.append({
            "id": sid, "name": s["name"],
            "price": round(cur, 2),
            "ttm_div": round(ttm, 3),
            "yield_pct": round(ttm / cur * 100, 2),
            "yield_5y_avg_pct": round(all_div / 5.3 / avg_px * 100, 2),
            "cash_per_100w": round(1_000_000 * ttm / cur, 0),
            "cash_per_1000w_5yavg": round(10_000_000 * (all_div / 5.3 / avg_px), 0),
        })

    result = {
        "meta": {
            "range": [axis[0], axis[-1]],
            "days": n,
            "assets": len(navs),
            "assumptions": {
                "cash_annual_pct": CASH_ANNUAL * 100,
                "bond_annual_pct": BOND_ANNUAL * 100,
                "fee_pct": FEE * 100,
                "tax_stock_pct": TAX_STOCK * 100,
                "tax_etf_pct": TAX_ETF * 100,
                "note": "含息总报酬，股息再投入；调仓成本单边 0.25%（ETF）",
            },
        },
        "correlation": cm,
        "correlation_all": cm_all,
        "liquid_n": len(liquid),
        "valuation": {
            "median_pe_pct": vt["median_pe_pct"],
            "cheap_n": vt["cheap_n"],
            "rich_n": vt["rich_n"],
            "n": vt["n"],
            "cheap": vt["cheap"][:8],
            "rich": vt["rich"][-8:],
        },
        "configs": [{"key": k, **v} for k, v in rows],
        "take_profit": tp,
        "buyhold_equal": bh,
        "cashflow": cashflow,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"\n已写出 {OUT}")

    return result


if __name__ == "__main__":
    main()
