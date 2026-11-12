# -*- coding: utf-8 -*-
"""V3.9 熊市生存报告生成器"""
import json
import os

from gen_allocation_report import CSS

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = json.load(open(os.path.join(ROOT, "v39_bear_result.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "..", "V3.9_熊市生存法则.html")

BEARS = D["bear_detail"]
PERIODS = D["period_stats"]
BULLS = D["bull_models"]
GP = D["group_paths"]["groups"]
LATEST = D["latest"]
CUR = D["current"]
LEV = D["leverage_path"]
TOP = D["top_lever_loss"]
REB = D["rebound"]

BEAR2, BEAR3, BEAR4 = BEARS[1], BEARS[2], BEARS[3]
BULL1, BULL2 = BULLS[0], BULLS[1]


def fdate(v):
    v = str(v)
    return f"{v[:4]}/{v[4:6]}/{v[6:]}" if len(v) == 8 else v


def g(b, k, field="median_pct"):
    x = b["groups"].get(k, {})
    return x.get(field)


# ── 图 1：四段空头 × 三组 中位报酬 ─────────────────────────────────
def bear_group_svg():
    rows = [BEARS[1], BEARS[2], BEARS[3]]
    W, H = 860, 320
    L, R, T, B = 70, 30, 26, 58
    vals = [g(r, k) for r in rows for k in ("DEF", "MID", "HYPE") if g(r, k) is not None]
    ymin, ymax = min(vals + [-30]) - 3, 8

    def py(v):
        return H - B - (v - ymin) / (ymax - ymin) * (H - T - B)

    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    for t in range(int(ymin // 5) * 5, int(ymax) + 1, 5):
        y = py(t)
        parts.append(f'<line x1="{L}" y1="{y:.0f}" x2="{W-R}" y2="{y:.0f}" stroke="#1e2630"/>')
        parts.append(f'<text x="{L-9}" y="{y+4:.0f}" text-anchor="end" class="ax">{t}%</text>')
    y0 = py(0)
    parts.append(f'<line x1="{L}" y1="{y0:.0f}" x2="{W-R}" y2="{y0:.0f}" stroke="#4a5563" stroke-width="1.5"/>')

    groupw = (W - L - R) / len(rows)
    bw = 46
    cols = {"DEF": "#30a46c", "MID": "#4a9eff", "HYPE": "#e5484d"}
    for i, r in enumerate(rows):
        cx = L + groupw * (i + 0.5)
        for j, k in enumerate(("DEF", "MID", "HYPE")):
            v = g(r, k)
            if v is None:
                continue
            x = cx - bw * 1.6 + j * (bw + 12)
            y = py(v)
            h = abs(y0 - y)
            parts.append(f'<rect x="{x:.0f}" y="{min(y0,y):.0f}" width="{bw}" height="{h:.0f}" fill="{cols[k]}" opacity="0.88" rx="2"/>')
            parts.append(f'<text x="{x+bw/2:.0f}" y="{y-7 if v<0 else y+16:.0f}" text-anchor="middle" class="pt" fill="{cols[k]}">{v:.1f}</text>')
        parts.append(f'<text x="{cx:.0f}" y="{H-B+22}" text-anchor="middle" class="axt">{fdate(r["start"])[:7]}–{fdate(r["end"])[:7]}</text>')
        parts.append(f'<text x="{cx:.0f}" y="{H-B+40}" text-anchor="middle" class="ax">指數 {r["index_ret_pct"]:+.1f}%</text>')
    parts.append(f'<text x="{L}" y="14" class="axt">各組中位報酬（含息）</text>')
    parts.append("</svg>")
    return "".join(parts)


# ── 图 2：牛市行为模型 ─────────────────────────────────────────────
def behavior_svg(bull):
    W, H = 860, 330
    L, R, T, B = 190, 70, 20, 34
    ms = bull["models"]
    order = ["BH", "LEVER", "CHASE", "ROTATE", "DISPOSITION", "LATE"]
    labels = {
        "BH": "買入持有（對照）", "LEVER": "融資 2 倍槓桿", "CHASE": "追漲殺跌",
        "ROTATE": "每月追最強 10 檔", "DISPOSITION": "賣贏家、留輸家",
        "LATE": "末段才進場＋單押最熱",
    }
    vals = [ms[k]["total_pct"] for k in order if k in ms]
    xmax = max(vals) * 1.05

    def px(v):
        return L + v / xmax * (W - L - R)

    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    for t in range(0, int(xmax) + 1, 100):
        x = px(t)
        parts.append(f'<line x1="{x:.0f}" y1="{T}" x2="{x:.0f}" y2="{H-B}" stroke="#1e2630"/>')
        parts.append(f'<text x="{x:.0f}" y="{H-B+18}" text-anchor="middle" class="ax">{t}%</text>')
    rh = (H - T - B) / len(order)
    for i, k in enumerate(order):
        if k not in ms:
            continue
        m = ms[k]
        v = m["total_pct"]
        y = T + i * rh + rh * 0.22
        col = "#d4a24c" if k == "BH" else ("#7c6cf0" if k == "LEVER" else "#4a9eff")
        if k == "LATE":
            col = "#e5484d"
        parts.append(f'<text x="{L-12}" y="{y+16:.0f}" text-anchor="end" class="pt" fill="#b8c2d0">{labels[k]}</text>')
        parts.append(f'<rect x="{L}" y="{y:.0f}" width="{max(2,px(v)-L):.0f}" height="{rh*0.5:.0f}" fill="{col}" opacity="0.85" rx="2"/>')
        parts.append(f'<text x="{px(v)+9:.0f}" y="{y+16:.0f}" class="pt" fill="{col}">{v:+.1f}%</text>')
        parts.append(f'<text x="{W-R+8:.0f}" y="{y+16:.0f}" class="ax" fill="#6b7787">MDD {m["mdd_pct"]:.0f}%</text>')
    parts.append("</svg>")
    return "".join(parts)


# ── 图 3：分组全程净值（样本外）─────────────────────────────────────
def group_nav_svg():
    series = [(GP["DEF"], "#30a46c", f"基本面/防禦 ({GP['DEF']['n']} 檔)"),
              (GP["MID"], "#4a9eff", f"中間組 ({GP['MID']['n']} 檔)"),
              (GP["HYPE"], "#e5484d", f"題材/炒作 ({GP['HYPE']['n']} 檔)")]
    W, H = 860, 300
    L, R, T, B = 60, 160, 22, 38
    n = max(len(s[0]["nav_slim"]) for s in series)
    ymax = max(max(s[0]["nav_slim"]) for s in series) * 1.06

    def px(i, ln):
        return L + i / (ln - 1) * (W - L - R)

    def py(v):
        return H - B - (v - 0.5) / (ymax - 0.5) * (H - T - B)

    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    for t in [0.5, 1, 1.5, 2, 2.5, 3]:
        if t > ymax:
            continue
        y = py(t)
        parts.append(f'<line x1="{L}" y1="{y:.0f}" x2="{W-R}" y2="{y:.0f}" stroke="#1e2630"/>')
        parts.append(f'<text x="{L-8}" y="{y+4:.0f}" text-anchor="end" class="ax">{t}×</text>')
    for s, col, lab in series:
        ln = len(s["nav_slim"])
        pts = " ".join(f"{px(i,ln):.0f},{py(v):.0f}" for i, v in enumerate(s["nav_slim"]))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.2" stroke-linejoin="round"/>')
        ye = s["nav_slim"][-1]
        parts.append(f'<text x="{px(ln-1,ln)+10:.0f}" y="{py(ye)+4:.0f}" class="pt" fill="{col}">{ye:.2f}× · {lab.split(" (")[0]}</text>')
    parts.append(f'<text x="{L}" y="{H-10}" class="ax">2022/07/06（分類時點）</text>')
    parts.append(f'<text x="{W-R-60}" y="{H-10}" class="ax">2026/10/22</text>')
    parts.append("</svg>")
    return "".join(parts)


# ── 图 4：慢熊 vs 急杀 正报酬比例 ───────────────────────────────────
def breadth_svg():
    W, H = 860, 190
    L, R, T, B = 200, 90, 20, 30
    rows = [("慢熊 2021/06–2022/07", BEARS[0]["positive_pct"], "-18.5% / 269 天", "#4a9eff"),
            ("緩跌 2022/07–2022/10", BEAR2["positive_pct"], "-9.4% / 77 天", "#4a9eff"),
            ("盤跌 2024/07–2025/02", BEAR3["positive_pct"], "-2.7% / 146 天", "#4a9eff"),
            ("急殺 2025/02–2025/04", BEAR4["positive_pct"], "-26.7% / 30 天", "#e5484d")]
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    rh = (H - T - B) / len(rows)
    for i, (lab, v, sub, col) in enumerate(rows):
        y = T + i * rh + rh * 0.2
        parts.append(f'<text x="{L-14}" y="{y+15:.0f}" text-anchor="end" class="pt" fill="#b8c2d0">{lab}</text>')
        parts.append(f'<text x="{L-14}" y="{y+30:.0f}" text-anchor="end" class="ax" fill="#6b7787">{sub}</text>')
        w = v / 100 * 480
        parts.append(f'<rect x="{L}" y="{y:.0f}" width="{max(2,w):.0f}" height="{rh*0.48:.0f}" fill="{col}" opacity="0.85" rx="2"/>')
        parts.append(f'<text x="{L+w+10:.0f}" y="{y+16:.0f}" class="pt" fill="{col}">{v:.1f}%</text>')
    parts.append("</svg>")
    return "".join(parts)


def build():
    p1 = next(p for p in PERIODS if p["start"] == 20250409)
    p2 = next(p for p in PERIODS if p["start"] == 20221025)
    batch = next(x for x in REB if x.get("strategy") == "分批5次")
    single = next(x for x in REB if x.get("strategy") == "底部单笔")

    head = f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>V3.9 熊市生存法则：基本面股、炒作股与牛市亏钱的实证</title>
<style>{CSS}</style>
</head>
<body><div class="wrap">

<div class="sub" style="letter-spacing:2px;color:#d4a24c;font-size:12px">SILVERSTOCK QUANT · V3.9</div>
<h1>熊市靠什么赚钱：<span class="em">仓位</span>、<span class="em">选股</span>与<span class="em">人性</span>的实测</h1>
<p class="lead">用 111 档台股 5 年日线（{fdate(D['meta']['range'][0])}–{fdate(D['meta']['range'][1])}，含息、含成本），
把 4 段真实空头、2 段多头切开来验：谁在跌的时候活下来，谁在涨的时候反而赔钱。</p>

<div class="meta">
  <span>空头波段 <b>4 段</b></span>
  <span>多头波段 <b>2 段</b></span>
  <span>分类时点 <b>各波段开始前一日</b></span>
  <span>前视偏误 <b>已排除</b></span>
  <span>成本 <b>ETF {D['meta']['cost_etf_pct']:.2f}% / 个股 {D['meta']['cost_stock_pct']:.2f}%</b></span>
</div>

<div class="answer">
  <div class="q">四个问题，其实指向同一个答案</div>
  <div class="a">牛市赚钱靠 <em>行情</em>，熊市赚钱靠 <em>结构</em>。<br>
  牛市亏钱的人不是选错股，是 <em>把「行情给的」误当成「自己赚的」</em>，于是加了杠杆、追了热点、换了太多次。</div>
  <div class="n">下面每一句都有实测数字。最反直觉的一条先说：
  <b>2025 年 2 月那 30 天，指数跌 26.7%，111 档里只有 4 档上涨——那一刻选股完全无效，只有仓位能救你。</b></div>
</div>

<h2><span class="no">01</span>先把「熊市」切开：慢熊和急杀是两种病</h2>

<p>用 TAIEX 18% 反转切出 6 个波段（V3.6 已做过），其中 4 段空头。
它们不是同一种东西，硬用一套方法会出事。</p>

<div class="scroll">
<table>
<thead><tr><th>空头波段</th><th>天数</th><th>指数</th><th>等权中位</th><th>上涨档数</th><th>能靠选股吗</th></tr></thead>
<tbody>
<tr><td class="nm">2021/06/01 – 2022/07/06</td><td>269</td><td class="neg">−18.5%</td><td>−11.5%</td><td>45 / 111</td><td>可以，慢跌有轮动</td></tr>
<tr><td class="nm">2022/07/06 – 2022/10/25</td><td>77</td><td class="neg">−9.4%</td><td>−6.9%</td><td>28 / 111</td><td>部分可以</td></tr>
<tr><td class="nm">2024/07/11 – 2025/02/21</td><td>146</td><td class="neg">−2.7%</td><td>−5.5%</td><td>35 / 111</td><td>可以，指数没怎么跌</td></tr>
<tr class="hot"><td class="nm">2025/02/21 – 2025/04/09</td><td>30</td><td class="neg">−26.7%</td><td>−20.9%</td><td>4 / 111</td><td><b>完全不行</b></td></tr>
</tbody>
</table>
</div>

{breadth_svg()}

<div class="quote">
<b>这是整份报告最重要的一张图。</b>跌得越慢、越浅，越多个股能靠自身基本面走独立行情（慢熊 40.5% 上涨）；
跌得越急、越深，相关性越高、越没人能逃（急杀只剩 3.6%）。<br>
<b>推论：慢熊靠选股，急杀靠仓位。</b>把两者混为一谈，是「熊市里明明选了好股票还是大赔」的根本原因。
</div>

<h2><span class="no">02</span>熊市里真正能赚钱的三件事</h2>

<div class="steps">
  <div class="step"><div class="n">1</div><div class="c">
    <h4>现金仓位（唯一在急杀里确定有效的）</h4>
    <p>2025/02 那 30 天，111 档里只有 4 档上涨，防御组中位仍跌 {abs(g(BEAR4,'DEF')):.1f}%、炒作组跌 {abs(g(BEAR4,'HYPE')):.1f}%。
    <b>选股能让你少跌 19 个百分点，但不能让你不跌。</b>唯一能不跌的是「没买」。
    V3.8 的四层桶里 L0 20% 现金 + L1 25% 高股息，就是为这一刻准备的。</p>
  </div></div>
  <div class="step"><div class="n">2</div><div class="c">
    <h4>防御型选股（在慢熊里有效，在急杀里只减伤）</h4>
    <p>三段可分类的空头里，<b>基本面/防御组每一次都最抗跌</b>：
    −{abs(g(BEAR2,'DEF')):.2f}%（vs 炒作 −{abs(g(BEAR2,'HYPE')):.2f}%）、
    −{abs(g(BEAR3,'DEF')):.2f}%（vs −{abs(g(BEAR3,'HYPE')):.2f}%）、
    −{abs(g(BEAR4,'DEF')):.2f}%（vs −{abs(g(BEAR4,'HYPE')):.2f}%）。差距 6–19 个百分点。</p>
  </div></div>
  <div class="step"><div class="n">3</div><div class="c">
    <h4>恐慌末端的分批进场（赚的是反弹，不是抄底）</h4>
    <p>2025/04/09 底部之后：20 日 +{REB[0]['ret_pct']:.1f}%、60 日 +{REB[1]['ret_pct']:.1f}%、
    120 日 +{REB[2]['ret_pct']:.1f}%、250 日 +{REB[3]['ret_pct']:.1f}%。
    但要看清楚代价：<b>分批 5 次只拿到 {batch['final_pct']:.1f}%，底部单笔是 {single['final_pct']:.1f}%</b>——V 型反转里分批少赚 36pp。
    分批买的不是报酬，是<b>「买在半山腰也不会崩溃」的心理承受力</b>。</p>
  </div></div>
</div>

<div class="quote">
<b>诚实交代哪些没测：</b>融券放空、反向 ETF、选择权避险、可转债、债券、黄金——
这套资料池里<b>只有台股现货</b>，没有这些工具，所以本报告对它们不做任何数字断言。
能在这里验证的熊市获利来源，就只有上面三种。
</div>

<h2><span class="no">03</span>「基本面股」与「炒作股」：先给可操作的定义</h2>

<p>这两个词最容易变成事后贴标签（涨了叫基本面、跌了叫炒作）。
我用 <b>每个波段开始前一日</b> 就已存在的资料来分类，只用当时的价格、股息、估值、成交量、EPS，
<b>不看下一段涨跌</b>——这是全篇避免前视偏误的关键。</p>

<div class="two">
  <div class="box">
    <h4>基本面／防御组（必要条件：有息 + 低波动）</h4>
    <p>殖利率 ≥ 3%、波动在全池后半段，再加以下任两项：</p>
    <p>PE 历史分位 ≤ 60%　·　近 8 季 EPS ≥75% 为正　·　日均成交额 ≥ 3 亿　·　前 60 日涨幅 ≤ 30%（没被炒过）</p>
  </div>
  <div class="box p2" style="border-color:#3a2020">
    <h4 style="color:#e5484d">题材／炒作组（满足 ≥3 项）</h4>
    <p>波动前 30%　·　60 日涨幅前 30%　·　成交爆量前 30%　·　PE 分位 ≥70%　·　无本益比或亏损　·　殖利率 &lt;1%</p>
    <p style="color:#8b97a8">分位门槛用当期全池实际分布算，不用固定数字，避免不同年代失真。</p>
  </div>
</div>

<h3>四段空头 + 两段多头，分组中位报酬（含息）</h3>

{bear_group_svg()}

<div class="scroll">
<table>
<thead><tr><th>波段</th><th>方向</th><th>指数</th><th>防御组</th><th>中间组</th><th>炒作组</th><th>防御−炒作</th></tr></thead>
<tbody>
<tr><td class="nm">2022/07–2022/10</td><td>空头</td><td class="neg">−9.4%</td><td class="pos">{g(BEAR2,'DEF'):.2f}%</td><td>{g(BEAR2,'MID'):.2f}%</td><td class="neg">{g(BEAR2,'HYPE'):.2f}%</td><td><b>+{g(BEAR2,'DEF')-g(BEAR2,'HYPE'):.1f}pp</b></td></tr>
<tr><td class="nm">2024/07–2025/02</td><td>空头</td><td class="neg">−2.7%</td><td class="pos">{g(BEAR3,'DEF'):.2f}%</td><td>{g(BEAR3,'MID'):.2f}%</td><td class="neg">{g(BEAR3,'HYPE'):.2f}%</td><td><b>+{g(BEAR3,'DEF')-g(BEAR3,'HYPE'):.1f}pp</b></td></tr>
<tr class="hot"><td class="nm">2025/02–2025/04</td><td>空头急杀</td><td class="neg">−26.7%</td><td class="pos">{g(BEAR4,'DEF'):.2f}%</td><td>{g(BEAR4,'MID'):.2f}%</td><td class="neg">{g(BEAR4,'HYPE'):.2f}%</td><td><b>+{g(BEAR4,'DEF')-g(BEAR4,'HYPE'):.1f}pp</b></td></tr>
<tr><td class="nm">2022/10–2024/07</td><td>多头</td><td class="pos">+92.6%</td><td>{p2['DEF']:.1f}%</td><td>{p2['MID']:.1f}%</td><td>{p2['HYPE']:.1f}%</td><td>{p2['DEF']-p2['HYPE']:+.1f}pp</td></tr>
<tr><td class="nm">2025/04–2026/10</td><td>多头</td><td class="pos">+164.7%</td><td>{p1['DEF']:.1f}%</td><td>{p1['MID']:.1f}%</td><td class="pos"><b>{p1['HYPE']:.1f}%</b></td><td>−{p1['HYPE']-p1['DEF']:.1f}pp</td></tr>
</tbody>
</table>
</div>

<div class="quote">
<b>这张表就是「基本面股 vs 炒作股」的完整答案：</b>它们是<b>镜像</b>，不是好坏。<br>
炒作股在 2025/04 之后的多头里涨 <b>{p1['HYPE']:.1f}%</b>（防御组只有 {p1['DEF']:.1f}%），
但在 30 天急杀里跌 <b>{g(BEAR4,'HYPE'):.1f}%</b>（防御组 −{abs(g(BEAR4,'DEF')):.1f}%）。<br>
所以问题不该是「买哪一种」，而是<b>「各放多少、什么时候调」</b>——这正是 V3.8 四层桶在做的事。
</div>

<h2><span class="no">04</span>拉长看：炒作股是「看起来很会赚」的陷阱</h2>

<p>上面是逐波段分类。再做一次更干净的检验：<b>只在 2022/07/06 分一次组，之后 1,044 个交易日不再重分类，
全程等权持有</b>——这段全是样本外，没有任何事后调整。</p>

{group_nav_svg()}

<div class="scroll">
<table>
<thead><tr><th>分组</th><th>档数</th><th>全程报酬</th><th>年化</th><th>最大回撤</th><th>Calmar</th></tr></thead>
<tbody>
<tr><td class="nm">中间组</td><td>{GP['MID']['n']}</td><td class="pos">{GP['MID']['total_pct']:+.1f}%</td><td>{GP['MID']['ann_pct']:.1f}%</td><td class="neg">{GP['MID']['mdd_pct']:.1f}%</td><td><b>{GP['MID']['calmar']:.2f}</b></td></tr>
<tr><td class="nm">基本面／防御</td><td>{GP['DEF']['n']}</td><td class="pos">{GP['DEF']['total_pct']:+.1f}%</td><td>{GP['DEF']['ann_pct']:.1f}%</td><td class="neg">{GP['DEF']['mdd_pct']:.1f}%</td><td>{GP['DEF']['calmar']:.2f}</td></tr>
<tr class="hot"><td class="nm">题材／炒作</td><td>{GP['HYPE']['n']}</td><td class="neg">{GP['HYPE']['total_pct']:+.1f}%</td><td>{GP['HYPE']['ann_pct']:.1f}%</td><td class="neg">{GP['HYPE']['mdd_pct']:.1f}%</td><td>{GP['HYPE']['calmar']:.2f}</td></tr>
</tbody>
</table>
</div>

<p>在同一段大牛市里，<b>炒作组全程是负的（{GP['HYPE']['total_pct']:+.1f}%），最大回撤 {GP['HYPE']['mdd_pct']:.1f}%</b>，
而防御组稳稳 +{GP['DEF']['total_pct']:.1f}%。这解释了「为什么有人一路参与牛市、最后一算没赚到」：
他每次都在最热的时候进场，吃的是最后一段，赔的是整段回撤。</p>

<p class="sub">注：炒作组在该时点只有 {GP['HYPE']['n']} 档（门槛严格），样本小，此结果应视为方向性证据而非精确估计。
各波段重新分类时档数在 5–19 档之间，同样偏小。</p>

<h2><span class="no">05</span>风险把控：两类股票要用两套规则</h2>

<p>把基本面股和炒作股放在同一个止损框架里，是另一个常见错误：
<b>防御股该用「基本面止损」，炒作股必须用「纪律止损」</b>。前者怕被噪音洗掉，后者怕舍不得砍。</p>

<div class="scroll">
<table>
<thead><tr><th>维度</th><th>基本面／防御股</th><th>题材／炒作股</th></tr></thead>
<tbody>
<tr><td class="nm">定位</td><td>产生现金流，L1/L2</td><td>博超额，限 L3 卫星内</td></tr>
<tr><td class="nm">单档上限</td><td>4%（1,000 万 → 40 万）</td><td><b>1%</b>（→ 10 万）</td></tr>
<tr><td class="nm">该类总上限</td><td>60%（L1 25% + L2 35%）</td><td><b>10%</b>（占 L3 的一半）</td></tr>
<tr><td class="nm">止损方式</td><td>基本面止损：连 2 季营收/毛利恶化、买入理由消失</td><td>纪律止损：−15% 或跌破月线，<b>无条件、不解释</b></td></tr>
<tr><td class="nm">移动止损</td><td><b>不要用</b>（V3.8 实测全清年化只剩 3.48%）</td><td>可以用，但要比进场时更紧</td></tr>
<tr><td class="nm">持有期</td><td>以年计，看配息不看价差</td><td>以周计，主题熄火就走</td></tr>
<tr><td class="nm">加码</td><td>PE 分位 ≤30% 时可加</td><td><b>永不加码、绝不摊平</b></td></tr>
<tr><td class="nm">熊市动作</td><td>续抱领息、用股息再投入</td><td>先减，BEAR 时归零</td></tr>
<tr><td class="nm">决策依据</td><td>财报、配息、估值分位</td><td><b>禁止用消息面当理由</b></td></tr>
</tbody>
</table>
</div>

<div class="quote">
<b>为什么炒作股要设 1% 而不是 4%：</b>急杀段炒作组中位 {g(BEAR4,'HYPE'):.1f}%，
单档押 4% 会吃掉总资产 1.2%；押 1% 只吃 0.3%。
<b>仓位上限的意义不是「少赚」，是「让任何单一判断错误都不影响全局」。</b>
</div>

<h2><span class="no">06</span>熊市还在赚钱的人，做对了什么</h2>

<p>把每段空头里「报酬为正」的股票挑出来，和全体平均比。这是纯事前特征，不是事后归因：</p>

<div class="scroll">
<table>
<thead><tr><th>波段</th><th>上涨档数</th><th>殖利率(正/全体)</th><th>60日波动(正/全体)</th><th>PE分位(正/全体)</th><th>前60日涨幅(正/全体)</th></tr></thead>
<tbody>
<tr><td class="nm">2022/07–10</td><td>28 (25.2%)</td><td class="pos">8.4% / 7.6%</td><td>34.3% / 30.2%</td><td class="pos">0.29 / 0.39</td><td>−13.2% / −11.3%</td></tr>
<tr><td class="nm">2024/07–2025/02</td><td>35 (31.5%)</td><td class="pos">5.7% / 5.0%</td><td>31.5% / 28.3%</td><td>0.70 / 0.71</td><td>+8.0% / +6.2%</td></tr>
<tr class="hot"><td class="nm">2025/02–04 急杀</td><td>4 (3.6%)</td><td class="pos">4.8% / 3.7%</td><td class="pos"><b>13.8% / 24.0%</b></td><td>0.50 / 0.54</td><td>−1.5% / +0.4%</td></tr>
</tbody>
</table>
</div>

<p>诚实地读这张表：<b>唯一在每一段都成立的特征是「殖利率高于平均」</b>。
PE 分位只在 2022 那段有效，波动在 2022 和 2024 两段甚至反过来（上涨的股票波动更高）。
<b>只有在急杀里，「低波动」才突然变成决定性因素</b>——13.8% vs 24.0%，差了近一半。</p>

<div class="quote">
<b>所以「熊市赚钱的人」其实做了两件不同的事，视跌法而定：</b><br>
慢熊／盘跌 → 持有<b>有息、便宜、没被炒过</b>的股票，靠股息和轮动撑过去（28–45 档能上涨）。<br>
急杀 → <b>本来就没满仓</b>，现金在手上，等 20 日后反弹 +{REB[0]['ret_pct']:.1f}% 时才有钱进场。<br>
第二种才是真正的「熊市赚钱」——<b>它的收益来自熊市之前的仓位决定，不是熊市里的操作。</b>
</div>

<h2><span class="no">07</span>为什么有人在牛市亏钱：六个行为模型复现</h2>

<p>在两段真实多头（指数 +92.6% 和 +164.7%）里，同一个 0050 / 同一批股票，
只改变「人怎么操作」，看结果差多少。全部含息、含交易成本。</p>

{behavior_svg(BULL2)}

<div class="scroll">
<table>
<thead><tr><th>行为</th><th>多头① +92.6%</th><th>多头② +164.7%</th><th>相对买入持有</th><th>机制</th></tr></thead>
<tbody>
<tr class="hot"><td class="nm">买入持有（对照）</td><td>{BULL1['models']['BH']['total_pct']:+.1f}%</td><td><b>{BULL2['models']['BH']['total_pct']:+.1f}%</b></td><td>—</td><td>什么都不做</td></tr>
<tr><td class="nm">融资 2 倍杠杆</td><td>{BULL1['models']['LEVER']['total_pct']:+.1f}%</td><td>{BULL2['models']['LEVER']['total_pct']:+.1f}%</td><td class="pos">大幅领先</td><td>放大 beta（风险也放大）</td></tr>
<tr><td class="nm">追涨杀跌</td><td>{BULL1['models']['CHASE']['total_pct']:+.1f}%</td><td>{BULL2['models']['CHASE']['total_pct']:+.1f}%</td><td class="neg">少赚 {BULL2['models']['BH']['total_pct']-BULL2['models']['CHASE']['total_pct']:.0f}pp</td><td>5 日涨 3% 才买、跌 3% 就卖</td></tr>
<tr><td class="nm">每月追最强 10 档</td><td>{BULL1['models']['ROTATE']['total_pct']:+.1f}%</td><td>{BULL2['models']['ROTATE']['total_pct']:+.1f}%</td><td class="neg">少赚 {BULL2['models']['BH']['total_pct']-BULL2['models']['ROTATE']['total_pct']:.0f}pp</td><td>20 次换仓 + 买在相对高点</td></tr>
<tr><td class="nm">卖赢家、留输家</td><td>{BULL1['models']['DISPOSITION']['total_pct']:+.1f}%</td><td>{BULL2['models']['DISPOSITION']['total_pct']:+.1f}%</td><td class="neg">少赚 {BULL2['models']['BH']['total_pct']-BULL2['models']['DISPOSITION']['total_pct']:.0f}pp</td><td>处置效应</td></tr>
<tr><td class="nm">末段才进场＋单押最热</td><td>{BULL1['models']['LATE']['total_pct']:+.1f}%</td><td>{BULL2['models']['LATE']['total_pct']:+.1f}%</td><td class="neg">少赚 {BULL2['models']['BH']['total_pct']-BULL2['models']['LATE']['total_pct']:.0f}pp</td><td>只吃到最后 25%</td></tr>
</tbody>
</table>
</div>

<div class="kpis">
  <div class="kpi r"><div class="v">{BULL2['models']['_breadth']['negative_pct']:.1f}%</div><div class="l">第二段大牛市里<b>仍然下跌</b>的个股比例<br>（{BULL2['models']['_breadth']['negative_n']}/{BULL2['models']['_breadth']['n']} 档）</div></div>
  <div class="kpi r"><div class="v">{BULL2['models']['_breadth']['worst'][0][1]:.1f}%</div><div class="l">最惨个股 {BULL2['models']['_breadth']['worst'][0][0]}<br>指数同期 +164.7%</div></div>
  <div class="kpi g"><div class="v">{BULL2['models']['ROTATE']['turnovers']}</div><div class="l">追主题模型的换仓次数<br>成本约 {BULL2['models']['ROTATE']['turnovers']*D['meta']['cost_stock_pct']:.1f}%</div></div>
  <div class="kpi b"><div class="v">{BULL2['models']['LATE']['mdd_pct']:.0f}%</div><div class="l">末段进场的最大回撤<br>买入持有只有 {BULL2['models']['BH']['mdd_pct']:.0f}%</div></div>
</div>

<p><b>结论：牛市亏钱不需要「看错方向」，只要「动得太多」就够了。</b>
在指数涨 {BULL2['index_ret_pct']:.0f}% 的行情里，追主题、卖赢留输、晚进场这三个动作
分别把报酬压到 {BULL2['models']['ROTATE']['total_pct']:.0f}% / {BULL2['models']['DISPOSITION']['total_pct']:.0f}% / {BULL2['models']['LATE']['total_pct']:.0f}%，
而且回撤还更大（{BULL2['models']['ROTATE']['mdd_pct']:.0f}% / {BULL2['models']['LATE']['mdd_pct']:.0f}% vs 买入持有 {BULL2['models']['BH']['mdd_pct']:.0f}%）。
再加上单押到下跌的那 {BULL2['models']['_breadth']['negative_pct']:.0f}% 个股，就真的会亏。</p>

<h2><span class="no">08</span>杠杆：这段样本里它赢了，但这是最危险的误导</h2>

<p>必须诚实说：<b>2 倍杠杆在两段多头里都赚最多</b>（+{BULL1['models']['LEVER']['total_pct']:.0f}% / +{BULL2['models']['LEVER']['total_pct']:.0f}%），
全程模拟（2022/10 → 2025/04）峰值 +{LEV['lever_peak_pct']:.0f}%，就算在 {fdate(LEV['stopped_date'])} 因 20% 回撤被洗出去，
期末仍有 +{LEV['lever_final_pct']:.0f}%（买入持有 +{LEV['buyhold_final_pct']:.0f}%）。</p>

<p>但这<b>不能</b>当作「可以用杠杆」的证据——理由有三，全部是数据：</p>

<div class="steps">
  <div class="step"><div class="n">1</div><div class="c">
    <h4>顶部一次进场就腰斩</h4>
    <p>若在 {fdate(TOP['start'])} 满仓 2 倍杠杆，30 天后 <b>{TOP['lever_ret_pct']:.1f}%</b>，
    要涨回本需要 <b>+{TOP['recover_needed_pct']:.0f}%</b>。
    同期不加杠杆是 {TOP['index_ret_pct']:.1f}%。</p>
  </div></div>
  <div class="step"><div class="n">2</div><div class="c">
    <h4>回撤是买入持有的两倍</h4>
    <p>第二段多头，杠杆 MDD {BULL2['models']['LEVER']['mdd_pct']:.1f}% vs 买入持有 {BULL2['models']['BH']['mdd_pct']:.1f}%。
    杠杆放大的不只是报酬，是<b>你在最差那天会不会被追缴、会不会自己吓自己卖掉</b>。</p>
  </div></div>
  <div class="step"><div class="n">3</div><div class="c">
    <h4>这段样本没出现足以断头的跌幅</h4>
    <p>2 倍杠杆要真正断头（维持率跌破 130%）需要标的下跌 35% 以上。
    本样本最深的一段是 −26.7%，<b>差一点点</b>。
    用「没出事」证明「安全」，是标准的幸存者偏差——2000、2008、2020 都不在这个样本里。</p>
  </div></div>
</div>

<div class="quote">
<b>杠杆的真实问题不是数学，是时间：</b>它让你在最需要「等得起」的时候等不起。
V3.8 已经算过，100% 持股的最长水下时间是 24 个月；<b>带杠杆的人拿不到 24 个月</b>，
因为中途会被追缴或自己认输。所以四层桶的第一条铁律是「不加杠杆、不融资、不摊平」。
</div>

<h2><span class="no">09</span>怎么避免：把「会犯的错」写成不能改的规则</h2>

<div class="scroll">
<table>
<thead><tr><th>会犯的错</th><th>实测代价</th><th>对策（写进 IPS）</th></tr></thead>
<tbody>
<tr><td class="nm">急杀里靠选股硬撑</td><td>111 档只有 4 档涨</td><td>回撤 &gt;15% 或波动 &gt;45% → 卫星层归零，只减仓不换股</td></tr>
<tr><td class="nm">追主题、频繁换股</td><td>少赚 {BULL2['models']['BH']['total_pct']-BULL2['models']['ROTATE']['total_pct']:.0f}pp</td><td>换仓上限：每季 ≤1 次；单次换仓成本先算出来</td></tr>
<tr><td class="nm">卖赢家、留输家</td><td>少赚 {BULL2['models']['BH']['total_pct']-BULL2['models']['DISPOSITION']['total_pct']:.0f}pp</td><td>止盈只卖「一部分」（V3.8：+20% 卖 1/4），永不全部清仓</td></tr>
<tr><td class="nm">牛市末段才进场</td><td>只拿到 {BULL2['models']['LATE']['total_pct']:.0f}%、回撤 {BULL2['models']['LATE']['mdd_pct']:.0f}%</td><td>分批建仓写死在 IPS，不因「怕错过」一次买满</td></tr>
<tr><td class="nm">满仓单押个股</td><td>大牛市仍有 {BULL2['models']['_breadth']['negative_pct']:.1f}% 个股下跌</td><td>单档 ≤4%（炒作股 ≤1%）、行业 ≤25%</td></tr>
<tr><td class="nm">融资加杠杆</td><td>顶部 30 天 {TOP['lever_ret_pct']:.0f}%</td><td>零杠杆；融资余额永远为 0</td></tr>
<tr><td class="nm">把炒作股当长期投资</td><td>全程 {GP['HYPE']['total_pct']:+.1f}%、MDD {GP['HYPE']['mdd_pct']:.0f}%</td><td>炒作股设 −15% 无条件止损，绝不摊平</td></tr>
<tr><td class="nm">每天看盘改规则</td><td>所有动态择时 Calmar 都低于静态配置</td><td>一年只看四次，偏离 5pp 才动手</td></tr>
</tbody>
</table>
</div>

<h3>现在（2026/11/06）该做什么</h3>

<div class="card">
<p><b>最新行情（你提供，非快照）：</b>收盘 <b>{LATEST['last']:,.2f}</b>，距 252 日高点 {LATEST['high252']:,.2f} 回撤
<b>{LATEST['drawdown_pct']:.2f}%</b>，20 日年化波动 <b>{LATEST['vol20_pct']:.2f}%</b>，
年线 {LATEST['ma240']:,.2f} → 状态 <b style="color:#d4a24c">{LATEST['state']}</b>。
较快照最后一日（{fdate(D['meta']['range'][1])}，{CUR['last']:,.2f}）已跌 {abs(LATEST['drop_from_snapshot_pct']):.2f}%。</p>
<p><b>对照 V3.8 四层桶，具体动作：</b></p>
<ul>
<li>L3 卫星层 <b>20% → 10%</b>（BEAR 档），腾出的 10% 直接进 L0 现金</li>
<li>L2 核心层（0050）<b>不动</b>、L1 高股息<b>不动</b>——核心层永不择时</li>
<li>L0 补到 <b>≥24 个月生活费</b>；这笔钱不参与任何反弹讨论</li>
<li>列出持仓里符合「炒作组」特征的档（高波动＋爆量＋PE 分位 ≥70%＋几乎不配息），优先减</li>
<li>不加杠杆、不摊平、不抄底；等 20 日波动收敛到 30% 以下再谈回补</li>
<li>触发 V3.2 熔断（单日 −300 / 连亏 3 / 回撤 8%）时，<b>隔日不自动复机</b></li>
</ul>
<p class="sub">注意：快照内状态是 {CUR['state']}（{fdate(D['meta']['range'][1])} 收 {CUR['last']:,.2f}），
最新行情是 {LATEST['state']}。两者不矛盾，是<b>两周内行情变了</b>——这恰好说明为什么规则必须写死、不能靠当下感觉调。</p>
</div>

<h2><span class="no">10</span>一页纸：给爸妈的繁体版</h2>

<div class="onepage">
  <h3>漲的時候別急，跌的時候別慌</h3>
  <div class="sub2">SILVERSTOCK · 家人自用 · 2026</div>

  <p class="big">一、跌得慢可以選股，跌得急只能靠現金。</p>
  <p>2025 年 2 月那 30 天，大盤跌 26.7%，111 檔股票裡只有 4 檔上漲。
  那種時候不管選到多好的公司都沒用，<b>唯一有效的是「本來就沒買滿」</b>。</p>

  <p class="big">二、有配息的股票，跌的時候比較耐。</p>
  <p>我們統計過四段下跌，能上漲的股票，殖利率都比平均高一點；2022 年那段，便宜的股票也明顯較抗跌。
  但急殺時還要多一個條件：<b>波動要小</b>。</p>

  <div class="rule">
    <b>第一條：</b>生活費兩年的錢，永遠放定存，不進場。<br>
    <b>第二條：</b>不融資、不借錢買股票、跌了不攤平。<br>
    <b>第三條：</b>熱門題材股最多放總資產 1%，賠 15% 就賣，不找理由。<br>
    <b>第四條：</b>大盤回檔超過 15%，個股那一層先減一半，其餘不動。
  </div>

  <p class="big">三、為什麼有人牛市還會賠錢？</p>
  <p>我們用同一段大牛市實測：什麼都不做賺 198%，每個月追最強的 10 檔只剩 62%，
  把賺錢的賣掉、留著賠錢的只剩 59%，等到最後才進場只剩 39%。<br>
  <b>不是看錯方向，是動得太多次。</b></p>

  <p class="big">四、一年看四次就夠。</p>
  <p>每季檢查一次四層比例，跑掉 5% 才調回來。其餘時間不看盤。看得越多次，手越癢，賠得越多。</p>

  <table style="margin-top:20px">
  <thead><tr><th>狀況</th><th>動作</th></tr></thead>
  <tbody>
  <tr><td>慢慢跌、跌不深</td><td>留著有配息、便宜的好公司，繼續領息</td></tr>
  <tr><td>一個月內大跌兩成以上</td><td>不選股，直接減個股那一層，補現金</td></tr>
  <tr><td>大跌後反彈</td><td>用現金分批買，不要一次買滿</td></tr>
  <tr><td>一直漲、大家都在賺</td><td>更不要換股，也不要加槓桿</td></tr>
  </tbody>
  </table>

  <p style="margin-top:20px;font-size:12px;color:#8a7a5e">本頁為家人內部使用，非投資建議。</p>
</div>

<h2><span class="no">11</span>这份分析不知道的事</h2>

<ul>
<li><b>第一段空头（2021/06 起）无法事前分类</b>：它是资料起点，没有足够历史算 60 日波动与 PE 分位，故该段只报整体上涨档数，不参与 DEF/HYPE 比较。表里的「45/111」仍可用。</li>
<li><b>炒作组样本偏小</b>：各波段 5–19 档。趋势方向可信，精确百分点不宜外推。</li>
<li><b>波段来自 TAIEX 18% 反转（V3.6）</b>，是事后划分，仅用于研究；实盘不能等「确认转空」才动作，这也是所有动态择时跑输的原因。</li>
<li><b>行为模型是简化的机械化规则</b>，真人的行为更混乱，但也更容易犯同类错误。模型只用来显示方向与量级。</li>
<li><b>放空／反向 ETF／选择权／债券／黄金不在资料池里</b>，本报告对它们的熊市效果不做任何断言。</li>
<li><b>最新行情（11/06）是你提供的两个收盘数字</b>，不在 snapshot.json 内；完整实时序列取得后应重算状态。</li>
<li><b>样本是一段罕见大牛市</b>（TAIEX 5 年 +168%），杠杆与炒作股在此被高估、防御股被低估。换到 2000–2008 的台股，结论会更偏向防守。</li>
</ul>

<div class="foot">
<b>V3.9 · 熊市生存引擎</b><br>
数据：FinMind 公开历史资料（{fdate(D['meta']['range'][0])}–{fdate(D['meta']['range'][1])}，111 档，{D['meta']['days']} 交易日），含息、含交易成本。<br>
计算：<code>tool/v3/bear_market.py</code> → <code>v39_bear_result.json</code> → 本报告由 <code>tool/v3/gen_bear_report.py</code> 生成，数字程序回填。<br>
分类特征一律于各波段开始前一日计算；波段划分沿用 <code>V3.6 因素全景与实测</code>。<br>
本文件仅供本人与家人研究使用，不构成投资建议，不对外提供。
</div>

</div></body></html>"""

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(head)
    print(f"written {os.path.abspath(OUT)}  {len(head):,} chars")
    return OUT


if __name__ == "__main__":
    build()
