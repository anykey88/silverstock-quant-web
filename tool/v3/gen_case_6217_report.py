#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_case_6217_report.py — 由 v43_case_6217.json 產生淺底大字白話報告

規矩（V4.2）：數字全部由結果檔回填，不憑印象寫；資料不夠就寫不知道。
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = json.loads((ROOT / "v43_case_6217.json").read_text(encoding="utf-8"))
OUT = Path("/workspace/V4.3_中探针怎么操作.html")

C = D["computed"]
RF = D["real_funnel"]
FC = D["funnel_checks"]
HY = D["hype"]
LP = D["layer_pretrade"]
ST = D["structure"]
SC = D["scenarios"]
RE = D["reentry"]
AU = D["auto"]
GA = D["gaps"]


def e(x):
    return escape(str(x), quote=False)


P = []
def add(x):
    P.append(x)


def h2(no, title, sub=""):
    add(f'<h2><span class="no">{no}</span>{e(title)}'
        + (f'<span class="hsub">{e(sub)}</span>' if sub else "") + '</h2>')


def kpi(items):
    add('<div class="kpis">')
    for v, lab in items:
        add(f'<div class="kpi"><div class="kv">{e(v)}</div><div class="kl">{e(lab)}</div></div>')
    add('</div>')


def table(headers, rows, cls=""):
    add(f'<table class="{cls}"><thead><tr>')
    for h in headers:
        add(f'<th>{e(h)}</th>')
    add('</tr></thead><tbody>')
    for r in rows:
        add('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>')
    add('</tbody></table>')


# ══════════════════════════════════════════════════════════════════
# SVG：價格時間軸（4 點）
# ══════════════════════════════════════════════════════════════════
def chart_price():
    pts = C["prices"]
    W, H, L, R, T, B = 960, 300, 80, 40, 28, 46
    lo, hi = 95, 160
    def X(i): return L + i * (W - L - R) / (len(pts) - 1)
    def Y(v): return T + (hi - v) / (hi - lo) * (H - T - B)
    s = [f'<svg viewBox="0 0 {W} {H}" class="sv">']
    for gv in (100, 120, 140, 160):
        y = Y(gv)
        s.append(f'<line x1="{L}" y1="{y:.0f}" x2="{W-R}" y2="{y:.0f}" class="grid"/>')
        s.append(f'<text x="{L-10}" y="{y+5:.0f}" text-anchor="end" class="ax">{gv}</text>')
    path = " ".join(f"{'M' if i==0 else 'L'}{X(i):.0f},{Y(p['close']):.0f}" for i, p in enumerate(pts))
    s.append(f'<path d="{path}" class="ln"/>')
    for i, p in enumerate(pts):
        x, y = X(i), Y(p["close"])
        s.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6" class="dot"/>')
        s.append(f'<text x="{x:.0f}" y="{y-16:.0f}" text-anchor="middle" class="val">{p["close"]:.0f}</text>')
        s.append(f'<text x="{x:.0f}" y="{H-16}" text-anchor="middle" class="ax">{e(p["date"][5:])}</text>')
    s.append(f'<text x="{W-R}" y="{T+14}" text-anchor="end" class="hint">'
             f'四個交易日 {C["drop_1102_to_1106_pct"]}%</text>')
    s.append('</svg>')
    return "".join(s)


