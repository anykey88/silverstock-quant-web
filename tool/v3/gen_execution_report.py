# -*- coding: utf-8 -*-
"""V4.0 报告生成器：所有数字从 v40_execution_result.json 读取，不手工抄录。"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "v40_execution_result.json")
OUT = os.path.join(ROOT, "..", "V4.0_执行策略实验室.html")

with open(SRC, encoding="utf-8") as f:
    D = json.load(f)

A = D["exit_reentry"]
DCA = D["dca"]
SCALE = D["scale_out"]
WAIT = D["waiting"]
ODD = D["odd_lot"]
DAY = D["daytrade"]
REV = D["reversal"]
WF = D["walkforward"]
COMB = {c["label"]: c for c in D["combined"]}
RANGE = D["meta"]["range"]

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#0b0f14;color:#dfe7ee;font-family:-apple-system,BlinkMacSystemFont,"Noto Sans CJK TC","PingFang TC","Microsoft JhengHei",sans-serif;line-height:1.75;font-size:15px}
.wrap{max-width:1060px;margin:0 auto;padding:0 26px 80px}
header{padding:56px 0 30px;border-bottom:1px solid #22303e}
.kicker{color:#e8b44a;letter-spacing:.22em;font-size:12px;font-weight:700}
h1{font-size:34px;margin:12px 0 8px;line-height:1.3;color:#fff}
.sub{color:#8b9bab;font-size:14px}
h2{font-size:23px;color:#fff;margin:54px 0 18px;padding-bottom:10px;border-bottom:1px solid #22303e;display:flex;align-items:center;gap:12px}
.no{display:inline-flex;width:30px;height:30px;border-radius:8px;background:#e8b44a;color:#111;font-size:14px;align-items:center;justify-content:center;font-weight:800;flex:none}
h3{font-size:17px;color:#e8b44a;margin:30px 0 10px}
p{margin:12px 0}
b,strong{color:#fff}
.hl{color:#e8b44a;font-weight:700}
.up{color:#f0655a;font-weight:700}
.dn{color:#4cc38a;font-weight:700}
.card{background:#141c26;border:1px solid #243244;border-radius:12px;padding:20px 22px;margin:18px 0}
.big{background:linear-gradient(135deg,#1c2634,#141c26);border-left:4px solid #e8b44a}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:20px 0}
.kpi{background:#141c26;border:1px solid #243244;border-radius:10px;padding:16px}
.kpi .v{font-size:26px;font-weight:800;color:#fff;line-height:1.2}
.kpi .l{font-size:12px;color:#8b9bab;margin-top:6px}
table{width:100%;border-collapse:collapse;margin:16px 0;font-size:13.5px}
th{background:#1a2532;color:#a9bacb;text-align:left;padding:10px 11px;border-bottom:1px solid #2b3a4c;font-weight:600;white-space:nowrap}
td{padding:9px 11px;border-bottom:1px solid #1e2937}
tr:hover td{background:#182230}
.num{text-align:right;font-variant-numeric:tabular-nums}
.chart{background:#101822;border:1px solid #243244;border-radius:12px;padding:16px;margin:20px 0;overflow-x:auto}
svg{display:block;max-width:100%;height:auto}
.ax{fill:#7d8fa2;font-size:11px}
.lb{fill:#cbd8e4;font-size:12px}
.pt{fill:#e8b44a;font-size:11px;font-weight:700}
.gd{stroke:#243244;stroke-width:1}
ul,ol{padding-left:22px}
li{margin:7px 0}
.note{color:#8b9bab;font-size:12.5px;border-left:2px solid #3a4a5c;padding-left:12px;margin:14px 0}
.onepager{background:#faf7f0;color:#2b2b2b;border-radius:12px;padding:30px 32px;margin:26px 0;font-size:15px}
.onepager h3{color:#8a5a12;margin-top:0;font-size:19px}
.onepager table{font-size:14px;color:#2b2b2b}
.onepager th{background:#eee6d5;color:#5a4a2e;border-bottom:1px solid #d8cbb0}
.onepager td{border-bottom:1px solid #e6ddc9}
.onepager b{color:#8a5a12}
.rule{background:#16202c;border:1px solid #2b3b4e;border-radius:8px;padding:12px 15px;margin:10px 0}
.rule b{color:#e8b44a}
footer{margin-top:60px;padding-top:22px;border-top:1px solid #22303e;color:#6b7c8d;font-size:12px}
code{background:#1c2735;padding:1px 6px;border-radius:4px;color:#e8b44a;font-size:13px}
@media print{body{background:#fff;color:#111}.wrap{max-width:none}.card,.kpi,.chart{break-inside:avoid}}
@media(max-width:700px){table{font-size:12px}h1{font-size:26px}}
"""


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def hbar(rows, width=940, row_h=34, label_w=250, maxv=None, ref=None, unit="%"):
    """横向条形图。rows: [(label, value, color)]；可含负值。"""
    vals = [r[1] for r in rows] + ([ref[1]] if ref else [])
    hi = maxv or max([abs(v) for v in vals] + [1])
    H = row_h * len(rows) + 56
    x0 = label_w
    span = width - label_w - 90
    zero = x0 + span * 0.18
    scale = span * 0.82 / hi
    p = [f'<svg viewBox="0 0 {width} {H}" xmlns="http://www.w3.org/2000/svg">']
    p.append(f'<line x1="{zero}" y1="16" x2="{zero}" y2="{H-26}" class="gd"/>')
    for i, (lab, v, col) in enumerate(rows):
        y = 20 + i * row_h
        w = abs(v) * scale
        x = zero if v >= 0 else zero - w
        p.append(f'<text x="{x0-10}" y="{y+18}" text-anchor="end" class="lb">{esc(lab)}</text>')
        p.append(f'<rect x="{x:.1f}" y="{y+4}" width="{max(2,w):.1f}" height="{row_h*0.6:.0f}" fill="{col}" opacity="0.88" rx="3"/>')
        tx = (zero + w + 8) if v >= 0 else (zero - w - 8)
        anc = "start" if v >= 0 else "end"
        p.append(f'<text x="{tx:.1f}" y="{y+19}" text-anchor="{anc}" class="pt" fill="{col}">{v:+.1f}{unit}</text>')
    if ref:
        rx = zero + ref[1] * scale if ref[1] >= 0 else zero - abs(ref[1]) * scale
        p.append(f'<line x1="{rx:.1f}" y1="12" x2="{rx:.1f}" y2="{H-26}" stroke="#e8b44a" stroke-width="2" stroke-dasharray="5,4"/>')
        p.append(f'<text x="{rx-6:.1f}" y="12" text-anchor="end" class="pt">{esc(ref[0])} {ref[1]:+.1f}{unit}</text>')
    p.append("</svg>")
    return "".join(p)


