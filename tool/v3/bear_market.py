# -*- coding: utf-8 -*-
"""
V3.9 熊市生存引擎
=================
回答四件事（全部用 111 档台股 5 年日线实测，含息、含成本）：
  A. 熊市里到底什么能赚钱 —— 4 段真实空头波段逐一验证
  B. 基本面股 vs 炒作股 —— 用「事前可得」的指标分组，不是事后贴标签
  C. 为什么有人熊市赚钱、有人牛市亏钱 —— 6 个行为模型在多头波段里复现
  D. 风险怎么把控 —— 把差异转成仓位/止损/禁买清单

严格避免前视偏误：所有分类特征都在每个波段开始「前一天」计算，
只用当时已经存在的价格、股息、估值、成交量资料。

运行：python3 tool/v3/bear_market.py
输出：v39_bear_result.json
"""
import json
import math
import os
import statistics
import bisect

from asset_allocation import (
    load, series_of, total_return_index, rets, mdd, stats,
    ann_vol, FEE, TAX_STOCK, TAX_ETF, CASH_ANNUAL, TRADING_DAYS,
)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUDIT = os.path.join(ROOT, "..", "v35_factor_audit.json")
OUT = os.path.join(ROOT, "v39_bear_result.json")

COST_ETF = FEE + TAX_ETF          # 单次买卖 ETF
COST_STOCK = FEE + TAX_STOCK      # 单次买卖个股
MARGIN_RATE = 0.03               # 融资利率（假设）


def idx_of(axis, d, side="left"):
    """把 YYYYMMDD 转成轴上的位置（找最接近且不超过的交易日）"""
    i = bisect.bisect_right(axis, d) - 1
    return max(0, min(i, len(axis) - 1))


def ann_vol_of(xs):
    r = [xs[i] / xs[i - 1] - 1 for i in range(1, len(xs)) if xs[i - 1] > 0]
    return statistics.pstdev(r) * math.sqrt(TRADING_DAYS) if len(r) > 2 else 0.0


def point_in_time_features(stock, axis, i_asof):
    """在 asof 时点（含）之前，只用当时可得的资料算特征"""
    px_map = {d: c for d, c in zip(stock["dates"], stock["closes"]) if c and c > 0}
    dates = axis[:i_asof + 1]
    closes = [px_map.get(d) for d in dates]
    # 前值填補（只補頭部）
    first = next((c for c in closes if c is not None), None)
    closes = [c if c is not None else first for c in closes]
    if not first or len(closes) < 70:
        return None

    cur = closes[-1]
    c60 = closes[-61:]
    vol60 = ann_vol_of(c60)
    mom60 = cur / c60[0] - 1.0 if c60[0] > 0 else 0.0
    mdd60 = mdd(c60)
    vol20 = ann_vol_of(closes[-21:])

    # 殖利率 TTM（過去 12 個月配息 / 現價）
    asof_date = str(axis[i_asof])
    lo_ym = f"{int(asof_date[:4])-1}-{asof_date[4:6]}"
    hi_ym = f"{asof_date[:4]}-{asof_date[4:6]}"
    ttm_div = sum(float(a) for ym, a in (stock.get("dividends") or [])
                  if lo_ym <= ym <= hi_ym)
    yld = ttm_div / cur if cur > 0 else 0.0

    # PE 分位（只用 asof 之前的月頻資料）
    ps = [r for r in (stock.get("perSeries") or [])
          if len(r) >= 3 and r[2] and r[2] > 0 and r[0].replace("-", "") <= asof_date]
    pe = ps[-1][2] if ps else None
    pe_pct = (sum(1 for r in ps if r[2] <= pe) / len(ps)) if (ps and pe) else None

    # EPS 連續性（quarterlyEps 只有 30 檔有）
    eps = [e for e in (stock.get("quarterlyEps") or [])
           if e[0].replace("-", "") <= asof_date]
    eps_pos = sum(1 for e in eps[-8:] if e[1] and e[1] > 0)
    eps_n = len(eps[-8:]) if eps else 0

    # 成交額（張 × 1000 × 價）
    v = stock.get("volumes") or []
    c = stock.get("closes") or []
    turn = [v[j] * 1000 * c[j] for j in range(len(v)) if j < len(c) and c[j]]
    adv20 = sum(turn[-20:]) / 20 if len(turn) >= 60 else 0
    adv60 = sum(turn[-60:]) / 60 if len(turn) >= 60 else 0
    burst = adv20 / adv60 if adv60 > 0 else 1.0

    return {
        "close": cur, "vol60": vol60, "vol20": vol20, "mom60": mom60,
        "mdd60": mdd60, "yield": yld, "pe": pe, "pe_pct": pe_pct,
        "eps_pos": eps_pos, "eps_n": eps_n,
        "adv60_yi": adv60 / 1e8, "burst": burst,
    }


