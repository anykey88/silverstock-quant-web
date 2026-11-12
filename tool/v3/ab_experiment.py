# -*- coding: utf-8 -*-
"""V3.1 雙軌策略 + AI 模擬盤 / 人工 / 買入持有 對照實驗

領港人 2026-11-06 12:30 指示：「AI 用模擬盤」。
=> 本檔 PAPER_ONLY = True，完全不連券商、不讀憑證、不送任何委託，
   用歷史收盤價做紙上撮合。零真錢、零授權需求，可即刻執行。

實驗設計（控制變因，只留「決策方式」這一個差異）：
  · 相同標的組合、相同起始股數、相同起始現金、相同行情區間、相同費率
  · 四條軌道同時跑：AI-短線 / AI-長線 / 人工 / 買入持有（基準）
  · 比較：淨損益、報酬率、總交易成本、交易次數、勝率、最大回撤、費用侵蝕

⚠️ 誠實聲明：
  1. 人工端若未提供真人交易紀錄，報告中的「人工」是**可解釋的行為模型示範**
     （追漲、延遲反應、過度交易、不執行停損），不是任何真人的實際績效。
     提供真人 CSV/JSON 後即可替換，見 ManualRecorder。
  2. 紙上撮合假設「收盤價全額成交」，實盤會有滑點、部分成交、零股流動性、
     漲跌停鎖死、交割款等；模擬結果必然偏樂觀。
  3. 「去除人的因素」去除的是情緒與執行不一致，**不是去除風險**；
     策略參數、標的與風控仍由人設定，且有過度擬合歷史的風險。
"""

from __future__ import annotations

import csv
import html
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from trade_plan_engine import (FeeConfig, buy_cost, sell_proceeds,
                               plan_buy_size, round_to_tick, TPE)

PAPER_ONLY = True

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "assets/data/snapshot.json"
OUT_JSON = Path("/workspace/v31_ab_result.json")
OUT_HTML = Path("/workspace/V3.1_AI模拟盘对照复盘.html")
MANUAL_INPUT = Path("/workspace/manual_trades.csv")   # 真人記錄放這裡（選配）

SYMBOLS = ["0050", "2881", "2303", "2891", "2884"]
N_BARS = 120
START_QTY = 100          # 每檔起始股數：四條軌道完全相同
START_CASH = 30_000.0    # 起始現金：四條軌道完全相同
PER_ORDER_BUDGET = 12_000.0

TRACK_COLORS = {"AI-短線": "#c62828", "AI-長線": "#0969da",
                "人工（行為模型）": "#e69500", "買入持有": "#57606a"}


# ---------------------------------------------------------------------------
# 資料
# ---------------------------------------------------------------------------

def load_bars(symbol: str, n: int = N_BARS) -> list[tuple[int, float]]:
    d = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    s = d["stocks"][symbol]
    return list(zip(s["dates"], [float(c) for c in s["closes"]]))[-n:]


def ma(v: list[float], n: int) -> Optional[float]:
    return sum(v[-n:]) / n if len(v) >= n else None


# ---------------------------------------------------------------------------
# 模擬盤帳本（PAPER ONLY）
# ---------------------------------------------------------------------------

@dataclass
class Pos:
    qty: int = 0
    avg_cost: float = 0.0      # 含買進手續費的每股成本
    held_bars: int = 0
    add_times: int = 0


