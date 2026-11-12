#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_largest_report.py — 由 v46_largest_asset.json 產生 V4.6 淺底大字白話報告

規矩（V4.2 起，泰哥要求）：
  · 給長輩看：淺底、大字、短句、生活比喻、術語立刻換白話
  · 每一個數字都由結果檔回填，不憑印象寫
  · 資料不夠就寫「不知道」，不編總資產、不編該賣幾股
  · 全文手寫繁體，不做簡繁自動轉換（避免「不准→不準」「當沖→當衝」誤轉）
  · 不印出引擎原始簡體題目，只用白話轉述
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = json.loads((ROOT / "v46_largest_asset.json").read_text(encoding="utf-8"))
OUT = Path("/workspace/V4.6_最大资产怎么办.html")
CARD = Path("/workspace/V4.6_最大资产决策卡.md")

T = D["truth"]
WC = D["what_changed"]
ST = D["size_trap"]
TP = D["two_piles"]
CO = D["concentration"]
RU = D["ruler"]
UR = D["urgent"]
PT = D["pretrade"]
WB = D["wrongbook"]
AC = D["actions"]
UP = D["upgrade"]
AU = D["auto"]


def e(x):
    return escape(str(x), quote=False)


def money(x):
    return f"{x:,.0f}"


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


def shrink_chart():
    """兩根長條：買進當時這一張值多少 vs 現在值多少。"""
    then, now = ST["then_value"], ST["now_value"]
    W, H = 960, 300
    x0, x1 = 250, 900
    top, gap = 55, 105
    def width(v): return (x1 - x0) * v / then
    s = [f'<svg viewBox="0 0 {W} {H}" class="sv">']
    s.append(f'<text x="{x0}" y="{top-16}" class="lb">買進當時，這一張帳面上值</text>')
    s.append(f'<rect x="{x0}" y="{top}" width="{width(then):.0f}" height="52" fill="#b0812c" rx="6"/>')
    s.append(f'<text x="{x0+width(then)-14:.0f}" y="{top+35}" text-anchor="end" '
             f'style="fill:#fff;font-size:22px;font-weight:800">{money(then)} 元</text>')
    y2 = top + gap
    s.append(f'<text x="{x0}" y="{y2-16}" class="lb">現在，這一張值</text>')
    s.append(f'<rect x="{x0}" y="{y2}" width="{width(now):.0f}" height="52" fill="#3b5a78" rx="6"/>')
    s.append(f'<text x="{x0+width(now)+14:.0f}" y="{y2+35}" '
             f'style="fill:#2b2620;font-size:22px;font-weight:800">{money(now)} 元</text>')
    s.append(f'<text x="{x0}" y="{y2+92}" class="hint">自己縮掉了 {e(ST["shrink_down"])}。'
             '我們還記得它當初有多重，但那不是今天的重量。</text>')
    s.append('</svg>')
    return "".join(s)


def piles_chart():
    """一根長條切成兩段：已經不見的 vs 還守得住的。"""
    gone, left = TP["gone"], TP["left"]
    total = gone + left
    W, H = 960, 240
    x0, x1 = 60, 900
    y, hh = 70, 68
    def width(v): return (x1 - x0) * v / total
    wg = width(gone)
    s = [f'<svg viewBox="0 0 {W} {H}" class="sv">']
    s.append(f'<text x="{x0}" y="{y-18}" class="lb">當初付出去的那一袋米，現在分成兩塊</text>')
    s.append(f'<rect x="{x0}" y="{y}" width="{wg:.0f}" height="{hh}" fill="#b4453a" rx="6"/>')
    s.append(f'<rect x="{x0+wg:.0f}" y="{y}" width="{width(left):.0f}" height="{hh}" '
             f'fill="#3c7a58" rx="6"/>')
    s.append(f'<text x="{x0+16}" y="{y+43}" style="fill:#fff;font-size:21px;font-weight:800">'
             f'已經不見 {money(gone)} 元</text>')
    s.append(f'<text x="{x0+wg+14:.0f}" y="{y+43}" '
             f'style="fill:#fff;font-size:21px;font-weight:800">還在 {money(left)} 元</text>')
    s.append(f'<text x="{x0}" y="{y+hh+46}" class="hint">'
             '左邊那塊追不回來；現在能守的，是右邊那一塊不要再縮。</text>')
    s.append('</svg>')
    return "".join(s)


