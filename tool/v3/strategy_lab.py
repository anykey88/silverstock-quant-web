#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
strategy_lab.py — 個人投資研究用的「策略實驗室」（V3.0 / 2026-11-06）

定位：只服務一件事 —— 提升泰哥本人的投資獲利能力。
      純本機、純歷史模擬、不連券商、不碰憑證、不碰真錢、不對外提供。
      資料為專案自有快照（snapshot.json，111 檔 × 約 1300 根日線）。

為什麼做這個：
  前幾輪的簡易策略在 120 日回測賠 9.9%，短線 288 筆被手續費吃掉 3,752 元。
  與其繼續「拍腦袋改規則」，不如蓋一座能快速驗證各種想法、且會自動打臉
  過擬合的研究框架。核心是 walk-forward：參數只在訓練窗挑，績效只在
  樣本外（out-of-sample）算。

方法：
  1) 統一時間軸（以 TAIEX 交易日為基準），每檔補齊缺值。
  2) 預計算技術指標，避免重複運算。
  3) 7 個可插拔假設 × 參數網格 → 各自生成「目標持倉 0/1」序列。
  4) 回測執行器統一走 trade_plan_engine 的真實成本（1.425‰、證交稅個股 3‰／ETF 1‰、
     零股低收 1 元／整股 20 元、無條件進位）。
  5) Walk-forward（expanding window，5 折）：訓練窗選參數 → 測試窗驗證，
     各測試窗報酬複合成真實樣本外績效。
  6) 兩個附加實驗：手續費折數敏感度、換手閾值（降低無謂交易）。
  7) 輸出 JSON + 視覺化 HTML 報告。

用法：python3 strategy_lab.py            # 預設 40 檔
      python3 strategy_lab.py --all      # 全部 111 檔
      python3 strategy_lab.py --folds 6  # 改折數