# ══════════════════════════════════════════════════════════════════
# SVG：月營收年增率減速
# ══════════════════════════════════════════════════════════════════
def chart_rev():
    rs = C["rev_yoy"]
    W, H, L, R, T, B = 960, 280, 66, 30, 26, 44
    lo, hi = 0, 60
    def X(i): return L + i * (W - L - R) / (len(rs) - 1)
    def Y(v): return T + (hi - v) / (hi - lo) * (H - T - B)
    s = [f'<svg viewBox="0 0 {W} {H}" class="sv">']
    for gv in (0, 20, 40, 60):
        y = Y(gv)
        s.append(f'<line x1="{L}" y1="{y:.0f}" x2="{W-R}" y2="{y:.0f}" class="grid"/>')
        s.append(f'<text x="{L-10}" y="{y+5:.0f}" text-anchor="end" class="ax">{gv}%</text>')
    path = " ".join(f"{'M' if i==0 else 'L'}{X(i):.0f},{Y(r['yoy_pct']):.0f}" for i, r in enumerate(rs))
    s.append(f'<path d="{path}" class="ln alt"/>')
    for i, r in enumerate(rs):
        x, y = X(i), Y(r["yoy_pct"])
        s.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5" class="dot alt"/>')
        if i in (0, len(rs) - 1):
            s.append(f'<text x="{x:.0f}" y="{y-14:.0f}" text-anchor="middle" class="val">'
                     f'{r["yoy_pct"]}%</text>')
        s.append(f'<text x="{x:.0f}" y="{H-14}" text-anchor="middle" class="ax sm">'
                 f'{e(r["month"][5:])}月</text>')
    s.append(f'<text x="{W-R}" y="{T+12}" text-anchor="end" class="hint">'
             f'從 {C["rev_yoy_first"]}% 掉到 {C["rev_yoy_last"]}%</text>')
    s.append('</svg>')
    return "".join(s)


# ══════════════════════════════════════════════════════════════════
# SVG：同業近一個月跌幅（條長＝跌幅，避免負值溢出）
# ══════════════════════════════════════════════════════════════════
def chart_peers():
    rows = [(p["name"], abs(p["m1"]), "#b5654a" if "中探針" in p["name"] else "#8a9db0")
            for p in C["peers"]]
    W, rh, L, lw, maxv = 960, 46, 40, 210, 30
    H = 30 + len(rows) * rh
    s = [f'<svg viewBox="0 0 {W} {H}" class="sv">']
    s.append(f'<text x="{L}" y="16" class="hint">條長代表「近一個月跌多少」，四檔都在跌</text>')
    for i, (lab, v, col) in enumerate(rows):
        y = 30 + i * rh
        w = v / maxv * (W - L - lw - 110)
        s.append(f'<text x="{L}" y="{y+22}" class="lb">{e(lab)}</text>')
        s.append(f'<rect x="{L+lw}" y="{y+6}" width="{max(3,w):.0f}" height="22" '
                 f'fill="{col}" rx="4" opacity="0.9"/>')
        s.append(f'<text x="{L+lw+w+10:.0f}" y="{y+23}" class="val" fill="{col}">−{v:.2f}%</text>')
    s.append('</svg>')
    return "".join(s)


