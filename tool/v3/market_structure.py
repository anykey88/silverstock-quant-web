# -*- coding: utf-8 -*-
"""
V4.1 個股印證與市場結構引擎
===========================
回答泰哥四件事，全部用 111 檔台股 5 年日線（含息、含成本）實測：

  A. 把 V3.7 選股原則 / V3.8 四層桶 / V3.9 分組 / V4.0 狀態機
     套到「具體股票」上，逐一印證或舉反例（含衝突案例）。
  B. 交易量／換手頻繁中找買賣時機：量比的分組統計與量價四象限。
  C. 指數大漲大跌 / 產業齊漲跌 / 個股走勢突出：每日報酬三分解，
     判別市場結構狀態並給應對。
  D. 短線 vs 長線兩套參數、自動交易對應（規則表，不回測）。

誠實紀律：
  - volumes 單位是「張」，沒有流通股數 → 無法算真實換手率，只用「量比」代理。
  - 量能分組是描述性統計，20 日報酬視窗重疊，不可當策略績效。
  - 結構分解用「事後橫截面」判別當日狀態，不用來預測隔日。
  - 「選最強產業／選贏家」僅作事後上限，不宣稱可執行。

執行：cd tool/v3 && python3 market_structure.py
輸出：v41_structure_result.json
"""
import json
import math
import os
import statistics
import bisect
from collections import defaultdict

from asset_allocation import (
    load, series_of, total_return_index, mdd, ann_vol,
    FEE, TAX_ETF, TRADING_DAYS,
)
from principles import screen
from bear_market import point_in_time_features, classify

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "v41_structure_result.json")
BEAR_JSON = os.path.join(ROOT, "v39_bear_result.json")

PERIODS = [
    {"dir": "空頭", "start": 20210601, "end": 20220706, "label": "2021/06–2022/07 慢熊"},
    {"dir": "空頭", "start": 20220706, "end": 20221025, "label": "2022/07–2022/10 空頭"},
    {"dir": "多頭", "start": 20221025, "end": 20240711, "label": "2022/10–2024/07 多頭一"},
    {"dir": "空頭", "start": 20240711, "end": 20250221, "label": "2024/07–2025/02 震盪"},
    {"dir": "空頭", "start": 20250221, "end": 20250409, "label": "2025/02–2025/04 急殺"},
    {"dir": "多頭", "start": 20250409, "end": 20261022, "label": "2025/04–2026/10 多頭二"},
]

# 案例股：刻意涵蓋「通過原則」「違反原則」「衝突」「指數核心」「高息」「炒作」
CASE_IDS = ["0050", "0056", "00878", "2330", "2317", "2412", "3045", "4904",
            "1102", "2891", "2890", "2382", "2357", "2618", "1605", "8908",
            "2227", "1795", "2454", "2884"]


def idx_of(axis, d):
    i = bisect.bisect_right(axis, d) - 1
    return max(0, min(i, len(axis) - 1))


def band_ret(nav, axis, d0, d1):
    i0, i1 = idx_of(axis, d0), idx_of(axis, d1)
    if i1 <= i0 or nav[i0] <= 0:
        return None
    return round((nav[i1] / nav[i0] - 1) * 100, 2)


# ══════════════════════════════════════════════════════════════════
# A. 個股案例庫：原則判定 vs 實際績效
# ══════════════════════════════════════════════════════════════════
def suggested_layer(sid, s, p, group):
    """把 V3.8 四層桶邏輯映射到單一個股（示範規則，不是回測結論）"""
    ind = s.get("industry", "")
    if sid == "0050":
        return "L2 指數核心", "市場基準，永不擇時"
    if sid in ("0056", "00878"):
        return "L1 高股息", "現金流安全墊"
    if group == "HYPE":
        return "排除／僅 L3 ≤1%", "炒作組：−15% 無條件砍、不攤平"
    if not p or not p.passed:
        return "排除", "未通過 V3.7 五層漏斗"
    # V3.8 核心層要低波動；深回撤／高波動一律降到衛星層
    if (abs(p.mdd_pct or 0) > 40) or ((p.vol_pct or 0) > 30):
        return "L3 衛星 ≤5%", f"MDD {p.mdd_pct}%／波動 {p.vol_pct}% 過高，不進核心層"
    yld = p.yield_pct or 0
    if yld >= 3.5:
        return "L1 高股息", f"殖利率 {yld:.2f}% 且通過漏斗"
    if (p.adv_yi or 0) >= 50:
        return "L2 核心候選", "流動性極高，可作核心衛星"
    return "L2／L3 邊界", "通過漏斗但殖利率偏低，單檔不超過 5%"