# ══════════════════════════════════════════════════════════════════
CSS = """
:root{--bg:#faf7f0;--card:#fffdf8;--ink:#2b2620;--mut:#6b6154;--line:#e2d9c8;
--gold:#b0812c;--goldbg:#fbf3df;--red:#b4453a;--redbg:#fbeeeb;
--green:#3c7a58;--greenbg:#edf5ef;--blue:#3b5a78;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:"PingFang TC","Microsoft JhengHei","Noto Sans TC",sans-serif;
 font-size:20px;line-height:1.9;padding:0 0 70px}
.wrap{max-width:1000px;margin:0 auto;padding:0 28px}
header{padding:54px 0 30px;border-bottom:3px solid var(--ink)}
.eyebrow{font-size:16px;letter-spacing:2px;color:var(--gold);font-weight:700}
h1{font-size:40px;line-height:1.35;margin:14px 0 10px;letter-spacing:1px}
.meta{color:var(--mut);font-size:16px}
h2{font-size:28px;margin:60px 0 20px;padding-bottom:12px;border-bottom:2px solid var(--line);
 display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.no{display:inline-flex;width:40px;height:40px;border-radius:50%;background:var(--ink);
 color:#fff;font-size:20px;align-items:center;justify-content:center;flex:none}
.hsub{font-size:16px;color:var(--mut);font-weight:400}
p{margin:16px 0}
.lead{font-size:23px;line-height:1.85}
.big{background:var(--goldbg);border-left:8px solid var(--gold);padding:26px 30px;
 font-size:27px;line-height:1.7;border-radius:0 10px 10px 0;margin:28px 0;font-weight:700}
.warn{background:var(--redbg);border-left:8px solid var(--red);padding:22px 28px;
 border-radius:0 10px 10px 0;margin:24px 0;font-size:20px}
.ok{background:var(--greenbg);border-left:8px solid var(--green);padding:22px 28px;
 border-radius:0 10px 10px 0;margin:24px 0;font-size:20px}
.kpis{display:flex;gap:14px;flex-wrap:wrap;margin:26px 0}
.kpi{flex:1 1 200px;background:var(--card);border:2px solid var(--line);
 border-radius:12px;padding:20px 16px;text-align:center}
.kv{font-size:32px;font-weight:800;color:var(--red);line-height:1.2}
.kl{font-size:16px;color:var(--mut);margin-top:8px}
table{width:100%;border-collapse:collapse;margin:22px 0;font-size:18px;background:var(--card)}
th,td{border:1px solid var(--line);padding:14px 16px;text-align:left;vertical-align:top}
th{background:#f0e9da;font-weight:700;font-size:16px}
.chart{background:var(--card);border:2px solid var(--line);border-radius:12px;
 padding:18px;margin:24px 0}
.sv{width:100%;height:auto;display:block}
.lb{fill:var(--ink);font-size:19px;font-weight:700}
.hint{fill:var(--mut);font-size:17px}
ul,ol{padding-left:28px}li{margin:12px 0}
.card{background:var(--card);border:2px solid var(--line);border-radius:12px;
 padding:24px 28px;margin:20px 0}
.card h3{margin:0 0 10px;font-size:23px}
.card.chgcard{border-left:8px solid var(--gold)}
.card.urgentcard{border-left:8px solid var(--red)}
.onepager{background:#fff;border:3px solid var(--ink);border-radius:14px;
 padding:36px 40px;margin:28px 0;font-size:23px;line-height:2}
.onepager h3{font-size:28px;margin:0 0 20px;text-align:center;
 border-bottom:2px solid var(--ink);padding-bottom:16px}
.onepager .row{display:flex;gap:18px;align-items:flex-start;margin:20px 0}
.onepager .n{font-size:32px;font-weight:800;color:var(--gold);line-height:1;flex:none;width:44px}
.onepager .bigline{font-size:25px;font-weight:800;margin-bottom:4px}
.note{font-size:16px;color:var(--mut);margin:12px 2px}
footer{margin-top:64px;padding-top:22px;border-top:2px solid var(--line);
 color:var(--mut);font-size:15px}
@media print{body{background:#fff}.chart,.card,.kpi{break-inside:avoid}}
@media(max-width:640px){body{font-size:18px}h1{font-size:31px}h2{font-size:24px}
 .wrap{padding:0 16px}.onepager{padding:22px;font-size:20px}}
"""


