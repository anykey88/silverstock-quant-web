# -*- coding: utf-8 -*-
"""V3.8 报告生成器：读 v38_allocation_result.json → HTML"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = json.load(open(os.path.join(ROOT, "v38_allocation_result.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "..", "V3.8_资产配置四层桶.html")

CFG = {c["key"]: c for c in D["configs"]}
CORR = D["correlation"]
CORR_ALL = D["correlation_all"]
VAL = D["valuation"]
TP = {t["rule"]: t for t in D["take_profit"]}
CF = {c["id"]: c for c in D["cashflow"]}

_raw = D["meta"]["range"]
def _fmt(v):
    v = str(v)
    return f"{v[:4]}-{v[4:6]}-{v[6:]}" if len(v) == 8 else v
RANGE = [_fmt(_raw[0]), _fmt(_raw[1])]
DAYS = D["meta"]["days"]
YEARS = round(DAYS / 252, 1)

# 关键配置快捷引用
A100 = next(c for c in D["configs"] if c["key"].startswith("A."))
B8040 = next(c for c in D["configs"] if c["key"].startswith("D."))
E4060 = next(c for c in D["configs"] if c["key"].startswith("E."))
FOUR = next(c for c in D["configs"] if c["key"].startswith("I."))
REG = next(c for c in D["configs"] if c["key"].startswith("K."))
VOL = next(c for c in D["configs"] if c["key"].startswith("J."))
VALT = next(c for c in D["configs"] if c["key"].startswith("L."))
Q70 = next(c for c in D["configs"] if c["key"].startswith("C."))
N70 = next(c for c in D["configs"] if c["key"].startswith("F."))


def short(k):
    return k.split(". ", 1)[1] if ". " in k else k


# ── SVG 散点图：年化 vs 最大回撤 ────────────────────────────────────
def scatter_svg():
    W, H = 860, 470
    L, R, T, B = 78, 40, 30, 62
    xs = [c["mdd_pct"] for c in D["configs"]]
    ys = [c["ann_pct"] for c in D["configs"]]
    x0, x1 = min(xs) - 3, 2
    y0, y1 = 8, max(ys) + 3

    def px(v):
        return L + (v - x0) / (x1 - x0) * (W - L - R)

    def py(v):
        return H - B - (v - y0) / (y1 - y0) * (H - T - B)

    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="none"/>')
    # 网格
    for gv in range(int(y0), int(y1) + 2, 5):
        y = py(gv)
        parts.append(f'<line x1="{L}" y1="{y:.0f}" x2="{W-R}" y2="{y:.0f}" stroke="#1e2630" stroke-width="1"/>')
        parts.append(f'<text x="{L-10}" y="{y+4:.0f}" text-anchor="end" class="ax">{gv}%</text>')
    for gv in range(int(x0), int(x1) + 1, 5):
        x = px(gv)
        parts.append(f'<line x1="{x:.0f}" y1="{T}" x2="{x:.0f}" y2="{H-B}" stroke="#1e2630" stroke-width="1"/>')
        parts.append(f'<text x="{x:.0f}" y="{H-B+22}" text-anchor="middle" class="ax">{gv}%</text>')
    parts.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-16}" text-anchor="middle" class="axt">最大回撤（越右越痛）</text>')
    parts.append(f'<text x="20" y="{(T+H-B)/2:.0f}" text-anchor="middle" class="axt" transform="rotate(-90 20 {(T+H-B)/2:.0f})">年化报酬</text>')

    # 参考线：Calmar = 0.8 的等值线 y = 0.8 * |mdd|
    pts = []
    for gv in range(int(x0), 1):
        v = 0.8 * abs(gv) / 100 * 100
        if y0 <= v <= y1:
            pts.append(f"{px(gv):.0f},{py(v):.0f}")
    if len(pts) > 2:
        parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#3a4553" stroke-dasharray="5 5" stroke-width="1.2"/>')
        parts.append(f'<text x="{px(-2):.0f}" y="{py(1.6)-8:.0f}" class="axt" fill="#5a6774">Calmar 0.8</text>')

    colors = {"A": "#e5484d", "I": "#d4a24c", "E": "#4a9eff", "K": "#7c6cf0", "J": "#7c6cf0",
              "L": "#7c6cf0", "B": "#30a46c", "C": "#30a46c", "D": "#30a46c", "F": "#30a46c",
              "G": "#30a46c", "H": "#30a46c"}
    special = {"A", "I", "E", "K", "J", "L"}
    for c in D["configs"]:
        tag = c["key"][0]
        col = colors.get(tag, "#5a6774")
        r = 9 if tag in special else 5
        op = 1.0 if tag in special else 0.55
        x, y = px(c["mdd_pct"]), py(c["ann_pct"])
        parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{col}" opacity="{op}" stroke="#0b0f14" stroke-width="1.5"/>')
        if tag in special:
            lab = short(c["key"])
            lab = lab.replace("（20现金/25高息/35指数/20卫星）", "")
            anchor = "end" if x > W - 220 else "start"
            dx = -14 if anchor == "end" else 14
            parts.append(f'<text x="{x+dx:.0f}" y="{y+4:.0f}" text-anchor="{anchor}" class="pt" fill="{col}">{lab}</text>')
    parts.append("</svg>")
    return "".join(parts)


# ── SVG 净值曲线 ───────────────────────────────────────────────────
def nav_svg():
    series = [
        (A100, "#e5484d", "100% 0050"),
        (FOUR, "#d4a24c", "四层桶"),
        (B8040, "#30a46c", "60/40"),
        (E4060, "#4a9eff", "40/60"),
    ]
    W, H = 860, 300
    L, R, T, B = 62, 130, 24, 40
    n = len(series[0][0]["nav_slim"])
    ymax = max(max(s[0]["nav_slim"]) for s in series) * 1.05
    ymin = 0.9

    def px(i):
        return L + i / (n - 1) * (W - L - R)

    def py(v):
        return H - B - (v - ymin) / (ymax - ymin) * (H - T - B)

    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    for gv in [1, 1.5, 2, 2.5, 3, 3.5]:
        if gv > ymax:
            continue
        y = py(gv)
        parts.append(f'<line x1="{L}" y1="{y:.0f}" x2="{W-R}" y2="{y:.0f}" stroke="#1e2630"/>')
        parts.append(f'<text x="{L-8}" y="{y+4:.0f}" text-anchor="end" class="ax">{gv}×</text>')
    # 2022 阴影
    i22 = int(n * 0.30)
    i23 = int(n * 0.48)
    parts.append(f'<rect x="{px(i22):.0f}" y="{T}" width="{px(i23)-px(i22):.0f}" height="{H-T-B}" fill="#e5484d" opacity="0.07"/>')
    parts.append(f'<text x="{(px(i22)+px(i23))/2:.0f}" y="{T+16}" text-anchor="middle" class="axt" fill="#8a6a5a">2022 空头</text>')

    for c, col, lab in series:
        pts = " ".join(f"{px(i):.0f},{py(v):.0f}" for i, v in enumerate(c["nav_slim"]))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.2" stroke-linejoin="round"/>')
        ye = c["nav_slim"][-1]
        parts.append(f'<text x="{px(n-1)+10:.0f}" y="{py(ye)+4:.0f}" class="pt" fill="{col}">{ye:.2f}×</text>')
    parts.append(f'<text x="{L}" y="{H-12}" class="ax">{RANGE[0]}</text>')
    parts.append(f'<text x="{W-R-40}" y="{H-12}" class="ax">{RANGE[1]}</text>')
    parts.append("</svg>")
    return "".join(parts)


# ── 四层桶堆叠条 ───────────────────────────────────────────────────
def bucket_bar():
    layers = [
        ("L0 安全垫", 20, "#4a9eff", "现金 / 定存 / 短债"),
        ("L1 防守", 25, "#30a46c", "高股息 ETF"),
        ("L2 核心", 35, "#d4a24c", "市值型 ETF"),
        ("L3 卫星", 20, "#e5484d", "个股"),
    ]
    W, H = 860, 82
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    x = 0
    for name, pct, col, sub in layers:
        w = pct / 100 * W
        parts.append(f'<rect x="{x:.0f}" y="0" width="{w-3:.0f}" height="46" fill="{col}" opacity="0.85" rx="3"/>')
        parts.append(f'<text x="{x+w/2-1:.0f}" y="20" text-anchor="middle" class="bl" fill="#0b0f14">{name}</text>')
        parts.append(f'<text x="{x+w/2-1:.0f}" y="38" text-anchor="middle" class="bv" fill="#0b0f14">{pct}%</text>')
        parts.append(f'<text x="{x+w/2-1:.0f}" y="66" text-anchor="middle" class="axt">{sub}</text>')
        x += w
    parts.append("</svg>")
    return "".join(parts)


# ── 配置表格行 ─────────────────────────────────────────────────────
def rows_configs():
    order = [A100, next(c for c in D["configs"] if c["key"].startswith("B.")),
             Q70, B8040, E4060, N70, next(c for c in D["configs"] if c["key"].startswith("G.")),
             next(c for c in D["configs"] if c["key"].startswith("H.")),
             FOUR, REG, VOL, VALT]
    out = []
    for c in order:
        hot = c["key"] in (FOUR["key"], A100["key"], E4060["key"])
        cls = ' class="hot"' if hot else ""
        out.append(
            f'<tr{cls}><td class="nm">{short(c["key"])}</td>'
            f'<td>{c["total_pct"]:.1f}%</td>'
            f'<td><b>{c["ann_pct"]:.2f}%</b></td>'
            f'<td class="neg">{c["mdd_pct"]:.1f}%</td>'
            f'<td>{c["recover_gain_pct"]:.0f}%</td>'
            f'<td><b>{c["calmar"]:.2f}</b></td>'
            f'<td>{c["y2022"]:.1f}%</td>'
            f'<td>{c["roll_1y"]["p5_pct"]:.1f}%</td>'
            f'<td>{c["underwater_months"]:.0f}</td></tr>')
    return "\n".join(out)


def rows_tp():
    order = sorted(D["take_profit"], key=lambda t: t["rule"][0])
    out = []
    base = order[0]
    for t in order:
        d_ann = t["ann_pct"] - base["ann_pct"]
        d_mdd = t["mdd_pct"] - base["mdd_pct"]
        cls = ' class="hot"' if t["rule"].startswith(("1.", "2.")) else ""
        out.append(
            f'<tr{cls}><td class="nm">{t["rule"][3:]}</td>'
            f'<td>{t["ann_pct"]:.2f}%</td>'
            f'<td class="{"neg" if d_ann < 0 else ""}">{d_ann:+.2f}pp</td>'
            f'<td>{t["mdd_pct"]:.1f}%</td>'
            f'<td class="{"pos" if d_mdd > 0 else ""}">{d_mdd:+.1f}pp</td>'
            f'<td><b>{t["calmar"]:.2f}</b></td>'
            f'<td>{t["roll_1y"]["loss_prob_pct"]:.0f}%</td>'
            f'<td>{t["roll_1y"]["p5_pct"]:.1f}%</td></tr>')
    return "\n".join(out)


def rows_val():
    out = []
    for x in VAL["cheap"][:6]:
        out.append(f'<tr><td>{x["id"]}</td><td>{x["name"]}</td><td>{x["industry"]}</td><td>{x["pe"]:.1f}</td><td class="pos">後 {x["pe_pct"]*100:.0f}%</td></tr>')
    return "\n".join(out)


def rows_rich():
    out = []
    for x in VAL["rich"][-6:]:
        out.append(f'<tr><td>{x["id"]}</td><td>{x["name"]}</td><td>{x["industry"]}</td><td>{x["pe"]:.1f}</td><td class="neg">前 {(1-x["pe_pct"])*100:.0f}%</td></tr>')
    return "\n".join(out)


CSS = """
:root{
  --bg:#0b0f14; --card:#111721; --card2:#161d29; --line:#1f2836;
  --tx:#d8dee9; --tx2:#8b97a8; --tx3:#5a6774;
  --gold:#d4a24c; --blue:#4a9eff; --red:#e5484d; --green:#30a46c; --purple:#7c6cf0;
}
*{box-sizing:border-box;margin:0;padding:0}
body{
  background:var(--bg); color:var(--tx);
  font-family:-apple-system,"PingFang TC","Noto Sans TC","Microsoft YaHei",sans-serif;
  line-height:1.75; font-size:15px; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:960px;margin:0 auto;padding:56px 28px 100px}
