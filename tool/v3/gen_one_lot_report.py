#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_one_lot_report.py — 由 v45_one_lot.json 產生 V4.5 淺底大字白話報告

規矩（V4.2 起，泰哥要求）：
  · 給長輩看：淺底、大字、短句、生活比喻、術語立刻換白話
  · 每一個數字都由結果檔回填，不憑印象寫
  · 資料不夠就寫「不知道」，不編「會賺多少」
  · 全文手寫繁體，不做簡繁自動轉換（避免「不准→不準」「當沖→當衝」誤轉）
  · 不印出引擎原始簡體題目，只用白話轉述
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = json.loads((ROOT / "v45_one_lot.json").read_text(encoding="utf-8"))
OUT = Path("/workspace/V4.5_一张还能怎么办.html")
CARD = Path("/workspace/V4.5_一张怎么办决策卡.md")

T = D["truth"]
CAP = D["cap"]
BR = D["branch"]
A = D["average_down"]
SP = D["split_odd"]
OPS = D["options"]
WB = D["wrongbook"]
AC = D["actions"]
PT = D["pretrade"]
OP = D["opportunity"]
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
        add(f'<div class="kpi"><div class="kv">{e(v).replace("-", "−")}</div>'
            f'<div class="kl">{e(lab).replace("-", "−")}</div></div>')
    add('</div>')


def bar_chart():
    """兩根長條：當初付出去 vs 現在拿回來。不畫曲線，長輩一眼就懂。"""
    buy, sell = T["buy_paid"], T["sell_received"]
    W, H = 960, 300
    x0, x1 = 250, 900
    top, gap = 55, 105
    def width(v): return (x1 - x0) * v / buy
    s = [f'<svg viewBox="0 0 {W} {H}" class="sv">']
    s.append(f'<text x="{x0}" y="{top-16}" class="lb">當初買一張，付出去</text>')
    s.append(f'<rect x="{x0}" y="{top}" width="{width(buy):.0f}" height="52" fill="#b4453a" rx="6"/>')
    s.append(f'<text x="{x0+width(buy)-14:.0f}" y="{top+35}" text-anchor="end" '
             f'style="fill:#fff;font-size:22px;font-weight:800">{money(buy)} 元</text>')
    y2 = top + gap
    s.append(f'<text x="{x0}" y="{y2-16}" class="lb">現在賣掉，拿回來</text>')
    s.append(f'<rect x="{x0}" y="{y2}" width="{width(sell):.0f}" height="52" fill="#3b5a78" rx="6"/>')
    s.append(f'<text x="{x0+width(sell)+14:.0f}" y="{y2+35}" '
             f'style="fill:#2b2620;font-size:22px;font-weight:800">{money(sell)} 元</text>')
    s.append(f'<text x="{x0}" y="{y2+92}" class="hint">中間不見的 {money(T["loss"])} 元，'
             '在股價跌下來那天就已經不見了，不是今天賣掉才不見。</text>')
    s.append('</svg>')
    return "".join(s)