# ══════════════════════════════════════════════════════════════════
add('<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">')
add('<meta name="viewport" content="width=device-width,initial-scale=1">')
add('<title>它是我最大的資產，該怎麼辦｜中探針決策卡</title>')
add(f'<style>{CSS}</style></head><body><div class="wrap">')

add('<header><div class="eyebrow">V4.6 ．接著 V4.5，補上「它是我最大的一筆資產」</div>')
add('<h1>它是我最大的資產，<br>前面的結論要怎麼改？</h1>')
add(f'<div class="meta">中探針 6217 ｜ 資料最新到 {e(D["asof"])} ｜ '
    f'下一個交易日 {e(D["next_trading_day"])} ｜ 給家人看的版本：大字、白話、繁體</div></header>')

# ── 1 一句話 ────────────────────────────────────────────────────────
h2("1", "先給一句話")
add(f'<div class="big">{e(D["one_line"])}</div>')
add(f'<div class="ok"><b>您今天補的這句話很重要：</b>{e(D["new_fact"])}。'
    '它沒有改變股票的價格，卻改變了【該怎麼做】——因為問題從「一張股票怎麼辦」，'
    '變成「家裡最重的一袋米放在哪裡」。</div>')
kpi([
    (f'{money(T["buy_paid"])} 元', "當初買一張，付出去"),
    (f'{money(T["sell_received"])} 元', "現在賣掉，拿回來"),
    (f'少 {e(T["loss_down"])}', "中間不見的"),
])
add('<p class="note">錢的數字真的用既有的費用引擎算過：買賣各一次手續費、賣出還有交易稅。'
    '以下所有數字都由結果檔回填，沒有一個是憑印象寫的。</p>')

# ── 2 給爸媽的一頁紙 ────────────────────────────────────────────────
h2("2", "給爸媽的一頁紙", "可以單獨印這張給長輩")
add('<div class="onepager"><h3>三件事就好</h3>')
add('<div class="row"><div class="n">1</div><div><div class="bigline">最重的一袋米，別再放在漏水的房間。</div>'
    f'既然它是家裡最大的一筆，上一版「{RU["cap_pct"]:.0f}% 以內可以先留著」那條退路就用不上了。'
    '方向只有一個：慢慢把錢搬回乾的地方，不是明天一次砍光。<br>'
    '<span class="note">不是認賠，是搬家。</span></div></div>')
add('<div class="row"><div class="n">2</div><div><div class="bigline">當初的「最大」，現在只剩三分之一不到。</div>'
    f'買進當時這一張值 {money(ST["then_value"])} 元，現在值 {money(ST["now_value"])} 元，'
    f'自己縮掉了 {e(ST["shrink_down"])}。別拿舊的重量當今天的重量。<br>'
    f'<span class="note">{e(ST["analogy"])}</span></div></div>')
add('<div class="row"><div class="n">3</div><div><div class="bigline">先顧還在的那袋，不要追已經不見的。</div>'
    f'回不來的是 {money(TP["gone"])} 元，還守得住的是 {money(TP["left"])} 元。'
    f'先確認家裡 {D["cash_months"]} 個月生活費還在，'
    '再照日曆一天搬一點。<br>'
    f'<span class="note">{e(TP["analogy"])}</span></div></div>')
add('</div>')