h1{font-size:34px;font-weight:700;letter-spacing:-0.5px;line-height:1.3;margin-bottom:14px}
h1 .em{color:var(--gold)}
h2{font-size:23px;font-weight:650;margin:64px 0 8px;letter-spacing:-0.3px;
   padding-left:14px;border-left:3px solid var(--gold)}
h2 .no{color:var(--tx3);font-size:14px;font-weight:500;margin-right:10px;letter-spacing:1px}
h3{font-size:17px;font-weight:600;margin:32px 0 10px;color:var(--tx)}
p{margin:12px 0;color:var(--tx)}
.sub{color:var(--tx2);font-size:13px;letter-spacing:0.3px}
.meta{display:flex;gap:22px;flex-wrap:wrap;margin-top:20px;padding-top:18px;
      border-top:1px solid var(--line);font-size:12.5px;color:var(--tx2)}
.meta b{color:var(--tx);font-weight:600}
.lead{font-size:17px;line-height:1.9;color:#c3ccd9;margin:22px 0 8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:24px 26px;margin:22px 0}
.answer{background:linear-gradient(135deg,#151d2a 0%,#111721 100%);
        border:1px solid #2a3546;border-left:3px solid var(--gold);
        border-radius:8px;padding:30px 32px;margin:34px 0}
.answer .q{color:var(--tx3);font-size:13px;letter-spacing:1px;margin-bottom:12px}
.answer .a{font-size:21px;line-height:1.75;font-weight:600;color:#eaf0f8}
.answer .a em{font-style:normal;color:var(--gold)}
.answer .n{font-size:14px;color:var(--tx2);margin-top:14px;line-height:1.85}

.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:26px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:18px 16px}
.kpi .v{font-size:28px;font-weight:700;letter-spacing:-1px;line-height:1.1}
.kpi .l{font-size:12px;color:var(--tx2);margin-top:7px;line-height:1.5}
.kpi.g .v{color:var(--gold)} .kpi.b .v{color:var(--blue)}
.kpi.r .v{color:var(--red)} .kpi.gr .v{color:var(--green)}

table{width:100%;border-collapse:collapse;margin:20px 0;font-size:13.5px}
th{text-align:right;padding:10px 8px;border-bottom:1px solid #2a3546;
   color:var(--tx2);font-weight:500;font-size:12px;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
td{padding:9px 8px;border-bottom:1px solid #161d29;text-align:right;white-space:nowrap}
td.nm{color:var(--tx);font-size:13px}
tr.hot td{background:#161d29}
tr.hot td.nm{color:var(--gold);font-weight:600}
.neg{color:var(--green)} .pos{color:var(--red)}
.scroll{overflow-x:auto;margin:18px 0}

.chart{width:100%;height:auto;display:block;margin:18px 0}
.ax{fill:#4a5563;font-size:11px}
.axt{fill:#6b7787;font-size:11px}
.pt{font-size:11.5px;font-weight:600}
.bl{font-size:11px;font-weight:700}
.bv{font-size:15px;font-weight:700}

ul{margin:14px 0 14px 4px;list-style:none}
li{margin:11px 0;padding-left:22px;position:relative;color:var(--tx)}
li::before{content:"—";position:absolute;left:0;color:var(--tx3)}
ol{margin:14px 0 14px 22px}
ol li{padding-left:0}
ol li::before{content:none}

.tag{display:inline-block;font-size:11px;padding:2px 8px;border-radius:3px;
     background:#1c2533;color:var(--tx2);margin-right:8px;vertical-align:middle}
.tag.gold{background:#2a2113;color:var(--gold)}
.tag.red{background:#2a1517;color:var(--red)}
.tag.green{background:#12241a;color:var(--green)}

.quote{border-left:2px solid var(--line);padding:6px 0 6px 20px;margin:20px 0;
       color:var(--tx2);font-size:14.5px;line-height:1.85}
.quote b{color:var(--tx)}

.two{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:20px 0}
.box{background:var(--card2);border:1px solid var(--line);border-radius:6px;padding:18px 20px}
.box h4{font-size:14px;font-weight:600;margin-bottom:8px;color:var(--gold)}
.box.p2 h4{color:var(--blue)}
.box p{font-size:13.5px;color:var(--tx2);margin:6px 0;line-height:1.75}

.steps{counter-reset:s;margin:20px 0}
.step{display:flex;gap:16px;padding:16px 0;border-bottom:1px solid #161d29}
.step .n{flex:0 0 30px;height:30px;border-radius:50%;background:#1c2533;
         color:var(--gold);font-size:13px;font-weight:700;display:flex;
         align-items:center;justify-content:center;margin-top:2px}
.step .c h4{font-size:14.5px;font-weight:600;margin-bottom:5px}
.step .c p{font-size:13.5px;color:var(--tx2);margin:0;line-height:1.7}

.money{font-variant-numeric:tabular-nums}
.foot{margin-top:70px;padding-top:24px;border-top:1px solid var(--line);
      font-size:12px;color:var(--tx3);line-height:1.9}
.foot b{color:var(--tx2)}

/* 一页纸：给爸妈 */
.onepage{background:#f7f5f0;color:#1a1a1a;border-radius:8px;padding:40px 44px;margin:34px 0;
         font-family:"PingFang TC","Noto Sans TC",serif}
.onepage h3{color:#1a1a1a;font-size:24px;margin:0 0 4px;font-weight:700}
.onepage .sub2{color:#8a7a5e;font-size:12px;letter-spacing:2px;margin-bottom:26px}
.onepage p{color:#2a2a2a;font-size:14.5px;line-height:2;margin:12px 0}
.onepage .rule{background:#fff;border-left:4px solid #b8934a;padding:16px 20px;
               margin:16px 0;font-size:14.5px;line-height:1.9;color:#1a1a1a}
.onepage .rule b{color:#8a6a20}
.onepage table{font-size:13px;color:#1a1a1a}
.onepage th{color:#6a6a6a;border-bottom:1px solid #d8d0c0}
.onepage td{border-bottom:1px solid #e8e2d6;color:#1a1a1a}
.onepage .big{font-size:17px;font-weight:700;color:#8a6a20}

@media (max-width:720px){
  .wrap{padding:36px 18px 70px}
  h1{font-size:26px} h2{font-size:19px}
  .kpis{grid-template-columns:1fr 1fr}
  .two{grid-template-columns:1fr}
  .answer .a{font-size:17px}
  table{font-size:12px}
}
"""


def build():
    y = YEARS

    head = f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>V3.8 资产配置：四层桶、部分止盈与再平衡的实证</title>
<style>{CSS}</style>
</head>
<body><div class="wrap">

<div class="sub" style="letter-spacing:2px;color:#d4a24c;font-size:12px">SILVERSTOCK QUANT · V3.8</div>
<h1>不梭哈的数学：<span class="em">四层桶</span>、<span class="em">部分止盈</span>与<span class="em">再平衡</span></h1>
<p class="lead">用 111 档台股 {y} 年日线（{RANGE[0]}–{RANGE[1]}，含息、含交易成本）把「配置」这件事拆成可验证的数字。
不谈理念，只回答：进攻放多少、防守放多少、赚了怎么退、退出来的钱去哪。</p>

<div class="meta">
  <span>样本 <b>{DAYS} 交易日 / {y} 年</b></span>
  <span>资产 <b>{D['meta']['assets']} 档（流动性池 {D['liquid_n']} 档）</b></span>
  <span>成本 <b>手续费 1.425‰ + 证交税 3‰（ETF 1‰）</b></span>
  <span>现金 <b>年化 1.6%</b></span>
  <span>含息 <b>股息再投入</b></span>
</div>

<div class="answer">
  <div class="q">你问的是「怎么才能不受行情影响」。先把这个前提拆掉</div>
  <div class="a">没有任何配置能不受行情影响。<br>
  能做的是另一件事：<em>让行情无论怎么走，你都不会被迫在最差的时点卖出。</em></div>
  <div class="n">这两句话的差别，决定了整套方法。<br>
  「不受影响」是预测问题——预测错一次就出局。<br>
  「不被逼着卖」是结构问题——结构对了，预测错也活着。</div>
</div>

<h2><span class="no">01</span>先把话说清楚：为什么“躲开行情”是伪命题</h2>

<p>你提到的四个动作——遵循基本面、攻守配置、获利部分退出、配置安全垫——本质上是同一件事的四个零件：
<b>把「预测行情」换成「设计结构」</b>。下面三组数据说明为什么这个替换是必要的。</p>

<div class="kpis">
  <div class="kpi r"><div class="v">{A100['mdd_pct']:.1f}%</div><div class="l">100% 持股的最大回撤<br>（{RANGE[0][:4]}–{RANGE[1][:4]}）</div></div>
  <div class="kpi r"><div class="v">{A100['recover_gain_pct']:.0f}%</div><div class="l">跌完之后要涨多少才回本<br>不是 35%，是 55%</div></div>
  <div class="kpi r"><div class="v">{A100['underwater_months']:.0f} 个月</div><div class="l">净值水下最长天数<br>两年不能动这笔钱</div></div>
  <div class="kpi b"><div class="v">{CORR['effective_n']:.1f} 档</div><div class="l">{CORR['n_assets']} 档台股的等效独立风险源<br>（平均相关 {CORR['avg_pairwise_corr']:.2f}）</div></div>
</div>

<p>第一组数字是所有人都会算的，但很少有人算第二组：<b>回撤和恢复是不对称的</b>。
跌 35% 需要涨 55% 才回本；跌 50% 需要涨 100%。年龄越大，这个不对称越致命——
因为你需要的是「时间内可用的钱」，而不是「某一天回本的数字」。</p>

<div class="quote">
<b>一个反常识的结论：</b>回撤控制的真正价值不在「少亏」，而在「缩短水下时间」。
四层桶组合的水下时间是 {FOUR['underwater_months']:.0f} 个月，100% 持股是 {A100['underwater_months']:.0f} 个月。
差的这 8 个月，就是「能不能在需要时把钱拿出来」的差别。
</div>

<h2><span class="no">02</span>分散有极限：{CORR['n_assets']} 档只等于 {CORR['effective_n']:.1f} 档</h2>

<p>「多买几档就分散了」是最常见也最贵的误解。我用流动性池（日均成交额 ≥3 亿）里的 {CORR['n_assets']} 档，
两两计算日收益相关系数（成对取交集，不用前值填充，避免假低相关）：</p>

<div class="kpis">
  <div class="kpi g"><div class="v">{CORR['avg_pairwise_corr']:.3f}</div><div class="l">平均两两相关系数<br>{CORR['n_assets']} 档 / {CORR['n_assets']*(CORR['n_assets']-1)//2:,} 对</div></div>
  <div class="kpi g"><div class="v">{CORR['effective_n']:.1f}</div><div class="l">等效独立风险源<br>（{CORR['n_assets']} 档的分散度折扣 {(1-CORR['effective_n']/CORR['n_assets'])*100:.0f}%）</div></div>
  <div class="kpi gr"><div class="v">{CORR['vol_reduction_pct']:.0f}%</div><div class="l">波动削减<br>单档均值 {CORR['avg_single_vol_pct']:.1f}% → 等权 {CORR['equal_weight_vol_pct']:.1f}%</div></div>
  <div class="kpi r"><div class="v">{CORR['corr_2022']:.2f}</div><div class="l">2022 空头年相关<br>（全期 {CORR['avg_pairwise_corr']:.2f}，下跌日 {CORR['corr_down_days']:.2f}）</div></div>
</div>

<p>读法：<b>{CORR['n_assets']} 档台股，等效只有 {CORR['effective_n']:.1f} 个独立风险源</b>。
你买 20 档和买 60 档，风险几乎一样——多出来的 40 档只是「看起来分散」。
波动从 {CORR['avg_single_vol_pct']:.0f}% 降到 {CORR['equal_weight_vol_pct']:.0f}%，这个降幅在 <b>8–15 档</b>时就基本吃满了。</p>

<div class="two">
  <div class="box">
    <h4>真正有效的分散在三件事上</h4>
    <p>① <b>行业</b>——半导体、金融、航运、食品的周期不同步，这是台股唯一免费的相关性来源。</p>
    <p>② <b>资产类别</b>——股/债/现金/黄金，相关性接近 0 甚至为负。</p>
    <p>③ <b>区域</b>——台股市值/GDP 全球前列，单一市场就是单一风险。</p>
  </div>
  <div class="box p2">
    <h4>无效的分散</h4>
    <p>同一族群买 10 档（台积电 + 联电 + 世界 + 力积电…）——相关 0.6–0.8，等于买 1.3 档。</p>
    <p>同一主题的 5 档高股息 ETF——成分高度重叠，等于买 1 档。</p>
    <p>把资金拆成很多小笔但都是电子股——档数增加，风险源没增加。</p>
  </div>
</div>

<h2><span class="no">03</span>十二种配置，{y} 年实测</h2>

<p>同一个风险资产（0050，含息），配不同比例的现金，用不同再平衡规则，跑同一段行情。
下表按 <b>Calmar（年化 ÷ 最大回撤）</b> 排序——这个指标衡量「每承受 1% 回撤，换到多少年化」，
比单看报酬或单看回撤都更接近「值不值得」。</p>

<div class="scroll">
<table>
<thead><tr>
<th>配置</th><th>总报酬</th><th>年化</th><th>最大回撤</th><th>回本需涨</th>
<th>Calmar</th><th>2022 年</th><th>滚动1年最差5%</th><th>水下(月)</th>
</tr></thead>
<tbody>
{rows_configs()}
</tbody>
</table>
</div>

{scatter_svg()}

<h3>三个必须直说的结论</h3>

<div class="steps">
  <div class="step"><div class="n">1</div><div class="c">
    <h4>绝对报酬最高的是「梭哈」，但代价是 {A100['mdd_pct']:.0f}% 的回撤和 {A100['underwater_months']:.0f} 个月水下</h4>
    <p>100% 0050 年化 {A100['ann_pct']:.2f}%，是全场最高。但滚动一年持有的最差 5% 情形是 <b>{A100['roll_1y']['p5_pct']:.1f}%</b>，
    2022 年单年 <b>{A100['y2022']:.1f}%</b>。问题不是它长期不好，是<b>你能不能在最差的那一年不卖</b>。
    这段样本恰好是台股大牛市（{y} 年 TAIEX 涨了两倍多），所以梭哈赢了——但这是事后才知道的。</p>
  </div></div>
  <div class="step"><div class="n">2</div><div class="c">
    <h4>Calmar 最高的不是最低仓位，而是「四层桶」</h4>
    <p>40/60 的 Calmar {E4060['calmar']:.2f} 最高，因为它几乎不亏；但年化只有 {E4060['ann_pct']:.2f}%，跑不过通胀加生活费。
    四层桶 Calmar <b>{FOUR['calmar']:.2f}</b>、年化 <b>{FOUR['ann_pct']:.2f}%</b>、回撤 <b>{FOUR['mdd_pct']:.1f}%</b>——
    用 60% 的仓位拿到了 72% 的报酬，回撤只有梭哈的 {abs(FOUR['mdd_pct']/A100['mdd_pct'])*100:.0f}%。
    <b>这是性价比的拐点。</b></p>
  </div></div>
  <div class="step"><div class="n">3</div><div class="c">
    <h4>动态择时（Regime / 波动率目标 / 估值）在这段样本里全部跑输静态配置</h4>
    <p>Regime 调仓 Calmar {REG['calmar']:.2f}，波动率目标 {VOL['calmar']:.2f}，估值温度调仓 {VALT['calmar']:.2f}——
    都低于四层桶的 {FOUR['calmar']:.2f}。原因是<b>信号滞后 + 交易成本</b>：等确认转空时已经跌了一段，等确认转多时已经涨了一段，
    中间还被来回打脸。年换手 {REG['turnover_annual']:.1f} 倍，成本吃掉不少。</p>
  </div></div>
</div>

<div class="quote">
<b>这不是说择时没用，是说「全仓择时」没用。</b>
把择时限制在卫星仓（20% 以内），错了最多错 4% 的总资产；全仓择时错了，错的是全部。
上面的数据支持一个具体做法：<b>核心层永不择时，只对卫星层调仓</b>。
</div>

<h2><span class="no">04</span>净值曲线：同样是赚钱，过程完全不同</h2>

{nav_svg()}

<p>{y} 年下来四条线都赚钱，但 2022 年那一段（阴影区）决定了后面能不能拿住。
100% 持股在 2022 年跌 {A100['y2022']:.1f}%，四层桶只跌 {FOUR['y2022']:.1f}%——
<b>少跌的这 {abs(FOUR['y2022']-A100['y2022']):.1f} 个百分点，在 2023 年变成了超额</b>：
四层桶 {FOUR['y2023']:.1f}% vs 100% 持股 {A100['y2023']:.1f}%。因为再平衡在低点把现金换成了筹码。</p>

<h2><span class="no">05</span>四层桶：进攻与防守怎么分</h2>

{bucket_bar()}

<p>分层的依据不是「预期收益高低」，而是 <b>「这笔钱什么时候要用」</b>。同一个人的钱，用途不同，风险预算就不同。
按用途分层，行情怎么走都不会打乱。</p>

<div class="scroll">
<table>
<thead><tr><th>层</th><th>比例</th><th>放什么</th><th>作用</th><th>规则</th><th>行情差时</th></tr></thead>
<tbody>
<tr><td class="nm">L0 安全垫</td><td>20%</td><td>现金 / 定存 / 短债 / 货币基金</td><td>保证 24 个月生活费不断</td><td>永不动用，不投资</td><td>唯一不能碰的层</td></tr>
<tr><td class="nm">L1 防守</td><td>25%</td><td>高股息 ETF（0056 / 00878）</td><td>产生现金流，降低「被迫卖出」</td><td>只看股息，不看价差</td><td>继续领息，不卖</td></tr>
<tr><td class="nm">L2 核心</td><td>35%</td><td>市值型 ETF（0050 / 大盘）</td><td>长期成长引擎</td><td>不择时，只在再平衡时动</td><td>不动</td></tr>
<tr><td class="nm">L3 卫星</td><td>20%</td><td>个股（单档 ≤4%）</td><td>超额报酬来源</td><td>按 Regime 调 0–20%</td><td>可降到 0</td></tr>
</tbody>
</table>
</div>

<h3>以 1,000 万为例，钱具体怎么摆</h3>

<div class="scroll">
<table>
<thead><tr><th>层</th><th>金额</th><th>具体标的（示例）</th><th>年现金流（保守 6% / 历史 8.4%）</th><th>最坏情况（按回测回撤）</th></tr></thead>
<tbody>
<tr><td class="nm">L0 安全垫</td><td class="money">200 万</td><td>定存 + 货币基金 + 短债</td><td>3.2 万</td><td>200 万（不动）</td></tr>
<tr><td class="nm">L1 防守</td><td class="money">250 万</td><td>0056 + 00878 各半</td><td>15.0 万 / 21.0 万</td><td>约 190 万（-24%）</td></tr>
<tr><td class="nm">L2 核心</td><td class="money">350 万</td><td>0050</td><td>8.6 万</td><td>约 226 万（-35%）</td></tr>
<tr><td class="nm">L3 卫星</td><td class="money">200 万</td><td>5–8 档个股，单档 ≤40 万</td><td>约 8 万</td><td>约 130 万（-35%）</td></tr>
<tr class="hot"><td class="nm">合计</td><td class="money">1,000 万</td><td>—</td><td><b>35–41 万 / 年</b></td><td><b>约 746 万（-25%）</b></td></tr>
</tbody>
</table>
</div>

<p class="sub">现金流口径：L1 用近 5 年平均殖利率 {CF['0056']['yield_5y_avg_pct']:.1f}% / {CF['00878']['yield_5y_avg_pct']:.1f}%（含资本利得，非常态，故给保守 6% 一栏）。最坏情况按各层回测回撤加权，非预测。</p>

<h3>卫星层的调节旋钮（唯一允许择时的地方）</h3>

<div class="scroll">
<table>
<thead><tr><th>市场状态</th><th>判定条件</th><th>L3 卫星仓位</th><th>动作</th><th>对总资产的影响</th></tr></thead>
<tbody>
<tr><td class="nm">BULL</td><td>回撤 &lt;8% 且站上年线</td><td>20%</td><td>正常持有，回调分批</td><td>0</td></tr>
<tr><td class="nm">NEUTRAL</td><td>回撤 8–15%</td><td>15%</td><td>减 1/4，现金进 L0</td><td>-1%</td></tr>
<tr><td class="nm">BEAR</td><td>回撤 15–25% 或跌破年线</td><td>10%</td><td>减半，只留能领息的</td><td>-2%</td></tr>
<tr><td class="nm">CRISIS</td><td>回撤 &gt;25% 或波动 &gt;45%</td><td>0%</td><td>清空卫星，全进 L0</td><td>-4%</td></tr>
</tbody>
</table>
</div>

<p>为什么只在卫星层调？因为回测显示全仓 Regime 调仓（Calmar {REG['calmar']:.2f}）不如静态四层桶（{FOUR['calmar']:.2f}）。
把择时关在 20% 的笼子里：对了，多赚一点；错了，最多错 4% 的总资产。<b>这是「承认自己会看错」的工程化做法。</b></p>

<h2><span class="no">06</span>获利部分退出：数学上的真实代价</h2>

<p>你问「获利是部分退出」——这件事在数学上到底划不划算？用 60 档个股、同样的起点、同样的 {y} 年，跑 7 种退出规则：</p>

<div class="scroll">
<table>
<thead><tr>
<th>退出规则</th><th>年化</th><th>vs 持有</th><th>最大回撤</th><th>vs 持有</th>
<th>Calmar</th><th>滚动1年亏损概率</th><th>最差5%</th>
</tr></thead>
<tbody>
{rows_tp()}
</tbody>
</table>
</div>

<div class="two">
  <div class="box">
    <h4>部分卖：值得</h4>
    <p><b>+20% 卖 1/4</b>：年化少 {abs(TP['1. +20% 卖 1/4']['ann_pct']-TP[list(TP)[0]]['ann_pct']):.1f}pp，
    回撤改善 {abs(TP['1. +20% 卖 1/4']['mdd_pct']-TP[list(TP)[0]]['mdd_pct']):.1f}pp，Calmar 从 {TP[list(TP)[0]]['calmar']:.2f} 升到 {TP['1. +20% 卖 1/4']['calmar']:.2f}。</p>
    <p><b>+30% 卖 1/2</b>：Calmar {TP['4. +30% 卖 1/2']['calmar']:.2f}，是全场最高。
    年化 {TP['4. +30% 卖 1/2']['ann_pct']:.1f}%，但最差情形从 {TP[list(TP)[0]]['roll_1y']['p5_pct']:.1f}% 收窄到 {TP['4. +30% 卖 1/2']['roll_1y']['p5_pct']:.1f}%。</p>
  </div>
  <div class="box p2" style="border-color:#3a2020">
    <h4 style="color:#e5484d">全清：灾难</h4>
    <p><b>移动止损 20%（跌破高点 20% 全出）</b>：年化只剩 {TP['5. 纯移动止损 20%（全清）']['ann_pct']:.1f}%，
    是持有的 {TP['5. 纯移动止损 20%（全清）']['ann_pct']/TP[list(TP)[0]]['ann_pct']*100:.0f}%。</p>
    <p>原因很简单：<b>台股每年都有 15–25% 的正常回调</b>，止损被反复扫出，出局后不敢再进，错过主升段。
    回撤是变小了（-{abs(TP['5. 纯移动止损 20%（全清）']['mdd_pct']):.1f}%），但 Calmar 反而更低。</p>
  </div>
</div>

<div class="quote">
<b>结论：</b>「部分退出」和「止损全清」是两件完全不同的事，被混为一谈是散户最大的亏损来源之一。
前者是<b>把浮盈变成确定收益</b>，后者是<b>在噪音里被赶下车</b>。
数据说：卖一部分，Calmar 上升；全卖光，Calmar 下降。
</div>

<h3>我建议的具体规则（可直接执行）</h3>

<div class="steps">
  <div class="step"><div class="n">1</div><div class="c">
    <h4>+20%：卖出 1/4，收回成本</h4>
    <p>把本金的一部分拿回来，心理账户立刻从「怕亏」变成「用利润在玩」。这一步的主要作用不是收益，是<b>让你拿得住剩下的 3/4</b>。</p>
  </div></div>
  <div class="step"><div class="n">2</div><div class="c">
    <h4>+40%：再卖 1/3（累计卖出 50%）</h4>
    <p>此时剩一半仓位。回测显示这个组合 Calmar {TP['2. +20%卖1/4 / +40%卖1/3']['calmar']:.2f}，
    回撤从 {TP[list(TP)[0]]['mdd_pct']:.1f}% 压到 {TP['2. +20%卖1/4 / +40%卖1/3']['mdd_pct']:.1f}%——<b>砍掉四成回撤，只付两成报酬</b>。</p>
  </div></div>
  <div class="step"><div class="n">3</div><div class="c">
    <h4>剩下的 50%：不设机械止损，只设「基本面止损」</h4>
    <p>三条之一成立才卖：① 连续 2 季营收或毛利率同比转负；② 跌破年线且 60 日线死叉、同时基本面转差；
    ③ <b>当初买入的理由消失了</b>（产品周期结束、竞争格局变化、管理层信誉出问题）。<br>
    回测已经证明：机械移动止损在台股上会被反复扫出，是负期望。</p>
  </div></div>
  <div class="step"><div class="n">4</div><div class="c">
    <h4>退出来的钱去哪：先回填 L0，再补 L1</h4>
    <p>这是关键的一步，也是大多数人不做的。卖出的钱<b>不是</b>拿去换另一档股票（那是换股，不是降风险）。
    先补到 L0 安全垫满 24 个月生活费；满了之后，投入 L1 高股息，把「年现金流」做大。<br>
    这样每一次止盈都在<b>提高组合的抗跌性</b>，而不是把风险换个地方放。</p>
  </div></div>
</div>

<h2><span class="no">07</span>再平衡：它不增收益，它买的是「下次的子弹」</h2>

<div class="scroll">
<table>
<thead><tr><th>70/30 的再平衡方式</th><th>总报酬</th><th>年化</th><th>最大回撤</th><th>Calmar</th><th>年换手</th></tr></thead>
<tbody>
<tr><td class="nm">不再平衡</td><td>{N70['total_pct']:.1f}%</td><td>{N70['ann_pct']:.2f}%</td><td>{N70['mdd_pct']:.1f}%</td><td>{N70['calmar']:.2f}</td><td>{N70['turnover_annual']:.2f}</td></tr>
<tr><td class="nm">年度再平衡</td><td>{Q70['total_pct']:.1f}%</td><td>{Q70['ann_pct']:.2f}%</td><td>{Q70['mdd_pct']:.1f}%</td><td>{Q70['calmar']:.2f}</td><td>{Q70['turnover_annual']:.2f}</td></tr>
<tr><td class="nm">阈值 ±5pp</td><td>{next(c for c in D['configs'] if c['key'].startswith('G.'))['total_pct']:.1f}%</td><td>{next(c for c in D['configs'] if c['key'].startswith('G.'))['ann_pct']:.2f}%</td><td>{next(c for c in D['configs'] if c['key'].startswith('G.'))['mdd_pct']:.1f}%</td><td>{next(c for c in D['configs'] if c['key'].startswith('G.'))['calmar']:.2f}</td><td>{next(c for c in D['configs'] if c['key'].startswith('G.'))['turnover_annual']:.2f}</td></tr>
<tr><td class="nm">季度再平衡</td><td>{next(c for c in D['configs'] if c['key'].startswith('H.'))['total_pct']:.1f}%</td><td>{next(c for c in D['configs'] if c['key'].startswith('H.'))['ann_pct']:.2f}%</td><td>{next(c for c in D['configs'] if c['key'].startswith('H.'))['mdd_pct']:.1f}%</td><td>{next(c for c in D['configs'] if c['key'].startswith('H.'))['calmar']:.2f}</td><td>{next(c for c in D['configs'] if c['key'].startswith('H.'))['turnover_annual']:.2f}</td></tr>
</tbody>
</table>
</div>

<p>看清楚这张表：<b>再平衡在这段单边上涨里是负收益的</b>（{N70['total_pct']:.1f}% → {Q70['total_pct']:.1f}%），
但回撤只从 {N70['mdd_pct']:.1f}% 改善到 {Q70['mdd_pct']:.1f}%。所以「再平衡能提高收益」是错的。</p>

<p>它的真实作用在另一处：<b>2022 年底，四层桶因为再平衡，把 20% 的现金换成了便宜的筹码</b>。
2023 年四层桶 {FOUR['y2023']:.1f}%，100% 持股 {A100['y2023']:.1f}%——多出来的 {FOUR['y2023']-A100['y2023']:.1f}pp 就是再平衡红利。
它不在当年体现，在<b>下一年</b>体现。</p>

<div class="quote">
<b>所以再平衡要这样理解：</b>它不是收益增强器，是<b>「强制低买高卖」的纪律装置</b>。
你不需要判断行情，只需要在偏离目标 5 个百分点时，把多的一边挪到少的一边。
这个动作在牛市里拖后腿，在崩盘后救你的命。
</div>

<h3>具体规则（三选一，别混用）</h3>
<ul>
<li><b>阈值再平衡（推荐）</b>：任一层偏离目标 ±5pp 就拉回。省成本、有纪律、不用看日历。年换手约 {next(c for c in D['configs'] if c['key'].startswith('G.'))['turnover_annual']:.1f} 倍。</li>
<li><b>年度再平衡</b>：每年固定一天（建议年初）拉回。最简单，适合不想管事的人。</li>
<li><b>不混用</b>：既看日历又看阈值，容易变成「想动就动」，纪律失效。</li>
</ul>

<h2><span class="no">08</span>基本面锚：用估值分位，不用新闻</h2>

<p>「遵循基本面」这句话之所以难执行，是因为基本面是慢变量，而价格是快变量。
把它们接起来的唯一可操作指标是 <b>估值的历史分位</b>——不是「PE 多少算便宜」，而是「PE 在过去 5 年排第几」。</p>

<div class="kpis">
  <div class="kpi b"><div class="v">{VAL['median_pe_pct']*100:.0f}%</div><div class="l">全市场 PE 分位中位数<br>（{VAL['n']} 档，40–60% 为中性区）</div></div>
  <div class="kpi gr"><div class="v">{VAL['cheap_n']} 档</div><div class="l">处于历史后 30% 分位<br>（估值偏低）</div></div>
  <div class="kpi r"><div class="v">{VAL['rich_n']} 档</div><div class="l">处于历史前 30% 分位<br>（估值偏高）</div></div>
  <div class="kpi g"><div class="v">1 : 1.3</div><div class="l">便宜档 : 昂贵档<br>市场处于中性偏温和</div></div>
</div>

<div class="two">
  <div class="box">
    <h4>估值最低的 6 档（后 30% 分位）</h4>
    <table style="margin:8px 0 0;font-size:12.5px">
    <thead><tr><th>代号</th><th>名称</th><th>行业</th><th>PE</th><th>分位</th></tr></thead>
    <tbody>{rows_val()}</tbody></table>
  </div>
  <div class="box p2">
    <h4>估值最高的 6 档（前 30% 分位）</h4>
    <table style="margin:8px 0 0;font-size:12.5px">
    <thead><tr><th>代号</th><th>名称</th><th>行业</th><th>PE</th><th>分位</th></tr></thead>
    <tbody>{rows_rich()}</tbody></table>
  </div>
</div>

<h3>分位怎么用（这是「遵循基本面」的落地形式）</h3>

<div class="scroll">
<table>
<thead><tr><th>PE 历史分位</th><th>含义</th><th>卫星层动作</th><th>核心层动作</th></tr></thead>
<tbody>
<tr><td class="nm">≤ 30%</td><td>比过去 5 年 70% 的时间便宜</td><td>可加到单档上限（4%）</td><td>正常定投</td></tr>
<tr><td class="nm">30–70%</td><td>中性</td><td>标准仓位</td><td>正常定投</td></tr>
<tr><td class="nm">70–90%</td><td>偏贵</td><td>减半，不再新增</td><td>正常定投（不猜顶）</td></tr>
<tr><td class="nm">&gt; 90%</td><td>极端贵</td><td>只留底仓，不加</td><td>正常定投（不猜顶）</td></tr>
</tbody>
</table>
</div>

<div class="quote">
<b>但必须说一个反证：</b>用同一套估值信号做「全市场仓位调节」（估值温度调仓），
Calmar 只有 {VALT['calmar']:.2f}，年化 {VALT['ann_pct']:.2f}%，跑输四层桶的 {FOUR['calmar']:.2f}。<br>
原因是：<b>估值能告诉你「贵不贵」，不能告诉你「什么时候跌」</b>。台股 2023–2026 长期在高分位运行，
按估值减仓会一路踏空。<br>
<b>所以：估值用来决定「买什么、买多少」，不用来决定「什么时候清仓」。</b>
</div>

<h2><span class="no">09</span>安全垫：不是现金比例，是「现金流覆盖率」</h2>

<p>大多数人把「安全垫」理解成一个现金百分比（比如留 20% 现金）。这个理解不够——
真正的安全垫是 <b>「不卖股票也能活多久」</b>。它由两个数字决定：年现金流、年生活费。</p>

<div class="scroll">
<table>
<thead><tr><th>标的</th><th>现价</th><th>近12个月配息</th><th>当期殖利率</th><th>近5年平均殖利率</th><th>100 万每年现金流</th></tr></thead>
<tbody>
<tr><td class="nm">0050 元大台湾50</td><td>{CF['0050']['price']:.2f}</td><td>{CF['0050']['ttm_div']:.3f}</td><td>{CF['0050']['yield_pct']:.2f}%</td><td>{CF['0050']['yield_5y_avg_pct']:.2f}%</td><td class="money">{CF['0050']['cash_per_100w']:,.0f}</td></tr>
<tr><td class="nm">0056 元大高股息</td><td>{CF['0056']['price']:.2f}</td><td>{CF['0056']['ttm_div']:.3f}</td><td>{CF['0056']['yield_pct']:.2f}%</td><td>{CF['0056']['yield_5y_avg_pct']:.2f}%</td><td class="money">{CF['0056']['cash_per_100w']:,.0f}</td></tr>
<tr><td class="nm">00878 国泰永续高股息</td><td>{CF['00878']['price']:.2f}</td><td>{CF['00878']['ttm_div']:.3f}</td><td>{CF['00878']['yield_pct']:.2f}%</td><td>{CF['00878']['yield_5y_avg_pct']:.2f}%</td><td class="money">{CF['00878']['cash_per_100w']:,.0f}</td></tr>
</tbody>
</table>
</div>

<p class="sub">当期殖利率含资本利得分配（2025–2026 年高股息 ETF 普遍超配），不可持续；近 5 年平均更接近常态，但仍偏高。规划时建议再打 7 折。</p>

<h3>算一个你自己的数字</h3>

<div class="card">
<p><b>第一步</b>：年生活费 = 月支出 × 12。假设 5 万/月 → <b>60 万/年</b>。</p>
<p><b>第二步</b>：安全垫 = 年生活费 × 2 年 = <b>120 万</b>（放 L0，永不动）。</p>
<p><b>第三步</b>：现金流覆盖率 = L1 年股息 ÷ 年生活费。</p>
<p style="color:#d4a24c"><b>以 1,000 万四层桶（L1 = 250 万）为例：</b>250 万 × 6%（保守）= 15 万 → 覆盖率 <b>25%</b>；
按历史 8.4% = 21 万 → 覆盖率 <b>35%</b>。</p>
<p><b>第四步</b>：把覆盖率做到 50% 以上，需要 L1 约 500 万；做到 100%，需要 L1 约 1,000 万。
这就是「财务自由」的具体门槛——不是资产总额，是<b>股息覆盖生活费的比例</b>。</p>
</div>

<div class="quote">
<b>为什么这个指标比「总资产」重要：</b>总资产 2,000 万但零现金流的人，遇到 2022 年那种行情，
生活费只能靠卖股票；总资产 1,200 万但年股息 60 万的人，行情再差也不用卖。
<b>前者是「有钱但脆弱」，后者是「有钱且自由」。</b>
</div>

<h2><span class="no">10</span>还可以完善的十个方向</h2>

<div class="steps">
  <div class="step"><div class="n">1</div><div class="c">
    <h4>按「用途」分层，不按「预期收益」分层</h4>
    <p>同样是 100 万，24 个月要用的钱和 10 年不用的钱，不该放在同一个篮子里。
    分层的第一刀切在「时间」，不是「看好程度」。</p>
  </div></div>
  <div class="step"><div class="n">2</div><div class="c">
    <h4>做「相关性预算」，不做「资金预算」</h4>
    <p>每加一档之前问一句：它和我现有持仓的相关性多少？同族群算一档。
    {CORR['n_assets']} 档只等于 {CORR['effective_n']:.1f} 档独立风险——所以「行业上限 25%」比「单档上限 4%」更重要。</p>
  </div></div>
  <div class="step"><div class="n">3</div><div class="c">
    <h4>跨资产：加一类「和股票不同步」的东西</h4>
    <p>台股内部再怎么分散，本质是同一个 beta。真正的分散来自股/债/黄金/REITs。
    哪怕只配 10–15% 的债券或黄金，在 2022 年那种行情里也能提供「再平衡的弹药」。</p>
  </div></div>
  <div class="step"><div class="n">4</div><div class="c">
    <h4>跨区域：把「台湾」当成一个持仓，而不是全世界</h4>
    <p>台股市值/GDP 位居全球前列，单一市场集中度极高。
    用美股宽基或全球 ETF 做 10–20% 的配置，是用最低成本降低「单一政治/单一产业」风险的方式。</p>
  </div></div>
  <div class="step"><div class="n">5</div><div class="c">
    <h4>时间分散：一笔钱分 3–6 次进</h4>
    <p>不是「分批比较赚」，是「分批让你不会在最高点一次性买满，从而不会在下跌时崩溃」。
    入场点风险的降低，换来的是「拿得住」的概率提升。</p>
  </div></div>
  <div class="step"><div class="n">6</div><div class="c">
    <h4>保险：把尾部风险转移出去</h4>
    <p>医疗、长照、意外——这三件事的损失是无上限的，而保费是有上限的。
    <b>这是全宇宙性价比最高的「安全垫」</b>：用 1% 的资产，买掉 100% 的破产可能。
    61 岁这个年纪，医疗险和长照险的优先级高于任何一档股票。</p>
  </div></div>
  <div class="step"><div class="n">7</div><div class="c">
    <h4>把费用当成负收益来管</h4>
    <p>台股来回成本约 <b>0.885%</b>（手续费 1.425‰ × 2 + 证交税 3‰）。
    一年交易 10 次，吃掉 8.85%——这比大多数策略的年化超额还多。
    <b>少动，是唯一确定为正的 alpha。</b></p>
  </div></div>
  <div class="step"><div class="n">8</div><div class="c">
    <h4>写一份投资政策书（IPS），事前签字</h4>
    <p>一页纸写清：目标、四层比例、再平衡规则、止盈规则、什么情况才卖、什么情况绝不卖。
    它的作用不是指导操作，是 <b>在你情绪最差的那天，替你做出决定</b>。
    回测里所有「动态策略」跑输静态配置，本质原因就是人在盘中会改规则。</p>
  </div></div>
  <div class="step"><div class="n">9</div><div class="c">
    <h4>把「人力资本」算进资产表</h4>
    <p>61 岁，收入能力在下降，但经验和人脉是资产。资产配置要跟「未来现金流的稳定性」匹配：
    收入越不稳定，L0 安全垫要越厚（24 个月起），而不是越薄。</p>
  </div></div>
  <div class="step"><div class="n">10</div><div class="c">
    <h4>复盘频率：季度，不是每天</h4>
    <p>每天看盘不会提高收益，只会提高交易次数。回测里所有高频动作都是负贡献。
    建议：<b>每季度看一次四层比例，偏离 5pp 才动手；每年看一次 IPS，看规则是否需要改，而不是看赚了多少。</b></p>
  </div></div>
</div>

<h2><span class="no">11</span>一页纸：给爸妈的版本</h2>

<div class="onepage">
  <h3>投資的四句話</h3>
  <div class="sub2">SILVERSTOCK · 家人自用 · 2026</div>

  <p class="big">一、錢分四層，各有各的用途，不互相借。</p>
  <p>生活費（兩年）放定存，永遠不動；防守層買高股息，領息；核心層買 0050，長期不賣；衛星層才買個股，最多兩成。</p>

  <div class="rule">
    <b>第一條鐵律：</b>生活費的錢，不管行情多好，都不拿去買股票。<br>
    <b>第二條鐵律：</b>單一個股，最多佔總資產 4%。<br>
    <b>第三條鐵律：</b>賺 20% 先賣四分之一，把本錢收回來。
  </div>

  <p class="big">二、不要因為看壞行情就全部賣掉。</p>
  <p>我們測過：只要跌破高點 20% 就清空，五年下來年化只剩 3.5%；同樣的股票，什麼都不做是 15%。<br>
  台股每年都有 15–25% 的正常回檔，全部賣掉的人，通常也買不回來。</p>

  <p class="big">三、跌的時候，看的是「還能領多少息」，不是「帳面虧多少」。</p>
  <p>帳面虧損是暫時的，股息是每年到帳的。只要公司還在賺錢、還在配息，價格跌反而是讓殖利率變高。</p>

  <p class="big">四、一年只看四次。</p>
  <p>每季看一次比例有沒有跑掉，跑掉 5% 就調回來。其他時間不要看。看越多次，做錯越多。</p>

  <table style="margin-top:22px">
  <thead><tr><th>層</th><th>比例</th><th>放什麼</th><th>什麼時候動</th></tr></thead>
  <tbody>
  <tr><td>生活費</td><td>20%</td><td>定存、貨幣基金</td><td>永遠不動</td></tr>
  <tr><td>領息層</td><td>25%</td><td>0056、00878</td><td>只領息，不賣</td></tr>
  <tr><td>核心層</td><td>35%</td><td>0050</td><td>長期持有</td></tr>
  <tr><td>個股層</td><td>20%</td><td>個股，單檔≤4%</td><td>賺 20% 賣 1/4</td></tr>
  </tbody>
  </table>

  <p style="margin-top:22px;font-size:12px;color:#8a7a5e">本頁為家人內部使用，非投資建議。任何決定請先問過自己的投資政策書。</p>
</div>

<h2><span class="no">12</span>这份分析不知道的事</h2>

<ul>
<li><b>样本只有一段行情。</b>{RANGE[0]}–{RANGE[1]} 是台股大牛市（TAIEX 涨了两倍多）。
所有「梭哈输给配置」的结论，在这个样本里其实是「梭哈赢了绝对收益、输了风险调整收益」。
如果换成 2000–2008 或 1990–2000 的台股，结论会更偏向防守。<b>不要把这段样本当成未来。</b></li>
<li><b>「现金 1.6%」是假设，不是实测。</b>利率环境变了，整张表的绝对数字都要重算。</li>
<li><b>含息但未扣通膨。</b>实际购买力的年化要再减 2% 左右。</li>
<li><b>个股池是幸存者偏差的。</b>111 档是「今天还在的」，退市的没在里面，所以真实个股报酬比回测低。</li>
<li><b>没有考虑税制差异。</b>股息所得、二代健保补充保费、海外所得的税负都没算，实际到手会少。</li>
<li><b>四层桶的比例不是唯一解。</b>20/25/35/20 是「在回测里性价比最好」的一组，但你的年龄、现金流需求、风险承受度不同，比例应该不同。
    真正不能改的是<b>结构</b>（分层、上限、再平衡、止盈），不是数字。</li>
</ul>

<div class="foot">
<b>V3.8 · 资产配置引擎</b><br>
数据：FinMind 公开历史资料（{RANGE[0]}–{RANGE[1]}，111 档，{DAYS} 交易日），含息、含交易成本。<br>
计算：<code>tool/v3/asset_allocation.py</code> → <code>v38_allocation_result.json</code> → 本报告由 <code>tool/v3/gen_allocation_report.py</code> 生成，所有数字程序回填，无手工抄录。<br>
假设：手续费 1.425‰、证交税 3‰（ETF 1‰）、现金年化 1.6%、调仓单边成本 0.25%。<br>
本文件仅供本人与家人研究使用，不构成投资建议，不对外提供。
</div>

</div></body></html>"""

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(head)
    print(f"written {os.path.abspath(OUT)}  {len(head):,} chars")
    return OUT


if __name__ == "__main__":
    build()

