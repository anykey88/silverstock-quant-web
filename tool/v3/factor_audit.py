# -*- coding: utf-8 -*-
"""V3.5 因素盤點實測：用現有 snapshot.json 檢查「還有哪些變因沒進模型」

領港人 2026-11-07 提問：牛市/熊市、選股條件、季節性、全世界股市走勢…
是不是還有其他因素？本檔只做「用現有資料能誠實測出來的」四件事：

  A. 牛熊波段  — 用 TAIEX 18% 反轉切波段，看買入持有在各段的表現
  B. 選股離散度 — 111 檔全區間報酬分布，對比「擇時」的影響量級
  C. 股息偏差  — 只用收盤價算報酬，漏掉多少（總報酬 vs 價格報酬）
  D. 季節性    — 月份效應 + 隨機安慰劑檢定（證明加因素易過擬合）

⚠️ 全部為歷史離線模擬、個人研究用；不是投資建議、不是成交紀錄。
   本檔不連券商、不讀憑證、不送任何委託。
"""
from __future__ import annotations

import json
import random
import statistics as st
from pathlib import Path

SNAPSHOT = Path("/workspace/silverstock_quant_web/assets/data/snapshot.json")
OUT_JSON = Path("/workspace/v35_factor_audit.json")

V31_SYMBOLS = ["0050", "2881", "2303", "2891", "2884"]  # V3.1 對照實驗挑的 5 檔


def pct(x: float) -> float:
    return x * 100.0


def ret_between(s: dict, d0: int, d1: int):
    """個股在 [d0,d1] 內首→末收盤價報酬；資料不足回 None。"""
    pairs = [(dt, c) for dt, c in zip(s["dates"], s["closes"])
             if d0 <= dt <= d1 and c and c > 0]
    if len(pairs) < 2:
        return None
    return pairs[-1][1] / pairs[0][1] - 1


def div_sum(s: dict, d0: int, d1: int) -> float:
    """區間內每股現金股利累加（已含分割回溯調整，見 meta.cleaning）。"""
    y0, y1 = d0 // 100, d1 // 100
    total = 0.0
    for item in s.get("dividends", []):
        ym = int(str(item[0]).replace("-", ""))
        if y0 <= ym <= y1:
            total += float(item[1])
    return total


def swings(dates: list, closes: list, thr: float = 0.18):
    """ZigZag：以 18% 反轉切出交替峰谷，回傳 [(idx, 'peak'/'trough'/'start'/'end')]。"""
    piv = [(0, "start")]
    direction = 0
    ext_i, ext_v = 0, closes[0]
    base = closes[0]
    for i, v in enumerate(closes):
        if direction == 0:
            if v / base - 1 >= thr:
                direction, ext_i, ext_v, piv = 1, i, v, piv + [(i, "trough")]
            elif v / base - 1 <= -thr:
                direction, ext_i, ext_v, piv = -1, i, v, piv + [(i, "peak")]
            continue
        if direction == 1:
            if v > ext_v:
                ext_i, ext_v = i, v
            elif v / ext_v - 1 <= -thr:
                piv.append((ext_i, "peak"))
                direction, ext_i, ext_v = -1, i, v
        else:
            if v < ext_v:
                ext_i, ext_v = i, v
            elif v / ext_v - 1 >= thr:
                piv.append((ext_i, "trough"))
                direction, ext_i, ext_v = 1, i, v
    piv.append((len(closes) - 1, "end"))
    # 過濾太短的波段（< 20 個交易日）避免雜訊
    out = [piv[0]]
    for p in piv[1:-1]:
        if p[0] - out[-1][0] >= 20:
            out.append(p)
    out.append(piv[-1])
    return out