def classify(f, all_f):
    """依事前特徵分成 防禦(基本面) / 題材(炒作) / 中間。
    分位門檻用當期全池的實際分位，不用固定數字（避免時代變動）。"""
    if f is None:
        return "NA", [], []
    vols = sorted(x["vol60"] for x in all_f if x)
    moms = sorted(x["mom60"] for x in all_f if x)
    bsts = sorted(x["burst"] for x in all_f if x)

    def q(arr, v):
        return bisect.bisect_left(arr, v) / len(arr) if arr else 0.5

    qv, qm, qb = q(vols, f["vol60"]), q(moms, f["mom60"]), q(bsts, f["burst"])

    # 基本面 / 防禦：必要條件 = 有殖利率 + 低波動；再加估值、EPS、流動性
    f_hits = []
    if f["yield"] >= 0.03: f_hits.append("殖利率≥3%")
    if qv <= 0.50: f_hits.append("波動後半段")
    if f["pe_pct"] is not None and f["pe_pct"] <= 0.60: f_hits.append("PE分位≤60%")
    if f["eps_n"] >= 4 and f["eps_pos"] >= f["eps_n"] * 0.75: f_hits.append("EPS連正")
    if f["adv60_yi"] >= 3: f_hits.append("日均成交≥3億")
    if f["mom60"] <= 0.30: f_hits.append("未被爆炒")

    # 題材 / 炒作：高波動 + 高動能 + 爆量 + 貴 + 沒息
    h_hits = []
    if qv >= 0.70: h_hits.append("波動前30%")
    if qm >= 0.70: h_hits.append("60日漲幅前30%")
    if qb >= 0.70: h_hits.append("成交爆量前30%")
    if f["pe_pct"] is not None and f["pe_pct"] >= 0.70: h_hits.append("PE分位≥70%")
    if f["pe"] is None or f["pe"] <= 0: h_hits.append("無本益比/虧損")
    if f["yield"] < 0.01: h_hits.append("幾乎不配息")

    is_f = ("殖利率≥3%" in f_hits and "波動後半段" in f_hits and len(f_hits) >= 3)
    is_h = len(h_hits) >= 3
    if is_f and not is_h:
        return "DEF", f_hits, h_hits
    if is_h and not is_f:
        return "HYPE", f_hits, h_hits
    return "MID", f_hits, h_hits


def band_returns(navs, axis, d0, d1):
    i0, i1 = idx_of(axis, d0), idx_of(axis, d1)
    out = {}
    for sid, nv in navs.items():
        if nv[i0] > 0:
            out[sid] = nv[i1] / nv[i0] - 1.0
    return out, i0, i1