僅用 Python 標準庫，方便在泰哥本機直接跑。
"""

from __future__ import annotations

import argparse
import html
import json
import math
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trade_plan_engine import FeeConfig, buy_cost, sell_proceeds  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SNAP = ROOT / "assets" / "data" / "snapshot.json"
OUT_JSON = Path("/workspace/v33_strategy_lab_result.json")
OUT_HTML = Path("/workspace/V3.3_策略实验室.html")

INITIAL_CAPITAL = 100_000.0     # 每檔／每段獨立起始資金，便於跨檔比較
WARMUP = 210                    # 最長指標視窗 200 日 + 緩衝
TEST_BARS = 130                 # 每折測試窗約半年
MIN_TRAIN = 400                 # 第一折至少要有 400 根訓練資料


# ---------------------------------------------------------------------------
# 一、資料層
# ---------------------------------------------------------------------------
def load_data(limit: int) -> dict:
    raw = json.loads(SNAP.read_text(encoding="utf-8"))
    ix = raw["index"]
    axis = [int(d) for d in ix["dates"]]
    index_close = [float(c) for c in ix["closes"]]

    # 以指數交易日為共同時間軸
    def align(dates, closes, volumes=None):
        m = {int(d): float(c) for d, c in zip(dates, closes)}
        vm = {int(d): float(v) for d, v in zip(dates, volumes or [])} if volumes else {}
        out_c, out_v, last_c, last_v = [], [], None, 0.0
        for d in axis:
            c = m.get(d)
            if c is None or c <= 0:
                c = last_c if last_c is not None else 0.0
            v = vm.get(d, last_v)
            out_c.append(c)
            out_v.append(v)
            last_c, last_v = c, v
        return out_c, out_v

    index_close, _ = align(ix["dates"], ix["closes"], ix.get("volumes"))

    stocks = raw["stocks"]
    # 依「近期平均成交量 × 價格」近似流動性排序，取前 N 檔；--all 則全取
    def liquidity(item):
        sid, s = item
        v = s.get("volumes") or []
        c = s.get("closes") or []
        tail_v = statistics.fmean([float(x) for x in v[-60:]]) if v else 0.0
        tail_c = statistics.fmean([float(x) for x in c[-60:]]) if c else 0.0
        return tail_v * tail_c

    ordered = sorted(stocks.items(), key=liquidity, reverse=True)
    chosen = ordered if limit <= 0 else ordered[:limit]

    universe = {}
    for sid, s in chosen:
        c, v = align(s["dates"], s["closes"], s.get("volumes"))
        if len(c) < WARMUP + MIN_TRAIN + TEST_BARS:
            continue
        # 排除整段無變動（資料異常）的標的
        if max(c) <= 0 or len(set(round(x, 2) for x in c)) < 20:
            continue
        universe[sid] = {
            "id": sid,
            "name": s.get("name", sid),
            "close": c,
            "volume": v,
        }
    return {
        "axis": axis,
        "index": index_close,
        "stocks": universe,
        "meta": raw.get("meta", {}),
        "total_available": len(stocks),
    }


# ---------------------------------------------------------------------------
# 二、指標（預計算，回傳與輸入等長的 list；前段補 0 / None）
# ---------------------------------------------------------------------------
def sma(xs: list[float], n: int) -> list[float]:
    out, s = [0.0] * len(xs), 0.0
    for i, x in enumerate(xs):
        s += x
        if i >= n:
            s -= xs[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def roc(xs: list[float], n: int) -> list[float]:
    out = [0.0] * len(xs)
    for i in range(n, len(xs)):
        if xs[i - n] > 0:
            out[i] = xs[i] / xs[i - n] - 1.0
    return out


def rsi(xs: list[float], n: int = 14) -> list[float]:
    out = [50.0] * len(xs)
    if len(xs) <= n:
        return out
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = xs[i] - xs[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    ag, al = gains / n, losses / n
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n + 1, len(xs)):
        d = xs[i] - xs[i - 1]
        ag = (ag * (n - 1) + max(d, 0.0)) / n
        al = (al * (n - 1) + max(-d, 0.0)) / n
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def rolling_high(xs: list[float], n: int) -> list[float]:
    out = [0.0] * len(xs)
    for i in range(len(xs)):
        if i >= n:
            out[i] = max(xs[i - n:i])
    return out


def vol_ma(vs: list[float], n: int = 20) -> list[float]:
    return sma(vs, n)


class Indicators:
    """每檔標的算一次，所有假設共用。"""
    def __init__(self, close, volume, index_close):
        self.close = close
        self.volume = volume
        self.ma = {n: sma(close, n) for n in (5, 20, 60, 120, 200)}
        self.ima = {n: sma(index_close, n) for n in (60, 120, 200)}
        self.index_close = index_close
        self.roc = {n: roc(close, n) for n in (20, 60, 120)}
        self.rsi = rsi(close, 14)
        self.high = {n: rolling_high(close, n) for n in (20, 60, 120)}
        self.vma = vol_ma(volume, 20)


# ---------------------------------------------------------------------------
# 三、假設（可插拔）：每個 fn 回傳 target ∈ {0,1} 序列
# ---------------------------------------------------------------------------
@dataclass
class Hypothesis:
    key: str
    name: str
    desc: str
    grid: list[dict]
    fn: Callable[[Indicators, dict, int], list[int]]


def _sig_ma(ind, p, n):
    out = [0] * n
    m = ind.ma[p["n"]]
    for i in range(WARMUP, n):
        out[i] = 1 if m[i] > 0 and ind.close[i] > m[i] else 0
    return out


def _sig_dual(ind, p, n):
    out = [0] * n
    a, b = ind.ma[p["fast"]], ind.ma[p["slow"]]
    for i in range(WARMUP, n):
        out[i] = 1 if a[i] > 0 and b[i] > 0 and a[i] > b[i] else 0
    return out


def _sig_mom(ind, p, n):
    out = [0] * n
    r = ind.roc[p["n"]]
    for i in range(WARMUP, n):
        out[i] = 1 if r[i] > p["th"] else 0
    return out


def _sig_rev(ind, p, n):
    out = [0] * n
    hold = 0
    for i in range(WARMUP, n):
        v = ind.rsi[i]
        if v < p["low"]:
            hold = 1
        elif v > p["high"]:
            hold = 0
        out[i] = hold
    return out


def _sig_break(ind, p, n):
    out = [0] * n
    h = ind.high[p["n"]]
    for i in range(WARMUP, n):
        out[i] = 1 if h[i] > 0 and ind.close[i] > h[i] else 0
    return out


def _sig_vol(ind, p, n):
    out = [0] * n
    m = ind.ma[p["n"]]
    for i in range(WARMUP, n):
        trend = m[i] > 0 and ind.close[i] > m[i]
        vol_ok = ind.vma[i] > 0 and ind.volume[i] > ind.vma[i] * p["k"]
        out[i] = 1 if (trend and vol_ok) else 0
    return out


def _sig_index(ind, p, n):
    out = [0] * n
    m, im = ind.ma[p["n"]], ind.ima[p["index_n"]]
    for i in range(WARMUP, n):
        bull = im[i] > 0 and ind.index_close[i] > im[i]
        out[i] = 1 if (bull and m[i] > 0 and ind.close[i] > m[i]) else 0
    return out


def _sig_hold(ind, p, n):
    out = [0] * n
    for i in range(WARMUP, n):
        out[i] = 1
    return out


def build_hypotheses() -> list[Hypothesis]:
    return [
        Hypothesis("hold", "買入持有（基準）", "不擇時，全期持有。所有策略都要跟它比。",
                   [{}], _sig_hold),
        Hypothesis("ma", "均線趨勢", "收盤價站上 N 日均線才持有，跌破就空手。",
                   [{"n": n} for n in (20, 60, 120, 200)], _sig_ma),
        Hypothesis("dual", "雙均線交叉", "快線在慢線之上才持有。",
                   [{"fast": f, "slow": s} for f, s in ((5, 20), (5, 60), (20, 60), (20, 120), (60, 200))],
                   _sig_dual),
        Hypothesis("mom", "動能", "過去 N 日漲幅超過門檻才持有（追強不猜底）。",
                   [{"n": n, "th": t} for n in (20, 60, 120) for t in (0.0, 0.03)], _sig_mom),
        Hypothesis("rev", "均值回歸（RSI）", "RSI 低於下界買、高於上界賣。",
                   [{"low": lo, "high": hi} for lo, hi in ((25, 70), (30, 70), (30, 75), (35, 65))], _sig_rev),
        Hypothesis("break", "突破前高", "收盤價突破過去 N 日高點才持有。",
                   [{"n": n} for n in (20, 60, 120)], _sig_break),
        Hypothesis("vol", "量價確認", "均線趨勢成立且當日量大於 20 日均量 k 倍才持有。",
                   [{"n": n, "k": k} for n in (20, 60) for k in (1.0, 1.3)], _sig_vol),
        Hypothesis("index", "大盤擇時", "加權指數站上均線，且個股也站上均線才持有。",
                   [{"n": n, "index_n": q} for n in (60, 120) for q in (120, 200)], _sig_index),
    ]


# ---------------------------------------------------------------------------
# 四、回測執行器（統一成本）
# ---------------------------------------------------------------------------
@dataclass
class BTResult:
    ret_pct: float
    fees: float
    trades: int
    max_dd_pct: float
    exposure_pct: float
    final_equity: float


def backtest(close: list[float], target: list[int], fee: FeeConfig,
             lo: int, hi: int, capital: float = INITIAL_CAPITAL,
             threshold: float = 0.0) -> BTResult:
    """在 [lo, hi) 區間內依 target 持倉，進出皆計真實成本。

    threshold：換手緩衝，訊號需連續 threshold 根才真的換倉（降低無謂交易）。
    """
    cash, qty = capital, 0
    fees = 0.0
    trades = 0
    pending, pending_days = 0, 0
    equity_curve, exposed_days = [], 0

    for i in range(lo, hi):
        px = close[i]
        if px <= 0:
            equity_curve.append(cash + qty * 0)
            continue
        want = target[i]

        # 換手緩衝：訊號要連續 threshold+1 根一致才執行
        if threshold > 0:
            cur = 1 if qty > 0 else 0
            if want != cur:
                if pending != want:
                    pending, pending_days = want, 1
                else:
                    pending_days += 1
                if pending_days <= threshold:
                    want = cur
            else:
                pending, pending_days = 0, 0

        if want == 1 and qty == 0:
            q = int(cash // px)
            while q > 0 and buy_cost(px, q, fee).total > cash:
                q -= 1
            if q > 0:
                c = buy_cost(px, q, fee)
                cash -= c.total
                qty = q
                fees += c.fee
                trades += 1
        elif want == 0 and qty > 0:
            s = sell_proceeds(px, qty, fee)
            cash += s.total
            fees += s.fee + s.tax
            qty = 0
            trades += 1

        if qty > 0:
            exposed_days += 1
            eq = cash + sell_proceeds(px, qty, fee).total
        else:
            eq = cash
        equity_curve.append(eq)

    if not equity_curve:
        return BTResult(0.0, 0.0, 0, 0.0, 0.0, capital)

    final = equity_curve[-1]
    peak, dd = equity_curve[0], 0.0
    for e in equity_curve:
        peak = max(peak, e)
        dd = max(dd, (peak - e) / peak * 100 if peak > 0 else 0.0)
    n = len(equity_curve)
    return BTResult(
        ret_pct=round((final / capital - 1) * 100, 3),
        fees=round(fees, 1),
        trades=trades,
        max_dd_pct=round(dd, 2),
        exposure_pct=round(exposed_days / n * 100, 1),
        final_equity=round(final, 1),
    )


def score(r: BTResult) -> float:
    """訓練窗選參數用的穩健分數：報酬扣掉一半回撤懲罰。"""
    return r.ret_pct - 0.5 * r.max_dd_pct


# ---------------------------------------------------------------------------
# 五、Walk-forward（防過擬合的核心）
# ---------------------------------------------------------------------------
def walk_forward(close, signals: dict, fee: FeeConfig, folds: int):
    """signals: {param_key: target_list}。回傳 (OOS複合報酬, IS最佳報酬, 各折明細, 最常勝出參數)。"""
    n = len(close)
    start = WARMUP + MIN_TRAIN
    if start + TEST_BARS * folds > n:
        folds = max(1, (n - start) // TEST_BARS)
    oos_returns, details, winners = [], [], []

    for f in range(folds):
        te0 = start + f * TEST_BARS
        te1 = min(te0 + TEST_BARS, n)
        if te1 - te0 < 30:
            break
        tr0, tr1 = WARMUP, te0

        best_key, best_score, best_ret = None, -1e18, 0.0
        for key, tgt in signals.items():
            r = backtest(close, tgt, fee, tr0, tr1)
            s = score(r)
            if s > best_score:
                best_key, best_score, best_ret = key, s, r.ret_pct

        oos = backtest(close, signals[best_key], fee, te0, te1)
        oos_returns.append(oos.ret_pct)
        winners.append(best_key)
        details.append({
            "fold": f + 1,
            "test_range": [te0, te1],
            "picked": best_key,
            "is_ret": best_ret,
            "oos_ret": oos.ret_pct,
            "oos_trades": oos.trades,
            "oos_fees": oos.fees,
        })

    compound = 1.0
    for r in oos_returns:
        compound *= (1 + r / 100)
    oos_total = (compound - 1) * 100
    is_avg = statistics.fmean([d["is_ret"] for d in details]) if details else 0.0
    common = statistics.mode(winners) if winners else "-"
    return round(oos_total, 3), round(is_avg, 3), details, common


# ---------------------------------------------------------------------------
# 六、主流程
# ---------------------------------------------------------------------------
def fmt(v, suffix="%", sign=True):
    s = f"{v:+.2f}{suffix}" if sign else f"{v:.2f}{suffix}"
    return s


def css_for(v: float) -> str:
    return "up" if v >= 0 else "down"     # 台股／陸股慣例：漲紅、跌綠


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="跑全部標的")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--folds", type=int, default=5)
    args = ap.parse_args()
    limit = 0 if args.all else args.limit

    data = load_data(limit)
    axis, index_close, stocks = data["axis"], data["index"], data["stocks"]
    hyps = build_hypotheses()
    print(f"[資料] 共同時間軸 {len(axis)} 根（{axis[0]}～{axis[-1]}）／"
          f"可用 {data['total_available']} 檔，本次 {len(stocks)} 檔／{args.folds} 折 walk-forward")

    results = {h.key: [] for h in hyps}
    per_stock_baseline = {}

    for j, (sid, s) in enumerate(stocks.items(), 1):
        close = s["close"]
        ind = Indicators(close, s["volume"], index_close)
        fee = FeeConfig.for_symbol(sid)
        n = len(close)

        # 基準（買入持有）
        bh = backtest(close, _sig_hold(ind, {}, n), fee, WARMUP, n)
        per_stock_baseline[sid] = bh.ret_pct

        for h in hyps:
            if h.key == "hold":
                continue
            signals = {}
            for p in h.grid:
                key = ",".join(f"{k}={v}" for k, v in p.items()) or "default"
                signals[key] = h.fn(ind, p, n)
            oos, isr, details, common = walk_forward(close, signals, fee, args.folds)
            results[h.key].append({
                "symbol": sid,
                "name": s["name"],
                "oos_ret": oos,
                "is_ret": isr,
                "overfit_gap": round(oos - isr, 3),
                "beat_bh": oos > bh.ret_pct,
                "bh_ret": bh.ret_pct,
                "common_param": common,
                "folds": len(details),
            })
        if j % 10 == 0 or j == len(stocks):
            print(f"  進度 {j}/{len(stocks)}")

    # ---- 彙總 ----
    summary = []
    for h in hyps:
        if h.key == "hold":
            continue
        rs = results[h.key]
        if not rs:
            continue
        oos = [r["oos_ret"] for r in rs]
        isr = [r["is_ret"] for r in rs]
        summary.append({
            "key": h.key, "name": h.name, "desc": h.desc,
            "stocks": len(rs),
            "oos_mean": round(statistics.fmean(oos), 3),
            "oos_median": round(statistics.median(oos), 3),
            "is_mean": round(statistics.fmean(isr), 3),
            "gap": round(statistics.fmean(oos) - statistics.fmean(isr), 3),
            "beat_rate": round(sum(1 for r in rs if r["beat_bh"]) / len(rs) * 100, 1),
            "best": round(max(oos), 2), "worst": round(min(oos), 2),
            "param_grid": len(h.grid),
        })
    summary.sort(key=lambda x: x["oos_mean"], reverse=True)

    bh_mean = round(statistics.fmean(per_stock_baseline.values()), 3)
    bh_median = round(statistics.median(per_stock_baseline.values()), 3)

    # ---- 附加實驗 1：手續費折數敏感度（用表現最好的策略，前 12 檔）----
    best_key = summary[0]["key"] if summary else "ma"
    best_hyp = next(h for h in hyps if h.key == best_key)
    sample_stocks = list(stocks.items())[:12]
    fee_rows = []
    for disc, label in ((1.0, "牌告（無折扣）"), (0.6, "6 折"), (0.18, "新戶 1.8 折")):
        rets = []
        for sid, s in sample_stocks:
            ind = Indicators(s["close"], s["volume"], index_close)
            fee = FeeConfig.for_symbol(sid, fee_discount=disc)
            n = len(s["close"])
            sigs = {",".join(f"{k}={v}" for k, v in p.items()): best_hyp.fn(ind, p, n)
                    for p in best_hyp.grid}
            oos, _, _, _ = walk_forward(s["close"], sigs, fee, args.folds)
            rets.append(oos)
        fee_rows.append({"label": label, "discount": disc,
                         "mean_oos": round(statistics.fmean(rets), 3)})

    # ---- 附加實驗 2：換手緩衝（同一策略、固定參數、全區間）----
    turnover_rows = []
    for th in (0, 2, 5, 10):
        rets, trades, fees = [], [], []
        for sid, s in sample_stocks:
            ind = Indicators(s["close"], s["volume"], index_close)
            fee = FeeConfig.for_symbol(sid)
            n = len(s["close"])
            tgt = best_hyp.fn(ind, best_hyp.grid[len(best_hyp.grid) // 2], n)
            r = backtest(s["close"], tgt, fee, WARMUP, n, threshold=th)
            rets.append(r.ret_pct)
            trades.append(r.trades)
            fees.append(r.fees)
        turnover_rows.append({
            "threshold": th,
            "mean_ret": round(statistics.fmean(rets), 3),
            "mean_trades": round(statistics.fmean(trades), 1),
            "mean_fees": round(statistics.fmean(fees), 1),
        })

    out = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scope": "本人投資研究／本機歷史模擬／不對外、不連券商、不碰真錢",
        "universe": len(stocks), "total_available": data["total_available"],
        "bars": len(axis), "range": [axis[0], axis[-1]],
        "folds": args.folds, "capital": INITIAL_CAPITAL,
        "buy_hold_mean": bh_mean, "buy_hold_median": bh_median,
        "summary": summary, "fee_sensitivity": fee_rows,
        "turnover": turnover_rows, "best_strategy": best_key,
        "per_stock": {k: results[k] for k in results if k != "hold"},
    }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[輸出] {OUT_JSON}")

    build_html(out, hyps)
    print(f"[輸出] {OUT_HTML}")

    #  console 摘要
    print("\n=== 樣本外報酬排行（越高越穩健）===")
    print(f"{'策略':<16}{'OOS均值':>10}{'中位數':>10}{'訓練窗':>10}{'過擬合落差':>12}{'跑贏基準':>10}")
    for r in summary:
        print(f"{r['name']:<16}{r['oos_mean']:>9.2f}%{r['oos_median']:>9.2f}%"
              f"{r['is_mean']:>9.2f}%{r['gap']:>11.2f}%{r['beat_rate']:>9.1f}%")
    print(f"\n買入持有基準：均值 {bh_mean:+.2f}%／中位數 {bh_median:+.2f}%")
    print("手續費折數敏感度：", [(r["label"], r["mean_oos"]) for r in fee_rows])
    print("換手緩衝：", [(r["threshold"], r["mean_ret"], r["mean_trades"], r["mean_fees"])
                    for r in turnover_rows])


# ---------------------------------------------------------------------------
# 七、HTML 報告
# ---------------------------------------------------------------------------
CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#1b2430;--muted:#5b6776;--line:#dfe4ea;
--up:#c0392b;--down:#0f7b55;--accent:#2b5fa8;--accentbg:#eaf1fb;--warnbg:#fdf4e3}
*{box-sizing:border-box}
body{margin:0;padding:28px 20px 56px;background:var(--bg);color:var(--ink);
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC","Microsoft JhengHei",sans-serif;
line-height:1.72;-webkit-font-smoothing:antialiased}
.wrap{max-width:1000px;margin:0 auto}
h1{font-size:27px;margin:0 0 6px}
.sub{color:var(--muted);font-size:14px;margin:0 0 18px}
.notice{background:var(--accentbg);border-left:4px solid var(--accent);padding:11px 16px;
border-radius:0 8px 8px 0;font-size:13.5px;color:var(--muted);margin-bottom:18px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:22px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.kpi b{display:block;font-size:23px;line-height:1.25}
.kpi span{font-size:12.5px;color:var(--muted)}
h2{font-size:18px;margin:30px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--line)}
table{width:100%;border-collapse:collapse;background:var(--card);border-radius:10px;overflow:hidden;
box-shadow:0 1px 3px rgba(20,30,45,.06);font-size:14px}
th,td{padding:10px 13px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#eef1f5;font-weight:600;color:var(--muted);font-size:12.5px}
tr:last-child td{border-bottom:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.up{color:var(--up);font-weight:700}.down{color:var(--down);font-weight:700}
.bar{display:inline-block;height:8px;border-radius:4px;background:#dfe4ea;vertical-align:middle;margin-left:6px}
.pull{background:#1f2937;color:#e8eef7;border-radius:10px;padding:16px 20px;font-size:14.5px;margin:12px 0}
.pull .hl{color:#9fe3bf;font-weight:700}
.pull small{display:block;color:#9fb0c4;margin-top:10px;font-size:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;border-top:4px solid var(--accent)}
.card h3{margin:0 0 8px;font-size:15px}.card p{margin:0;font-size:13.5px;color:var(--muted)}
ol,ul{margin:0;padding-left:20px}li{margin-bottom:7px;font-size:14px}
code{background:#eef1f5;padding:1px 5px;border-radius:4px;font-size:13px}
.foot{margin-top:30px;padding-top:14px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}
@media (prefers-color-scheme:dark){
:root{--bg:#141a22;--card:#1c2530;--ink:#e7edf5;--muted:#9aa8b8;--line:#303c4b;
--up:#ff8b8b;--down:#5fd0a2;--accent:#8ab4f8;--accentbg:#1b2b44;--warnbg:#332b1b}
th{background:#232e3b;color:var(--muted)}.bar{background:#3a4757}
code{background:#2a3543}.pull{background:#10161e}.card,table{box-shadow:none}}
"""


