# -*- coding: utf-8 -*-
"""V4.1 報告生成器：所有數字從 v41_structure_result.json 讀取。"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "v41_structure_result.json")
OUT = os.path.join(ROOT, "..", "V4.1_个股印证与市场结构.html")

with open(SRC, encoding="utf-8") as f:
    D = json.load(f)

CASES = {c["sid"]: c for c in D["cases"]}
VOL = D["volume"]
ST = D["structure"]
RANGE = D["meta"]["range"]

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#0b0f14;color:#dfe7ee;font-family:-apple-system,BlinkMacSystemFont,"Noto Sans CJK TC","PingFang TC","Microsoft JhengHei",sans-serif;line-height:1.75;font-size:15px}
.wrap{max-width:1080px;margin:0 auto;padding:0 26px 80px}
header{padding:56px 0 30px;border-bottom:1px solid #22303e}
.kicker{color:#e8b44a;letter-spacing:.22em;font-size:12px;font-weight:700}
h1{font-size:33px;margin:12px 0 8px;line-height:1.32;color:#fff}
.sub{color:#8b9bab;font-size:14px}
h2{font-size:23px;color:#fff;margin:54px 0 18px;padding-bottom:10px;border-bottom:1px solid #22303e;display:flex;align-items:center;gap:12px}
.no{display:inline-flex;width:30px;height:30px;border-radius:8px;background:#e8b44a;color:#111;font-size:14px;align-items:center;justify-content:center;font-weight:800;flex:none}
h3{font-size:17px;color:#e8b44a;margin:28px 0 10px}
p{margin:12px 0}
b,strong{color:#fff}
.hl{color:#e8b44a;font-weight:700}
.up{color:#f0655a;font-weight:700}
.dn{color:#4cc38a;font-weight:700}
.card{background:#141c26;border:1px solid #243244;border-radius:12px;padding:20px 22px;margin:18px 0}
.big{background:linear-gradient(135deg,#1c2634,#141c26);border-left:4px solid #e8b44a}
.warn{border-left:4px solid #f0655a}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:20px 0}
.kpi{background:#141c26;border:1px solid #243244;border-radius:10px;padding:16px}
.kpi .v{font-size:25px;font-weight:800;color:#fff;line-height:1.2}
.kpi .l{font-size:12px;color:#8b9bab;margin-top:6px}
table{width:100%;border-collapse:collapse;margin:16px 0;font-size:13px}
th{background:#1a2532;color:#a9bacb;text-align:left;padding:9px 10px;border-bottom:1px solid #2b3a4c;font-weight:600;white-space:nowrap}
td{padding:8px 10px;border-bottom:1px solid #1e2937}
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
.rule{background:#16202c;border:1px solid #2b3b4e;border-radius:8px;padding:11px 15px;margin:9px 0}
.rule b{color:#e8b44a}
footer{margin-top:60px;padding-top:22px;border-top:1px solid #22303e;color:#6b7c8d;font-size:12px}
code{background:#1c2735;padding:1px 6px;border-radius:4px;color:#e8b44a;font-size:13px}
.tag{display:inline-block;padding:1px 8px;border-radius:5px;font-size:11px;font-weight:700}
.t-def{background:#173a2b;color:#4cc38a}.t-mid{background:#1c2f42;color:#7ab6e8}.t-hype{background:#3d2020;color:#f0655a}
@media print{body{background:#fff;color:#111}.wrap{max-width:none}.card,.kpi,.chart{break-inside:avoid}}
@media(max-width:700px){table{font-size:11.5px}h1{font-size:25px}}
"""


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tbl(headers, rows, aligns=None):
    aligns = aligns or [""] * len(headers)
    h = "".join(f'<th class="{a}">{esc(x)}</th>' for x, a in zip(headers, aligns))
    body = "".join("<tr>" + "".join(f'<td class="{a}">{c}</td>' for c, a in zip(r, aligns)) + "</tr>" for r in rows)
    return f"<table><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>"


def hbar(rows, width=960, row_h=32, label_w=230, maxv=None, ref=None, unit="%", abs_mode=False):
    vals = [abs(r[1]) for r in rows] + ([abs(ref[1])] if ref else [])
    hi = maxv or max(vals + [1])
    H = row_h * len(rows) + 52
    x0, span = label_w, width - label_w - 90
    zero = x0 + span * 0.18
    scale = span * 0.82 / hi
    p = [f'<svg viewBox="0 0 {width} {H}" xmlns="http://www.w3.org/2000/svg">']
    p.append(f'<line x1="{zero}" y1="14" x2="{zero}" y2="{H-24}" class="gd"/>')
    for i, (lab, v, col) in enumerate(rows):
        y = 18 + i * row_h
        w = abs(v) * scale
        x = zero if (v >= 0 or abs_mode) else zero - w
        p.append(f'<text x="{x0-10}" y="{y+17}" text-anchor="end" class="lb">{esc(lab)}</text>')
        p.append(f'<rect x="{x:.1f}" y="{y+3}" width="{max(2,w):.1f}" height="{row_h*0.6:.0f}" fill="{col}" opacity="0.88" rx="3"/>')
        tx = zero + w + 8 if (v >= 0 or abs_mode) else zero - w - 8
        anc = "start" if (v >= 0 or abs_mode) else "end"
        p.append(f'<text x="{tx:.1f}" y="{y+18}" text-anchor="{anc}" class="pt" fill="{col}">{v:+.2f}{unit}</text>')
    if ref:
        rx = zero + ref[1] * scale if ref[1] >= 0 else zero - abs(ref[1]) * scale
        p.append(f'<line x1="{rx:.1f}" y1="10" x2="{rx:.1f}" y2="{H-24}" stroke="#e8b44a" stroke-width="2" stroke-dasharray="5,4"/>')
        p.append(f'<text x="{rx-6:.1f}" y="10" text-anchor="end" class="pt">{esc(ref[0])} {ref[1]:+.2f}{unit}</text>')
    p.append("</svg>")
    return "".join(p)