@dataclass
class Track:
    name: str
    cash: float
    pos: dict[str, Pos]
    fee: FeeConfig
    trades: list[dict] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    fees_paid: int = 0
    wins: int = 0
    closed_trades: int = 0
    pending: list[tuple] = field(default_factory=list)   # 人工端延遲下單用

    def __post_init__(self):
        # 依標的自動判別證交稅：0050（ETF）1‰，其餘個股 3‰
        self.fees = {s: FeeConfig.for_symbol(s) for s in self.pos}

    def fee_for(self, sym: str) -> FeeConfig:
        return self.fees.get(sym, self.fee)

    def equity(self, prices: dict[str, float]) -> float:
        """現金 + 持股變現淨額（誠實扣除預估賣出成本）。"""
        v = self.cash
        for s, p in self.pos.items():
            if p.qty > 0:
                v += sell_proceeds(prices[s], p.qty, self.fee_for(s)).total
        return v

    def buy(self, date: int, sym: str, price: float, qty: int,
            purpose: str, reason: str):
        c = buy_cost(price, qty, self.fee_for(sym))
        if c.total > self.cash:
            return False
        p = self.pos[sym]
        p.avg_cost = (p.avg_cost * p.qty + c.total) / (p.qty + qty)
        p.qty += qty
        p.held_bars = 0
        if purpose == "加碼":
            p.add_times += 1
        self.cash -= c.total
        self.fees_paid += c.fee
        self.trades.append(dict(date=date, symbol=sym, action="Buy", purpose=purpose,
                                qty=qty, price=price, amount=c.amount, fee=c.fee,
                                tax=0, reason=reason))
        return True

    def sell(self, date: int, sym: str, price: float, qty: int,
             purpose: str, reason: str):
        p = self.pos[sym]
        q = min(qty, p.qty)
        if q <= 0:
            return False
        s = sell_proceeds(price, q, self.fee_for(sym))
        basis = p.avg_cost * q
        self.cash += s.total
        self.fees_paid += s.fee + s.tax
        self.closed_trades += 1
        if s.total - basis > 0:
            self.wins += 1
        p.qty -= q
        if p.qty == 0:
            p.avg_cost, p.add_times, p.held_bars = 0.0, 0, 0
        self.trades.append(dict(date=date, symbol=sym, action="Sell", purpose=purpose,
                                qty=q, price=price, amount=s.amount, fee=s.fee,
                                tax=s.tax, realized=round(s.total - basis, 2),
                                reason=reason))
        return True


# ---------------------------------------------------------------------------
# 三種決策來源
# ---------------------------------------------------------------------------

def ai_signal(kind: Literal["short", "long"], hist: list[tuple[int, float]],
              pos: Pos, idx: int) -> Optional[tuple[str, str, str, float]]:
    """回傳 (action, purpose, reason, 賣出比例或買進預算)。規則式、可解釋。"""
    closes = [c for _, c in hist]
    px = closes[-1]
    prev = closes[:-1]

    if kind == "short":
        m = ma(prev, 5)
        if m is None:
            return None
        dev = px / m - 1
        if pos.qty > 0:
            ret = px / pos.avg_cost - 1
            if ret <= -0.02:
                return ("Sell", "停損", f"短線虧損 {ret*100:.2f}% 達 −2% 停損線，紀律出場", 1.0)
            if ret >= 0.03:
                return ("Sell", "停利", f"短線獲利 {ret*100:.2f}% 達 +3% 停利，減碼一半", 0.5)
            if pos.held_bars >= 10:
                return ("Sell", "時間出場", f"持有 {pos.held_bars} 根 K 棒達短線上限，不留隔夜風險", 1.0)
        else:
            if dev <= -0.01:
                return ("Buy", "短線建倉", f"收盤 {px} 低於 5 日均線 {m:.2f} {abs(dev)*100:.2f}%，進場", 0)
    else:  # long
        m = ma(prev, 60)
        if m is None:
            return None
        dev = px / m - 1
        if pos.qty > 0:
            ret = px / pos.avg_cost - 1
            if ret <= -0.12:
                return ("Sell", "長線停損", f"虧損 {ret*100:.2f}% 觸及 −12% 長線底線", 1.0)
            if ret >= 0.20:
                return ("Sell", "長線停利", f"獲利 {ret*100:.2f}% 達 +20%，減碼 1/3 保留核心部位", 1 / 3)
        else:
            if dev <= -0.03:
                return ("Buy", "長線建倉", f"收盤 {px} 低於季線 {m:.2f} {abs(dev)*100:.2f}%，分批建立核心部位", 0)
        if pos.qty > 0 and dev <= -0.06 and pos.add_times < 2:
            return ("Buy", "加碼", f"續跌至季線下方 {abs(dev)*100:.2f}%，第 {pos.add_times+1} 次加碼", 0)
        if idx > 0 and idx % 20 == 0 and pos.qty == 0:
            return ("Buy", "定期定額", f"第 {idx} 期定期定額，不看價進場", 0)
    return None