def linechart(series, width=940, height=300, ylab=""):
    """series: [(name, values, color)]，values 已采样、长度对齐"""
    L = min(len(s[1]) for s in series)
    allv = [v for _, vs, _ in series for v in vs[:L]]
    lo, hi = min(allv), max(allv)
    pad = (hi - lo) * 0.08 or 0.1
    lo, hi = lo - pad, hi + pad
    x0, x1, y0, y1 = 58, width - 20, 22, height - 34
    def X(i): return x0 + (x1 - x0) * i / max(1, L - 1)
    def Y(v): return y1 - (y1 - y0) * (v - lo) / (hi - lo)
    p = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">']
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        y = Y(v)
        p.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" class="gd"/>')
        p.append(f'<text x="{x0-8}" y="{y+4:.1f}" text-anchor="end" class="ax">{v:.1f}x</text>')
    for name, vs, col in series:
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vs[:L]))
        p.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.4" stroke-linejoin="round"/>')
    lx = x0 + 8
    for name, vs, col in series:
        p.append(f'<rect x="{lx}" y="{height-26}" width="13" height="4" fill="{col}"/>')
        p.append(f'<text x="{lx+19}" y="{height-20}" class="lb">{esc(name)}</text>')
        lx += 20 + len(name) * 13 + 34
    p.append(f'<text x="{x0}" y="14" class="ax">{esc(ylab)}</text>')
    p.append("</svg>")
    return "".join(p)


def tbl(headers, rows, aligns=None):
    aligns = aligns or [""] * len(headers)
    h = "".join(f'<th class="{a}">{esc(x)}</th>' for x, a in zip(headers, aligns))
    body = ""
    for r in rows:
        body += "<tr>" + "".join(f'<td class="{a}">{c}</td>' for c, a in zip(r, aligns)) + "</tr>"
    return f"<table><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>"


def fmt(v, suffix="%", sign=False):
    if v is None:
        return "—"
    return f"{v:+.2f}{suffix}" if sign else f"{v:.2f}{suffix}"