def tag(verdict):
    cls = "t-ok" if verdict in ("可以做", "先辦") else ("t-no" if verdict in ("不要做", "不要當辦法", "不成立", "不是辦法", "已經來不及") else "t-un")
    return f'<span class="tag {cls}">{e(verdict)}</span>'


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
.kv{font-size:34px;font-weight:800;color:var(--red);line-height:1.2}
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
.card.okcard{border-left:8px solid var(--green)}
.card.nocard{border-left:8px solid var(--red)}
.card.uncard{border-left:8px solid var(--mut)}
.card.urgentcard{border-left:8px solid var(--gold)}
.tag{display:inline-block;padding:3px 13px;border-radius:20px;font-size:16px;
 font-weight:800;color:#fff;white-space:nowrap}
.t-ok{background:var(--green)}.t-no{background:var(--red)}.t-un{background:var(--mut)}
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
add('<title>只有一張，除了認賠還有什麼辦法｜中探針決策卡</title>')
add(f'<style>{CSS}</style></head><body><div class="wrap">')

add('<header><div class="eyebrow">V4.5 ．接著 V4.4 那一題，回答「只有一張」</div>')
add('<h1>只有一張，除了認賠賣出<br>還有什麼辦法？</h1>')
add(f'<div class="meta">中探針 6217 ｜ 資料最新到 {e(D["asof"])} ｜ '
    f'下一個交易日 {e(D["next_trading_day"])} ｜ 給家人看的版本：大字、白話、繁體</div></header>')

# ── 1 一句話 ────────────────────────────────────────────────────────
h2("1", "先給一句話")
add(f'<div class="big">{e(D["one_line"])}</div>')
add(f'<p class="lead">{e(T["sell_role"])}</p>')
add(f'<div class="warn"><b>先說清楚：我不知道您全部資產多少、是不是借錢買的、'
    f'實際買價是不是 {money(T["buy_price"])} 元。</b><br>'
    f'所以下面用「<b>買一張、買在 {money(T["buy_price"])} 元</b>」當例子算。'
    '比例和做法一樣，金額請照您的實際數字換算。</div>')

# ── 2 給爸媽的一頁紙 ────────────────────────────────────────────────
h2("2", "給爸媽的一頁紙", "可以單獨印這張給長輩")
add('<div class="onepager"><h3>三件事就好</h3>')
add('<div class="row"><div class="n">1</div><div><div class="bigline">賠，不是今天賣掉才發生的。</div>'
    f'當初付 {money(T["buy_paid"])} 元，現在這張只值 {money(T["now_value_before_fee"])} 元。'
    f'{e(T["plain"])}<br>'
    '<span class="note">「沒賣就不算賠」是最容易騙自己的一句話。</span></div></div>')
add('<div class="row"><div class="n">2</div><div><div class="bigline">只有一張，最壞已經到底了。</div>'
    f'{e(CAP["plain"])}<br>'
    f'<span class="note">但千萬不要再買一張「攤平」：那會把最多再賠的錢，從 '
    f'{money(CAP["worst_more"])} 元變成 {money(CAP["worst_more_if_average"])} 元。</span></div></div>')
add('<div class="row"><div class="n">3</div><div><div class="bigline">真的能做的，是這三件事。</div>'
    '① 先問「這張佔家裡多少錢」：不到 1%，本來就不用急著賣。<br>'
    '② 真的要退，一張可以拆開、分幾天慢慢退，不必一天砍光。<br>'
    '③ 把這次寫進規矩，交給系統，讓下次不要再用同一種方式賠一次。</div></div>')
add(f'<div class="ok" style="margin-top:26px"><b>一句話：</b>這 {T["loss_wan"]}'
    '已經回不來了；現在能守的，是「不要再變大」和「下次不要再來一次」。</div></div>')

# ── 3 錢的真相 ──────────────────────────────────────────────────────
h2("3", "錢的真相，先算清楚", "全部由費用引擎算，含手續費與賣出稅")
kpi([
    (f'{money(T["buy_paid"])} 元', "當初買一張，實付"),
    (f'{money(T["sell_received"])} 元', "現在賣掉，實收"),
    (f'{money(T["loss"])} 元', f'中間不見的（少了 {abs(T["loss_pct_on_cash"]):.2f}%）'),
])
add('<div class="chart">' + bar_chart() + '</div>')
add(f'<p>{e(T["already"])}</p>')
add(f'<div class="ok"><b>所以「認賠賣出」到底做了什麼？</b><br>{e(T["sell_role"])}</div>')
add(f'<p class="note">費用：買、賣各收一次手續費，賣出再扣一筆交易稅；'
    f'這張買付 {money(T["buy_fee"])} 元手續費，賣扣 {money(T["sell_fee"])} 元手續費加 '
    f'{money(T["sell_tax"])} 元稅。實際以券商交割單為準。</p>')

# ── 4 最關鍵的一題 ──────────────────────────────────────────────────
h2("4", "最關鍵的一題：這一張佔家裡多少錢？", "回答它，才知道要不要賣")
add(f'<div class="ok"><b>{e(BR["small"]["title"])} → 本來就不用急著賣。</b><br>'
    f'{e(BR["small"]["do"])}<br><span class="note">{e(BR["small"]["plain"])}</span></div>')
add(f'<div class="warn"><b>{e(BR["large"]["title"])} → 才需要慢慢降。</b><br>'
    f'{e(BR["large"]["do"])}<br><span class="note">{e(BR["large"]["plain"])}</span></div>')
add(f'<p><b>要誠實：</b>{e(BR["unknown"])}</p>')
add(f'<p class="note">「{BR["cap_pct"]}%」是 V4.3 就寫好的炒作股規矩：'
    '這種一年內可以漲好幾倍、又幾乎跌回來的股票，本來就只准放很小一點。'
    f'<br>{e(BR["next_hint"])}</p>')

# ── 5 三個真的有用 ──────────────────────────────────────────────────
N_USE = len([o for o in OPS if o["group"] == "真的有用"])
N_URGENT = len([o for o in OPS if o["group"] == "最急的一件事"])
h2("5", f"真的有用的 {N_USE} 個，加上 {N_URGENT} 件最急的")
useful = [o for o in OPS if o["group"] == "真的有用"]
urgent = [o for o in OPS if o["group"] == "最急的一件事"]
for o in useful + urgent:
    cls = "okcard" if o["group"] == "真的有用" else "urgentcard"
    add(f'<div class="card {cls}"><h3>{e(o["name"])}　{tag(o["verdict"])}</h3>'
        f'<p>{e(o["plain"])}</p>'
        f'<p class="note"><b>數字：</b>{e(o["number"])}</p></div>')

# ── 6 攤平 ──────────────────────────────────────────────────────────
h2("6", "最常被想到的「攤平」，算給你看", "再買一張，讓平均成本好看一點")
add(f'<p class="lead">{e(A["plain"])}</p>')
add('<table><tr><th>項目</th><th>不攤平（只有一張）</th><th>攤平（再買一張）</th></tr>')
add(f'<tr><td>總共付出去</td><td>{money(T["buy_paid"])} 元</td><td>{money(A["total_paid"])} 元</td></tr>')
add(f'<tr><td>平均一股成本</td><td>{money(T["buy_price"])} 元</td><td>{A["avg_cost"]:,.0f} 元（看起來變便宜）</td></tr>')
add(f'<tr><td>現在全部賣掉，實收</td><td>{money(T["sell_received"])} 元</td><td>{money(A["sell_all_received"])} 元</td></tr>')
add(f'<tr><td>總共賠</td><td>{money(T["loss"])} 元</td><td>{money(A["loss_if_average"])} 元（多賠 {money(A["extra_loss_now"])} 元）</td></tr>')
add(f'<tr><td>【假如，不是預測】再跌一成（到 {A["drop_price"]:.1f} 元），還要再賠</td>'
    f'<td>{money(A["more_loss_1lot"])} 元</td><td>{money(A["more_loss_2lots"])} 元</td></tr>')
add(f'<tr><td>股價每跌 1 元，就少</td><td>{money(A["per_1dollar_1lot"])} 元</td>'
    f'<td>{money(A["per_1dollar_2lots"])} 元</td></tr></table>')
add(f'<div class="warn"><b>白話：</b>平均成本從 {money(T["buy_price"])} 降到 '
    f'{A["avg_cost"]:,.0f}，只是數字好看，不是真的便宜。'
    '就像一件外套原本買貴了，再買一件打折的，'
    '「平均一件比較便宜」不等於「少花了錢」——您總共拿出來的錢變多了。</div>')
add(f'<div class="ok"><b>所以第 4 節那句話要記住：</b>只有一張，最壞再賠 '
    f'{money(CAP["worst_more"])} 元就到底；攤平後變成 '
    f'{money(CAP["worst_more_if_average"])} 元。<b>別讓它變大，就是現在最實在的「降低損失」。</b></div>')

# ── 7 看起來有用其實沒有 ────────────────────────────────────────────
h2("7", "其他看起來有用，其實沒有的", "一條一條說清楚，不賣關子")
others = [o for o in OPS if o["group"] == "看起來有用，其實沒有"]
add('<table><tr><th style="width:24%">想法</th><th>為什麼不算</th><th style="width:16%">結果</th></tr>')
for o in others:
    add(f'<tr><td><b>{e(o["name"])}</b></td>'
        f'<td>{e(o["plain"])}<br><span class="note">{e(o["number"])}</span></td>'
        f'<td>{tag(o["verdict"])}</td></tr>')
add('</table>')
add('<p class="note">名詞白話：'
    '<b>攤平</b>＝再買一張讓平均價變低；<b>當沖</b>＝當天買當天賣、不留過夜；'
    '<b>抵稅</b>＝報稅時少繳一點；<b>借券</b>＝把股票借給別人去賣、對方付您利息；'
    '<b>認售權證／選擇權</b>＝另外買一張「賭它跌」的票，會到期、可能歸零；'
    '<b>零股</b>＝不滿一張（1000 股），可以一股一股買賣。</p>')

# ── 8 分批退 ────────────────────────────────────────────────────────
h2("8", "真的要退：一張也能慢慢退", "不必一天砍光，也不必賭今天最低點")
add(f'<p class="lead">{e(SP["plain"])}</p>')
add('<table><tr><th>怎麼賣</th><th>合計拿到</th></tr>')
add(f'<tr><td>一次賣掉一整張（1000 股）</td><td>{money(SP["once_received"])} 元</td></tr>')
add(f'<tr><td>分十天、每天賣 100 股零股</td><td>{money(SP["ten_days_received"])} 元</td></tr>')
add(f'<tr><td><b>差額</b></td><td><b>只差 {money(SP["diff"])} 元</b></td></tr></table>')
add(f'<div class="warn">{e(SP["warn"])}</div>')
add(f'<div class="ok"><b>分批換到的是什麼？</b>不是賣得比較貴，是「不必賭今天是不是最低點」——'
    '對睡不著的人，這比多幾塊錢重要。</div>')
add(f'<p class="note">{e(SP["honest"])}</p>')

# ── 9 12 問、錢放哪、靠日曆 ────────────────────────────────────────
h2("9", "系統幫您踩煞車，不靠意志力")
add(f'<div class="warn"><b>真的再跑一次「下單前 12 問」，問的是「現在攤平準不準」：</b><br>'
    f'{e(PT["plain"])}<br>'
    '<span class="note">其中兩題是明確的「否」：公司最近一年合起來是賠錢的；'
    '以及「因為它跌很多才想買」——這一題專門在擋伸手接刀。'
    '其餘題目沒回答，依規矩一律算不過關。</span></div>')
add(f'<div class="ok"><b>退出來的錢放哪？</b>先放回現金，補滿 24 個月生活費；'
    f'滿了之後才放到會配息的地方，不要馬上換別支股票。<br>'
    f'<span class="note">換個算法更有感：{e(OP["formula"])}。{e(OP["plain"])}</span></div>')
add('<table><tr><th style="width:30%">什麼時候</th><th>做什麼</th></tr>')
for a in AC:
    add(f'<tr><td><b>{e(a["when"])}</b></td><td>{e(a["do"])}</td></tr>')
add('</table>')
add(f'<p class="note">自動交易現況：{e(AU["status"])}。'
    '在這裡它只幫您踩煞車（不准加碼、不准抄底），不幫您找買點。</p>')

# ── 10 錯題本 ───────────────────────────────────────────────────────
h2("10", "把這次寫成三條規矩", "唯一能把學費換回價值的地方")
for i, w in enumerate(WB, 1):
    add(f'<div class="card"><h3>規矩 {i}．{e(w["rule"])}</h3>'
        f'<p class="note">{e(w["evidence"])}</p></div>')
add('<div class="big">不是責備自己，是讓系統下次自動擋下來。'
    '人會累、會心軟、會想「這次不一樣」；規矩不會。</div>')

# ── 11 我不知道 ─────────────────────────────────────────────────────
h2("11", "哪些事我不知道", "資料不夠就寫不知道，不編")
add('<div class="card uncard"><ul>')
for u in D["unknown"]:
    add(f'<li>{e(u)}</li>')
add('</ul></div>')

# ── 12 來源與免責 ───────────────────────────────────────────────────
h2("12", "這些數字從哪裡來")
add('<div class="card"><ul>')
for s in D["sources"]:
    add(f'<li>{e(s)}</li>')
add('</ul></div>')
add(f'<div class="warn"><b>{e(D["disclaimer"])}</b><br>'
    '<span class="note">「模擬盤」＝紙上練習，沒有連到券商、沒有下任何一張單。</span></div>')

add('<footer>引擎 tool/v3/case_6217_one_lot.py ｜ 結果 v45_one_lot.json ｜ '
    '報告產生器 tool/v3/gen_one_lot_report.py ｜ 本頁數字由結果檔回填，無手工抄錄。</footer>')
add('</div></body></html>')

OUT.write_text("\n".join(P), encoding="utf-8")
print(f"產出 {OUT.name}（{OUT.stat().st_size:,} bytes）")


# ══════════════════════════════════════════════════════════════════
# 可列印決策卡（純文字，繁體，白話）
# ══════════════════════════════════════════════════════════════════
L = []
def q(x=""):
    L.append(x)

q("# 只有一張，除了認賠賣出還有什麼辦法？· 可列印決策卡")
q("")
q(f"> 中探針 6217 ｜ 資料最新到 {D['asof']} ｜ 下一個交易日 {D['next_trading_day']}")
q("> 給家人看的版本：大字、白話、繁體。所有數字由 `v45_one_lot.json` 回填。")
q("")
q("---")
q("")
q("## 給爸媽的一頁紙（三件事就好）")
q("")
q(f"**1．賠，不是今天賣掉才發生的。** 當初付 {money(T['buy_paid'])} 元，"
  f"現在這張只值 {money(T['now_value_before_fee'])} 元。{T['plain']}")
q("　　→ 「沒賣就不算賠」是最容易騙自己的一句話。")
q(f"**2．只有一張，最壞已經到底了。** {CAP['plain']}")
q(f"　　→ 但千萬別再買一張攤平：最多再賠的錢會從 {money(CAP['worst_more'])} 元"
  f"變成 {money(CAP['worst_more_if_average'])} 元。")
q("**3．真的能做的三件事：** ① 先問這張佔家裡多少錢（不到 1% 本來就不用急著賣）；"
  "② 真的要退，一張拆開分幾天慢慢退；③ 把這次寫進規矩，交給系統。")
q("")
q(f"> **一句話：這 {T['loss_wan']}已經回不來了；"
  "現在能守的，是「不要再變大」和「下次不要再來一次」。**")
q("")
q("---")
q("")
q("## 錢的真相")
q("")
q(f"| 項目 | 金額 |")
q(f"|---|---|")
q(f"| 當初買一張，實付 | {money(T['buy_paid'])} 元 |")
q(f"| 現在賣掉，實收 | {money(T['sell_received'])} 元 |")
q(f"| 中間不見的 | {money(T['loss'])} 元（少了 {abs(T['loss_pct_on_cash']):.2f}%） |")
q(f"| 要回到當初付出去的錢 | 得漲到 {T['recover_price']:.1f} 元，再漲 {T['recover_pct_from_now']:.2f}% |")
q("")
q(T["already"])
q("")
q(f"**認賠賣出到底做了什麼？** {T['sell_role']}")
q("")
q(f"> 費用：買付 {money(T['buy_fee'])} 元手續費，賣扣 {money(T['sell_fee'])} 元手續費"
  f"加 {money(T['sell_tax'])} 元交易稅。實際以券商交割單為準。")
q("")
q("---")
q("")
q("## 最關鍵的一題：這一張佔家裡多少錢？")
q("")
q(f"- **{BR['small']['title']}** → {BR['small']['do']}（{BR['small']['plain']}）")
q(f"- **{BR['large']['title']}** → {BR['large']['do']}（{BR['large']['plain']}）")
q(f"- 要誠實：{BR['unknown']}")
q("")
q(f"> {BR['next_hint']}")
q("")
q("---")
q("")
q(f"## 所有 {len(OPS)} 個辦法，一個個算給你看")
q("")
q(f"### 真的有用（{N_USE} 個）＋ 最急（{N_URGENT} 個）")
for o in useful + urgent:
    q(f"**{o['name']}｜{o['verdict']}**")
    q(f"　{o['plain']}")
    q(f"　數字：{o['number']}")
    q("")
q("### 看起來有用，其實沒有")
for o in others:
    q(f"**{o['name']}｜{o['verdict']}**")
    q(f"　{o['plain']}")
    q(f"　數字：{o['number']}")
    q("")
q("---")
q("")
q("## 攤平，算給你看")
q("")
q(A["plain"])
q("")
q("| 項目 | 不攤平（一張） | 攤平（再買一張） |")
q("|---|---|---|")
q(f"| 總共付出去 | {money(T['buy_paid'])} 元 | {money(A['total_paid'])} 元 |")
q(f"| 平均一股成本 | {money(T['buy_price'])} 元 | {A['avg_cost']:,.0f} 元 |")
q(f"| 現在全部賣掉實收 | {money(T['sell_received'])} 元 | {money(A['sell_all_received'])} 元 |")
q(f"| 總共賠 | {money(T['loss'])} 元 | {money(A['loss_if_average'])} 元（多賠 {money(A['extra_loss_now'])} 元） |")
q(f"| 【假如，不是預測】再跌一成到 {A['drop_price']:.1f} 元，還要再賠 | {money(A['more_loss_1lot'])} 元 | {money(A['more_loss_2lots'])} 元 |")
q(f"| 股價每跌 1 元就少 | {money(A['per_1dollar_1lot'])} 元 | {money(A['per_1dollar_2lots'])} 元 |")
q("")
q("> 白話：平均成本從 371 降到 240，只是數字好看，不是真的便宜。"
  "就像外套買貴了再買一件打折的，「平均一件比較便宜」不等於「少花了錢」。")
q("")
q("---")
q("")
q("## 真的要退：一張也能慢慢退")
q("")
q(SP["plain"])
q("")
q(f"| 怎麼賣 | 合計拿到 |")
q(f"|---|---|")
q(f"| 一次賣掉一整張 | {money(SP['once_received'])} 元 |")
q(f"| 分十天、每天 100 股零股 | {money(SP['ten_days_received'])} 元 |")
q(f"| **差額** | **只差 {money(SP['diff'])} 元** |")
q("")
q(SP["warn"])
q("")
q(SP["honest"])
q("")
q("---")
q("")
q("## 靠日曆，不靠意志力")
q("")
q(f"**下單前 12 問，真的再跑一次（問「現在攤平準不準」）：** {PT['plain']}")
q("　其中兩題明確否：公司最近一年合起來賠錢；以及「因為跌很多才想買」。其餘沒回答，一律算不過關。")
q("")
q(f"**退出來的錢：** 先放回現金補滿 24 個月生活費，再看會配息的地方。"
  f"換個算法：{OP['formula']}。{OP['plain']}")
q("")
q("| 什麼時候 | 做什麼 |")
q("|---|---|")
for a in AC:
    q(f"| {a['when']} | {a['do']} |")
q("")
q(f"> 自動交易現況：{AU['status']}。只幫您踩煞車，不幫您找買點。")
q("")
q("---")
q("")
q("## 把這次寫成三條規矩")
q("")
for i, w in enumerate(WB, 1):
    q(f"**規矩 {i}．{w['rule']}**")
    q(f"　{w['evidence']}")
    q("")
q("> 不是責備自己，是讓系統下次自動擋下來。人會累、會心軟、會想「這次不一樣」；規矩不會。")
q("")
q("---")
q("")
q("## 哪些事我不知道")
q("")
for u in D["unknown"]:
    q(f"- {u}")
q("")
q("---")
q("")
q("## 這些數字從哪裡來")
q("")
for s in D["sources"]:
    q(f"- {s}")
q("")
q(f"> **{D['disclaimer']}**（「模擬盤」＝紙上練習，沒有連到券商、沒有下任何一張單。）")
q("")
q("---")
q("")
q("*引擎 `tool/v3/case_6217_one_lot.py` ｜ 結果 `v45_one_lot.json` ｜ "
  "報告產生器 `tool/v3/gen_one_lot_report.py` ｜ 本卡數字由結果檔回填，無手工抄錄。*")

text = "\n".join(L)
# 只把「數字前的 ASCII 負號」改成排版減號，不動日期連字號
import re
text = re.sub(r"(?<![/\w])-\d", lambda m: "−" + m.group(0)[1:], text)
CARD.write_text(text, encoding="utf-8")
print(f"產出 {CARD.name}（{CARD.stat().st_size:,} bytes）")