def manual_signal(hist: list[tuple[int, float]], pos: Pos,
                  idx: int) -> Optional[tuple[str, str, int]]:
    """⚠️ 行為模型示範（非真人）：追漲、延遲、過度交易、不執行停損。

    真人資料請用 ManualRecorder 匯入；匯入後本函式不會被呼叫。
    """
    closes = [c for _, c in hist]
    if len(closes) < 7:
        return None
    r5 = closes[-1] / closes[-6] - 1
    if r5 > 0.03 and pos.qty == 0:
        return ("Buy", "追漲進場（訊號後 2 天才下單）", 2)
    if r5 < -0.04 and pos.qty > 0:
        return ("Sell", "恐慌殺出（訊號後 1 天才下單，且不停損只砍一半）", 1)
    if idx % 17 == 0 and pos.qty > 0:
        return ("Sell", "手癢換股／過度交易", 0)
    return None


class ManualRecorder:
    """真人交易紀錄匯入（CSV）：date,symbol,action,qty,price,note

    檔案放 /workspace/manual_trades.csv；有檔就完全取代行為模型。
    """
    def __init__(self, path: Path = MANUAL_INPUT):
        self.rows: dict[int, list[dict]] = {}
        self.loaded = False
        if path.is_file():
            with path.open(encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    d = int(str(r["date"]).replace("-", ""))
                    self.rows.setdefault(d, []).append({
                        "symbol": r["symbol"], "action": r["action"],
                        "qty": int(r["qty"]), "price": float(r["price"]),
                        "note": r.get("note", ""),
                    })
            self.loaded = True

    def take(self, date: int) -> list[dict]:
        return self.rows.get(date, [])


# ---------------------------------------------------------------------------
# 實驗主體
# ---------------------------------------------------------------------------

def max_drawdown(curve: list[float]) -> float:
    peak, mdd = curve[0] if curve else 0.0, 0.0
    for v in curve:
        peak = max(peak, v)
        if peak > 0:
            mdd = max(mdd, (peak - v) / peak)
    return mdd * 100


def run_experiment() -> dict:
    bars = {s: load_bars(s) for s in SYMBOLS}
    dates = [d for d, _ in bars[SYMBOLS[0]]]
    fee = FeeConfig()
    start_prices = {s: bars[s][0][1] for s in SYMBOLS}

    def make_track(name: str) -> Track:
        return Track(name=name, cash=START_CASH,
                     pos={s: Pos(qty=START_QTY, avg_cost=start_prices[s]) for s in SYMBOLS},
                     fee=fee)

    tracks = [make_track("AI-短線"), make_track("AI-長線"),
              make_track("人工（行為模型）"), make_track("買入持有")]
    by_name = {t.name: t for t in tracks}
    recorder = ManualRecorder()
    if recorder.loaded:
        tracks[2].name = "人工（真人紀錄）"
        by_name = {t.name: t for t in tracks}
        TRACK_COLORS["人工（真人紀錄）"] = "#e69500"

    for i in range(N_BARS):
        date = dates[i]
        prices = {s: bars[s][i][1] for s in SYMBOLS}

        for t in tracks:
            for p in t.pos.values():
                if p.qty > 0:
                    p.held_bars += 1

        # ---- 買入持有：完全不動 ----
        pass

        for kind, name in (("short", "AI-短線"), ("long", "AI-長線")):
            t = by_name[name]
            for s in SYMBOLS:
                hist = bars[s][:i + 1]
                sig = ai_signal(kind, hist, t.pos[s], i)
                if not sig:
                    continue
                action, purpose, reason, ratio = sig
                px = prices[s]
                if action == "Sell":
                    q = max(1, int(t.pos[s].qty * ratio)) if ratio < 1 else t.pos[s].qty
                    t.sell(date, s, round_to_tick(px), q, purpose, reason)
                else:
                    budget = min(PER_ORDER_BUDGET, t.cash)
                    plan = plan_buy_size(budget, px, fee, prefer_odd=False, session="盤中")
                    if plan:
                        t.buy(date, s, round_to_tick(px), plan.qty, purpose, reason)

        # ---- 人工端 ----
        man = by_name.get("人工（真人紀錄）") or by_name["人工（行為模型）"]
        # 先處理到期的延遲單
        due = [p for p in man.pending if p[0] <= i]
        man.pending = [p for p in man.pending if p[0] > i]
        for _, s, action, purpose, reason in due:
            px = prices[s]
            if action == "Buy":
                plan = plan_buy_size(min(PER_ORDER_BUDGET, man.cash), px, fee,
                                     prefer_odd=False, session="盤中")
                if plan:
                    man.buy(date, s, round_to_tick(px), plan.qty, purpose, reason)
            else:
                q = max(1, man.pos[s].qty // 2)
                man.sell(date, s, round_to_tick(px), q, purpose, reason)
        # 真人紀錄
        if recorder.loaded:
            for r in recorder.take(date):
                if r["action"].lower().startswith("b"):
                    man.buy(date, r["symbol"], r["price"], r["qty"], "真人下單", r["note"])
                else:
                    man.sell(date, r["symbol"], r["price"], r["qty"], "真人下單", r["note"])
        else:
            for s in SYMBOLS:
                sig = manual_signal(bars[s][:i + 1], man.pos[s], i)
                if sig:
                    action, reason, delay = sig
                    man.pending.append((i + delay, s, action, "人工行為", reason))

        for t in tracks:
            t.equity_curve.append(round(t.equity(prices), 2))

    last_prices = {s: bars[s][-1][1] for s in SYMBOLS}
    out_tracks = []
    for t in tracks:
        eq = t.equity_curve[-1]
        init = t.equity_curve[0] if t.equity_curve else eq
        out_tracks.append({
            "name": t.name, "initial_equity": round(init, 2), "final_equity": round(eq, 2),
            "net_pnl": round(eq - init, 2),
            "return_pct": round((eq / init - 1) * 100, 2),
            "cash": round(t.cash, 2), "trades": len(t.trades),
            "fees_paid": t.fees_paid,
            "fee_drag_pct": round(t.fees_paid / init * 100, 2),
            "win_rate": round(t.wins / t.closed_trades * 100, 1) if t.closed_trades else None,
            "max_drawdown_pct": round(max_drawdown(t.equity_curve), 2),
            "holdings": {s: p.qty for s, p in t.pos.items()},
            "equity_curve": t.equity_curve,
            "trade_log": t.trades,
        })

    return {
        "generated_at": datetime.now(TPE).isoformat(timespec="seconds"),
        "paper_only": PAPER_ONLY,
        "symbols": SYMBOLS, "bars": N_BARS,
        "first_date": dates[0], "last_date": dates[-1],
        "start_qty_per_symbol": START_QTY, "start_cash": START_CASH,
        "start_prices": start_prices, "last_prices": last_prices,
        "fee_config": {"fee_rate": fee.fee_rate, "tax_rate": fee.tax(),
                       "min_fee_odd": fee.min_fee_odd, "min_fee_round": fee.min_fee_round},
        "manual_source": "真人紀錄 CSV" if recorder.loaded else "行為模型示範（非真人）",
        "tracks": out_tracks,
    }


# ---------------------------------------------------------------------------
# HTML 復盤報告
# ---------------------------------------------------------------------------

def chart_svg(tracks: list[dict]) -> str:
    allv = [v for t in tracks for v in t["equity_curve"]]
    lo, hi = min(allv), max(allv)
    pad = (hi - lo) * 0.08 or 1
    lo, hi = lo - pad, hi + pad
    W, H, L, R, T, B = 820, 280, 58, 12, 14, 28
    def xy(i, v):
        return (L + i / (N_BARS - 1) * (W - L - R),
                T + (hi - v) / (hi - lo) * (H - T - B))
    grid = []
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        y = xy(0, v)[1]
        grid.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="#e6e9ed"/>'
                    f'<text x="{L-6}" y="{y+4:.1f}" font-size="10" fill="#8b949e" text-anchor="end">{v:,.0f}</text>')
    lines = []
    for t in tracks:
        pts = " ".join(f"{xy(i,v)[0]:.1f},{xy(i,v)[1]:.1f}" for i, v in enumerate(t["equity_curve"]))
        c = TRACK_COLORS.get(t["name"], "#57606a")
        lines.append(f'<polyline fill="none" stroke="{c}" stroke-width="2.2" points="{pts}"/>')
    legend = "".join(
        f'<span style="margin-right:16px;font-size:12px"><i style="display:inline-block;width:14px;height:3px;background:{TRACK_COLORS.get(t["name"],"#57606a")};vertical-align:middle;margin-right:5px"></i>{html.escape(t["name"])}</span>'
        for t in tracks)
    return (f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto">'
            + "".join(grid) + "".join(lines) +
            f'<text x="{L}" y="{H-6}" font-size="10" fill="#8b949e">第 1 天</text>'
            f'<text x="{W-R}" y="{H-6}" font-size="10" fill="#8b949e" text-anchor="end">第 {N_BARS} 天</text>'
            f'</svg><div style="margin-top:6px">{legend}</div>')


def build_html(r: dict) -> str:
    e = html.escape

    def wr(t) -> str:
        return "—" if t["win_rate"] is None else f"{t['win_rate']:.1f}%"

    rows = "".join(
        f"<tr><td><b>{e(t['name'])}</b></td><td>{t['final_equity']:,.0f}</td>"
        f"<td class='{'up' if t['net_pnl']>=0 else 'down'}'><b>{t['net_pnl']:+,.0f}</b></td>"
        f"<td class='{'up' if t['return_pct']>=0 else 'down'}'><b>{t['return_pct']:+.2f}%</b></td>"
        f"<td>{t['trades']}</td><td>{t['fees_paid']:,}</td><td>{t['fee_drag_pct']:.2f}%</td>"
        f"<td>{wr(t)}</td>"
        f"<td class='down'>{t['max_drawdown_pct']:.2f}%</td></tr>"
        for t in r["tracks"])

    kpis = "".join(
        f"<div class='kpi'><div class='l'>{e(t['name'])}</div>"
        f"<div class='v {'up' if t['net_pnl']>=0 else 'down'}'>{t['net_pnl']:+,.0f}</div>"
        f"<div class='l'>{t['return_pct']:+.2f}%</div></div>" for t in r["tracks"])

    # 逐軌交易明細（各取前 6 筆）
    details = []
    for t in r["tracks"]:
        body = "".join(
            f"<tr><td>{x['date']}</td><td>{e(x['symbol'])}</td><td>{e(x['action'])}</td>"
            f"<td>{e(x['purpose'])}</td><td>{x['qty']}</td><td>{x['price']}</td>"
            f"<td>{x['fee']+x['tax']}</td><td class='reason'>{e(x['reason'])}</td></tr>"
            for x in t["trade_log"][:6]) or "<tr><td colspan='8'>完全沒有交易（買入持有基準）</td></tr>"
        details.append(f"<h3>{e(t['name'])} · 前 6 筆</h3><table><thead><tr>"
                       f"<th>日期</th><th>標的</th><th>方向</th><th>目的</th><th>股數</th><th>價格</th><th>費用</th><th>依據</th>"
                       f"</tr></thead><tbody>{body}</tbody></table>")

    best = max(r["tracks"], key=lambda t: t["net_pnl"])
    hold = next(t for t in r["tracks"] if t["name"] == "買入持有")
    ai_best = max((t for t in r["tracks"] if t["name"].startswith("AI")),
                  key=lambda t: t["net_pnl"])
    man = next(t for t in r["tracks"] if t["name"].startswith("人工"))

    return f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>V3.1 AI 模擬盤 vs 人工 對照復盤</title>
<style>
:root{{--bg:#f7f8fa;--card:#fff;--line:#e3e6ea;--ink:#1f2328;--soft:#57606a;--up:#c62828;--down:#2e7d32;--accent:#0969da}}
*{{box-sizing:border-box}}body{{margin:0;padding:26px 18px;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif;line-height:1.6}}
.wrap{{max-width:1000px;margin:0 auto}}h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:17px;margin:26px 0 10px;border-left:4px solid var(--accent);padding-left:10px}}h3{{font-size:14px;margin:14px 0 6px}}
.sub{{color:var(--soft);font-size:13px;margin-bottom:16px}}
.banner{{background:#e8f0fe;border:1px solid #0969da;color:#0a4fa8;border-radius:10px;padding:12px 15px;font-weight:700;font-size:14px;margin-bottom:16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:14px}}
.kpis{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}}.kpi{{flex:1;min-width:145px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:11px 13px}}
.kpi .l{{font-size:12px;color:var(--soft)}}.kpi .v{{font-size:21px;font-weight:800;margin:2px 0}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}th{{background:#f0f2f5;font-weight:700;white-space:nowrap}}
.up{{color:var(--up)}}.down{{color:var(--down)}}.reason{{color:var(--soft);font-size:12px;min-width:200px}}
.warn{{background:#fff8e6;border:1px solid #f0c36d;border-radius:10px;padding:12px 14px;font-size:13.5px;margin-bottom:14px}}
.note{{font-size:13px;color:var(--soft)}}code{{background:#eef1f4;padding:1px 5px;border-radius:4px;font-size:12px}}
ul{{margin:6px 0 0 18px;padding:0}}li{{margin:5px 0;font-size:13.5px}}
.two{{display:flex;gap:14px;flex-wrap:wrap}}.two>div{{flex:1;min-width:280px}}
</style></head><body><div class="wrap">
<h1>V3.1 雙軌策略 · AI 模擬盤 vs 人工 對照復盤</h1>
<div class="sub">產生 {e(r['generated_at'])}（台北）｜歷史行情 {e(str(r['first_date']))}～{e(str(r['last_date']))} 共 {r['bars']} 個交易日｜5 檔標的：{e(', '.join(r['symbols']))}</div>

<div class="banner">🛡️ AI 端為 <b>模擬盤（PAPER ONLY）</b>：不連券商、不讀憑證、不送任何委託、零真錢。不需簽授權書即可完整跑對照實驗。</div>

<h2>一、控制變因（只留「決策方式」一個差異）</h2>
<div class="card"><ul>
<li>相同標的：{e(', '.join(r['symbols']))}；相同起始股數：<b>每檔 {r['start_qty_per_symbol']} 股</b>；相同起始現金：<b>NT$ {r['start_cash']:,.0f}</b></li>
<li>相同行情區間、相同收盤價、相同費率（買賣手續費 1.425‰、賣出證交稅個股 3‰／ETF 0050 為 1‰、零股低收 1 元／整股 20 元）</li>
<li>四條軌道同時跑：<b>AI-短線</b>（5 日均線、+3% 停利、−2% 停損、持有 ≤10 根 K 棒）／<b>AI-長線</b>（季線 60 日、+20% 停利、−12% 停損、定期定額、最多加碼 2 次）／<b>人工</b>／<b>買入持有</b>（完全不動的基準）</li>
<li>人工端資料來源：<b>{e(r['manual_source'])}</b>{' — 提供真人 CSV 後即自動替換' if '行為模型' in r['manual_source'] else ''}</li>
</ul></div>

<h2>二、結果比較</h2>
<div class="kpis">{kpis}</div>
<div class="card"><table><thead><tr><th>軌道</th><th>期末權益</th><th>淨損益</th><th>報酬率</th><th>交易筆數</th><th>總費用</th><th>費用拖累</th><th>勝率</th><th>最大回撤</th></tr></thead><tbody>{rows}</tbody></table>
<p class="note">權益已誠實扣除「若現在賣出」的預估手續費與證交稅；費用拖累 = 累計費用 ÷ 起始權益。</p></div>

<h2>三、權益曲線</h2>
<div class="card">{chart_svg(r['tracks'])}</div>

<h2>四、復盤結論（自動歸因）</h2>
<div class="card"><ul>
<li>本期間最佳：<b>{e(best['name'])}</b>（{best['net_pnl']:+,.0f} 元／{best['return_pct']:+.2f}%）。</li>
<li>AI 兩軌最佳：<b>{e(ai_best['name'])}</b>（{ai_best['return_pct']:+.2f}%）vs 買入持有基準（{hold['return_pct']:+.2f}%）—— <b>{'紀律有超額' if ai_best['return_pct']>hold['return_pct'] else '這段行情裡，頻繁決策反而輸給「什麼都不做」'}</b>。這正是對照實驗最該看的一欄。</li>
<li>人工端（{e(r['manual_source'])}）：報酬 {man['return_pct']:+.2f}%、交易 {man['trades']} 筆、費用 {man['fees_paid']:,} 元、最大回撤 {man['max_drawdown_pct']:.2f}%。</li>
<li>費用侵蝕：交易最頻繁的軌道累計費用最高；小額資金下手續費低收會讓成本非線性放大（見 V3.0 試算：1000 元來回成本 0.52%～4.17%）。</li>
</ul></div>

<h2>五、逐軌決策留痕（可解釋、可稽核）</h2>
<div class="card">{''.join(details)}</div>

<h2>六、這份實驗要學的「投資風險」</h2>
<div class="two">
<div class="card"><b>模擬盤教得會的</b><ul>
<li><b>紀律的價值</b>：同一套規則不因心情改，停損確實執行</li>
<li><b>交易成本會吃掉獲利</b>：次數越多，費用拖累越大</li>
<li><b>追高殺跌的代價</b>：延遲反應 + 反向進出</li>
<li><b>回撤感受</b>：最大回撤比報酬率更貼近真實壓力</li>
<li><b>基準的重要性</b>：沒跑贏「買入持有」，紀律就沒創造價值</li>
</ul></div>
<div class="card"><b>模擬盤教不會的（必須實盤才知道）</b><ul>
<li><b>滑點與部分成交</b>：假設收盤價全額成交，實盤未必</li>
<li><b>零股流動性</b>：想賣不一定賣得掉</li>
<li><b>漲跌停鎖死</b>：訊號出現也下不了單</li>
<li><b>交割款與資金排程</b>：T+2、圈存、扣款失敗</li>
<li><b>情緒</b>：看到真錢虧損時，人會想關掉系統</li>
</ul></div></div>

<div class="warn">⚠️ <b>「去除人的因素」要精準理解</b>：去掉的是<b>情緒與執行不一致</b>，不是去掉風險。
策略參數、標的、風控仍由人設定；規則是從歷史歸納的，有<b>過度擬合</b>風險，也擋不住黑天鵝。
本頁所有數字皆為<b>歷史資料紙上試算</b>，不是即時行情、不是真人績效、不是投資建議。</div>

<h2>七、要換成真人對照，請給我這個檔</h2>
<div class="card"><p class="note">把另一位交易人的實際成交紀錄存成 <code>/workspace/manual_trades.csv</code>，
格式如下（日期、代號、方向、股數、成交價、備註）：</p>
<pre style="background:#f4f6f8;padding:10px;border-radius:8px;font-size:12px;overflow:auto">date,symbol,action,qty,price,note
20260803,0050,Buy,100,105.5,看到新聞加碼
20260820,2881,Sell,50,160.0,先獲利了結</pre>
<p class="note">放好後重跑 <code>python3 tool/v3/ab_experiment.py</code>，人工軌道會自動改用真人紀錄，
行為模型不再被呼叫。若要兩人都用模擬盤，也可給我第二份 AI 參數，我開第五條軌道。</p></div>
</div></body></html>"""


def main():
    r = run_experiment()
    OUT_JSON.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_HTML.write_text(build_html(r), encoding="utf-8")
    print(json.dumps({
        "paper_only": r["paper_only"], "manual_source": r["manual_source"],
        "period": [r["first_date"], r["last_date"]],
        "tracks": [{k: t[k] for k in ("name", "net_pnl", "return_pct", "trades",
                                      "fees_paid", "max_drawdown_pct")}
                   for t in r["tracks"]],
        "outputs": [str(OUT_JSON), str(OUT_HTML)],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