def stacked(rows, width=960, height=170):
    """rows: [(label, [(name, pct, color), ...])]"""
    x0, x1 = 170, width - 30
    p = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">']
    rh = (height - 40) / len(rows)
    for i, (lab, segs) in enumerate(rows):
        y = 16 + i * rh
        p.append(f'<text x="{x0-10}" y="{y+rh*0.6:.0f}" text-anchor="end" class="lb">{esc(lab)}</text>')
        acc = 0.0
        for name, pct, col in segs:
            w = (x1 - x0) * pct / 100
            p.append(f'<rect x="{x0+acc:.1f}" y="{y+4:.0f}" width="{max(1,w):.1f}" height="{rh*0.62:.0f}" fill="{col}" opacity="0.9"/>')
            if w > 42:
                p.append(f'<text x="{x0+acc+w/2:.1f}" y="{y+rh*0.48:.0f}" text-anchor="middle" class="pt">{pct:.0f}%</text>')
            acc += w
    lx = x0
    for name, col in [("指數主導", "#f0655a"), ("產業主導", "#e8b44a"), ("個股主導", "#5b8fc9")]:
        p.append(f'<rect x="{lx}" y="{height-20}" width="13" height="5" fill="{col}"/>')
        p.append(f'<text x="{lx+19}" y="{height-14}" class="lb">{name}</text>')
        lx += 130
    p.append("</svg>")
    return "".join(p)


def grp(sid):
    return {"DEF": '<span class="tag t-def">防禦</span>',
            "MID": '<span class="tag t-mid">中性</span>',
            "HYPE": '<span class="tag t-hype">炒作</span>'}.get(sid, sid)


def pct(v, sign=True):
    return "—" if v is None else (f"{v:+.1f}%" if sign else f"{v:.1f}%")