def main():
    d = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    ix, stocks = d["index"], d["stocks"]
    dates, closes = ix["dates"], ix["closes"]
    d0, d1 = dates[0], dates[-1]

    # ---- A. 牛熊波段 ----------------------------------------------------
    piv = swings(dates, closes)
    regimes = []
    for a, b in zip(piv, piv[1:]):
        i0, i1 = a[0], b[0]
        sd, ed = dates[i0], dates[i1]
        ix_ret = closes[i1] / closes[i0] - 1
        rs = [r for s in stocks.values() if (r := ret_between(s, sd, ed)) is not None]
        regimes.append({
            "start": sd, "end": ed, "bars": i1 - i0,
            "direction": "空頭" if ix_ret < 0 else "多頭",
            "index_ret": round(pct(ix_ret), 2),
            "equal_weight_mean": round(pct(st.mean(rs)), 2) if rs else None,
            "equal_weight_median": round(pct(st.median(rs)), 2) if rs else None,
            "n_stocks": len(rs),
        })
    # 大盤全程最大回撤
    peak, mdd = closes[0], 0.0
    for c in closes:
        peak = max(peak, c)
        mdd = min(mdd, c / peak - 1)

    # ---- B. 選股離散度 --------------------------------------------------
    cross = []
    for sid, s in stocks.items():
        r = ret_between(s, d0, d1)
        if r is None:
            continue
        p0 = next(c for dt, c in zip(s["dates"], s["closes"]) if dt >= d0 and c > 0)
        dv = div_sum(s, d0, d1)
        cross.append({
            "symbol": sid, "name": s.get("name", ""), "industry": s.get("industry", ""),
            "price_ret": round(pct(r), 2),
            "div_yield_on_start": round(pct(dv / p0), 2) if p0 else 0.0,
            "total_ret_approx": round(pct(r) + pct(dv / p0), 2),
        })
    vals = sorted(x["price_ret"] for x in cross)

    def q(p):
        return round(vals[int(p * (len(vals) - 1))], 2)

    dispersion = {
        "n": len(vals), "min": round(vals[0], 2), "p25": q(.25),
        "median": q(.5), "p75": q(.75), "max": round(vals[-1], 2),
        "mean": round(st.mean(vals), 2), "stdev": round(st.pstdev(vals), 2),
        "positive_pct": round(100 * sum(1 for v in vals if v > 0) / len(vals), 1),
        "spread": round(vals[-1] - vals[0], 2),
    }
    # V3.1 挑的 5 檔在全體中的分位
    rank = {x["symbol"]: i for i, x in enumerate(
        sorted(cross, key=lambda z: z["price_ret"]))}
    v31_rank = [{"symbol": s,
                 "price_ret": next(x["price_ret"] for x in cross if x["symbol"] == s),
                 "percentile": round(100 * rank[s] / (len(cross) - 1), 1)}
                for s in V31_SYMBOLS if s in rank]
    # 產業分組
    by_ind = {}
    for x in cross:
        by_ind.setdefault(x["industry"] or "未分類", []).append(x["price_ret"])
    industry = sorted(
        [{"industry": k, "n": len(v), "mean_ret": round(st.mean(v), 2)}
         for k, v in by_ind.items() if len(v) >= 3],
        key=lambda z: -z["mean_ret"])

    # ---- C. 股息偏差 ----------------------------------------------------
    dy = sorted(x["div_yield_on_start"] for x in cross)
    dividend = {
        "median_5y": round(dy[len(dy) // 2], 2),
        "p25": round(dy[int(.25 * len(dy))], 2),
        "p75": round(dy[int(.75 * len(dy))], 2),
        "max": round(dy[-1], 2),
        "v31_mean": round(st.mean(
            x["div_yield_on_start"] for x in cross if x["symbol"] in V31_SYMBOLS), 2),
    }

    # ---- D. 季節性 + 安慰劑 ---------------------------------------------
    month_last = {}
    for dt, c in zip(dates, closes):
        month_last[dt // 100] = c
    mkeys = sorted(month_last)
    monthly = [(mkeys[i], month_last[mkeys[i]] / month_last[mkeys[i - 1]] - 1)
               for i in range(1, len(mkeys))]
    labels = [ym % 100 for ym, _ in monthly]
    vals_m = [r for _, r in monthly]
    groups = {}
    for l, v in zip(labels, vals_m):
        groups.setdefault(l, []).append(v)
    season = sorted(
        [{"month": m, "n": len(v), "mean": round(pct(st.mean(v)), 2),
          "positive_pct": round(100 * sum(1 for x in v if x > 0) / len(v), 1)}
         for m, v in groups.items()], key=lambda z: -z["mean"])

    def best_month(vs):
        g = {}
        for l, v in zip(labels, vs):
            g.setdefault(l, []).append(v)
        return max(st.mean(x) for x in g.values() if x)

    real_best = pct(best_month(vals_m))
    random.seed(7)
    sims = []
    for _ in range(2000):
        shuffled = vals_m[:]
        random.shuffle(shuffled)
        sims.append(pct(best_month(shuffled)))
    sims.sort()
    placebo = {
        "real_best_month": season[0]["month"],
        "real_best_mean": round(real_best, 2),
        "placebo_median_best": round(sims[len(sims) // 2], 2),
        "placebo_p95_best": round(sims[int(.95 * len(sims))], 2),
        "placebo_max_best": round(sims[-1], 2),
        "p_value_approx": round(sum(1 for x in sims if x >= real_best) / len(sims), 3),
        "n_months": len(monthly), "n_sim": len(sims),
    }

    out = {
        "generated_at": "2026-11-07",
        "range": [d0, d1], "n_stocks": len(stocks), "n_bars": len(dates),
        "index_start": closes[0], "index_end": closes[-1],
        "index_total_ret": round(pct(closes[-1] / closes[0] - 1), 2),
        "index_max_drawdown": round(pct(mdd), 2),
        "regimes": regimes, "dispersion": dispersion,
        "v31_rank": v31_rank, "industry": industry,
        "dividend": dividend, "seasonality": season, "placebo": placebo,
        "data_gap": {
            "has": ["TAIEX 加權指數(日)", "111 檔收盤價/成交量", "現金股利(111/111)",
                    "本益比序列(108/111)", "季 EPS(30/111)", "產業分類", "股票分割回溯調整"],
            "missing": ["國際指數(美股/費半/日韓/陸港股)", "匯率(USD/TWD、日圓)",
                        "利率(Fed/央行、債殖利率)", "外資/投信/自營商買賣超",
                        "融資融券餘額、當沖比", "選擇權未平倉、VIX/台指期貨基差",
                        "月營收/財報時間序列(僅 30 檔 EPS)", "除息日/除權日事件表",
                        "成分股調整、處置股、全額交割註記", "地緣政治/政策事件"],
        },
    }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    # ---- 摘要輸出 -------------------------------------------------------
    print("=== A. 牛熊波段（TAIEX 18% 反轉）===")
    for r in regimes:
        print(f"  {r['start']}→{r['end']} {r['direction']} | 指數 {r['index_ret']:+7.2f}% "
              f"| 111檔等權 {r['equal_weight_mean']:+7.2f}% | {r['bars']} 天")
    print(f"  全程指數 {out['index_total_ret']:+.2f}% | 最大回撤 {out['index_max_drawdown']:.2f}%")
    print("\n=== B. 選股離散度（全區間價格報酬）===")
    print(" ", dispersion)
    print("  V3.1 五檔分位:", v31_rank)
    print("  產業前3:", industry[:3], "| 後3:", industry[-3:])
    print("\n=== C. 股息偏差（5年累計股利/起始價）===")
    print(" ", dividend)
    print("\n=== D. 季節性 + 隨機安慰劑 ===")
    print("  最佳月份:", season[0], "| 最差:", season[-1])
    print(" ", placebo)
    print("\n→ JSON:", OUT_JSON)


if __name__ == "__main__":
    main()