def build_cases(snap, navs, axis, picks, final, groups):
    pmap = {p.sid: p for p in picks}
    score_map = {p.sid: p.score for p in final}
    out = []
    for sid in CASE_IDS:
        if sid not in snap["stocks"]:
            continue
        s = snap["stocks"][sid]
        p = pmap.get(sid)
        nav = navs[sid]
        px, _ = series_of(s)
        vols = s.get("volumes") or []
        # 量比均值（近 60 日）
        rv = []
        for i in range(max(20, len(vols) - 60), len(vols)):
            base = sum(vols[i - 20:i]) / 20
            if base > 0:
                rv.append(vols[i] / base)
        rec = {
            "sid": sid, "name": s["name"], "industry": s.get("industry", ""),
            "close": round(s["closes"][-1], 2),
            "passed_v37": bool(p and p.passed),
            "v37_note": "ETF 不適用個股漏斗，直接歸核心層" if s.get("industry") == "ETF" else "",
            "score_v37": score_map.get(sid),
            "fail_reasons": (p.fail_reason if p else []),
            "group_v39": groups.get(sid, "NA"),
            "adv_yi": p.adv_yi if p else None,
            "pe": p.pe if p else None,
            "yield_pct": p.yield_pct if p else None,
            "vol_pct": p.vol_pct if p else None,
            "mdd_price_pct": p.mdd_pct if p else None,
            "ret5y_price_pct": p.ret5y_pct if p else None,
            "avg_rvol_60": round(sum(rv) / len(rv), 2) if rv else None,
            "rvol_gt2_pct": round(sum(1 for x in rv if x > 2) / len(rv) * 100, 1) if rv else None,
            "total_return_5y_pct": round((nav[-1] / nav[0] - 1) * 100, 2),
            "mdd_total_pct": round(mdd(nav) * 100, 2),
            "ann_vol_pct": round(ann_vol(nav) * 100, 2),
        }
        rec["layer"], rec["layer_reason"] = suggested_layer(sid, s, p, groups.get(sid, "NA"))
        rec["bands"] = {q["label"]: band_ret(nav, axis, q["start"], q["end"])
                        for q in PERIODS}
        # 樣本外：2022/07/06 起（V3.9 分組時點）
        i0 = idx_of(axis, 20220706)
        rec["oos_20220706_pct"] = round((nav[-1] / nav[i0] - 1) * 100, 2) if nav[i0] > 0 else None
        rec["crash_30d_pct"] = band_ret(nav, axis, 20250221, 20250409)
        out.append(rec)
    return out