# ── 3 最容易記錯的地方 ──────────────────────────────────────────────
h2("3", "最容易記錯：最大，是當初的記法")
add(f'<div class="chart">{shrink_chart()}</div>')
add(f'<p class="lead">{e(ST["plain"])}</p>')
add(f'<div class="ok"><b>白話：</b>{e(ST["analogy"])}</div>')
add(f'<p class="note">為什麼圖上寫縮掉 {e(ST["shrink_down"])}，前面卻寫少 {e(T["loss_down"])}：'
    '前者是股價本身跌的幅度，後者把買賣手續費與交易稅也算進去，是真正少掉的錢。'
    '差在費用，不是算錯。</p>')
add(f'<p class="note">順帶一提：要回到當初付出去的錢，得漲到 '
    f'{T["recover_price"]:.1f} 元，等於從現在再漲 {T["recover_pct"]:.2f}%；'
    f'而這家公司近四季還是賠錢（{e(T["eps_ttm"])}）、{e(T["dividend"])}，沒有息可墊著。</p>')

# ── 4 兩個袋子 ──────────────────────────────────────────────────────
h2("4", "兩個袋子，該顧的是後面那一袋")
add(f'<div class="chart">{piles_chart()}</div>')
add(f'<p class="lead">{e(TP["plain"])}</p>')
add(f'<div class="warn"><b>上一版有一句話要收回一半：</b>我說過「只有一張，最壞再賠 '
    f'{money(T["sell_received"])} 元就到底，算是做對了一件事」。數學上確實封頂了，'
    '但現在知道它同時是家裡最重的一袋米——不是無底洞，可是再掉下去會很痛。'
    '這條已經記進後面的錯題本。</div>')

# ── 5 為什麼最重的一袋放在這一格特別危險 ────────────────────────────
h2("5", "為什麼「最重的一袋放在這一格」特別危險", "下面每個數字都是前面實測過的")
add('<table><tr><th>看什麼</th><th>數字</th><th>白話</th></tr>')
for ref in CO["refs"]:
    add(f'<tr><td>{e(ref["lab"])}</td><td><b>{e(ref["val"])}</b></td>'
        f'<td>{e(ref["note"])}</td></tr>')
add('</table>')
add(f'<p class="lead">{e(CO["plain"])}</p>')
add(f'<div class="ok"><b>白話：</b>{e(CO["analogy"])}</div>')
add('<p class="note">這些數字全部由既有的「錢怎麼分」、熊市、市場結構這幾份舊結果檔讀出，'
    '不是為了這一題另外編的；資料池裡沒有這檔股票，所以任何「這樣做會賺多少」一律寫不知道。</p>')

# ── 6 1% 那格有多小 ────────────────────────────────────────────────
h2("6", f"「{RU['cap_pct']:.0f}% 那格」到底有多小", "給您一把可以自己套用的尺")
add(f'<p class="lead">我們給這類股票寫的上限是「只佔全部資產 {RU["cap_pct"]:.0f}% 以內」。'
    '下面三行只是示範怎麼算，<b>不是您的資產</b>：</p>')
add(f'<table><tr><th>假如家裡全部資產</th><th>這張現在佔</th>'
    f'<th>{RU["cap_pct"]:.0f}% 那格是</th><th>要搬走</th></tr>')
for x in RU["examples"]:
    add(f'<tr><td>{money(x["total"])} 元</td><td>{x["now_pct"]:.2f}%</td>'
        f'<td>{money(x["target"])} 元</td><td><b>{money(x["move"])} 元</b>'
        f'（這張的 {x["move_pct_of_lot"]:.1f}%）</td></tr>')
add('</table>')
add(f'<div class="warn"><b>公式：</b>{e(RU["formula"])}<br>{e(RU["caveat"])}</div>')
add(f'<div class="ok"><b>要誠實：</b>{e(RU["honest"])}<br>{e(RU["not_all_stocks"])}</div>')

# ── 7 最急的兩件事 ─────────────────────────────────────────────────
h2("7", "最急的兩件事，今天就能做")
for u in UR:
    add(f'<div class="card urgentcard"><h3>{e(u["title"])}</h3>'
        f'<p>{e(u["why"])}</p>'
        + (f'<p class="note">怎麼算：{e(u["formula"])}。{e(u["plain"])}</p>'
           if "formula" in u else f'<p class="note">{e(u["plain"])}</p>')
        + '</div>')