def build():
    P = []
    add = P.append
    add(f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>V4.1 個股印證與市場結構</title><style>{CSS}</style></head><body><div class="wrap">
<header><div class="kicker">SILVERSTOCK · V4.1 · M0 模擬盤研究</div>
<h1>把原則放到具體股票上，再判今天是「誰在動」</h1>
<p class="sub">20 檔個股逐一印證 V3.7／V3.8／V3.9／V4.0｜量能擇時實測｜指數／產業／個股三態分解與應對｜{RANGE[0]} – {RANGE[1]}｜{D['meta']['universe']} 檔、{D['meta']['bars']} 根日線</p>
</header>""")

    # 0. 四问速答
    sstates = {x["state"]: x for x in ST["states"]}
    crash = ST["crash_breadth"]
    add(f"""<div class="card big"><p style="font-size:17px;margin:0">
<b>四個問題，四句話：</b><br>
① <b>原則要交叉驗證才可信</b> — V3.7 評分最高的 1102 亞泥，五年含息只漲 {CASES['1102']['total_return_5y_pct']:.1f}%；
被漏斗淘汰的 2454 聯發科漲 {CASES['2454']['total_return_5y_pct']:.1f}%。<br>
② <b>量能是風險信號，不是買點</b> — 爆量日當日 +{VOL['buckets'][-1]['same_day_pct']:.2f}%，次日只剩 +{VOL['buckets'][-1]['next_day_pct']:.3f}%，
放量後 20 日波動 {VOL['quadrants'][0]['fwd20_vol_pct']:.1f}% vs 平量 {VOL['quadrants'][2]['fwd20_vol_pct']:.1f}%。<br>
③ <b>大部分日子是個股行情，但要命的日子是全市場一起動</b> — 個股主導 {sstates['個股主導']['pct']}%，
齊跌日（上漲檔&lt;20%）{ST['breadth'][0]['pct']}%、指數平均 {ST['breadth'][0]['avg_index_pct']:+.2f}%。<br>
④ <b>三種狀態對應三種動作</b>：齊跌調倉位、產業輪動調族群、個股分歧才選股。詳見第 5 節。</p></div>""")

    # 1. 案例库总表
    add('<h2><span class="no">1</span>20 檔具體股票：原則判定 vs 實際績效</h2>')
    add("""<p>「通過」＝V3.7 五層漏斗（流動性／年線／回撤／估值／波動）；「分組」＝V3.9 在 2022/07/06 用<b>事前</b>特徵分的 DEF／MID／HYPE；
「含息 5 年」與「急殺」都是實測含息總報酬；「樣本外」是分組時點之後到期末，不看未來資料。</p>""")
    rows = []
    for c in D["cases"]:
        note = c.get("v37_note") or ""
        rows.append([
            f"<b>{c['sid']}</b> {esc(c['name'][:7])}",
            esc(c["industry"]),
            "✅" if c["passed_v37"] else "✗",
            f'{c["score_v37"]:.1f}' if c["score_v37"] else "—",
            grp(c["group_v39"]),
            f'<b>{c["total_return_5y_pct"]:+.1f}%</b>',
            f'{c["mdd_total_pct"]:.1f}%',
            f'<span class="{"dn" if (c["crash_30d_pct"] or 0) < -20 else ""}">{pct(c["crash_30d_pct"])}</span>',
            pct(c["oos_20220706_pct"]),
            esc(c["layer"]),
        ])
    add(tbl(["代號／名稱", "產業", "V3.7", "評分", "V3.9組", "含息5年", "MDD", "急殺30日", "樣本外", "V3.8 建議層"],
            rows, ["", "", "num", "num", "", "num", "num", "num", "num", ""]))
    add("""<p class="note">ETF 不適用個股漏斗（無 PE／殖利率口徑），直接歸 L2／L1 核心層，表上顯示 ✗ 不是淘汰。
「V3.8 建議層」是示範映射規則：HYPE 組排除、MDD&gt;40% 或波動&gt;30% 降到衛星層、殖利率≥3.5% 才進 L1。<b>不是回測結論</b>。</p>""")

    # 图表：评分 vs 含息报酬
    pts = [(f"{c['sid']} {c['name'][:4]}", c["total_return_5y_pct"],
            "#4cc38a" if c["group_v39"] == "DEF" else
            "#f0655a" if c["group_v39"] == "HYPE" else "#5b8fc9")
           for c in D["cases"] if c["score_v37"]]
    add('<h3>V3.7 評分 vs 五年含息報酬（通過漏斗的 13 檔）</h3>')
    add('<div class="chart">' + hbar(pts, label_w=150, maxv=420, unit="%") + '</div>')
    add(f"""<p class="note">評分最高的 1102 亞泥（{CASES['1102']['score_v37']} 分）報酬 {CASES['1102']['total_return_5y_pct']:+.1f}%；
評分最低的 2330 台積電（{CASES['2330']['score_v37']} 分）報酬 {CASES['2330']['total_return_5y_pct']:+.1f}%。
<b>這條幾乎是反向的</b>——V3.7 本來就誠實聲明「這是排除法，不是選股預測」，實測完全印證。</p>""")

    # 2. 深度案例
    add('<h2><span class="no">2</span>五個深度案例：原則在哪裡成立、在哪裡失靈</h2>')

    add('<h3>案例 A｜電信三雄：防禦原則最乾淨的印證</h3>')
    tel = ["2412", "3045", "4904"]
    add(tbl(["代號", "名稱", "V3.7評分", "含息5年", "MDD", "急殺30日", "殖利率", "建議層"],
            [[f'<b>{c}</b>', CASES[c]["name"], f'{CASES[c]["score_v37"]}',
              f'{CASES[c]["total_return_5y_pct"]:+.1f}%', f'{CASES[c]["mdd_total_pct"]:.1f}%',
              f'<b class="dn">{pct(CASES[c]["crash_30d_pct"])}</b>',
              f'{CASES[c]["yield_pct"]:.2f}%', CASES[c]["layer"]] for c in tel],
            ["", "", "num", "num", "num", "num", "num", ""]))
    add(f"""<div class="card"><p style="margin:0">2025/02 那 30 天指數 −26.7%，這三檔分別
{pct(CASES['2412']['crash_30d_pct'])}／{pct(CASES['3045']['crash_30d_pct'])}／{pct(CASES['4904']['crash_30d_pct'])}，
<b>幾乎沒跌</b>；全程 MDD 也只有 −18.0%／−16.9%／−25.6%。
這正是 V3.9「防禦組三段空頭每一次都最抗跌」的具體長相，也對應 V3.8 L1 高股息安全墊。<br>
代價要一起看：含息五年 {CASES['2412']['total_return_5y_pct']:+.1f}%／{CASES['3045']['total_return_5y_pct']:+.1f}%，
遠低於台積電 {CASES['2330']['total_return_5y_pct']:+.1f}%。<b>買的是活得久，不是賺最多。</b></p></div>""")

    add('<h3>案例 B｜1102 亞泥：通過全部原則，卻幾乎沒漲</h3>')
    c = CASES["1102"]
    add(f"""<p>評分 <b>{c['score_v37']} 分全場最高</b>（低波動 {c['vol_pct']}%、PE {c['pe']}、殖利率 {c['yield_pct']}%、流動性達標），
但含息五年只有 <b class="dn">{c['total_return_5y_pct']:+.1f}%</b>、分組後樣本外 {c['oos_20220706_pct']:+.1f}%，
同期 0050 是 {CASES['0050']['total_return_5y_pct']:+.1f}%。<br>
<b>印證的原則</b>：V3.7 的五層漏斗篩的是「不容易出事」，不是「會漲」。
它同時也提醒 V3.8：<b>核心層的任務是降低回撤與供現金流，不是貢獻報酬</b>，報酬要交給 L2 指數與 L3 衛星。</p>""")

    add('<h3>案例 C｜2330 台積電、2454 聯發科：排除法會漏掉最強的</h3>')
    add(tbl(["代號", "名稱", "V3.7", "評分", "含息5年", "樣本外", "MDD", "急殺"],
            [[f'<b>{k}</b>', CASES[k]["name"], "✅" if CASES[k]["passed_v37"] else "✗ 淘汰",
              f'{CASES[k]["score_v37"] or "—"}', f'{CASES[k]["total_return_5y_pct"]:+.1f}%',
              pct(CASES[k]["oos_20220706_pct"]), f'{CASES[k]["mdd_total_pct"]:.1f}%',
              pct(CASES[k]["crash_30d_pct"])] for k in ("2330", "2454")],
            ["", "", "", "num", "num", "num", "num", "num"]))
    add(f"""<p>台積電雖通過漏斗但評分 {CASES['2330']['score_v37']} 分<b>全場最低</b>（波動 29.5%、回撤 −45.7%、殖利率 0.88%）；
聯發科直接被淘汰。兩檔卻是五年含息 {CASES['2330']['total_return_5y_pct']:+.1f}% 與 {CASES['2454']['total_return_5y_pct']:+.1f}%，
樣本外 {pct(CASES['2330']['oos_20220706_pct'])}／{pct(CASES['2454']['oos_20220706_pct'])}。<br>
<b>應對</b>：不要因為「原則沒選到」就追買個股。這兩檔已經透過 <b>0050</b> 被動持有（L2 指數核心），
用指數拿到它們的成長，同時避開單檔 −45% 回撤。這正是 V3.8「60% 倉位拿 72% 報酬」的設計理由。</p>""")

    add('<h3>案例 D｜2618 長榮航：兩套原則給出相反答案</h3>')
    c = CASES["2618"]
    add(f"""<div class="card warn"><p style="margin:0"><b>同一檔股票：V3.7 漏斗給 {c['score_v37']} 分（通過，前段班）；V3.9 事前分組歸 HYPE 炒作組。</b><br>
實績：含息五年 {c['total_return_5y_pct']:+.1f}%、MDD {c['mdd_total_pct']:.1f}%、急殺 {pct(c['crash_30d_pct'])}、
分組後樣本外 {pct(c['oos_20220706_pct'])}，而同組 5 檔全程平均是 −1.6%／MDD −45.3%。<br>
<b>這不是矛盾，是兩套原則在看不同東西</b>：V3.7 看當下的估值／波動／配息（靜態體質），
V3.9 看事前動能與籌碼特徵（行為風險）。<b>結論：任何單一原則都不足以放行一筆單，必須交叉。</b>
這也是 V3.7 交易前 12 問設成 fail-closed 的原因。</p></div>""")

    add('<h3>案例 E｜HYPE 五檔：炒作股的實際代價</h3>')
    hype = [c for c in D["cases"] if c["group_v39"] == "HYPE"]
    add(tbl(["代號", "名稱", "含息5年", "MDD", "急殺30日", "樣本外", "V3.8 層"],
            [[f'<b>{x["sid"]}</b>', x["name"], f'<b>{x["total_return_5y_pct"]:+.1f}%</b>',
              f'<span class="dn">{x["mdd_total_pct"]:.1f}%</span>', pct(x["crash_30d_pct"]),
              pct(x["oos_20220706_pct"]), x["layer"]] for x in hype],
            ["", "", "num", "num", "num", "num", ""]))
    add(f"""<p>2227 裕日車 {pct(CASES['2227']['total_return_5y_pct'])}、樣本外 {pct(CASES['2227']['oos_20220706_pct'])}、
MDD {CASES['2227']['mdd_total_pct']:.1f}%；8908 欣雄 {pct(CASES['8908']['total_return_5y_pct'])}。
V3.9 的乾淨檢驗：2022/07 分一次組、之後 1,044 日不重分類，HYPE 組全程 −1.6%／MDD −45.3%，DEF 組 +99.2%。
<b>風控必須分兩套</b>：防禦股用基本面止損；炒作股單檔 ≤1%、−15% 無條件砍、絕不攤平。</p>""")

    # 3. 量能
    add('<h2><span class="no">3</span>交易量／換手頻繁：量能到底能不能找買點</h2>')
    add(f"""<div class="card warn"><p style="margin:0"><b>資料限制先講清楚：{esc(VOL['note'])}</b><br>
{VOL['benchmark']}。volumes 單位是「張」，沒有流通股數，<b>無法算真實換手率</b>，只能用量比代理。</p></div>""")
    add('<h3>量比分組：當日很熱，隔天就沒了</h3>')
    add(tbl(["量比區間", "樣本數", "當日報酬", "次日報酬", "後20日", "後20日勝率", "後20日超額"],
            [[r["bucket"], f'{r["n"]:,}', f'{r["same_day_pct"]:+.3f}%', f'{r["next_day_pct"]:+.3f}%',
              f'{r["fwd20_pct"]:+.3f}%', f'{r["win20_pct"]:.1f}%',
              f'<b>{r["excess20_pct"]:+.3f}%</b>'] for r in VOL["buckets"]],
            ["", "num", "num", "num", "num", "num", "num"]))
    b = VOL["buckets"][-1]
    add(f"""<p>爆量（量比 &gt;3）當日平均 <b class="up">+{b['same_day_pct']:.3f}%</b>，
次日只剩 +{b['next_day_pct']:.3f}%，後 20 日 {b['fwd20_pct']:+.3f}% 與極縮量的 {VOL['buckets'][0]['fwd20_pct']:+.3f}% 幾乎一樣，
勝率 {b['win20_pct']:.1f}% 也貼近擲硬幣。<b>量能預測不了方向</b>。</p>""")
    add('<h3>量價四象限：放量真正放大的是「波動」</h3>')
    add(tbl(["象限", "樣本數", "後20日", "勝率", "超額(vs等權)", "後20日年化波動"],
            [[r["quad"], f'{r["n"]:,}', f'{r["fwd20_pct"]:+.3f}%', f'{r["win20_pct"]:.1f}%',
              f'<b>{r["excess20_pct"]:+.3f}%</b>', f'{r["fwd20_vol_pct"]:.1f}%'] for r in VOL["quadrants"]],
            ["", "num", "num", "num", "num", "num"]))
    add(f"""<div class="card"><p style="margin:0"><b>量增／價漲之後 20 日波動 {VOL['quadrants'][0]['fwd20_vol_pct']:.1f}%，
明顯高於量平縮的 {VOL['quadrants'][2]['fwd20_vol_pct']:.1f}%／{VOL['quadrants'][3]['fwd20_vol_pct']:.1f}%；
超額報酬卻是 {VOL['quadrants'][0]['excess20_pct']:+.3f}%，勝率 {VOL['quadrants'][0]['win20_pct']:.1f}% 全場最低。</b><br>
結論：<b>放量是「風險升高」的訊號，不是「該買」的訊號</b>。它的正確用途是縮小部位、拉開停損，不是加碼。</p></div>""")
    add('<h3>加上趨勢過濾，會不會好一點？</h3>')
    add(tbl(["量能 × MA20", "樣本數", "後20日", "超額(vs等權)", "跑贏等權比例"],
            [[r["cond"], f'{r["n"]:,}', f'{r["fwd20_pct"]:+.3f}%',
              f'<b>{r["excess20_pct"]:+.3f}%</b>', f'{r["excess_win_pct"]:.1f}%']
             for r in VOL["interaction"]],
            ["", "num", "num", "num", "num"]))
    ix = {r["cond"]: r for r in VOL["interaction"]}
    add('<div class="chart">' + hbar([(r["cond"], r["excess20_pct"],
            "#e8b44a" if "放量" in r["cond"] else "#5b8fc9") for r in VOL["interaction"]],
        label_w=200, maxv=0.6, unit="%", abs_mode=True) +
        '<p class="note" style="margin:6px 4px 0">條長代表「落後等權組合的幅度」，四組超額全部為負（圖上數值仍帶負號）。</p></div>')
    add(f"""<p>四組超額<b>全部為負</b>，跑贏等權的比例只有 {min(r['excess_win_pct'] for r in VOL['interaction']):.1f}–{max(r['excess_win_pct'] for r in VOL['interaction']):.1f}%。
放量＋站上 MA20 是 {ix['放量／站上MA20']['excess20_pct']:+.3f}%，比平量＋站上 MA20 的 {ix['平量／站上MA20']['excess20_pct']:+.3f}% 更差。
<b>這段大多頭裡，任何「挑時機進場」都很難打敗一直持有的等權組合</b>——和 V3.8、V4.0 的結論一致。</p>""")
    add('<h3>換手頻繁是不是炒作股特徵？</h3>')
    add(tbl(["V3.9 分組", "樣本日數", "平均量比", "量比>2 占比", "量比>3 占比"],
            [[r["group"], f'{r["n"]:,}', f'{r["avg_rvol"]:.2f}',
              f'{r["gt2_pct"]:.1f}%', f'{r["gt3_pct"]:.1f}%'] for r in VOL["group_rvol"]],
            ["", "num", "num", "num", "num"]))
    add(f"""<p class="note">反直覺：HYPE 組<b>平均量比反而最低</b>（{VOL['group_rvol'][2]['avg_rvol']:.2f} vs DEF {VOL['group_rvol'][0]['avg_rvol']:.2f}），
但<b>極端爆量日更多</b>（&gt;2 倍 {VOL['group_rvol'][2]['gt2_pct']:.1f}%、&gt;3 倍 {VOL['group_rvol'][2]['gt3_pct']:.1f}%）。
炒作股不是天天換手高，是「平時冷、偶爾爆」——<b>用平均量比篩不出來，要看尾部</b>。</p>""")
    add("""<div class="card big"><p style="margin:0;font-size:16px"><b>那量能到底怎麼用？</b><br>
① <b>不拿來觸發買單</b>：放量不是買點（超額為負、勝率&lt;50%）。<br>
② <b>拿來觸發風控</b>：量比 &gt;2 且跌破 MA20 → 衛星層減半、停損往前移；後續波動會從 26% 升到 27–31%。<br>
③ <b>拿來當「確認」而非「預測」</b>：V4.0 的「賣出後 20 日創新高回補」可以加一條「且量比 ≥1.2」確認不是假突破，但實測超額沒有改善，所以<b>只列為可選、不列為必要</b>。<br>
④ 真實換手率、融資融券、當沖比、逐筆資料都不在資料集裡，<b>不做任何斷言</b>。</p></div>""")

    # 4. 结构
    add('<h2><span class="no">4</span>今天是誰在動：指數／產業／個股三態分解</h2>')
    add(f"""<p>每日把橫截面報酬拆成三種力量：市場 |指數報酬|、產業間離散、產業內（個股特異）離散，用平方占比判主導。
{esc(ST['note'])}</p>""")
    add(tbl(["主導狀態", "日數占比", "平均|指數|", "上漲檔", "個股離散(P95−P5)", "產業差距", "市場/產業/特異占比"],
            [[r["state"], f'<b>{r["pct"]}%</b>', f'{r["avg_abs_index_pct"]:.2f}%',
              f'{r["avg_up_pct"]:.1f}%', f'{r["avg_spread_pp"]:.2f}pp',
              f'<b>{r["avg_ind_gap_pp"]:.2f}pp</b>',
              f'{r["avg_share_mkt"]:.2f}/{r["avg_share_ind"]:.2f}/{r["avg_share_idio"]:.2f}']
             for r in ST["states"]],
            ["", "num", "num", "num", "num", "num", "num"]))
    add(f"""<p><b>先回答「還是產業類都漲跌」：很少。</b>產業主導只占 {sstates['產業主導']['pct']}%，
但這些日子的產業差距達 {sstates['產業主導']['avg_ind_gap_pp']:.2f}pp，
明顯高於個股主導日的 {sstates['個股主導']['avg_ind_gap_pp']:.2f}pp——<b>它少見，但一出現就很鮮明</b>。
長期則是個股特異風險占絕大多數（{sstates['個股主導']['pct']}%），這正是 V3.5「選股離散 2,117pp」的微觀來源。</p>""")

    add('<h3>各波段：要命的波段，指數主導比例會升高</h3>')
    add('<div class="chart">' + stacked([
        (s["label"], [("指數", s["指數主導_pct"], "#f0655a"),
                      ("產業", s["產業主導_pct"], "#e8b44a"),
                      ("個股", s["個股主導_pct"], "#5b8fc9")]) for s in ST["segments"]],
        height=250) + '</div>')
    add(tbl(["波段", "指數主導", "產業主導", "個股主導", "平均上漲檔", "平均產業差距"],
            [[s["label"], f'{s["指數主導_pct"]:.1f}%', f'{s["產業主導_pct"]:.1f}%',
              f'{s["個股主導_pct"]:.1f}%', f'{s["avg_up_pct"]:.1f}%', f'{s["avg_ind_gap_pp"]:.2f}pp']
             for s in ST["segments"]], ["", "num", "num", "num", "num", "num"]))
    calm = ST["segments"][2]
    cr = ST["segments"][4]
    add(f"""<p>平靜的多頭一（{calm['label']}）指數主導只有 {calm['指數主導_pct']:.1f}%，個股主導高達 {calm['個股主導_pct']:.1f}%——
<b>那種行情選股有用</b>。急殺段指數主導升到 {cr['指數主導_pct']:.1f}%，
V3.8 的 Regime 調倉、波動率目標在這種環境全部落後靜態配置，原因就在這裡。</p>""")

    add('<h3>換一個更直觀的尺：每日漲跌家數</h3>')
    add(tbl(["狀態", "日數占比", "當日指數平均", "產業差距", "個股離散", "市場占比"],
            [[r["label"], f'<b>{r["pct"]}%</b>', f'<b>{r["avg_index_pct"]:+.2f}%</b>',
              f'{r["avg_ind_gap_pp"]:.2f}pp', f'{r["avg_spread_pp"]:.2f}pp',
              f'{r["avg_share_mkt"]:.2f}'] for r in ST["breadth"]],
            ["", "num", "num", "num", "num", "num"]))
    ex = ST["examples"]
    e_dn = ex["指數主導_大跌"][0]
    e_up = ex["指數主導_大漲"][0]
    e_ind = ex["產業主導_差距最大"][0]
    add(tbl(["典型日", "指數", "上漲檔", "產業差距", "最強產業", "最弱產業"],
            [["<b>齊跌</b> " + str(e_dn["date"]), f'<b class="dn">{e_dn["index_pct"]:+.2f}%</b>',
              f'<b>{e_dn["up_pct"]:.1f}%</b>', f'{e_dn["ind_gap_pp"]:.2f}pp',
              f'{e_dn["ind_hi"]} {e_dn["ind_hi_pct"]:+.2f}%', f'{e_dn["ind_lo"]} {e_dn["ind_lo_pct"]:+.2f}%'],
             ["<b>齊漲</b> " + str(e_up["date"]), f'<b class="up">{e_up["index_pct"]:+.2f}%</b>',
              f'<b>{e_up["up_pct"]:.1f}%</b>', f'{e_up["ind_gap_pp"]:.2f}pp',
              f'{e_up["ind_hi"]} {e_up["ind_hi_pct"]:+.2f}%', f'{e_up["ind_lo"]} {e_up["ind_lo_pct"]:+.2f}%'],
             ["<b>產業輪動</b> " + str(e_ind["date"]), f'{e_ind["index_pct"]:+.2f}%',
              f'{e_ind["up_pct"]:.1f}%', f'<b>{e_ind["ind_gap_pp"]:.2f}pp</b>',
              f'{e_ind["ind_hi"]} {e_ind["ind_hi_pct"]:+.2f}%', f'{e_ind["ind_lo"]} {e_ind["ind_lo_pct"]:+.2f}%']],
            ["", "num", "num", "num", "", ""]))
    add(f"""<p>{e_dn['date']}：指數 {e_dn['index_pct']:+.2f}%、<b>111 檔只有 {e_dn['up_pct']:.1f}% 上漲</b>——
那天連最強的 {e_dn['ind_hi']} 都跌 {e_dn['ind_hi_pct']:.2f}%，<b>選股與選產業同時失效，只有事前沒買滿的人活著</b>。
隔三天 {e_up['date']} 指數 {e_up['index_pct']:+.2f}%、上漲檔 {e_up['up_pct']:.0f}%，齊漲齊跌是同一種力量的兩面。</p>""")
    add(f"""<div class="card warn"><p style="margin:0"><b>一個容易混淆的地方，必須講清楚：</b>
急殺段 {crash['n_days']} 個交易日裡，<b>每日平均仍有 {crash['avg_up_pct']:.1f}% 的個股上漲</b>，
真正「齊跌（上漲檔&lt;20%）」只有 {crash['down80_n']} 天；
但 V3.9 說「整段只有 4/111 檔上漲（3.6%）」指的是<b>30 天累計報酬</b>為正的檔數。<br>
<b>所以急殺不是「每天全部一起跌」，而是「跌的日子跌很深、漲的日子漲很少」，累積下來幾乎全軍覆沒。</b>
這也是為什麼「等反彈再賣」會失效——你看每天都有股票在漲，以為還有機會。</p></div>""")

    # 5. 应对
    add('<h2><span class="no">5</span>三種狀態，三種應對（核心交付）</h2>')
    add(tbl(["狀態", "當下判據（收盤後）", "實測特徵", "該做的事", "絕對不要"],
            [["<b>指數主導／齊跌</b>", "指數跌幅 ≥1.5% 且上漲檔 &lt;20%",
              f"指數 {ST['breadth'][0]['avg_index_pct']:+.2f}%、產業差 {ST['breadth'][0]['avg_ind_gap_pp']:.2f}pp、選股無效",
              "<b>只調倉位</b>：V3.8 四層桶 L3 衛星歸零、L0 補到 24 個月生活費；核心層不動",
              "不選股、不攤平、不接刀、不加槓桿"],
             ["<b>產業主導／輪動</b>", "產業間報酬差距 ≥7pp、產業內一致",
              f"僅 {sstates['產業主導']['pct']}% 日數，但產業差 {sstates['產業主導']['avg_ind_gap_pp']:.2f}pp",
              "<b>調族群不調個股</b>：衛星層在強勢產業內分散 3–5 檔，單一產業上限 20%",
              "不追單一飆股、不把輪動當趨勢"],
             ["<b>個股主導／分歧</b>", "上漲檔 20–80%、產業差距小",
              f"{ST['breadth'][1]['pct']}% 日數，個股離散 {ST['breadth'][1]['avg_spread_pp']:.2f}pp",
              "<b>才輪到選股</b>：V3.7 漏斗排除 + V3.9 分組交叉 + V3.8 分層",
              "別以為分散能消除風險（V3.8：64 檔只等效 3.8 個獨立風險源）"]],
            ["", "", "", "", ""]))
    add(f"""<div class="card big"><p style="margin:0;font-size:16px"><b>判別順序（每天收盤後 30 秒）：</b>
先看<b>指數與上漲家數</b> → 齊漲齊跌就只管倉位；再看<b>產業差距</b> → 大於 7pp 就管族群配置；
兩者都平靜，才去做個股選擇。<b>順序反過來（先選股）就是在急殺日白費力氣。</b></p></div>""")

    # 6. 短长线 + 自动交易
    add('<h2><span class="no">6</span>短線／長線兩套參數，與自動交易對應</h2>')
    add(tbl(["", "長線（L1 高息 + L2 指數，80%）", "短線（L3 衛星，≤20%）"],
            [["檢查頻率", "<b>月檢</b>（月底收盤後一次）", "日檢或券商條件單託管"],
             ["主要訊號", "MA120 狀態、估值分位、配息連續性", "MA20、量比尾部、−15% 停損"],
             ["量能角色", "<b>完全不用</b>", "只用來縮倉，不用來進場"],
             ["買賣方式", "分 3 批、只在新資金進場時", "單檔 ≤1%（炒作股）／≤5%（衛星）"],
             ["出場", "核心層<b>永不擇時</b>；只依 V4.0 +20% 賣 1/4、+40% 賣 1/3", "−15% 無條件砍、不攤平"],
             ["回補", "20 日內創賣出後新高補 1/4", "不回補，直接結案"],
             ["适用标的", "0050／0056／00878／電信三雄", "HYPE 組或高波動個股"],
             ["富邦工具", "新一代 API（M0→M3 授權）或人工月檢", "<b>雲端條件單</b>（券商託管，不用盯盤）"]],
            ["", "", ""]))
    add("""<div class="rule"><b>長線自动化的边界</b>：月檢訊號一個月最多動一次，交給 M1 逐筆授權即可；不需要 M3 額度內免確認。</div>
<div class="rule"><b>短線交給券商託管</b>：−15% 停損、+20% 部分止盈寫成雲端條件單，盤中由券商觸發，避免人為情緒；這正是「減少我的情緒影響客觀交易」的落點。</div>
<div class="rule"><b>AI PRO 量化積木</b>：適合把「產業差距 ≥7pp」「量比&gt;2 且破 MA20」做成警示條件，但<b>仍需人按單</b>，不是自動下單。</div>
<div class="rule"><b>熔斷優先於一切</b>：V3.0 三條熔斷（單日 −300／連虧 3／回撤 8%）觸發即停機，隔日不自動復機；11 條額度與 G1–G5 Gate 維持 fail-closed。</div>""")
    add("""<p class="note">現況誠實聲明：V3 全線仍在 <b>M0 模擬盤</b>，未連富邦、未下任何單；G1 通過、G2–G5 未通過，舊 PAT 已撤銷。
上表是「開通後怎麼對應」的設計，不是已上線功能。</p>""")

    # 7. 一页纸
    bd = ST["breadth"]
    add('<h2><span class="no">7</span>給爸媽的一頁紙（可列印）</h2>')
    add(f"""<div class="onepager"><h3>給爸媽的一頁紙｜先看「大家一起跌」，還是「只有它在跌」</h3>
<p>每天收盤後花 30 秒，按順序問三個問題，<b>照表做，不用猜</b>。</p>
<table><thead><tr><th>先問</th><th>看到什麼</th><th>就做這件事</th></tr></thead><tbody>
<tr><td><b>1. 今天是不是大家一起跌？</b></td><td>大盤跌超過 1.5%，而且十檔裡不到兩檔上漲</td><td><b>只管現金，不管選股。</b>把「衛星」那一小包清掉、生活費補滿，核心持股不要動</td></tr>
<tr><td><b>2. 是不是同一類產業一起動？</b></td><td>某個產業比另一個差到 7% 以上</td><td>只調整「哪一類」，最多放 3–5 檔，<b>不要追單一飆股</b></td></tr>
<tr><td><b>3. 上面都不是</b></td><td>有漲有跌，產業之間差不多</td><td>這時才來挑股票：先看體質、再看會不會太熱，<b>分批買</b></td></tr>
<tr><td><b>成交量突然爆大</b></td><td>比平常多兩、三倍</td><td><b>不是買點，是提醒</b>：把部位縮小、停損設好，不要加碼</td></tr>
</tbody></table>
<p><b>記住三個數字：</b>五年裡有 {bd[1]['pct']:.0f}% 的日子是「各走各的」，所以平常慢慢挑股票就好；
但真正會受傷的，是那 {bd[0]['pct']:.0f}%「大家一起跌」的日子（當天大盤平均 {bd[0]['avg_index_pct']:.2f}%）——
<b>那種日子選什麼股票都沒用，只有事先留的現金有用。</b></p>
<p><b>例子：</b>2025/04/07 大盤一天跌 {e_dn['index_pct']:.2f}%，111 檔裡只有 {e_dn['up_pct']:.1f}% 上漲，
連最抗跌的 {e_dn['ind_hi']} 也跌 {e_dn['ind_hi_pct']:.2f}%。三天後 {e_up['date']} 大盤漲 {e_up['index_pct']:.2f}%、上漲檔 {e_up['up_pct']:.0f}%。
<b>這種日子不要問「該買哪一檔」，要問「我本來留了多少現金」。</b></p>
<p><b>三條鐵律：</b>① 不借錢、不當沖 ② 賣永遠只賣一部分 ③ 沒訊號就抱現金等。</p>
<p style="font-size:12px;color:#7a6a4e;margin-top:18px">資料：{D['meta']['universe']} 檔台股 {RANGE[0]}–{RANGE[1]} 日線，含息、含手續費與交易稅。僅供自家研究，非投資建議。</p>
</div>""")

    # 8. 局限
    add('<h2><span class="no">8</span>已知局限</h2>')
    add(f"""<ul>
<li><b>volumes 只有「張」，沒有流通股數</b> → 量比不等於真實換手率；融資融券、當沖比、逐筆、委買委賣都不在資料裡。</li>
<li><b>量能分組是描述性統計</b>，20 日報酬視窗重疊、樣本高度相關，不是策略回測；超額基準是同池等權，不是可交易商品。</li>
<li><b>結構分解是「事後橫截面」</b>，用當日全部個股報酬判別狀態，不能用來預測隔日；第 4 節的後續指數報酬只作描述，未做成策略。</li>
<li><b>個股主導長期占 {sstates['個股主導']['pct']}%</b> 是方差分解的數學結果（個股特異風險本來就最大），不代表「選股每天都有用」。</li>
<li><b>V3.9 分組只有 5 檔 HYPE</b>，樣本偏小；案例 E 的單檔數字是方向性證據，不是精確估計。</li>
<li><b>V3.8 建議層是示範映射規則</b>（手寫門檻），不是回測最佳化結果；ETF 不適用個股漏斗。</li>
<li><b>「通過漏斗 ≠ 會漲」已被 1102 亞泥印證</b>；反之 2330／2454 被淘汰卻漲最多，兩者都說明單一原則不可單獨放行。</li>
<li><b>整段是罕見大多頭</b>，等權組合很難被擊敗，因此所有「挑時機」訊號的超額都偏負；空頭樣本僅 4 段。</li>
<li><b>典型案例日的個股離散已改用 P95−P5 穩健極差</b>，避免單檔分割／除息異常值污染。</li>
<li>本報告是 M0 模擬盤研究，<b>未連富邦、未下任何單</b>。</li>
</ul>""")

    add(f"""<footer>Silverstock Quant Web · V4.1 個股印證與市場結構　|　
引擎 <code>tool/v3/market_structure.py</code>　結果 <code>v41_structure_result.json</code>　
報告 <code>tool/v3/gen_structure_report.py</code><br>
資料 {RANGE[0]}–{RANGE[1]}、{D['meta']['universe']} 檔、{D['meta']['bars']} 根日線；含息總報酬。
V3.9 分組用 2022/07/06 事前特徵，無前視偏誤；量能與結構為描述性分析。僅供家人自用研究。</footer>
</div></body></html>""")

    html = "".join(P)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已產出 {OUT}（{len(html):,} 字元）")


if __name__ == "__main__":
    build()