# ══════════════════════════════════════════════════════════════════
# B. 量能／換手代理：量比分組與量價四象限
# ══════════════════════════════════════════════════════════════════
def volume_analysis(snap, navs, axis, groups, idx):
    """volumes 單位「張」，無流通股數 → 用 量比 = 當日量 / 前 20 日均量。"""
    buckets = defaultdict(lambda: {"n": 0, "d0": [], "d1": [], "d5": [], "d20": [], "ex20": []})
    quad = defaultdict(lambda: {"n": 0, "d5": [], "d20": [], "vol20": [], "ex20": []})
    group_rvol = defaultdict(list)
    inter = defaultdict(lambda: {"n": 0, "ex20": [], "f20": []})
    n = len(axis)
    # 同池等權基準：衡量「這檔相對同池其他股票」，比 TAIEX 公平
    allnav = list(navs.values())
    ew = [sum(x[i] / x[0] for x in allnav) / len(allnav) for i in range(n)]

    for sid, s in snap["stocks"].items():
        if sid not in navs or len(s.get("volumes") or []) < 100:
            continue
        nav = navs[sid]
        vols = s["volumes"]
        # volumes 與 nav 對齊：用日期索引
        vmap = dict(zip(s["dates"], vols))
        dates = s["dates"]
        # 前 20 日均量（用該股自身序列，避免前視）
        vser = [vmap.get(d, 0) for d in dates]
        for i in range(20, min(len(dates), n)):
            base = sum(vser[i - 20:i]) / 20
            if base <= 0 or vser[i] <= 0:
                continue
            r = vser[i] / base
            d = dates[i]
            gi = idx_of(axis, d)
            if gi + 20 >= n:
                break
            r0 = nav[gi] / nav[gi - 1] - 1
            f1 = nav[gi + 1] / nav[gi] - 1
            f5 = nav[gi + 5] / nav[gi] - 1
            f20 = nav[gi + 20] / nav[gi] - 1
            f20_ew = ew[gi + 20] / ew[gi] - 1 if ew[gi] > 0 else 0.0
            ex20 = f20 - f20_ew
            v20 = statistics.pstdev(
                [nav[gi + k + 1] / nav[gi + k] - 1 for k in range(20)
                 if gi + k + 1 < n and nav[gi + k] > 0]) * math.sqrt(TRADING_DAYS)

            if r < 0.7:
                b = "① <0.7 極縮"
            elif r < 1.0:
                b = "② 0.7–1.0"
            elif r < 1.5:
                b = "③ 1.0–1.5"
            elif r < 2.0:
                b = "④ 1.5–2.0"
            elif r < 3.0:
                b = "⑤ 2.0–3.0"
            else:
                b = "⑥ >3.0 爆量"
            z = buckets[b]
            z["n"] += 1
            z["d0"].append(r0); z["d1"].append(f1)
            z["d5"].append(f5); z["d20"].append(f20); z["ex20"].append(ex20)

            qk = ("量增" if r >= 1.5 else "量平縮") + "／" + ("價漲" if r0 > 0 else "價跌")
            q = quad[qk]
            q["n"] += 1
            q["d5"].append(f5); q["d20"].append(f20); q["vol20"].append(v20)
            q["ex20"].append(ex20)

            # 量能 × 趨勢交互：MA20 只用截至當日的資料
            ma20 = sum(nav[gi - 19:gi + 1]) / 20 if gi >= 19 else None
            if ma20 and ma20 > 0:
                ik = ("放量" if r >= 1.5 else "平量") + "／" + \
                     ("站上MA20" if nav[gi] >= ma20 else "跌破MA20")
                iz = inter[ik]
                iz["n"] += 1; iz["ex20"].append(ex20); iz["f20"].append(f20)

            g = groups.get(sid, "NA")
            if g in ("DEF", "MID", "HYPE"):
                group_rvol[g].append(r)

    def avg(xs):
        return round(sum(xs) / len(xs) * 100, 3) if xs else None

    brows = []
    for k in sorted(buckets):
        z = buckets[k]
        brows.append({"bucket": k, "n": z["n"],
                      "same_day_pct": avg(z["d0"]), "next_day_pct": avg(z["d1"]),
                      "fwd5_pct": avg(z["d5"]), "fwd20_pct": avg(z["d20"]),
                      "win20_pct": round(sum(1 for x in z["d20"] if x > 0) / len(z["d20"]) * 100, 1) if z["d20"] else None,
                      "excess20_pct": avg(z["ex20"]),
                      "excess_win_pct": round(sum(1 for x in z["ex20"] if x > 0) / len(z["ex20"]) * 100, 1) if z["ex20"] else None})
    qrows = []
    for k in sorted(quad):
        z = quad[k]
        qrows.append({"quad": k, "n": z["n"], "fwd5_pct": avg(z["d5"]),
                      "fwd20_pct": avg(z["d20"]),
                      "win20_pct": round(sum(1 for x in z["d20"] if x > 0) / len(z["d20"]) * 100, 1) if z["d20"] else None,
                      "fwd20_vol_pct": round(sum(z["vol20"]) / len(z["vol20"]) * 100, 1) if z["vol20"] else None,
                      "excess20_pct": avg(z["ex20"])})
    irows = []
    for k in sorted(inter):
        z = inter[k]
        irows.append({"cond": k, "n": z["n"], "fwd20_pct": avg(z["f20"]),
                      "excess20_pct": avg(z["ex20"]),
                      "excess_win_pct": round(sum(1 for x in z["ex20"] if x > 0) / len(z["ex20"]) * 100, 1) if z["ex20"] else None})
    grows = []
    for g in ("DEF", "MID", "HYPE"):
        xs = group_rvol.get(g, [])
        if xs:
            grows.append({"group": g, "n": len(xs),
                          "avg_rvol": round(sum(xs) / len(xs), 2),
                          "gt2_pct": round(sum(1 for x in xs if x > 2) / len(xs) * 100, 1),
                          "gt3_pct": round(sum(1 for x in xs if x > 3) / len(xs) * 100, 1)})
    return {
        "buckets": brows, "quadrants": qrows, "interaction": irows, "group_rvol": grows,
        "benchmark": "同池 111 檔等權含息報酬（非 TAIEX），超額＝個股20日報酬 − 等權20日報酬",
        "note": "量比＝當日成交量(張)/前20日均量；無流通股數，非真實換手率。分組為描述性統計，20日視窗重疊，非策略績效。",
    }


