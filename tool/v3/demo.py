# -*- coding: utf-8 -*-
"""V3.0 即刻執行示範：1000 元起始、0050、含成本回測 + 決策留痕 + HTML 報告。

完全是離線模擬：不連富邦、不讀憑證、不送任何真實委託。
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from trade_plan_engine import (FeeConfig, RiskConfig, StrategyConfig,
                               buy_cost, sell_proceeds, breakeven_move,
                               plan_buy_size, run_backtest, TPE)
from fubon_bridge import smoke_test

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "assets/data/snapshot.json"
OUT_JSON = Path("/workspace/v3_demo_result.json")
OUT_HTML = Path("/workspace/V3.0_交易计划试算.html")


def load_bars(symbol: str, n: int = 120):
    d = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    s = d["stocks"][symbol]
    pairs = list(zip(s["dates"], [float(c) for c in s["closes"]]))
    return pairs[-n:]


def esc(x) -> str:
    return html.escape(str(x))


def main():
    bars = load_bars("0050", 120)
    price = bars[-1][1]

    # --- 1. 費率情境比較（1000 元起始的關鍵） ---
    # 0050 是 ETF：賣出證交稅 1‰（非個股 3‰），由 for_symbol 自動判定
    fee_odd = FeeConfig.for_symbol("0050")                       # 富邦零股低收 1 元
    fee_bad = FeeConfig.for_symbol("0050", min_fee_odd=20)      # 若誤套整股 20 元低收
    plan = plan_buy_size(1000.0, price, fee_odd, prefer_odd=True)
    scenarios = []
    for name, cfg in (("零股低收 1 元（正確）", fee_odd),
                      ("誤用整股低收 20 元", fee_bad)):
        p = plan_buy_size(1000.0, price, cfg, prefer_odd=True)
        if not p:
            continue
        b = buy_cost(price, p.qty, cfg)
        s = sell_proceeds(price, p.qty, cfg)
        scenarios.append({
            "name": name, "qty": p.qty,
            "amount": round(b.amount, 2), "buy_fee": b.fee,
            "sell_fee": s.fee, "tax": s.tax,
            "round_trip_cost": round(b.fee + s.fee + s.tax, 2),
            "cost_ratio_pct": round((b.fee + s.fee + s.tax) / b.total * 100, 2),
            "breakeven_pct": round(breakeven_move(price, p.qty, cfg), 2),
            "cash_left": round(1000 - b.total, 2),
        })

    # --- 2. 決策引擎回測（模擬成交，非真錢） ---
    risk = RiskConfig(mode="backtest", initial_capital=1000.0,
                      max_order_amount=1000.0, max_daily_amount=2000.0,
                      max_orders_per_day=3, max_position_pct=0.98,
                      allow_round_lot=False, require_fresh_quote=True)
    strat = StrategyConfig(ma_window=20, buy_below_ma_pct=0.02,
                           add_below_ma_pct=0.05, take_profit_pct=0.06,
                           stop_loss_pct=0.05, trim_ratio=0.5,
                           max_add_times=1, periodic_every_n_bars=20)
    bt = run_backtest(bars, fee_odd, risk, strat, symbol="0050")

    # --- 3. dry_run（預設）：只留決策與風控，不改帳 ---
    dry = run_backtest(bars, fee_odd,
                       RiskConfig(mode="dry_run", initial_capital=1000.0,
                                  max_position_pct=0.98),
                       strat, symbol="0050")

    result = {
        "generated_at": __import__("datetime").datetime.now(TPE).isoformat(timespec="seconds"),
        "symbol": "0050", "price": price, "bars": len(bars),
        "first_date": bars[0][0], "last_date": bars[-1][0],
        "plan": plan.__dict__ if plan else None,
        "scenarios": scenarios,
        "backtest": {k: bt[k] for k in ("mode", "initial_capital", "equity",
                                        "net_pnl", "net_return_pct", "cash",
                                        "position_qty", "avg_cost", "realized_pnl")},
        "trades": bt["trades"], "rejected": bt["rejected"][:8],
        "intents": bt["intents"][:8],
        "dry_run_intents": dry["intents"][:5],
        "dry_run_trades": len(dry["trades"]),
        "bridge_smoke": smoke_test(),
    }
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- 4. HTML 報告 ---
    rows_sc = "".join(
        f"<tr><td>{esc(x['name'])}</td><td>{x['qty']}</td><td>{x['amount']}</td>"
        f"<td>{x['buy_fee']}</td><td>{x['sell_fee']}</td><td>{x['tax']}</td>"
        f"<td><b>{x['round_trip_cost']}</b></td><td>{x['cost_ratio_pct']}%</td>"
        f"<td class='up'><b>+{x['breakeven_pct']}%</b></td></tr>"
        for x in scenarios)

    rows_tr = "".join(
        f"<tr><td>{esc(t['date'])}</td><td>{esc(t['action'])}</td>"
        f"<td>{esc(t['purpose'])}</td><td>{t['qty']}</td><td>{t['price']}</td>"
        f"<td>{t['fee']}</td><td>{t['tax']}</td>"
        f"<td>{esc(t.get('realized_pnl','—'))}</td>"
        f"<td class='reason'>{esc(t['reason'])}</td></tr>"
        for t in bt["trades"]) or "<tr><td colspan='9'>本區間無成交（詳見決策留痕）</td></tr>"

    rows_it = "".join(
        f"<tr><td>{esc(i['date'])}</td><td>{esc(i['purpose'])}</td>"
        f"<td>{i['qty']} 股 @ {i['price']}</td>"
        f"<td>{'✅ 放行' if i['approved'] else '⛔ 攔下'}</td>"
        f"<td class='reason'>{esc('；'.join(i['gate_reasons']) or i['reason'])}</td></tr>"
        for i in bt["intents"][:8]) or "<tr><td colspan='5'>無決策</td></tr>"

    b = result["backtest"]
    pnl_cls = "up" if b["net_pnl"] >= 0 else "down"
    smoke = result["bridge_smoke"]

    OUT_HTML.write_text(f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>V3.0 富邦 API 交易計畫試算</title>
<style>
:root{{--bg:#f7f8fa;--card:#fff;--line:#e3e6ea;--ink:#1f2328;--soft:#57606a;--up:#c62828;--down:#2e7d32;--accent:#0969da}}
*{{box-sizing:border-box}}body{{margin:0;padding:28px 18px;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif;line-height:1.6}}
.wrap{{max-width:980px;margin:0 auto}}h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:17px;margin:26px 0 10px;border-left:4px solid var(--accent);padding-left:10px}}
.sub{{color:var(--soft);font-size:13px;margin-bottom:18px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:14px}}
.kpis{{display:flex;gap:12px;flex-wrap:wrap}}.kpi{{flex:1;min-width:150px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}}
.kpi .l{{font-size:12px;color:var(--soft)}}.kpi .v{{font-size:22px;font-weight:800;margin-top:2px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:8px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
th{{background:#f0f2f5;font-weight:700;white-space:nowrap}}.reason{{color:var(--soft);font-size:12px;min-width:220px}}
.up{{color:var(--up)}}.down{{color:var(--down)}}.warn{{background:#fff8e6;border:1px solid #f0c36d;border-radius:10px;padding:12px 14px;font-size:13.5px}}
.note{{font-size:13px;color:var(--soft)}}code{{background:#eef1f4;padding:1px 5px;border-radius:4px;font-size:12px}}
ul{{margin:6px 0 0 18px;padding:0}}li{{margin:4px 0;font-size:13.5px}}
</style></head><body><div class="wrap">
<h1>V3.0 富邦新一代 API · 交易計畫試算</h1>
<div class="sub">產生 {esc(result['generated_at'])}（台北）｜標的 0050 元大台灣50｜歷史收盤 {esc(result['first_date'])}～{esc(result['last_date'])} 共 {len(bars)} 根｜<b>全程離線模擬，未連券商、未送任何真實委託</b></div>

<div class="kpis">
<div class="kpi"><div class="l">起始資金</div><div class="v">NT$ 1,000</div></div>
<div class="kpi"><div class="l">期末總權益（已扣預估賣出成本）</div><div class="v">{b['equity']:.2f}</div></div>
<div class="kpi"><div class="l">淨損益（含所有交易成本）</div><div class="v {pnl_cls}">{b['net_pnl']:+.2f}</div></div>
<div class="kpi"><div class="l">報酬率</div><div class="v {pnl_cls}">{b['net_return_pct']:+.2f}%</div></div>
</div>

<h2>一、1000 元能買多少？手續費低收是關鍵</h2>
<div class="card">
<p class="note">收盤價 {price} 元，資金 1000 元買不起一張（需 106,900 元），只能走<b>盤中零股</b>。
引擎反推可買 <b>{esc(result['plan']['qty'] if result['plan'] else 0)} 股</b>，並預留手續費不超支。</p>
<table><thead><tr><th>情境</th><th>股數</th><th>價金</th><th>買手續費</th><th>賣手續費</th><th>證交稅</th><th>來回成本</th><th>佔比</th><th>打平需漲</th></tr></thead>
<tbody>{rows_sc}</tbody></table>
</div>
<div class="warn">⚠️ <b>最重要的結論</b>：若誤套整股「單筆最低 20 元」，1000 元小額來回成本會從不到 1% 暴增到 4% 以上，
還沒賺錢先賠手續費。所以 <b>1000 元起始必須走零股</b>。富邦營業員已於 2026-11-05 明確回覆「零股手續費最低收 1 元」；
0050 為 ETF，賣出證交稅 <b>1‰</b>（個股才是 3‰，2026-11-06 修正）。
手續費折扣（6 折／新戶 1.8 折）仍待向營業員確認後填進 <code>FeeConfig</code>。</div>

<h2>二、AI 決策規則（可解釋、每筆留理由）</h2>
<div class="card"><ul>
<li>建倉：收盤價跌破 20 日均線 2% → 買零股，目的「建倉」</li>
<li>加碼：再跌到均線下方 5% → 最多加碼 1 次，目的「加碼」</li>
<li>停利：相對含費成本 +6% → 減碼一半，目的「停利」</li>
<li>停損：相對含費成本 −5% → 全數出場，目的「停損」</li>
<li>定期定額：每 20 根 K 棒一期，目的「定期定額」</li>
<li>所有決策先過風控閘門：白名單、單筆 1000 元、每日 3 筆 / 2000 元、持股比重 98%、只准零股、報價需新於 5 分鐘</li>
</ul></div>

<h2>三、決策與風控留痕（前 8 筆）</h2>
<div class="card"><table><thead><tr><th>日期</th><th>目的</th><th>意圖</th><th>風控</th><th>理由／攔下原因</th></tr></thead><tbody>{rows_it}</tbody></table></div>

<h2>四、模擬成交明細（含成本損益）</h2>
<div class="card"><table><thead><tr><th>日期</th><th>方向</th><th>目的</th><th>股數</th><th>價格</th><th>手續費</th><th>稅</th><th>已實現損益</th><th>決策依據</th></tr></thead><tbody>{rows_tr}</tbody></table>
<p class="note">已實現損益合計 <b>{b['realized_pnl']:+.2f}</b> 元；期末持股 {b['position_qty']} 股，平均成本 {b['avg_cost']} 元／股（含買進手續費）。</p></div>

<h2>五、橋接層現況（尚未具備真實下單條件）</h2>
<div class="card"><ul>
<li>模式：<code>{esc(smoke['mode'])}</code>（預設 sandbox，官方測試環境，零真錢）</li>
<li>SDK 已安裝：<b>{'是' if smoke['sdk_installed'] else '否'}</b>｜Python 版本可支援：<b>{'是' if smoke['python_ok'] else '否'}</b></li>
<li>待補設定：<code>{esc(', '.join(smoke['config_errors']) or '無')}</code></li>
<li>測試環境：<code>wss://neoapitest.fbs.com.tw/TASP/XCPXWS</code>，官方測試包內含測試憑證與假庫存</li>
</ul></div>

<div class="warn">本頁所有數字皆為<b>歷史資料離線試算</b>，不是即時行情、不是投資建議、更不是成交紀錄。
真實下單必須完成：API 聲明書簽署 → 連線測試 → 隔日開通 → sandbox 全流程驗證 → 泰哥設定風控參數並逐筆授權。</div>
</div></body></html>""", encoding="utf-8")

    print(json.dumps({
        "plan": result["plan"], "scenarios": scenarios,
        "backtest": result["backtest"], "trade_count": len(bt["trades"]),
        "rejected_count": len(bt["rejected"]), "dry_run_trades": dry["trades"],
        "outputs": [str(OUT_JSON), str(OUT_HTML)],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