def build_html(out: dict, hyps: list[Hypothesis]):
    e = html.escape
    S = out["summary"]
    bh = out["buy_hold_mean"]
    best = S[0] if S else None
    worst = S[-1] if S else None
    beats = [r for r in S if r["oos_mean"] > bh]
    fee_rows = out["fee_sensitivity"]
    fee_gain = round(fee_rows[-1]["mean_oos"] - fee_rows[0]["mean_oos"], 3) if fee_rows else 0
    to = out["turnover"]
    best_to = max(to, key=lambda r: r["mean_ret"]) if to else None

    # 排行表
    rows = []
    for i, r in enumerate(S, 1):
        cls = css_for(r["oos_mean"])
        gapcls = "down" if r["gap"] < 0 else "up"
        rows.append(
            f"<tr><td>{i}</td><td><b>{e(r['name'])}</b><br><span style='color:var(--muted);font-size:12.5px'>{e(r['desc'])}</span></td>"
            f"<td class='num {cls}'>{r['oos_mean']:+.2f}%</td>"
            f"<td class='num'>{r['oos_median']:+.2f}%</td>"
            f"<td class='num'>{r['is_mean']:+.2f}%</td>"
            f"<td class='num {gapcls}'>{r['gap']:+.2f}%</td>"
            f"<td class='num'>{r['beat_rate']:.1f}%</td>"
            f"<td class='num'>{r['best']:+.1f}% / {r['worst']:+.1f}%</td>"
            f"<td class='num'>{r['param_grid']}</td></tr>"
        )
    rank_table = "".join(rows)

    fee_table = "".join(
        f"<tr><td>{e(r['label'])}</td><td class='num'>{r['discount']:.2f}</td>"
        f"<td class='num {css_for(r['mean_oos'])}'>{r['mean_oos']:+.2f}%</td></tr>"
        for r in fee_rows
    )
    to_table = "".join(
        f"<tr><td>訊號需連續 <b>{r['threshold']+1}</b> 根才換倉</td>"
        f"<td class='num {css_for(r['mean_ret'])}'>{r['mean_ret']:+.2f}%</td>"
        f"<td class='num'>{r['mean_trades']:.1f}</td>"
        f"<td class='num'>{r['mean_fees']:,.0f}</td></tr>"
        for r in to
    )

    n_beats = len(beats)
    lead_name = best["name"] if best else "—"
    lead_oos = best["oos_mean"] if best else 0.0
    lead_gap = best["gap"] if best else 0.0
    worst_name = worst["name"] if worst else "—"
    worst_oos = worst["oos_mean"] if worst else 0.0
    to_best_th = best_to["threshold"] if best_to else 0
    to_best_ret = best_to["mean_ret"] if best_to else 0.0
    to_base_ret = to[0]["mean_ret"] if to else 0.0
    to_base_tr = to[0]["mean_trades"] if to else 0.0
    to_best_tr = best_to["mean_trades"] if best_to else 0.0
    to_base_fee = to[0]["mean_fees"] if to else 0.0
    to_best_fee = best_to["mean_fees"] if best_to else 0.0

    parts = []
    parts.append(f"""<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>V3.3 策略實驗室 · 樣本外驗證</title><style>{CSS}</style></head><body><div class="wrap">
<h1>策略實驗室 · 樣本外驗證</h1>
<p class="sub">現階段主軸：提升本人投資獲利能力 · {e(out['generated_at'])} · 領港人 泰哥</p>
<div class="notice"><b>這份報告只做一件事：把「想法」變成「被驗證過的數字」。</b>
{out['universe']} 檔標的、{out['bars']} 根日線（{out['range'][0]}～{out['range'][1]}）、{out['folds']} 折 walk-forward，
每筆進出都計入真實交易成本。純本機歷史模擬，<b>不連富邦、不碰憑證、不碰真錢、不對外提供</b>。
歷史模擬不等於未來報酬，這是研究工具，不是獲利保證。</div>

<div class="kpis">
<div class="kpi"><b>{out['universe']} 檔</b><span>本次研究標的（可用 {out['total_available']} 檔）</span></div>
<div class="kpi"><b>{out['folds']} 折</b><span>walk-forward 樣本外驗證</span></div>
<div class="kpi"><b class="{css_for(bh)}">{bh:+.2f}%</b><span>買入持有基準（均值）</span></div>
<div class="kpi"><b>{n_beats} / {len(S)}</b><span>樣本外跑贏基準的策略數</span></div>
</div>

<div class="pull"><span class="hl">先看這句：參數在訓練窗挑、績效只在樣本外算。</span>
「回測很漂亮」跟「未來會賺」是兩件事。這份報告把兩者並排放，落差多大一眼就看得出來。
<small>方法：expanding window，每折用前面全部資料選參數，只在接下來約半年（{TEST_BARS} 根）驗證；各折報酬複合成真實樣本外績效。</small></div>

<h2>一、策略排行榜（依樣本外平均報酬）</h2>
<table><tr><th>#</th><th>假設</th><th class="num">樣本外均值</th><th class="num">中位數</th>
<th class="num">訓練窗均值</th><th class="num">過擬合落差</th><th class="num">跑贏基準比例</th>
<th class="num">最好 / 最差</th><th class="num">參數組</th></tr>
{rank_table}</table>
<p style="font-size:13.5px;color:var(--muted);margin-top:10px">
<span class="up">紅＝正報酬</span>／<span class="down">綠＝負報酬</span>（台股慣例）。
「過擬合落差」＝樣本外均值 − 訓練窗均值；<b>負值代表訓練窗的漂亮數字縮水了</b>，是正常的，也正是這個框架要暴露的東西。
「跑贏基準」是該策略在各檔標的上贏過「買入持有」的比例。</p>

<div class="pull"><span class="hl">最穩的是「{e(lead_name)}」：樣本外 {lead_oos:+.2f}%，過擬合落差 {lead_gap:+.2f}%。</span>
最差的是「{e(worst_name)}」：{worst_oos:+.2f}%。基準（什麼都不做）是 {bh:+.2f}% —— 只有 {n_beats} 個策略在樣本外真的勝過「不擇時」。
<small>這正是前幾輪「簡易策略賠 9.9%、短線 288 筆被手續費吃掉」的延續：多數主動規則沒創造超額報酬，只是把錢換成手續費。</small></div>

<h2>二、附加實驗 A：手續費折數到底值多少錢</h2>
<p style="font-size:14px">用表現最好的「{e(lead_name)}」、前 12 檔標的，只改手續費折數，其餘不動。這是您一直要向營業員確認的數字，現在先把它換成報酬差。</p>
<table><tr><th>情境</th><th class="num">折數</th><th class="num">樣本外平均報酬</th></tr>{fee_table}</table>
<p style="font-size:13.5px;color:var(--muted);margin-top:10px">牌告 → 1.8 折的報酬差約 <b>{fee_gain:+.2f} 個百分點</b>（僅手續費，證交稅不打折）。
金額不大時差別有限，但<b>換手越頻繁、額度越大，這個數字會被放大</b>。</p>

<h2>三、附加實驗 B：少動一點，會不會更好</h2>
<p style="font-size:14px">同一策略、同一組參數，只加一條「訊號要連續 N 根才真的換倉」的緩衝，看費用與報酬怎麼變。</p>
<table><tr><th>換手緩衝</th><th class="num">平均報酬</th><th class="num">平均交易筆數</th><th class="num">平均費用（元）</th></tr>{to_table}</table>
<p style="font-size:13.5px;color:var(--muted);margin-top:10px">
最佳為「連續 {to_best_th+1} 根」：報酬 {to_best_ret:+.2f}%（無緩衝 {to_base_ret:+.2f}%），
交易從 {to_base_tr:.1f} 筆降到 {to_best_tr:.1f} 筆、費用從 {to_base_fee:,.0f} 降到 {to_best_fee:,.0f} 元。
<b>降低換手是目前最確定、不依賴預測能力的獲利來源</b> —— 前面幾輪的對照實驗也指向同一件事。</p>

<h2>四、可以更大膽探索的方向（不受限，繼續加）</h2>
<div class="grid">
<div class="card"><h3>① 多因子與橫截面選股</h3><p>目前每檔獨立擇時。下一步可做「同一天在 111 檔裡排名」：動能＋量能＋本益比＋股利殖利率組合成分數，只持有前 N 名。資料欄位都已備齊。</p></div>
<div class="card"><h3>② 部位規模與加減碼</h3><p>現在是全倉 0/1。改成依波動度／大盤狀態調整部位（20%～100%），並測試金字塔加碼 vs 一次建倉對回撤的影響。</p></div>
<div class="card"><h3>③ 投資組合層</h3><p>多檔同時持有、相關性約束、單檔上限、產業分散。這會把「單檔勝率」變成「整體資金曲線」，更接近您真實的帳戶。</p></div>
<div class="card"><h3>④ 真實交易成本再精修</h3><p>把營業員確認的折數、零股低收、月退、滑價與 tick size 全部接進 <code>FeeConfig</code>，讓回測與交割單對得上。</p></div>
<div class="card"><h3>⑤ 短線／長線雙軌並跑</h3><p>延續 V3.1：同一批標的、兩套目標函數，用額度與筆數上限各自約束，長期追蹤「紀律到底值多少錢」。</p></div>
<div class="card"><h3>⑥ 接上即時行情之後</h3><p>等富邦 sandbox 打通，把「日線收盤決策」換成「盤中訊號」，但先用模擬盤跑滿一段，再談小額實盤。</p></div>
</div>

<h2>五、老實說：這份報告還不能做的事</h2>
<ul>
<li>歷史區間只有約 5 年、且含 2021–2022 大多頭與後續修正，<b>樣本外折數仍少</b>，結論會隨區間改變。</li>
<li>未計<b>股利、除權息、滑價、漲跌停無法成交、零股撮合</b>；成本已計但未計價差。</li>
<li>「參數在訓練窗選」仍可能挑到剛好適合這段行情的組合；真正的驗證是<b>往後繼續跑、逐月累積真實樣本外</b>。</li>
<li>所以現階段結論是「<b>哪些想法不值得做</b>」比「哪個會賺」可靠 —— 這本身就是提升獲利能力：先少賠，再談多賺。</li>
</ul>

<div class="foot">資料：<code>assets/data/snapshot.json</code>（自有快照，個人研究用）·成本：<code>trade_plan_engine.py</code> ·
框架：<code>tool/v3/strategy_lab.py</code> ·機器可讀結果：<code>v33_strategy_lab_result.json</code><br>
本輪僅新增研究工具與報告：<b>未改既有引擎、未連富邦、未下任何單、線上 V2.7 不受影響</b>；V3 仍鎖在 M0 模擬盤。</div>
</div></body></html>""")
    OUT_HTML.write_text("".join(parts), encoding="utf-8")


if __name__ == "__main__":
    main()