# ══════════════════════════════════════════════════════════════════
# C. 市場結構三分解：指數 / 產業 / 個股
# ══════════════════════════════════════════════════════════════════
def structure_analysis(snap, navs, axis):
    """每日把橫截面報酬拆成三種力量：
       市場 |R_mkt| ／ 產業間離散 between ／ 產業內(個股特異)離散 within
       用平方占比判別當日由誰主導，純事後描述，不用來預測隔日。"""
    idx = snap["index"]["closes"]
    ind_of = {sid: s.get("industry", "") for sid, s in snap["stocks"].items()}
    # ETF 與樣本太少的產業不計入產業效應
    by_ind = defaultdict(list)
    for sid, ind in ind_of.items():
        if ind and ind != "ETF" and sid in navs:
            by_ind[ind].append(sid)

    daily = []
    for i in range(1, len(axis)):
        if idx[i - 1] <= 0:
            continue
        rm = idx[i] / idx[i - 1] - 1
        rets = {}
        for sid, nav in navs.items():
            if nav[i - 1] > 0:
                rets[sid] = nav[i] / nav[i - 1] - 1
        if len(rets) < 60:
            continue
        ind_means, within_sq = {}, []
        for ind, members in by_ind.items():
            xs = [rets[m] for m in members if m in rets]
            if len(xs) >= 3:
                ind_means[ind] = sum(xs) / len(xs)
                within_sq.append(statistics.pvariance(xs))
        if len(ind_means) < 5:
            continue
        between = statistics.pstdev(list(ind_means.values())) if len(ind_means) > 1 else 0.0
        within = math.sqrt(sum(within_sq) / len(within_sq)) if within_sq else 0.0
        market = abs(rm)
        den = market ** 2 + between ** 2 + within ** 2
        sm = market ** 2 / den if den else 0
        sb = between ** 2 / den if den else 0
        sw = within ** 2 / den if den else 0
        if sm >= 0.50 or (market >= 0.015 and sm >= 0.40):
            state = "指數主導"
        elif sb >= sw * 1.15:
            state = "產業主導"
        else:
            state = "個股主導"
        up = sum(1 for v in rets.values() if v > 0) / len(rets) * 100
        xs = sorted(rets.values())
        spread = (xs[int(len(xs) * 0.95)] - xs[int(len(xs) * 0.05)]) * 100
        ind_lo = min(ind_means, key=ind_means.get)
        ind_hi = max(ind_means, key=ind_means.get)
        daily.append({
            "date": axis[i], "rm_pct": round(rm * 100, 2),
            "market": round(market * 100, 3), "between": round(between * 100, 3),
            "within": round(within * 100, 3),
            "share_mkt": round(sm, 3), "share_ind": round(sb, 3), "share_idio": round(sw, 3),
            "state": state, "up_pct": round(up, 1),
            "spread_pp": round(spread, 2),  # P95−P5 穩健極差
            "ind_hi": ind_hi, "ind_hi_pct": round(ind_means[ind_hi] * 100, 2),
            "ind_lo": ind_lo, "ind_lo_pct": round(ind_means[ind_lo] * 100, 2),
            "ind_gap_pp": round((ind_means[ind_hi] - ind_means[ind_lo]) * 100, 2),
        })

    cnt = defaultdict(int)
    for d in daily:
        cnt[d["state"]] += 1
    total = len(daily)
    states = []
    for k in ("指數主導", "產業主導", "個股主導"):
        ds = [d for d in daily if d["state"] == k]
        if not ds:
            continue
        states.append({
            "state": k, "n": len(ds), "pct": round(len(ds) / total * 100, 1),
            "avg_abs_index_pct": round(sum(abs(d["rm_pct"]) for d in ds) / len(ds), 2),
            "avg_up_pct": round(sum(d["up_pct"] for d in ds) / len(ds), 1),
            "avg_spread_pp": round(sum(d["spread_pp"] for d in ds) / len(ds), 2),
            "avg_ind_gap_pp": round(sum(d["ind_gap_pp"] for d in ds) / len(ds), 2),
            "avg_share_mkt": round(sum(d["share_mkt"] for d in ds) / len(ds), 2),
            "avg_share_ind": round(sum(d["share_ind"] for d in ds) / len(ds), 2),
            "avg_share_idio": round(sum(d["share_idio"] for d in ds) / len(ds), 2),
        })
    # 各波段結構占比
    segs = []
    for q in PERIODS:
        i0, i1 = idx_of(axis, q["start"]), idx_of(axis, q["end"])
        ds = [d for d in daily if i0 <= idx_of(axis, d["date"]) <= i1]
        c = defaultdict(int)
        for d in ds:
            c[d["state"]] += 1
        segs.append({"label": q["label"], "dir": q["dir"], "n": len(ds),
                     "指數主導_pct": round(c["指數主導"] / len(ds) * 100, 1) if ds else 0,
                     "產業主導_pct": round(c["產業主導"] / len(ds) * 100, 1) if ds else 0,
                     "個股主導_pct": round(c["個股主導"] / len(ds) * 100, 1) if ds else 0,
                     "avg_up_pct": round(sum(d["up_pct"] for d in ds) / len(ds), 1) if ds else 0,
                     "avg_ind_gap_pp": round(sum(d["ind_gap_pp"] for d in ds) / len(ds), 2) if ds else 0})
    # 漲跌家數三態（直接對應「指數齊漲跌 / 產業輪動 / 個股突出」）
    breadth = []
    for lo, hi, label in ((0, 20, "齊跌（上漲檔<20%）"),
                          (20, 80, "分歧（20–80%）"),
                          (80, 101, "齊漲（上漲檔≥80%）")):
        ds = [d for d in daily if lo <= d["up_pct"] < hi]
        if not ds:
            continue
        breadth.append({
            "label": label, "n": len(ds), "pct": round(len(ds) / total * 100, 1),
            "avg_index_pct": round(sum(d["rm_pct"] for d in ds) / len(ds), 2),
            "avg_abs_index_pct": round(sum(abs(d["rm_pct"]) for d in ds) / len(ds), 2),
            "avg_ind_gap_pp": round(sum(d["ind_gap_pp"] for d in ds) / len(ds), 2),
            "avg_spread_pp": round(sum(d["spread_pp"] for d in ds) / len(ds), 2),
            "avg_share_mkt": round(sum(d["share_mkt"] for d in ds) / len(ds), 2),
            "avg_share_ind": round(sum(d["share_ind"] for d in ds) / len(ds), 2),
            "avg_share_idio": round(sum(d["share_idio"] for d in ds) / len(ds), 2),
        })
    # 急殺段的齊跌天數
    crash = [q for q in PERIODS if "急殺" in q["label"]][0]
    ci0, ci1 = idx_of(axis, crash["start"]), idx_of(axis, crash["end"])
    crash_days = [d for d in daily if ci0 <= idx_of(axis, d["date"]) <= ci1]
    crash_breadth = {
        "n_days": len(crash_days),
        "down80_n": sum(1 for d in crash_days if d["up_pct"] < 20),
        "down50_n": sum(1 for d in crash_days if d["up_pct"] < 50),
        "avg_up_pct": round(sum(d["up_pct"] for d in crash_days) / len(crash_days), 1) if crash_days else 0,
        "avg_ind_gap_pp": round(sum(d["ind_gap_pp"] for d in crash_days) / len(crash_days), 2) if crash_days else 0,
    }

    # 典型案例日
    def top(k, key, rev=True, m=5):
        xs = [d for d in daily if d["state"] == k]
        xs = sorted(xs, key=lambda d: d[key], reverse=rev)[:m]
        return [{"date": d["date"], "index_pct": d["rm_pct"], "up_pct": d["up_pct"],
                 "spread_pp": d["spread_pp"], "ind_gap_pp": d["ind_gap_pp"],
                 "ind_hi": d["ind_hi"], "ind_hi_pct": d["ind_hi_pct"],
                 "ind_lo": d["ind_lo"], "ind_lo_pct": d["ind_lo_pct"]} for d in xs]
    examples = {
        "指數主導_大跌": top("指數主導", "rm_pct", False),
        "指數主導_大漲": top("指數主導", "rm_pct", True),
        "產業主導_差距最大": top("產業主導", "ind_gap_pp", True),
        "個股主導_離散最大": top("個股主導", "spread_pp", True),
    }
    # 後續 5/20 日指數報酬（描述性）
    fwd = []
    date_pos = {d: i for i, d in enumerate(axis)}
    for k in ("指數主導", "產業主導", "個股主導"):
        ds = [d for d in daily if d["state"] == k]
        f5, f20 = [], []
        for d in ds:
            i = date_pos[d["date"]]
            if i + 20 < len(idx):
                f5.append(idx[i + 5] / idx[i] - 1)
                f20.append(idx[i + 20] / idx[i] - 1)
        fwd.append({"state": k, "fwd5_index_pct": round(sum(f5) / len(f5) * 100, 2) if f5 else None,
                    "fwd20_index_pct": round(sum(f20) / len(f20) * 100, 2) if f20 else None,
                    "fwd20_win_pct": round(sum(1 for x in f20 if x > 0) / len(f20) * 100, 1) if f20 else None})
    return {
        "n_days": total, "states": states, "segments": segs,
        "breadth": breadth, "crash_breadth": crash_breadth,
        "examples": examples, "forward_index": fwd,
        "note": "事後橫截面分解：market=|指數報酬|、between=產業平均報酬的橫截面標準差、within=產業內標準差均值；以平方占比判主導。不用於預測隔日。",
    }