# ── 8 12 問再跑一次 ────────────────────────────────────────────────
h2("8", "有人叫您「再補一點」，怎麼辦")
add(f'<p class="lead">{e(PT["purpose"])}</p>')
add(f'<div class="warn"><b>{e(PT["plain"])}</b></div>')
add('<ul>')
for k in PT["key_fails"]:
    add(f'<li>{e(k)}</li>')
add('</ul>')
add(f'<p class="note"><b>要誠實：</b>{e(PT["honest"])}</p>')

# ── 9 接下來照日曆做 ───────────────────────────────────────────────
h2("9", "接下來照日曆做", "不看盤、不改方向")
add('<table><tr><th>什麼時候</th><th>做什麼</th></tr>')
for a in AC:
    add(f'<tr><td><b>{e(a["when"])}</b></td><td>{e(a["do"])}</td></tr>')
add('</table>')
add(f'<div class="card chgcard"><h3>{e(UP["title"])}</h3>'
    f'<p><b>建議的規矩：</b>{e(UP["rule"])}</p>'
    f'<p>{e(UP["why"])}</p>'
    f'<p class="note">{e(UP["status"])}</p></div>')
add(f'<div class="ok"><b>{e(AU["plain"])}</b>'
    f'<br><span class="note">{e(AU["status"])}；{e(AU["whitelist"])}。</span></div>')

# ── 10 哪些事我不知道 ──────────────────────────────────────────────
h2("10", "哪些事我不知道", "不知道就寫不知道，不編")
add('<ul>')
for u in D["unknown"]:
    add(f'<li>{e(u)}</li>')
add('</ul>')
add(f'<div class="warn"><b>提醒：</b>{e(D["disclaimer"])}</div>')

# ── footer ─────────────────────────────────────────────────────────
add('<footer><b>數字從哪裡來</b><ul>')
for s in D["sources"]:
    add(f'<li>{e(s)}</li>')
add('</ul></footer>')
add('</div></body></html>')
OUT.write_text("\n".join(P), encoding="utf-8")
print(f"產出 {OUT.name}（{OUT.stat().st_size:,} bytes）")


# ══════════════════════════════════════════════════════════════════
# 可列印決策卡（純文字、繁體、大字標題）
# ══════════════════════════════════════════════════════════════════
L = []
def q(x=""):
    L.append(x)


q("# 它是我最大的資產，前面的結論要怎麼改？· 可列印決策卡")
q("")
q(f"> 中探針 6217 ｜ 資料最新到 {D['asof']} ｜ 下一個交易日 {D['next_trading_day']}")
q("> 給家人看的版本：大字、白話、繁體。所有數字由 `v46_largest_asset.json` 回填。")
q("")
q("---")
q("")
q("## 給爸媽的一頁紙（三件事就好）")
q("")
q(f"**1．最重的一袋米，別再放在漏水的房間。** 既然它是家裡最大的一筆，"
  f"上一版「{RU['cap_pct']:.0f}% 以內可以先留著」那條退路就用不上了。"
  "方向只有一個：慢慢把錢搬回乾的地方，不是明天一次砍光。")
q(f"**2．當初的「最大」，現在只剩三分之一不到。** 買進當時值 "
  f"{money(ST['then_value'])} 元，現在值 {money(ST['now_value'])} 元，自己縮掉了 "
  f"{ST['shrink_down']}。別拿舊的重量當今天的重量。")
q(f"**3．先顧還在的那袋，不要追已經不見的。** 回不來的是 {money(TP['gone'])} 元，"
  f"還守得住的是 {money(TP['left'])} 元。先確認生活費，再照日曆一天搬一點。")
q("")
q(f"> **{D['one_line']}**")
q("")
q("---")
q("")
q("## 1．您補的這句話，改了什麼")
q("")
for w in WC:
    q(f"- {w['before']} **→ {w['after']}**")
    q(f"　　{w['why']}")