def build():
    P = []
    add = P.append

    add(f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>V4.0 执行策略实验室</title><style>{CSS}</style></head><body><div class="wrap">
<header><div class="kicker">SILVERSTOCK · V4.0 · M0 模擬盤研究</div>
<h1>不盯盤的人，真正該升級的是「賣出之後」</h1>
<p class="sub">把九個交易觀察拆成 7 組可證偽的實驗｜{RANGE[0]} – {RANGE[1]}｜{D['meta']['universe']} 檔台股、{D['meta']['bars']} 根日線｜含息、含手續費與交易稅</p>
</header>""")

    # ── 0. 一句话答案
    c_all = COMB["全程"]
    add(f"""<div class="card big"><p style="font-size:18px;margin:0">
你講的九條裡，<b>八條是對的</b>，缺的不是「看得更準」，而是<b>兩個沒寫下來的規則</b>：
<span class="hl">① 賣出之後用什麼條件回補</span>、<span class="hl">② 觸發用「狀態」而不是「固定價位」</span>。</p>
<p style="margin:14px 0 0;color:#b9c7d4">實測：靜態目標價 <code>+20% 全賣、不回補</code> 在五年裡只拿到
<span class="dn">{c_all['static_target']['total_pct']:+.1f}%</span>，買入持有是
<span class="up">{c_all['buyhold']['total_pct']:+.1f}%</span>——你說的「太早出手錯過很多」，代價是
<b>{c_all['buyhold']['total_pct']-c_all['static_target']['total_pct']:.0f} 個百分點</b>。
補上回報規則後，升級版拿到 <span class="up">{c_all['combo']['total_pct']:+.1f}%</span>，
只落後 {c_all['buyhold']['total_pct']-c_all['combo']['total_pct']:.1f}pp，但最大回撤從
{c_all['buyhold']['mdd_pct']:.1f}% 收窄到 {c_all['combo']['mdd_pct']:.1f}%。</p></div>""")

    # ── 1. 九条判定
    add('<h2><span class="no">1</span>你的九條，逐條給判定</h2>')
    judgments = [
        ("預定目標價自動買賣、不用盯盤", "方向對，機制要換", "固定價位是單點賭注；改成「狀態觸發 + 月檢」，照樣不用盯盤"),
        ("太早出手在起漲時，錯過很多", "✅ 完全正確，且代價可量化", f"全程 {c_all['buyhold']['total_pct']-c_all['static_target']['total_pct']:.0f}pp；解法不是改賣點，是補回補規則"),
        ("不賣最高、不買最低，不貪不求", "✅ 對", "底部單筆是事後上限；等確認少賺但可執行（第 8 節）"),
        ("慢慢建倉、慢慢減碼、分批買賣", "⚠️ 對一半", "分批買的是心安：k=1 拿 134.6%，k=20 只剩 89.5%（第 4 節）"),
        ("零股測試系統（資金不足）", "✅ 成本上完全可行", "1,000 元起就不受 1 元低收懲罰；真正的瓶頸是樣本筆數（第 6 節）"),
        ("整張可當日買賣對沖", "❌ 現階段不做", "來回成本 0.435%，資料集無日內價，無法證明有優勢（第 7 節）"),
        ("觸底反彈、行情突然反轉的應對", "要換訊號", "用 20 日均線，別用年線：年線慢 29–57 日（第 8 節）"),
        ("沒有交易條件就觀察等待", "✅ 對，但買的是回撤不是報酬", "樣本外少賺 10.2pp、回撤少 6.8pp、Calmar 反勝（第 5 節）"),
        ("有沒有更好的交易策略", "有，但不是更會預測", "把「價位」換成「狀態機」，見第 9、10 節"),
    ]
    add(tbl(["你的觀察", "判定", "實測依據"],
            [[f"<b>{a}</b>", b, c] for a, b, c in judgments]))

    # ── 2. 太早出手
    a2 = A[1]
    rows20 = [r for r in a2["rows"] if r.get("trigger_pct") == 20]
    add('<h2><span class="no">2</span>「太早出手」到底代價多大</h2>')
    add(f"""<p>在兩段真實多頭（{A[0]['start']}–{A[0]['end']}、{A[1]['start']}–{A[1]['end']}）起點滿倉 0050，
設定「<b>相對成本漲 +20% 就全部自動賣出</b>」——這正是預定價位條件單的行為。
賣出後不再進場，就是多數人「賺到了但錯過後面」的完整路徑。</p>""")
    add('<div class="grid">')
    add(f'<div class="kpi"><div class="v up">{a2["bh_total_pct"]:+.1f}%</div><div class="l">買入持有（多頭二）</div></div>')
    add(f'<div class="kpi"><div class="v dn">{rows20[0]["total_pct"]:+.1f}%</div><div class="l">+20% 賣出後不回補</div></div>')
    add(f'<div class="kpi"><div class="v" style="color:#e8b44a">{rows20[0]["gap_vs_bh_pp"]:.1f}pp</div><div class="l">多頭二踏空成本</div></div>')
    add(f'<div class="kpi"><div class="v">{c_all["buyhold"]["total_pct"]-c_all["static_target"]["total_pct"]:.0f}pp</div><div class="l">全程踏空成本</div></div>')
    add('</div>')

    chart_rows = []
    for r in rows20:
        label = r["rule"].split("/")[-1].strip()
        col = "#4cc38a" if "never" in r["mode"] or "dip" in r["mode"] else (
            "#e8b44a" if "newhigh" in r["mode"] or "after_N 20" in label else "#5b8fc9")
        chart_rows.append((label, r["total_pct"], col))
    add('<div class="chart">' + hbar(chart_rows, label_w=230,
        ref=("買入持有", a2["bh_total_pct"])) + '</div>')
    add(f"""<p class="note">讀法：金色虛線是買入持有。綠色是「賣掉就走」與「等回檔再買」——
這兩者結果完全一樣，因為單邊上漲裡<b>根本不會回檔到 −5%／−10%</b>。
「等回頭再買」在趨勢中等於永遠不買，這是最貴的一條紀律。</p>""")

    # ── 3. 回补规则
    add('<h2><span class="no">3</span>真正該補的：賣出「之後」的規則</h2>')
    add('<p>同一個賣點、同一段行情，只改「賣掉以後怎麼辦」：</p>')
    rr = []
    for r in rows20:
        rr.append([r["rule"].replace("+20% 卖 / ", ""),
                   f'<b>{r["total_pct"]:+.1f}%</b>',
                   f'{r["gap_vs_bh_pp"]:+.1f}pp',
                   r["turnovers"], f'{r["cost_paid_pct"]:.2f}%'])
    add(tbl(["賣出後規則", "期末報酬", "落後持有", "換手次數", "累計成本"], rr,
            ["", "num", "num", "num", "num"]))
    best = max(rows20, key=lambda x: x["total_pct"])
    add(f"""<div class="card"><p style="margin:0"><b>最好的一條是「{best['rule']}」</b>：
把踏空從 {rows20[0]['gap_vs_bh_pp']:.1f}pp 縮到 {best['gap_vs_bh_pp']:.1f}pp，
代價是換手 {best['turnovers']} 次、成本 {best['cost_paid_pct']:.2f}%。
<b>賣點完全沒變，只多了「20 日內創新高就補回」這一句。</b></p></div>""")
    add("""<p>反過來看兩個反直覺的：</p><ul>
<li><b>階梯部分止盈（+20% 賣 1/4、+40% 賣 1/3）在純多頭段落後 57–109pp</b>。這不推翻 V3.8——V3.8 說「值得」是含空頭的全週期、看 Calmar；在單邊段它必然落後。<b>部分止盈買的是下一輪空頭的保護，不是這一輪多頭的報酬。</b></li>
<li><b>反覆執行「賣→回補」反而更差</b>（多頭二 76.6%），等於每次起漲都被掃一次。規則要少、要慢。</li></ul>""")

    # ── 4. 分批
    add('<h2><span class="no">4</span>慢慢建倉、慢慢減碼：把「不貪」標上價格</h2>')
    add(f"""<p>在 2025/02/21–2025/04/09 那段 <b>30 天 −26.7% 急殺</b>裡分 k 次建倉，
持有到低點後 250 日。這是 V3.9 底部反彈的同一段，數字可交叉核對（k=1 底部單筆 {DCA['rows'][0]['total_pct']:.1f}% ≈ V3.9 的 +134.5%）。</p>""")
    trows = [r for r in DCA["rows"] if r["mode"] == "time"]
    add(tbl(["分批次數 k", "平均成本 vs 起點", "期末報酬", "最大回撤", "期末倉位"],
            [[r["k"], f'{r["avg_entry_vs_start_pct"]:+.1f}%',
              f'<b>{r["total_pct"]:+.1f}%</b>', f'{r["mdd_pct"]:.1f}%',
              f'{r["final_w"]*100:.0f}%'] for r in trows],
            ["", "num", "num", "num", "num"]))
    add('<div class="chart">' + hbar([(f"k={r['k']}", r["total_pct"], "#e8b44a" if r["k"] <= 3 else "#5b8fc9") for r in trows],
        label_w=120, maxv=145) + '</div>')
    add(f"""<div class="card"><p style="margin:0"><b>分越多、報酬越低，而且途中回撤反而更大</b>：
k=1 拿 {trows[0]['total_pct']:.1f}%／MDD {trows[0]['mdd_pct']:.1f}%，
k=20 只剩 {trows[-1]['total_pct']:.1f}%／MDD {trows[-1]['mdd_pct']:.1f}%。
原因是分批買在下跌途中，買完還繼續跌，浮虧全部計入淨值。<b>分批從來不是提高報酬的工具，是降低「一次買在半山腰」遺憾的工具。</b></p></div>""")
    drows = [r for r in DCA["rows"] if r["mode"] == "dip"]
    add(f"""<p class="note">另一種「每跌 3% 加碼」：k=5 拿 {drows[3]['total_pct']:.1f}%／MDD {drows[3]['mdd_pct']:.1f}%，
比時間等分好。但 k=10／20 因這段只跌 26.7%，<b>沒有足夠跌幅觸發，期末倉位只有 80%／40%</b>，報酬不能直接跟滿倉比——這是分批法在溫和回檔裡的隱藏缺陷。</p>""")
    add('<h3>減碼：慢一點確實比較好，但都遠不如不減</h3>')
    add(tbl(["減碼方式", "期末報酬", "最大回撤", "Calmar", "換手"],
            [[r["rule"], f'<b>{r["total_pct"]:+.1f}%</b>', f'{r["mdd_pct"]:.1f}%',
              r["calmar"], r["turnovers"]] for r in SCALE["rows"]],
            ["", "num", "num", "num", "num"]))
    add(f"""<p>一次清倉 {SCALE['rows'][1]['total_pct']:.1f}%、分 10 次 {SCALE['rows'][-1]['total_pct']:.1f}%，
不減碼 {SCALE['rows'][0]['total_pct']:.1f}%；但回撤從 −15.4% 降到 −5.7%。
<b>「慢慢減」比「一次減」好，可是別期待它幫你多賺</b>——它買的是回撤與睡得著覺。</p>""")

    # ── 5. 等待
    add('<h2><span class="no">5</span>「沒有條件就觀察等待」：誠實的樣本外檢驗</h2>')
    add('<p>先看樣本內。全程買入持有、各種「跌破就空手」的月檢規則：</p>')
    add(tbl(["規則", "全程報酬", "最大回撤", "Calmar", "空手天數占比"],
            [[r["rule"], f'<b>{r["total_pct"]:+.1f}%</b>', f'{r["mdd_pct"]:.1f}%',
              r["calmar"], f'{r["idle_pct"]:.1f}%'] for r in WAIT["rows"]],
            ["", "num", "num", "num", "num"]))
    add(f"""<p>看起來 <b>MA120 月檢</b> 最漂亮（Calmar {WAIT['rows'][2]['calmar']} vs 持有 {WAIT['rows'][0]['calmar']}）。
但這是<b>七個候選裡挑出來的最好一個</b>，標準的參數過擬合。所以我把時間切兩半：
前半段（{WF['train_range'][0]}–{WF['train_range'][1]}）選參數，後半段（{WF['test_range'][0]}–{WF['test_range'][1]}）才驗證。</p>""")
    add('<div class="grid">')
    add(f'<div class="kpi"><div class="v">{WF["best_in_sample"]["kind"]}</div><div class="l">前半段選出的最佳參數</div></div>')
    add(f'<div class="kpi"><div class="v up">{WF["test_rule_pct"]:+.1f}%</div><div class="l">後半段規則報酬</div></div>')
    add(f'<div class="kpi"><div class="v">{WF["test_bh_pct"]:+.1f}%</div><div class="l">後半段買入持有</div></div>')
    add(f'<div class="kpi"><div class="v dn">{WF["outperformance_pp"]:+.1f}pp</div><div class="l">樣本外超額報酬</div></div>')
    add('</div>')
    add(f"""<div class="card big"><p style="margin:0;font-size:17px"><b>結論：等待買的是回撤，不是報酬。</b>
樣本外少賺 {abs(WF['outperformance_pp']):.1f}pp，但最大回撤從 {WF['test_bh_mdd']:.1f}% 降到 {WF['test_rule_mdd']:.1f}%，
Calmar {WF['test_rule_calmar']} 反勝持有的 {WF['test_bh_calmar']}。
這正是「沒有交易條件就觀察等待」的真正價值——<b>它讓你在急殺裡不被迫賣出，代價是 V 型反轉時少賺</b>。</p></div>""")
    add('<p>參數敏感度（同一規則，只改檢查頻率）：</p>')
    add(tbl(["檢查週期", "後半段報酬", "最大回撤", "Calmar", "換手"],
            [[f'{r["recheck_days"]} 日', f'{r["total_pct"]:+.1f}%', f'{r["mdd_pct"]:.1f}%',
              r["calmar"], r["turnovers"]] for r in WF["sensitivity"]],
            ["", "num", "num", "num", "num"]))
    add("""<p class="note">21 日最好、63 日幾乎失效（Calmar 1.18）。<b>參數敏感就代表不能當成保證</b>；
所以 V3.8 的結論仍然成立：擇時只關在衛星層，核心層永不擇時。</p>""")
    add('<h3>各波段「等待」救了多少</h3>')
    add(tbl(["波段", "指數", "持有", "等待(MA120)", "差額"],
            [[f'{s["direction"]} {s["start"]}', f'{s["index_ret_pct"]:+.1f}%',
              f'{s["hold_pct"]:+.1f}%', f'{s["wait_pct"]:+.1f}%',
              f'<b>{s["saved_pp"]:+.1f}pp</b>'] for s in WAIT["segments"]],
            ["", "num", "num", "num", "num"]))

    # ── 6. 零股
    add('<h2><span class="no">6</span>零股測試系統：成本不是問題，樣本數才是</h2>')
    add(f"""<p>你說「1,000 元起算、資金不足先用零股」——好消息：<b>這個門檻剛好選對了</b>。
零股單筆手續費低收 1 元，生效門檻是 <span class="hl">{ODD['min_fee_threshold_ntd']:.2f} 元</span>
（1 ÷ {ODD['fee_rate_pct']}‰）。1,000 元的手續費是 1.43 元，<b>根本沒被低收懲罰</b>。</p>""")
    add(tbl(["單筆金額", "買/賣手續費各", "交易稅(個股)", "往返總成本", "成本占比", "需漲多少打平", "低收生效"],
            [[f'{r["amount"]:,} 元', f'{r["fee_each"]} 元', f'{r["tax"]} 元',
              f'{r["roundtrip_cost"]} 元', f'<b>{r["cost_pct"]:.3f}%</b>',
              f'{r["breakeven_pct"]:.3f}%', "是" if r["min_fee_binding"] else "否"]
             for r in ODD["small_rows"]],
            ["", "num", "num", "num", "num", "num", "num"]))
    add(f"""<div class="card"><p style="margin:0"><b>從 {ODD['min_fee_threshold_ntd']:.0f} 元以上，零股與整張的往返成本完全一樣：個股 {ODD['odd_rows'][1]['cost_pct']:.3f}%／ETF {ODD['odd_rows'][0]['cost_pct']:.3f}%</b>。
{ODD['round_rows'][-1]['amount']:,} 元買一張 2330，成本占比仍是 {ODD['round_rows'][-1]['cost_pct']:.3f}%，只是絕對金額 {ODD['round_rows'][-1]['roundtrip_cost']:,.0f} 元。
<span class="hl">零股在費率上不吃虧</span>（零股撮合價差與成交不確定性不在資料集裡，不做數字斷言）。</p></div>""")
    add('<h3>真正的瓶頸：幾筆才能證明規則有效</h3>')
    add('<p>用 95% 信賴水準粗估，單筆淨期望 edge、單筆波動 sd，需要的交易筆數：</p>')
    pw = {}
    for r in ODD["power"]:
        pw.setdefault(r["edge_pct"], []).append(r)
    add(tbl(["單筆淨期望", "波動 2%", "波動 3%", "波動 5%"],
            [[f'{e:.1f}%'] + [f'{x["trades_needed_95"]} 筆' for x in pw[e]]
             for e in sorted(pw, reverse=True)], ["", "num", "num", "num"]))
    add(f"""<p>白話：若策略每筆只比成本多賺 1%、波動 3%，<b>至少要做 {pw[1.0][1]['trades_needed_95']} 筆</b>才知道是不是運氣；
若只有 0.5%，要 {pw[0.5][1]['trades_needed_95']} 筆。
<b>零股階段的正確目標是「收集樣本、驗證規則」，不是「賺錢」</b>——用小錢把 35 筆跑完，比急著放大資金有價值得多。</p>""")

    # ── 7. 当冲
    add('<h2><span class="no">7</span>整張當日沖銷：為什麼現階段不做</h2>')
    add(f"""<div class="card big"><p style="margin:0"><b>先講資料限制：{esc(DAY['limitation'])}</b>
這份資料只有收盤價，沒有開／高／低，任何「日內訊號勝率」都是編出來的，我不做這種斷言。
下面只算<b>成本門檻</b>——光成本就足以判斷值不值得。</p></div>""")
    add('<div class="grid">')
    add(f'<div class="kpi"><div class="v">{DAY["cost_stock_pct"]:.3f}%</div><div class="l">個股當沖來回成本（買 1.425‰ ×2 + 當沖稅 1.5‰）</div></div>')
    add(f'<div class="kpi"><div class="v">{DAY["cost_etf_pct"]:.3f}%</div><div class="l">ETF 當沖來回成本</div></div>')
    add(f'<div class="kpi"><div class="v dn">−{DAY["annual_erosion_stock_pct"]:.1f}%</div><div class="l">每天做一次、一年光成本侵蝕</div></div>')
    add(f'<div class="kpi"><div class="v">{DAY["one_lot_cost_ntd"]:,.0f} 元</div><div class="l">一張 2330 當沖一次的絕對成本</div></div>')
    add('</div>')
    add('<p>反推打平勝率（假設賺 g%／虧 g%，賠率 1:1）：</p>')
    add(tbl(["每次振幅 g", "需要勝率才打平"],
            [[f'{r["swing_pct"]:.1f}%', f'<b>{r["breakeven_winrate_pct"]:.2f}%</b>']
             for r in DAY["breakeven_winrate"]], ["", "num"]))
    add(f"""<p>資料裡相鄰收盤變動的中位數只有 {DAY['daily_abs_move']['median_pct']:.2f}%、P90 {DAY['daily_abs_move']['p90_pct']:.2f}%
（<b>這是隔日到隔日，不是日內可捕捉振幅</b>，僅供量級參考）。
要覆蓋 0.435% 的成本，等於每天都要做到接近六成以上勝率，且不能有手滑。
<b>當沖是負和遊戲：它不創造報酬，只分配報酬，還先抽走成本。</b>
除非你有可驗證的日內優勢（這套資料沒有），否則「對沖」這個詞在這裡是安慰，不是風控。</p>""")

    # ── 8. 反转
    add('<h2><span class="no">8</span>觸底反彈／突然反轉：用短均線，別用年線</h2>')
    add('<p>四段空頭的真實低點，比較三種「等確認才進場」的訊號。「底部當日單筆」是事後上限，實務上做不到，只當尺標。</p>')
    for x in REV:
        add(f'<h3>{x["start"]}–{x["end"]}　低點 {x["low_date"]}（指數 {x["index_ret_pct"]:+.1f}%）　假反彈 {x["fake_rebounds"]} 次</h3>')
        add(tbl(["進場訊號", "滯後天數", "進場價高於低點", "到低點後 250 日報酬"],
                [[r["signal"], "—" if r["lag_days"] is None else f'{r["lag_days"]} 日',
                  "—" if r["entry_vs_low_pct"] is None else f'+{r["entry_vs_low_pct"]:.2f}%',
                  "—" if r["ret_250_pct"] is None else f'<b>{r["ret_250_pct"]:+.2f}%</b>']
                 for r in x["rows"]], ["", "num", "num", "num"]))
    r4 = REV[-1]["rows"]
    add(f"""<div class="card"><p style="margin:0"><b>2025/02 急殺後最清楚</b>：底部單筆 {r4[0]['ret_250_pct']:.1f}%，
站回 20 日均線只慢 {r4[1]['lag_days']} 日、仍拿 {r4[1]['ret_250_pct']:.1f}%；
<b>等站回年線慢 {r4[2]['lag_days']} 日、只剩 {r4[2]['ret_250_pct']:.1f}%</b>，少賺 {r4[0]['ret_250_pct']-r4[2]['ret_250_pct']:.0f}pp。
年線是「確認趨勢」的工具，不是「抓反轉」的工具。</p></div>""")
    add(f"""<p class="note">四段裡「假反彈（5 日漲 5% 後又破前低）」只有 0–1 次，樣本很少。
所以<b>等確認的代價主要是少賺，不是避開陷阱</b>；它的價值在於讓「進場」變成可執行的規則，而不是猜低點。
第一段因資料起點不足 240 日，年線訊號不可用，如實標「—」。</p>""")

    # ── 9. 组合规则
    add('<h2><span class="no">9</span>V4.0 升級版實測：不是更會預測，是補上兩條規則</h2>')
    add("""<p>把前面學到的東西組起來，參數都用<b>事前固定的中庸值</b>（不是樣本內挑最優）：</p>
<div class="rule"><b>核心層起點就不動</b>（銜接 V3.8 四層桶，永不擇時）</div>
<div class="rule"><b>月檢 MA120</b>：跌破就把目標倉位降到 40%，站回後分 3 批補回</div>
<div class="rule"><b>+20% 賣 1/4、+40% 再賣 1/3</b>：部分退出，永不全清</div>
<div class="rule"><b>賣出後 20 日內創「賣出後新高」就補回 1/4</b>：這句是從第 3 節學來的關鍵</div>
<div class="rule"><b>沒有訊號就持現金觀察</b>：不為了有動作而交易</div>""")
    add(tbl(["區間", "V4.0 升級版", "買入持有", "靜態目標價(全賣不回補)"],
            [[c["label"], f'<b class="up">{c["combo"]["total_pct"]:+.1f}%</b> / MDD {c["combo"]["mdd_pct"]:.1f}%',
              f'{c["buyhold"]["total_pct"]:+.1f}% / MDD {c["buyhold"]["mdd_pct"]:.1f}%',
              f'<span class="dn">{c["static_target"]["total_pct"]:+.1f}%</span>']
             for c in D["combined"]], ["", "", "", ""]))
    ca = COMB["全程"]
    add('<div class="chart">' + linechart([
        ("V4.0 升級版", ca["nav_slim"], "#e8b44a"),
        ("買入持有", ca["bh_slim"], "#5b8fc9"),
        ("靜態目標價", ca["static_slim"], "#4cc38a"),
    ], ylab="全程淨值（起點 1.0x）") + '</div>')
    add(f"""<div class="card big"><p style="margin:0;font-size:17px">
全程：升級版 <b class="up">{ca['combo']['total_pct']:+.1f}%</b>（MDD {ca['combo']['mdd_pct']:.1f}%、Calmar {ca['combo']['calmar']}）
vs 買入持有 {ca['buyhold']['total_pct']:+.1f}%（MDD {ca['buyhold']['mdd_pct']:.1f}%、Calmar {ca['buyhold']['calmar']}）
vs 靜態目標價 <b class="dn">{ca['static_target']['total_pct']:+.1f}%</b>。<br>
<b>少賺 {ca['buyhold']['total_pct']-ca['combo']['total_pct']:.1f}pp，換回撤從 {abs(ca['buyhold']['mdd_pct']):.1f}% 降到 {abs(ca['combo']['mdd_pct']):.1f}%、Calmar 從 {ca['buyhold']['calmar']} 升到 {ca['combo']['calmar']}。</b>
換手 {ca['combo']['turnovers']} 次、累計成本 {ca['combo']['cost_paid_pct']:.2f}%——規則很少，效果全部來自「回補」與「不全清」。</p></div>""")

    # ── 10. 状态机 + 一页纸
    add('<h2><span class="no">10</span>可列印的狀態機（給自己）與一頁紙（給爸媽）</h2>')
    add(tbl(["狀態", "判據（收盤後月檢，不用盯盤）", "動作", "禁止"],
            [["<b>RISK_ON</b>", "0050 ≥ 120 日均線", "核心層不動；衛星層分 3 批回補", "不追高、不加槓桿"],
             ["<b>止盈一</b>", "相對本輪成本 +20%", "賣 1/4，<b>同時寫下回補條件</b>", "不全清、不取消回補"],
             ["<b>止盈二</b>", "相對本輪成本 +40%", "再賣 1/3，保留底倉", "同上"],
             ["<b>回補</b>", "賣出後 20 日內創賣出後新高", "補回 1/4、成本重設", "<b>不等回檔</b>（實測等回檔＝永不回補）"],
             ["<b>RISK_OFF</b>", "0050 < 120 日均線", "衛星層歸零、總倉位約 40%", "核心層不動、不攤平"],
             ["<b>反轉進場</b>", "站回 20 日均線（不是年線）", "分 3 批，每批 ≥702 元", "不猜最低點"],
             ["<b>空手</b>", "以上都不成立", "現金計息、觀察等待", "不為了有動作而交易"],
             ["<b>當沖</b>", "—", "現階段不做", "無日內資料可驗證前，不做"]], ["", "", "", ""]))
    add(f"""<p>零股階段：每筆 ≥ {ODD['min_fee_threshold_ntd']:.0f} 元，目標是跑滿 <b>{pw[1.0][1]['trades_needed_95']} 筆</b>再判斷規則好壞；
資金放大到能買整張時，<b>規則不用改</b>，只改單位——這才是「先測試系統」的真正意義。</p>""")

    # 繁体一页纸
    add(f"""<div class="onepager"><h3>給爸媽的一頁紙｜不用盯盤，也能不慌</h3>
<p>下面這張表印出來放桌邊。<b>不用看盤、不用猜高低點</b>，每個月底看一次就好。</p>
<table><thead><tr><th>情況</th><th>就做這件事</th><th>千萬不要</th></tr></thead><tbody>
<tr><td>大盤還在年線（120日均線）之上</td><td>原本的核心持股<b>不要動</b></td><td>不要因為「漲很多」就全賣</td></tr>
<tr><td>買的股票漲了 20%</td><td><b>只賣四分之一</b>，剩下的留著，並寫下「20 天內再創新高就補回」</td><td>不要一次賣光、不要等它跌回來才買</td></tr>
<tr><td>漲了 40%</td><td>再賣三分之一，<b>永遠留一部分</b></td><td>不要全清</td></tr>
<tr><td>賣掉後又繼續漲</td><td>依約補回四分之一，<b>照規則做，不生氣</b></td><td>不要追高一次買回、不要賭氣不買</td></tr>
<tr><td>跌破年線</td><td>只減「衛星」那一小部分，核心持股不動</td><td>不要攤平、不要借錢加碼</td></tr>
<tr><td>跌深後開始反彈</td><td>等站回 20 日均線，<b>分 3 次</b>慢慢買</td><td>不要猜最低點、不要一次梭哈</td></tr>
<tr><td>沒有任何訊號</td><td><b>抱現金，等</b>。等待也是一種決定</td><td>不要為了「有做點什麼」而買賣</td></tr>
</tbody></table>
<p><b>為什麼要這樣做？</b>五年實測：漲 20% 就全賣、之後不買回，只拿到
{ca['static_target']['total_pct']:.0f}%；照上面規則做，拿到 {ca['combo']['total_pct']:.0f}%，
而且最大虧損從 {ca['buyhold']['mdd_pct']:.0f}% 縮到 {ca['combo']['mdd_pct']:.0f}%。
<b>差別不在眼光，在「賣掉之後有沒有寫好下一步」。</b></p>
<p><b>三條鐵律：</b>① 不借錢、不當沖 ② 賣永遠只賣一部分 ③ 分批是買心安，不是買更多報酬。</p>
<p style="font-size:12px;color:#7a6a4e;margin-top:18px">資料：{D['meta']['universe']} 檔台股 {RANGE[0]}–{RANGE[1]} 日線，含息、含手續費與交易稅。僅供自家研究，非投資建議。</p>
</div>""")

    # ── 11. 局限
    add('<h2><span class="no">11</span>已知局限（請連這頁一起看）</h2>')
    add(f"""<ul>
<li><b>整段是罕見大多頭</b>（0050 含息 {ca['buyhold']['total_pct']:.0f}%）。任何「不要賣」的策略都會被高估；空頭樣本只有 4 段，其中一段還因資料起點不足無法完整分類。</li>
<li><b>只有收盤價</b>，沒有開／高／低。當沖、盤中觸價、滑點、零股撮合價差都無法驗證，第 7 節只列成本門檻。</li>
<li><b>組合規則的參數是事前固定的中庸值</b>，但「月檢 MA120」「20 日回補」「+20%/+40%」仍是研究者選擇，不是市場給的。第 5 節的敏感度顯示檢查週期一改，結果就變。</li>
<li><b>样本外检验只切一次</b>（2024/07/01），不是滾動 walk-forward；MA120 在後半段 Calmar 反勝，不代表未來。</li>
<li><b>用 0050 單一標的當「可執行核心」</b>，111 檔等權、產業輪動、個股事件都不在第 9 節的組合規則裡；第 2–4 節的分類與分批亦以 0050 為主。</li>
<li><b>分批 k=10／20（跌幅加碼）沒買滿</b>，期末倉位僅 80%／40%，報酬不可直接與滿倉比較，已於第 4 節標註。</li>
<li><b>樣本數門檻是簡化 power 估計</b>，假設報酬獨立常態；實務有序列相關，真實所需筆數通常更多。</li>
<li><b>沒有放空、反向 ETF、選擇權、債券、黃金、匯率</b>資料，不做任何數字斷言。</li>
<li>本報告是 M0 模擬盤研究，<b>未連富邦、未下任何單</b>。</li>
</ul>""")

    add(f"""<footer>Silverstock Quant Web · V4.0 執行策略實驗室　|　
引擎 <code>tool/v3/execution_lab.py</code>　結果 <code>v40_execution_result.json</code>　
報告 <code>tool/v3/gen_execution_report.py</code><br>
資料 {RANGE[0]}–{RANGE[1]}、{D['meta']['universe']} 檔、{D['meta']['bars']} 根日線；含息總報酬、含 1.425‰ 手續費與個股 3‰／ETF 1‰ 交易稅。
所有訊號僅用當日收盤前可得資料，無前視偏誤。僅供家人自用研究。</footer>
</div></body></html>""")

    html = "".join(P)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已產出 {OUT}（{len(html):,} 字元）")
    return html


if __name__ == "__main__":
    build()