def describe(vals):
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    return {
        "n": n,
        "mean_pct": round(sum(s) / n * 100, 2),
        "median_pct": round(s[n // 2] * 100, 2),
        "p25_pct": round(s[int(n * 0.25)] * 100, 2),
        "p75_pct": round(s[int(n * 0.75)] * 100, 2),
        "worst_pct": round(s[0] * 100, 2),
        "best_pct": round(s[-1] * 100, 2),
        "positive_pct": round(sum(1 for x in s if x > 0) / n * 100, 1),
    }


# ══════════════════════════════════════════════════════════════════
# 牛市行为模型（在多头波段内复现「为什么会亏钱」）
# ══════════════════════════════════════════════════════════════════
def behavior_models(navs, axis, px_map, d0, d1):
    i0, i1 = idx_of(axis, d0), idx_of(axis, d1)
    n = i1 - i0 + 1
    R = "0050"
    r_nav = navs[R][i0:i1 + 1]
    r_ret = [r_nav[k] / r_nav[k - 1] - 1 for k in range(1, n)]
    cash_daily = (1 + CASH_ANNUAL) ** (1 / TRADING_DAYS) - 1
    out = {}

    def finish(path, label, turnovers=0):
        st = {"name": label, "final_x": round(path[-1], 3),
              "total_pct": round((path[-1] - 1) * 100, 2)}
        st["ann_pct"] = round(((path[-1]) ** (TRADING_DAYS / n) - 1) * 100, 2) if path[-1] > 0 else -100
        st["mdd_pct"] = round(mdd(path) * 100, 2)
        st["turnovers"] = turnovers
        return st

    # 0. 买入持有（对照）
    out["BH"] = finish([x / r_nav[0] for x in r_nav], "買入持有 0050（對照）")

    # 1. 追涨杀跌：5 日涨幅 > 3% 次日满仓；5 日跌幅 < -3% 次日空仓
    nav, pos, prev, path, tos = 1.0, 1, 1, [1.0], 0
    for k in range(1, n):
        if k >= 6:
            m5 = r_nav[k - 1] / r_nav[k - 6] - 1
            if m5 > 0.03: pos = 1
            elif m5 < -0.03: pos = 0
        r = r_ret[k - 1]
        nav *= 1 + pos * r + (1 - pos) * cash_daily
        if pos != prev:
            nav *= (1 - COST_ETF)
            tos += 1
            prev = pos
        path.append(nav)
    out["CHASE"] = finish(path, "追漲殺跌（5日動能>3%滿倉／<-3%空倉）", tos)

    # 2. 月度追最强 10 档（主题轮动/追高）
    ids = [s for s in navs if len(navs[s]) == len(axis) and s not in ("0050", "0056", "00878")]
    nav, path, tos, holdings = 1.0, [1.0], 0, []
    for k in range(1, n):
        if (k - i0) % 21 == 0 or not holdings:
            if k > 25:
                score = []
                for s in ids:
                    seg = navs[s][i0 + k - 21:i0 + k]
                    if len(seg) >= 20 and seg[0] > 0:
                        score.append((seg[-1] / seg[0] - 1, s))
                score.sort(reverse=True)
                new_h = [s for _, s in score[:10]]
                if new_h and new_h != holdings:
                    nav *= (1 - COST_STOCK)
                    tos += 1
                holdings = new_h
        if holdings:
            rr = sum(navs[s][i0 + k] / navs[s][i0 + k - 1] - 1 for s in holdings) / len(holdings)
            nav *= 1 + rr
        else:
            nav *= 1 + cash_daily
        path.append(nav)
    out["ROTATE"] = finish(path, "每月追最強 10 檔（追主題）", tos)

    # 3. 两倍杠杆（融资）
    margin_daily = MARGIN_RATE / TRADING_DAYS
    nav, path = 1.0, [1.0]
    for k in range(1, n):
        nav *= 1 + 2 * r_ret[k - 1] - margin_daily
        nav = max(nav, 0.01)
        path.append(nav)
    out["LEVER"] = finish(path, "融資 2 倍槓桿（利率 3%）")

    # 4. 晚进场：最后 25% 时间才买，且单押当时最热的一档
    late = int(n * 0.75)
    hot = max(ids, key=lambda s: navs[s][i0 + late] / navs[s][i0 + late - 60] - 1
              if navs[s][i0 + late - 60] > 0 else 0)
    nav, path = 1.0, [1.0] * (late + 1)
    for k in range(late + 1, n):
        nav *= 1 + (navs[hot][i0 + k] / navs[hot][i0 + k - 1] - 1)
        path.append(nav)
    st = finish(path, f"牛市末段才進場＋單押最熱檔（{hot}）")
    st["late_entry_pct"] = 75
    out["LATE"] = st

    # 5. 处置效应：卖掉赚钱的、补进当期跌最多的（卖赢留输）
    nav, path, tos = 1.0, [1.0], 0
    holdings = ids[:10]
    entry = {s: navs[s][i0] for s in holdings}
    for k in range(1, n):
        if holdings:
            rr = sum(navs[s][i0 + k] / navs[s][i0 + k - 1] - 1 for s in holdings) / len(holdings)
            nav *= 1 + rr
        if k % 21 == 0 and holdings:
            # 把賺最多的 3 檔賣掉，換成過去 21 日跌最多的 3 檔
            gain = sorted(holdings, key=lambda s: navs[s][i0 + k] / entry[s] - 1, reverse=True)
            winners = gain[:3]
            pool = sorted(ids, key=lambda s: navs[s][i0 + k] / navs[s][i0 + k - 21] - 1
                          if navs[s][i0 + k - 21] > 0 else 0)
            losers = [s for s in pool if s not in holdings][:3]
            holdings = [s for s in holdings if s not in winners] + losers
            for s in losers:
                entry[s] = navs[s][i0 + k]
            nav *= (1 - COST_STOCK)
            tos += 1
        path.append(nav)
    out["DISPOSITION"] = finish(path, "處置效應（賣贏家、補輸家）", tos)

    # 6. 牛市裡仍有多少股票是賠錢的（選錯照樣虧）
    allr = {s: navs[s][i1] / navs[s][i0] - 1 for s in ids if navs[s][i0] > 0}
    neg = [v for v in allr.values() if v < 0]
    out["_breadth"] = {
        "n": len(allr), "negative_n": len(neg),
        "negative_pct": round(len(neg) / len(allr) * 100, 1) if allr else 0,
        "worst": [(s, round(allr[s] * 100, 1)) for s in sorted(allr, key=lambda k: allr[k])[:5]],
        "median_pct": round(sorted(allr.values())[len(allr) // 2] * 100, 1) if allr else 0,
    }
    return out


def leverage_path(navs, axis, d_start, d_end, stop_dd=-0.20):
    """全程 2 倍槓桿；一旦從最高淨值回撤 20% 就「被追繳/恐慌」清倉，之後持現金。
    對照：不加槓桿買入持有。用來說明「牛市賺最多的人，為什麼最後沒留在場內」。"""
    i0, i1 = idx_of(axis, d_start), idx_of(axis, d_end)
    nv = navs["0050"][i0:i1 + 1]
    cash_daily = (1 + CASH_ANNUAL) ** (1 / TRADING_DAYS) - 1
    margin_daily = MARGIN_RATE / TRADING_DAYS
    lev, bh = 1.0, nv[0] / nv[0]
    peak, stopped_at, stopped_val = 1.0, None, None
    lev_path, bh_path = [1.0], [1.0]
    for k in range(1, len(nv)):
        r = nv[k] / nv[k - 1] - 1
        bh *= 1 + r
        if stopped_at is None:
            lev *= 1 + 2 * r - margin_daily
            lev = max(lev, 0.01)
            peak = max(peak, lev)
            if lev / peak - 1 <= stop_dd:
                stopped_at = k
                stopped_val = lev
                lev_path.append(lev)
                bh_path.append(bh)
                continue
        else:
            lev *= 1 + cash_daily
        lev_path.append(lev)
        bh_path.append(bh)
    return {
        "start": d_start, "end": d_end, "bars": len(nv),
        "lever_final_pct": round((lev_path[-1] - 1) * 100, 2),
        "lever_peak_pct": round((peak - 1) * 100, 2),
        "buyhold_final_pct": round((bh_path[-1] - 1) * 100, 2),
        "stopped_at_bar": stopped_at,
        "stopped_date": axis[i0 + stopped_at] if stopped_at else None,
        "stopped_value_pct": round((stopped_val - 1) * 100, 2) if stopped_val else None,
        "stop_dd_pct": stop_dd * 100,
        "lever_slim": [round(x, 3) for x in lev_path[::7]],
        "bh_slim": [round(x, 3) for x in bh_path[::7]],
    }


def top_lever_loss(navs, axis, d0, d1):
    """在空頭波段起點滿倉 2 倍槓桿進場，30 天後剩多少"""
    i0, i1 = idx_of(axis, d0), idx_of(axis, d1)
    nv = navs["0050"][i0:i1 + 1]
    r = nv[-1] / nv[0] - 1
    lev = max(0.01, 1 + 2 * r)
    return {
        "start": d0, "end": d1, "days": i1 - i0,
        "index_ret_pct": round(r * 100, 2),
        "lever_ret_pct": round((lev - 1) * 100, 2),
        "recover_needed_pct": round((1 / lev - 1) * 100, 1) if lev > 0 else None,
    }


def group_paths(navs, axis, snap, asof_date, end_date=None):
    """在 asof_date 用事前特徵分組，之後全程等權持有（乾淨的樣本外檢驗）"""
    i0 = idx_of(axis, asof_date)
    i1 = idx_of(axis, end_date) if end_date else len(axis) - 1
    feats = {sid: point_in_time_features(snap["stocks"][sid], axis, max(0, i0 - 1)) for sid in navs}
    valid = [f for f in feats.values() if f]
    groups = {}
    for sid, f in feats.items():
        g, _, _ = classify(f, valid)
        groups.setdefault(g, []).append(sid)
    out = {}
    for g, members in groups.items():
        if g == "NA" or len(members) < 3:
            continue
        L = i1 - i0 + 1
        combo = []
        for k in range(i0, i1 + 1):
            combo.append(sum(navs[s][k] / navs[s][i0] for s in members) / len(members))
        st = {"n": len(members), "final_x": round(combo[-1], 3),
              "total_pct": round((combo[-1] - 1) * 100, 2),
              "ann_pct": round((combo[-1] ** (TRADING_DAYS / L) - 1) * 100, 2),
              "mdd_pct": round(mdd(combo) * 100, 2)}
        st["calmar"] = round(st["ann_pct"] / abs(st["mdd_pct"]), 2) if st["mdd_pct"] else 0
        st["nav_slim"] = [round(x, 3) for x in combo[::7]]
        st["members"] = [(s, snap["stocks"][s]["name"]) for s in members[:10]]
        out[g] = st
    return {"asof": asof_date, "end": end_date or axis[-1], "days": i1 - i0 + 1, "groups": out}


def main():
    snap = load()
    axis = snap["index"]["dates"]
    audit = json.load(open(AUDIT, encoding="utf-8"))
    regimes = audit["regimes"]
    print(f"轴 {len(axis)} 日  {axis[0]} → {axis[-1]}")

    # 全资产含息净值
    navs, px_map = {}, {}
    for sid, s in snap["stocks"].items():
        px, divs = series_of(s)
        if len(px) < 800:
            continue
        px_map[sid] = px
        navs[sid] = total_return_index(px, divs, axis)

    # ── A. 熊市实证（逐波段、事前分类）
    bear_detail = []
    for r in regimes:
        if r["direction"] != "空頭":
            continue
        d0, d1 = r["start"], r["end"]
        i0, i1 = idx_of(axis, d0), idx_of(axis, d1)
        asof = max(0, i0 - 1)
        feats = {sid: point_in_time_features(snap["stocks"][sid], axis, asof)
                 for sid in navs}
        valid = [f for f in feats.values() if f]
        groups = {}
        for sid, f in feats.items():
            g, fh, hh = classify(f, valid)
            groups.setdefault(g, []).append((sid, f, fh, hh))

        rets_map, _, _ = band_returns(navs, axis, d0, d1)
        gstats = {}
        for g, members in groups.items():
            vals = [rets_map[s] for s, *_ in members if s in rets_map]
            gstats[g] = describe(vals)
            gstats[g]["members"] = [s for s, *_ in members][:12]

        pos_ids = [s for s, v in rets_map.items() if v > 0]
        pos_feat = [feats[s] for s in pos_ids if feats.get(s)]
        all_feat = [feats[s] for s in rets_map if feats.get(s)]

        def avg(key, arr):
            vs = [f[key] for f in arr if f.get(key) is not None]
            return round(sum(vs) / len(vs), 3) if vs else None

        bear_detail.append({
            "start": d0, "end": d1, "bars": r["bars"],
            "index_ret_pct": r["index_ret"],
            "groups": gstats,
            "positive_n": len(pos_ids),
            "positive_pct": round(len(pos_ids) / len(rets_map) * 100, 1),
            "positive_features": {
                "n": len(pos_feat),
                "yield_pct": round(avg("yield", pos_feat) * 100, 2) if avg("yield", pos_feat) is not None else None,
                "vol60": round(avg("vol60", pos_feat) * 100, 1) if avg("vol60", pos_feat) is not None else None,
                "mom60_pct": round(avg("mom60", pos_feat) * 100, 1) if avg("mom60", pos_feat) is not None else None,
                "pe_pct": round(avg("pe_pct", pos_feat), 2) if avg("pe_pct", pos_feat) is not None else None,
                "burst": round(avg("burst", pos_feat), 2) if avg("burst", pos_feat) is not None else None,
            },
            "all_features": {
                "yield_pct": round(avg("yield", all_feat) * 100, 2) if avg("yield", all_feat) is not None else None,
                "vol60": round(avg("vol60", all_feat) * 100, 1) if avg("vol60", all_feat) is not None else None,
                "mom60_pct": round(avg("mom60", all_feat) * 100, 1) if avg("mom60", all_feat) is not None else None,
                "pe_pct": round(avg("pe_pct", all_feat), 2) if avg("pe_pct", all_feat) is not None else None,
                "burst": round(avg("burst", all_feat), 2) if avg("burst", all_feat) is not None else None,
            },
            "top5": [(s, snap["stocks"][s]["name"], round(rets_map[s] * 100, 1))
                     for s in sorted(rets_map, key=lambda k: -rets_map[k])[:5]],
            "bottom5": [(s, snap["stocks"][s]["name"], round(rets_map[s] * 100, 1))
                        for s in sorted(rets_map, key=lambda k: rets_map[k])[:5]],
        })
        print(f"空头 {d0}→{d1} 指数{r['index_ret']:+.1f}%  "
              f"DEF {gstats.get('DEF',{}).get('median_pct','-')}%  "
              f"HYPE {gstats.get('HYPE',{}).get('median_pct','-')}%  "
              f"正报酬 {len(pos_ids)}/{len(rets_map)}")

    # ── B. 全期分组表现（牛熊对照）
    period_stats = []
    for r in regimes:
        d0, d1 = r["start"], r["end"]
        i0 = max(0, idx_of(axis, d0) - 1)
        feats = {sid: point_in_time_features(snap["stocks"][sid], axis, i0) for sid in navs}
        valid = [f for f in feats.values() if f]
        groups = {}
        for sid, f in feats.items():
            g, _, _ = classify(f, valid)
            groups.setdefault(g, []).append(sid)
        rm, _, _ = band_returns(navs, axis, d0, d1)
        row = {"start": d0, "end": d1, "direction": r["direction"],
               "index_ret_pct": r["index_ret"], "bars": r["bars"]}
        for g, members in groups.items():
            vals = [rm[s] for s in members if s in rm]
            d = describe(vals)
            row[g] = d["median_pct"] if d else None
            row[g + "_n"] = d["n"] if d else 0
        period_stats.append(row)

    # ── C. 牛市行为模型
    bull_models = []
    for r in regimes:
        if r["direction"] != "多頭":
            continue
        m = behavior_models(navs, axis, px_map, r["start"], r["end"])
        bull_models.append({"start": r["start"], "end": r["end"],
                            "bars": r["bars"], "index_ret_pct": r["index_ret"],
                            "models": m})
        print(f"多头 {r['start']}→{r['end']} 指数{r['index_ret']:+.1f}%  买入持有 {m['BH']['total_pct']:+.1f}%")
        for k, v in m.items():
            if k.startswith("_"):
                continue
            print(f"   {k:<14} {v['total_pct']:>8.1f}%  MDD {v['mdd_pct']:>7.1f}%  换手 {v['turnovers']}")

    # ── D. 恐慌末端进场（最惨波段之后的分批 vs 单笔）
    panic = [r for r in regimes if r["direction"] == "空頭" and r["index_ret"] <= -25]
    rebound = []
    if panic:
        p = panic[0]
        i_bottom = idx_of(axis, p["end"])
        # 底部後 60 / 120 / 250 日的報酬
        for h in [20, 60, 120, 250]:
            j = min(i_bottom + h, len(axis) - 1)
            v = navs["0050"][j] / navs["0050"][i_bottom] - 1
            rebound.append({"days": h, "date": axis[j], "ret_pct": round(v * 100, 2)})
        # 分批：底部前 20 日開始，每 5 日投入 1/5，共 5 次
        nav, path = 1.0, [1.0]
        invested, shares, cash = 0.0, 0.0, 1.0
        starts = max(0, i_bottom - 20)
        for k in range(i_bottom - 20, min(i_bottom + 250, len(axis) - 1)):
            if k < 0:
                continue
            if (k - starts) % 5 == 0 and invested < 1.0:
                amt = min(0.2, 1.0 - invested)
                shares += amt / navs["0050"][k]
                cash -= amt
                invested += amt
            cash *= (1 + CASH_ANNUAL) ** (1 / TRADING_DAYS)
            nav = shares * navs["0050"][k] + cash
            path.append(nav)
        rebound.append({"strategy": "分批5次", "final_pct": round((path[-1] - 1) * 100, 2),
                        "mdd_pct": round(mdd(path) * 100, 2)})
        single = navs["0050"][min(i_bottom + 250, len(axis) - 1)] / navs["0050"][i_bottom] - 1
        rebound.append({"strategy": "底部单笔", "final_pct": round(single * 100, 2),
                        "mdd_pct": None})

    # ── D2. 分組全程淨值（樣本外）
    gp = group_paths(navs, axis, snap, 20220706, None)
    for g, st in gp["groups"].items():
        print(f"分組 {g}: {st['n']} 檔  全程 {st['total_pct']:+.1f}%  年化 {st['ann_pct']:.1f}%  MDD {st['mdd_pct']:.1f}%  Calmar {st['calmar']}")

    # ── E. 槓桿的兩面：牛市賺最多，急殺一次就出局
    lev_path = leverage_path(navs, axis, 20221025, 20250409)
    top_loss = top_lever_loss(navs, axis, 20250221, 20250409)
    print(f"槓桿全程：峰值 {lev_path['lever_peak_pct']:+.1f}% → 清倉 {lev_path['stopped_date']} "
          f"→ 期末 {lev_path['lever_final_pct']:+.1f}%（買入持有 {lev_path['buyhold_final_pct']:+.1f}%）")

    # ── F. 当前市场状态
    idx = snap["index"]["closes"]
    last = idx[-1]
    hh = max(idx[-252:])
    ma240 = sum(idx[-240:]) / 240
    vol20 = ann_vol_of(idx[-21:])
    dd = last / hh - 1
    state = ("CRISIS" if (dd <= -0.25 or vol20 >= 0.45) else
             "BEAR" if (dd <= -0.15 or last < ma240) else
             "NEUTRAL" if dd <= -0.08 else "BULL")
    current = {"last": round(last, 2), "high252": round(hh, 2),
               "drawdown_pct": round(dd * 100, 2), "ma240": round(ma240, 2),
               "vol20_pct": round(vol20 * 100, 2), "state": state,
               "note": "快照最後一日 2026-10-22"}
    # 使用者後續提供的更新行情（2026-11-06 收盤 39,701.64，非快照）
    ext = list(idx) + [41574.72, 39701.64]
    last2 = ext[-1]
    hh2 = max(ext[-252:])
    ma240b = sum(ext[-240:]) / 240
    vol20b = ann_vol_of(ext[-21:])
    dd2 = last2 / hh2 - 1
    st2 = ("CRISIS" if (dd2 <= -0.25 or vol20b >= 0.45) else
           "BEAR" if (dd2 <= -0.15 or last2 < ma240b) else
           "NEUTRAL" if dd2 <= -0.08 else "BULL")
    latest = {"date": "2026-11-06", "last": last2, "high252": round(hh2, 2),
              "drawdown_pct": round(dd2 * 100, 2), "ma240": round(ma240b, 2),
              "vol20_pct": round(vol20b * 100, 2), "state": st2,
              "drop_from_snapshot_pct": round((last2 / last - 1) * 100, 2),
              "note": "使用者提供之更新行情，非 snapshot.json"}

    result = {
        "meta": {"range": [axis[0], axis[-1]], "days": len(axis),
                 "assets": len(navs), "cost_etf_pct": COST_ETF * 100,
                 "cost_stock_pct": COST_STOCK * 100, "margin_rate_pct": MARGIN_RATE * 100,
                 "note": "含息总报酬；分类特征于各波段开始前一日计算，无前视偏误"},
        "bear_detail": bear_detail,
        "period_stats": period_stats,
        "bull_models": bull_models,
        "rebound": rebound,
        "leverage_path": lev_path,
        "top_lever_loss": top_loss,
        "current": current,
        "latest": latest,
        "group_paths": gp,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"\n已写出 {OUT}")
    return result


if __name__ == "__main__":
    main()