q("")
q("## 2．一張的錢（費用引擎算過）")
q("")
q(f"| 項目 | 金額 |")
q(f"|---|---|")
q(f"| 當初買一張，付出去 | {money(T['buy_paid'])} 元 |")
q(f"| 現在賣掉，拿回來 | {money(T['sell_received'])} 元 |")
q(f"| 中間不見的 | {money(T['loss'])} 元（少 {T['loss_down']}） |")
q(f"| 要回到當初實付 | 漲到 {T['recover_price']:.1f} 元，再漲 {T['recover_pct']:.2f}% |")
q("")
q(f"{ST['plain']}")
q("")
q(f"為什麼圖上寫縮掉 {ST['shrink_down']}，表格卻寫少 {T['loss_down']}："
  "前者是股價本身跌的幅度，後者把買賣手續費與交易稅也算進去，是真正少掉的錢。"
  "差在費用，不是算錯。")
q("")
q(f"> {ST['analogy']}")
q("")
q("## 3．兩個袋子")
q("")
q(f"{TP['plain']}")
q("")
q(f"> 上一版「最壞已封頂，算是做對一件事」要收回一半：封頂不等於不痛，"
  f"因為封頂的那一筆正是家裡最重的一袋米。")
q("")
q("## 4．為什麼最重的一袋放在這一格特別危險")
q("")
q("| 看什麼 | 數字 | 白話 |")
q("|---|---|---|")
for ref in CO["refs"]:
    q(f"| {ref['lab']} | {ref['val']} | {ref['note']} |")
q("")
q(f"{CO['plain']}")
q("")
q(f"> {CO['analogy']}")
q("")
q(f"## 5．「{RU['cap_pct']:.0f}% 那格」到底有多小（舉例換算，不是您的資產）")
q("")
q(f"| 假如家裡全部資產 | 這張現在佔 | {RU['cap_pct']:.0f}% 那格是 | 要搬走 |")
q("|---|---|---|---|")
for x in RU["examples"]:
    q(f"| {money(x['total'])} 元 | {x['now_pct']:.2f}% | {money(x['target'])} 元 | "
      f"{money(x['move'])} 元（這張的 {x['move_pct_of_lot']:.1f}%） |")
q("")
q(f"公式：{RU['formula']}")
q(f"{RU['caveat']}")
q(f"要誠實：{RU['honest']}")
q(f"{RU['not_all_stocks']}")
q("")
q("## 6．最急的兩件事")
q("")
for u in UR:
    q(f"**{u['title']}**")
    q(f"　　{u['why']}")
    if "formula" in u:
        q(f"　　怎麼算：{u['formula']}。{u['plain']}")
    else:
        q(f"　　{u['plain']}")
    q("")
q("## 7．有人叫您「再補一點」，怎麼辦")
q("")
q(f"{PT['purpose']}")
q("")
q(f"> **{PT['plain']}**")
for k in PT["key_fails"]:
    q(f"- {k}")
q("")
q(f"要誠實：{PT['honest']}")
q("")
q("## 8．接下來照日曆做")
q("")
for a in AC:
    q(f"- **{a['when']}**：{a['do']}")
q("")
q(f"**{UP['title']}**：{UP['rule']}")
q(f"　　{UP['why']}")
q(f"　　{UP['status']}")
q("")
q("## 9．錯題本（系統自己記下來的）")
q("")
for w in WB:
    q(f"- **{w['rule']}**：{w['evidence']}")
q("")
q("## 10．哪些事我不知道")
q("")
for u in D["unknown"]:
    q(f"- {u}")
q("")
q("---")
q("")
q(f"> **提醒：{D['disclaimer']}**")
q(f"> {AU['plain']} {AU['status']}；{AU['whitelist']}。")
q("")
q("數字來源：" + "；".join(D["sources"][:4]) + "。")

CARD.write_text("\n".join(L), encoding="utf-8")
print(f"產出 {CARD.name}（{CARD.stat().st_size:,} bytes）")