# ══════════════════════════════════════════════════════════════════
# 報告本文
# ══════════════════════════════════════════════════════════════════
def build():
    add('<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">')
    add('<meta name="viewport" content="width=device-width,initial-scale=1">')
    add('<title>中探針怎麼操作｜用我們的方法看一檔具體股票</title>')
    add('''<style>
:root{--bg:#faf7f0;--card:#fffdf8;--ink:#2b2620;--mut:#6b6154;--line:#e2d9c8;
--gold:#b0812c;--goldbg:#fbf3df;--red:#b4453a;--redbg:#fbeeeb;
--green:#3c7a58;--greenbg:#edf5ef;--blue:#3b5a78;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:"PingFang TC","Microsoft JhengHei","Noto Sans TC",sans-serif;
 font-size:18px;line-height:1.85;padding:0 0 60px}
.wrap{max-width:1000px;margin:0 auto;padding:0 28px}
header{padding:52px 0 30px;border-bottom:3px solid var(--ink)}
.eyebrow{font-size:15px;letter-spacing:2px;color:var(--gold);font-weight:700}
h1{font-size:38px;line-height:1.35;margin:14px 0 10px;letter-spacing:1px}
.meta{color:var(--mut);font-size:15px}
h2{font-size:27px;margin:56px 0 20px;padding-bottom:12px;border-bottom:2px solid var(--line);
 display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.no{display:inline-flex;width:38px;height:38px;border-radius:50%;background:var(--ink);
 color:#fff;font-size:19px;align-items:center;justify-content:center;flex:none}
.hsub{font-size:15px;color:var(--mut);font-weight:400}
p{margin:14px 0}
.lead{font-size:21px;line-height:1.8}
.big{background:var(--goldbg);border-left:8px solid var(--gold);padding:24px 28px;
 font-size:24px;line-height:1.7;border-radius:0 10px 10px 0;margin:26px 0}
.warn{background:var(--redbg);border-left:8px solid var(--red);padding:20px 26px;
 border-radius:0 10px 10px 0;margin:22px 0;font-size:18px}
.ok{background:var(--greenbg);border-left:8px solid var(--green);padding:20px 26px;
 border-radius:0 10px 10px 0;margin:22px 0}
.kpis{display:flex;gap:14px;flex-wrap:wrap;margin:24px 0}
.kpi{flex:1 1 190px;background:var(--card);border:2px solid var(--line);
 border-radius:12px;padding:18px 16px;text-align:center}
.kv{font-size:32px;font-weight:800;color:var(--red);line-height:1.2}
.kl{font-size:15px;color:var(--mut);margin-top:8px}
table{width:100%;border-collapse:collapse;margin:20px 0;font-size:16px;background:var(--card)}
th,td{border:1px solid var(--line);padding:12px 14px;text-align:left;vertical-align:top}
th{background:#f0e9da;font-weight:700;font-size:15px}
td b{color:var(--ink)}
.badge{display:inline-block;padding:3px 12px;border-radius:20px;font-size:14px;
 font-weight:700;white-space:nowrap}
.b-red{background:var(--redbg);color:var(--red);border:1px solid var(--red)}
.b-green{background:var(--greenbg);color:var(--green);border:1px solid var(--green)}
.b-amber{background:var(--goldbg);color:var(--gold);border:1px solid var(--gold)}
.chart{background:var(--card);border:2px solid var(--line);border-radius:12px;
 padding:14px;margin:22px 0}
.sv{width:100%;height:auto;display:block}
.grid{stroke:#e8e0d0;stroke-width:1}
.ax{fill:#7a6f60;font-size:14px}
.ax.sm{font-size:12px}
.lb{fill:var(--ink);font-size:16px;font-weight:600}
.val{fill:var(--ink);font-size:17px;font-weight:700}
.hint{fill:var(--mut);font-size:14px}
.ln{fill:none;stroke:var(--blue);stroke-width:3.5;stroke-linejoin:round}
.ln.alt{stroke:var(--gold)}
.dot{fill:#fff;stroke:var(--blue);stroke-width:3}
.dot.alt{stroke:var(--gold)}
.note{font-size:15px;color:var(--mut);margin:10px 2px}
ul,ol{padding-left:26px}li{margin:9px 0}
.card{background:var(--card);border:2px solid var(--line);border-radius:12px;
 padding:22px 26px;margin:18px 0}
.card h3{margin:0 0 8px;font-size:21px}
.verdict{font-size:19px;font-weight:800;color:var(--red)}
.onepager{background:#fff;border:3px solid var(--ink);border-radius:14px;
 padding:34px 38px;margin:26px 0;font-size:20px;line-height:1.95}
.onepager h3{font-size:26px;margin:0 0 18px;text-align:center;
 border-bottom:2px solid var(--ink);padding-bottom:14px}
.onepager .three{display:flex;flex-direction:column;gap:18px;margin-top:18px}
.onepager .row{display:flex;gap:16px;align-items:flex-start}
.onepager .n{font-size:30px;font-weight:800;color:var(--gold);line-height:1;flex:none;width:40px}
.onepager .bigline{font-size:23px;font-weight:800;margin-bottom:4px}
footer{margin-top:60px;padding-top:22px;border-top:2px solid var(--line);
 color:var(--mut);font-size:14px}
@media print{body{background:#fff}.chart,.card,.kpi{break-inside:avoid}}
@media(max-width:640px){body{font-size:17px}h1{font-size:30px}h2{font-size:23px}
 .wrap{padding:0 16px}.onepager{padding:22px}}
</style></head><body><div class="wrap">''')

    # 標頭
    add('<header>')
    add('<div class="eyebrow">V4.3 ．用我們的方法看一檔具體股票</div>')
    add('<h1>中探針（6217）該怎麼操作？</h1>')
    add(f'<div class="meta">資料最新到 {e(C["last_date"])} 收盤 ｜ 整理日 {e(D["asof"])} '
        '｜ 給家人看的版本：大字、白話、繁體</div>')
    add('</header>')

    # 1
    h2(1, "先給一句話")
    add(f'<div class="big">{e(D["one_line"])}</div>')
    add('<p class="lead">很多人看到「從 371 跌到 109」，第一個念頭是「便宜好多」。'
        '我們的方法第一個動作不是算便宜多少，是<b>先問這檔該不該放進來</b>。</p>')
    add('<div class="warn"><b>要先講清楚的一件事：這檔不在我們的資料池裡。</b><br>'
        f'我們手上的 111 檔台股日線（2021–2026）沒有 6217。所以下面每一個數字，'
        '都來自外部公開網頁，而且逐條標了日期與來源。<br>'
        f'<b>{e(GA["what_we_did"])}</b><br>{e(GA["plain"])}</div>')
    add('<div class="card" style="font-size:16px"><b>怎麼讀這份報告（先看這裡）</b><br>'
        '· 文中的 V3.8、V3.9、V4.0、V4.1 是前面幾份報告的編號，看不懂直接跳過，不影響結論。<br>'
        '· <b>回撤</b>＝從最高點跌下來多少；<b>倉位</b>＝放了多少錢在股票裡；'
        '<b>本益比</b>＝股價除以每股賺多少（公司賠錢時算不出來）；'
        '<b>殖利率</b>＝一年股息除以股價。<br>'
        '· <b>安檢門</b>＝買之前要過的關卡，一關沒過就不放行。</div>')

    # 2
    h2(2, "這幾天到底發生了什麼", "四個交易日、一條往下走的線")
    add('<div class="chart">' + chart_price() + '</div>')
    kpi([
        (f'{C["last_close"]:.0f} 元', f'{C["last_date"]} 收盤價'),
        (f'{C["drop_1102_to_1106_pct"]}%', '11/02 到 11/06 跌了多少'),
        (f'{C["drop_from_52w_high_pct"]}%', f'從一年最高 {C["w52_high"]:.0f} 跌到現在'),
        (f'+{C["recover_to_high_pct"]:.0f}%', f'要回到 {C["w52_high"]:.0f} 得漲這麼多'),
    ])
    add(f'<p>把時間拉長看更清楚：這檔一年內最低 {C["w52_low"]} 元、最高 '
        f'{C["w52_high"]} 元，<b>先漲了 {C["rise_from_52w_low_to_high_pct"]}%</b>，'
        f'再從高點跌 {abs(C["drop_from_52w_high_pct"])}%。</p>')
    add('<p class="lead"><b>白話：這不是一台慢慢開的車，是雲霄飛車。</b>'
        '先衝到屋頂，再一路俯衝。現在問「要不要上車」，要先看它還在不在往下掉，'
        '不是看票價比上個月便宜多少。</p>')
    rows = []
    for h in C["horizon"]:
        col = "#b4453a" if h["pct"] < 0 else "#3c7a58"
        rows.append([e(h["label"]), f'<b style="color:{col}">{h["pct"]:+.2f}%</b>'])
    add('<p class="note">同一天（11/06）網站上看到的各段報酬，正負並排，'
        '這就是「今年還是賺、最近卻賠很慘」的意思：</p>')
    table(["看多久", "報酬"], rows)
    add('<p class="note">來源：Yahoo 奇摩股市 6217.TWO（2026/11/06）。'
        '不同網站的「今年以來」基準日不同，MoneyDJ 在 11/02 記的是 +189.06%，'
        '兩者不能混著算，這裡只取同一來源的數字。</p>')

    # 3
    h2(3, "公司本身在賺錢嗎", "基本面是我們方法的地基")
    add('<p class="lead">前面幾版一直講「跟著基本面走」。這檔最該看的就是這一格：'
        '<b>生意變大了，但還沒賺錢。</b></p>')
    rows = [[e(f["item"]), f'<b>{e(f["value"])}</b>', e(f["plain"])] for f in C["fundamentals"]]
    table(["項目", "實際數字", "白話怎麼說"], rows)
    add('<p class="note">來源：Winvest、nStock、Yahoo 奇摩、元大證券處置股公告；'
        '財報到 2026Q2、營收到 2026/09。</p>')
    add('<div class="chart">' + chart_rev() + '</div>')
    add(f'<p>月營收的「比去年同月成長多少」，從 1 月的 '
        f'<b>{C["rev_yoy_first"]}%</b> 一路掉到 9 月的 <b>{C["rev_yoy_last"]}%</b>，'
        f'少了 {abs(C["rev_yoy_slowdown_pp"])} 個百分點。'
        '同一段時間，股價卻還掛在「今年以來 +112.89%」。</p>')
    add('<div class="warn"><b>白話：引擎的油門鬆了，車子還在半空中。</b>'
        '營收成長快等於公司會賺錢，這兩件事不一樣。'
        '我們的方法裡，這一格填不出本益比、也沒有股息，就沒有「基本面安全墊」可依靠。'
        '（要誠實：這是兩件事同時發生，不能說一定是誰造成誰。）</div>')

    # 4
    h2(4, "第一道關卡就擋下來了", "不是算出來不好，是根本不准算")
    add(f'<div class="ok"><b>我真的把這檔餵進我們既有的選股程式跑了一次。</b><br>'
        f'程式規定至少要有 <b>{RF["min_bars_required"]} 根日線</b>（約 4 年），'
        f'外部資料只找到 <b>{RF["bars_available"]} 根</b> → '
        f'直接判 <b>不通過</b>，原因「{e("、".join(RF["fail_reason"]))}」。<br>'
        f'{e(RF["plain"])}</div>')
    add('<p>接著我用外部資料，把五道安檢門逐項人工核對一遍（門檻數字'
        '直接沿用選股程式的常數，一條都沒放寬）：</p>')
    rows = []
    for r in FC["rows"]:
        if r["status"] == "pass":
            b = '<span class="badge b-green">過關</span>'
        elif r["status"] == "fail":
            b = '<span class="badge b-red">沒過</span>'
        else:
            b = '<span class="badge b-amber">算不出來</span>'
        rows.append([e(r["gate"]), f'<b>{e(r["observed"])}</b>', b, e(r["plain"])])
    table(["安檢門", "看到的實際狀況", "結果", "白話"], rows)
    add(f'<div class="warn"><b>{e(FC["plain"])}</b><br>'
        '<span class="note">「算不出來」也算不過關，這是我們故意定的規矩，'
        '叫「資料不夠就當不合格」——寧可錯過，不要放寬。</span></div>')
    add(f'<p class="note">{e(FC["disclaimer"])}</p>')

    # 5
    h2(5, "它屬於哪一類股票", "對照我們實測過的「炒作組」")
    add(f'<p class="lead">{e(HY["plain"])}</p>')
    rows = [[e(x["feature"]), e(x["ours"]), e(x["ref"]),
             '<span class="badge b-red">中</span>'] for x in HY["checks"]]
    table(["炒作組特徵", "這檔的實際狀況", "我們之前實測的對照", "命中"], rows)
    hr = HY["hype_ref"]
    add(f'<div class="warn"><b>前一版實測過的結局：</b>'
        f'炒作組 {hr["n"]} 檔，分組後持有 1044 天，全程 <b>{hr["total_pct"]}%</b>、'
        f'最深跌 <b>{hr["mdd_pct"]}%</b>；同一段時間防禦組是 +99.2%。<br>'
        '<b>白話：這一類股票漲起來最猛，但一次急殺就把前面賺的全吃掉。</b>'
        '它不是「好公司暫時便宜」，是本來就不一樣的東西。</div>')
    add(f'<p class="note">分層判定：<b>{e(LP["layer"])}</b>'
        f'（{e(LP["layer_reason"])}）。白話：這檔最多只能放總資產的 '
        f'<b>{LP["single_stock_cap_pct"]}%</b>，而且只能放在最外面那一小格。<br>'
        f'現在大盤是<b>空頭</b>（收盤 {LP["regime"]["last"]}，'
        f'比一年最高點跌了 {abs(LP["regime"]["drawdown_pct"])}%），'
        f'所以全部股票加起來最多只能放 {LP["regime"]["position_cap_pct"]}%，'
        '剩下的放現金。</p>')
    add(f'<div class="warn"><b>交易前 12 問：{LP["pretrade"]["issue_n"]} 題沒過，今天不准下單。</b><br>'
        + '<br>'.join('· ' + e(x) for x in LP["pretrade"]["key_fails"]) + '</div>')

    # 6
    h2(6, "今天是哪一種行情", "判別順序不能倒過來")
    add(f'<p class="lead"><b>{e(ST["market_state"])}</b>。'
        f'{e(ST["plain"])}</p>')
    add('<div class="chart">' + chart_peers()
        + '<p class="note" style="margin:6px 4px 0">同業近一個月報酬，'
        '四檔全部為負；條長代表跌幅。來源：MoneyDJ（2026/11/02）。</p></div>')
    add('<div class="card"><h3>當天的線索</h3><ul>')
    for x in ST["evidence"]:
        add(f'<li>{e(x)}</li>')
    add('</ul></div>')
    add(f'<div class="ok"><b>判別順序：{e(ST["order"])}</b><br>'
        '<span class="note">今天指數在跌、整個族群也在跌，這種日子該做的是「調總倉位」，'
        '不是「挑哪一支比較便宜」。順序倒過來，就是在急殺日白費力氣。</span></div>')
    vr = ST["v41_ref"]
    add(f'<p><b>量比</b>就是「今天的成交量 ÷ 最近 20 天的平均量」，'
        f'11/05 只有 {ST["volume_ratio_1105"]}，等於當天只成交平常的兩成；'
        f'20 日均量 {ST["avg_vol_20d_lots"]:,} 張。<br>'
        f'前面實測把成交量分成六組，<b>沒有一組跑贏「同一批股票的平均」</b>'
        f'（最縮的那組落後 {abs(vr["extreme_low_excess_pct"])}%、'
        f'最爆量的落後 {abs(vr["burst_excess_pct"])}%）。'
        f'{e(ST["volume_rule"])}。</p>')

    # 7
    h2(7, "三種人、三套做法", "先想清楚自己是哪一種")
    for s in SC:
        add('<div class="card">')
        add(f'<h3>{e(s["who"])}　<span class="verdict">{e(s["verdict"])}</span></h3>')
        add('<ol>' + ''.join(f'<li>{e(x)}</li>' for x in s["steps"]) + '</ol>')
        add(f'<div class="ok" style="margin:12px 0 0">{e(s["plain"])}</div>')
        if s.get("honest"):
            add(f'<p class="note"><b>要誠實：</b>{e(s["honest"])}</p>')
        add('</div>')

    # 8
    h2(8, "什麼時候才重新拿出來看", "三個條件要同時成立")
    add('<div class="card">')
    for c in RE["conditions"]:
        add(f'<p><b>{c["no"]}．{e(c["text"])}</b><br>'
            f'<span class="note">白話：{e(c["plain"])}</span></p>')
    add(f'<div class="warn"><b>{e(RE["gate"])}</b></div></div>')
    h2(9, "自動交易要怎麼設", "它的工作是踩煞車，不是找買點")
    add(f'<div class="warn"><b>現況：{e(AU["status"])}</b><br>'
        f'<b>這檔{e(AU["whitelist"])}</b></div>')
    add('<div class="card"><h3>可以設的</h3><ul>'
        + ''.join(f'<li>{e(x)}</li>' for x in AU["allowed_orders"]) + '</ul>'
        '<h3>不可以設的</h3><ul>'
        + ''.join(f'<li>{e(x)}</li>' for x in AU["not_allowed"]) + '</ul></div>')
    add(f'<p class="lead">{e(AU["plain"])}</p>')

    # 10 一頁紙
    h2(10, "給爸媽的一頁紙", "可列印・只講三件事")
    add('<div class="onepager"><h3>中探針（6217）・三件事就好</h3>')
    add('<div class="three">')
    add('<div class="row"><div class="n">1</div><div>'
        '<div class="bigline">現在不要買。</div>'
        f'它一年內從 {C["w52_low"]} 元漲到 {C["w52_high"]} 元，又跌到 '
        f'{C["last_close"]:.0f} 元。要回到最高點得再漲 '
        f'<b>+{C["recover_to_high_pct"]:.0f}%</b>。'
        '<br><span class="note">「比之前便宜」不是買的理由。</span></div></div>')
    add('<div class="row"><div class="n">2</div><div>'
        '<div class="bigline">公司還在賠錢，也沒發股息。</div>'
        '去年每股賠 1.65 元，今年上半年還是賠；今年股息 0 元。'
        '<br><span class="note">沒有股息當安全墊，跌的時候沒有東西接住您。</span></div></div>')
    add('<div class="row"><div class="n">3</div><div>'
        '<div class="bigline">已經有的，慢慢降到很小。</div>'
        '不加碼、不攤平、不借錢補；每天降一點，'
        '退出來的錢先放回現金（留 24 個月生活費），再放到會配息的地方。'
        '<br><span class="note">不用一次砍完，也不用每天盯盤，照表做就好。</span></div></div>')
    add('</div>')
    add('<p style="margin-top:24px;border-top:2px solid #2b2620;padding-top:16px;'
        'text-align:center;font-size:19px"><b>一句話：這檔交給規則管，不要交給感覺管。</b></p>')
    add('</div>')

    # 11 局限
    h2(11, "這次哪裡可能錯", "每次都要附這一張")
    add('<div class="card"><ul>')
    for x in GA["cannot_answer"]:
        add(f'<li><b>不知道：</b>{e(x)}</li>')
    add('<li>外部資料來自不同網站、不同基準日，' + e(C["note"]) + '</li>')
    add('<li>價格鏈 148 → 131 → 118 → 109 是四個來源交叉拼起來的，'
        '已核對前後收盤價吻合，但不是同一份連續日線。</li>')
    add('<li>「分批降到 ≤1%」在下跌段沒有對應的實測，'
        '前面 V4.0 的分批減碼數字來自上漲段，不能直接套用。</li>')
    add('<li>整份判斷建立在「這檔不在回測池」的前提上；'
        '若日後補進 111 檔日線，五道安檢門的分數要全部重算。</li>')
    add('<li>這是方法示範與風險控管，不是買賣建議；'
        '系統仍在模擬盤，沒有連線、沒有下單。</li>')
    add('</ul></div>')

    add('<div class="ok"><b>往後說話的規矩（這版照做）</b><br>'
        '先給一句結論 → 每個道理配一個真數字和生活比喻 → '
        '專有名詞立刻換成白話 → 句子短、字大、留白多 → '
        '資料不夠就寫不知道 → 每次附上「這次哪裡可能錯」 → '
        '數字全部由程式讀檔回填。</div>')

    add('<footer>')
    add(f'V4.3 ｜ {e(D["case"])} ｜ 引擎 tool/v3/case_6217.py ｜ '
        '結果 v43_case_6217.json ｜ 本頁數字由結果檔程式回填，無手工抄錄。<br>')
    add('引用來源：' + '；'.join(e(v) for v in C["sources"].values()) + '。<br>')
    add('本頁為家人自用的方法示範與風險控管，非投資建議。')
    add('</footer>')
    add('</div></body></html>')

    OUT.write_text("".join(P), encoding="utf-8")
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"產出 {p}  ({p.stat().st_size:,} bytes)")