def main():
    snap = load()
    axis = snap["index"]["dates"]
    navs = {}
    for sid, s in snap["stocks"].items():
        px, divs = series_of(s)
        if len(px) >= 800:
            navs[sid] = total_return_index(px, divs, axis)
    print(f"資產 {len(navs)} 檔、{len(axis)} 日")

    picks, final = screen(snap)
    print(f"V3.7 漏斗通過 {len(final)} 檔")

    # V3.9 分組（2022/07/06 事前特徵）
    i0 = idx_of(axis, 20220706)
    feats = {sid: point_in_time_features(snap["stocks"][sid], axis, i0 - 1) for sid in navs}
    valid = [f for f in feats.values() if f]
    groups = {}
    for sid, f in feats.items():
        g, _, _ = classify(f, valid)
        groups[sid] = g
    from collections import Counter
    print("分組:", dict(Counter(groups.values())))

    print("\nA. 個股案例庫…")
    cases = build_cases(snap, navs, axis, picks, final, groups)
    for c in cases[:6]:
        print(f"  {c['sid']} {c['name']:<6} 通過{c['passed_v37']} 分{c['score_v37']} "
              f"組{c['group_v39']:<5} 含息5年{c['total_return_5y_pct']:>7.1f}% 急殺{c['crash_30d_pct']:>6.1f}% → {c['layer']}")

    print("\nB. 量能分組…")
    vol = volume_analysis(snap, navs, axis, groups, snap["index"]["closes"])
    for r in vol["buckets"]:
        print(f"  {r['bucket']:<12} n={r['n']:<6} 當日{r['same_day_pct']:>7}% 次日{r['next_day_pct']:>7}% "
              f"20日{r['fwd20_pct']:>7}% 勝率{r['win20_pct']}%")
    for r in vol["quadrants"]:
        print(f"  {r['quad']:<12} n={r['n']:<6} 20日{r['fwd20_pct']:>7}% 超額{r['excess20_pct']:>7}% 勝率{r['win20_pct']}% 後續波動{r['fwd20_vol_pct']}%")
    print("  量能×趨勢：")
    for r in vol["interaction"]:
        print(f"  {r['cond']:<18} n={r['n']:<6} 20日{r['fwd20_pct']:>7}% 超額{r['excess20_pct']:>7}% 跑贏率{r['excess_win_pct']}%")

    print("\nC. 市場結構三分解…")
    st = structure_analysis(snap, navs, axis)
    for r in st["states"]:
        print(f"  {r['state']}: {r['pct']}% 日數  上漲檔{r['avg_up_pct']}%  "
              f"個股離散{r['avg_spread_pp']}pp  產業差距{r['avg_ind_gap_pp']}pp")
    for s in st["segments"]:
        print(f"  {s['label']:<24} 指數{s['指數主導_pct']:>5}% 產業{s['產業主導_pct']:>5}% 個股{s['個股主導_pct']:>5}%")
    for b in st["breadth"]:
        print(f"  {b['label']:<20} {b['pct']:>5}% 日數  指數{b['avg_index_pct']:+.2f}%  產業差{b['avg_ind_gap_pp']:.2f}pp  個股離散{b['avg_spread_pp']:.2f}pp")
    print(f"  急殺段 {st['crash_breadth']['n_days']} 日中，齊跌(上漲<20%) {st['crash_breadth']['down80_n']} 日、平均上漲檔 {st['crash_breadth']['avg_up_pct']}%")

    result = {
        "meta": {"title": "V4.1 個股印證與市場結構", "universe": len(navs),
                 "range": snap["meta"]["range"], "bars": len(axis),
                 "note": "含息總報酬；量比為成交量代理，非真實換手率；結構為事後橫截面分解"},
        "periods": PERIODS,
        "cases": cases,
        "v37_pass_list": [{"sid": p.sid, "name": p.name, "industry": p.industry,
                           "score": p.score, "yield_pct": p.yield_pct,
                           "pe": p.pe, "mdd_pct": p.mdd_pct} for p in final],
        "volume": vol,
        "structure": st,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"\n已輸出 {OUT}")


if __name__ == "__main__":
    main()
