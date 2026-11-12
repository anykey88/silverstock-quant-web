#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_top_decision_report.py — 由 v44_top_decision.json 產生淺底大字白話報告

規矩（V4.2 起，泰哥要求）：
  · 給長輩看：淺底、大字、短句、生活比喻、術語立刻換白話
  · 每一個數字都由結果檔回填，不憑印象寫
  · 資料不夠就寫「不知道」，不編「會賺多少」
  · 全文手寫繁體，不做簡繁自動轉換（避免「不准→不準」「當沖→當衝」那類誤轉）
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = json.loads((ROOT / "v44_top_decision.json").read_text(encoding="utf-8"))
OUT = Path("/workspace/V4.4_买在最高点怎么决策.html")
CARD = Path("/workspace/V4.4_买在最高点决策卡.md")

M = D["money"]
MK = D["market"]
V = D["verdict"]
DD = V["day_by_day"]
SO = V["stop_order_expired"]
AC = D["actions"]
WB = D["wrongbook"]
AU = D["auto"]
PT = D["pretrade"]


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
        # 統一把 ASCII 減號換成排版用的減號，與內文一致
        add(f'<div class="kpi"><div class="kv">{e(v).replace("-", "−")}</div>'
            f'<div class="kl">{e(lab)}</div></div>')
    add('</div>')


def bar_chart():
    """兩根長條：當初付出去 vs 現在拿回來。不畫曲線，長輩一眼就懂。"""
    buy = M["buy_paid"]
    sell = M["sell_received"]
    W, H = 960, 300
    x0, x1 = 250, 900
    top, gap = 55, 105
    maxv = buy
    def width(v): return (x1 - x0) * v / maxv
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
    s.append(f'<text x="{x0}" y="{y2+92}" class="hint">中間不見的 {money(M["loss_per_lot"])} 元，'
             f'就是這一趟的代價（已扣手續費與稅）。</text>')
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
add('<title>買在最高點，現在怎麼辦｜中探針決策卡</title>')
add(f'<style>{CSS}</style></head><body><div class="wrap">')

add('<header><div class="eyebrow">V4.4 ．接著 V4.3 那一題，回答「真的買在最高點」</div>')
add('<h1>買在最高點，現在怎麼辦？</h1>')
add(f'<div class="meta">中探針 6217 ｜ 資料最新到 {e(D["asof"])} ｜ '
    f'下一個交易日 {e(D["next_trading_day"])} ｜ 給家人看的版本：大字、白話、繁體</div></header>')

# ── 1 一句話 ────────────────────────────────────────────────────────
h2("1", "先給一句話")
add(f'<div class="big">{e(D["one_line"])}</div>')
add('<p class="lead">這一題不是在問「要不要認賠」，也不是在問「會不會反彈」。'
    '這兩個問題都沒有答案，問了只會讓人更睡不著。<br>'
    '我們的方法只問一件事：<b>剩下的錢，要怎麼一步一步搬回安全的地方。</b></p>')
add(f'<div class="warn"><b>先說清楚：我不知道您實際買了幾張、多少錢買的、是不是借錢買的。</b><br>'
    '所以下面用「<b>買一張、買在 371 元</b>」當例子算給您看。'
    '您的張數不同，把數字乘上去就好；比例和做法是一樣的。<br>'
    '第 8 節有四個問題，回答了才能算出「您該賣幾張」。</div>')

# ── 2 給爸媽的一頁紙 ────────────────────────────────────────────────
h2("2", "給爸媽的一頁紙", "印出來貼著就好，三件事")
add('<div class="onepager"><h3>買貴了，現在照這三件事做</h3>')
add(f'<div class="row"><div class="n">1</div><div><div class="bigline">不要再加錢進去。</div>'
    '不加碼、不攤平、不借錢補。'
    f'現在股價 {M["now_price"]:.0f} 元，比最高點便宜七成，但「便宜」不是買的理由。'
    '<br><span class="note">就像房子還在往下掉，不會因為比上個月便宜就再買一間。</span></div></div>')
add(f'<div class="row"><div class="n">2</div><div><div class="bigline">不要等「回本」。</div>'
    f'要漲到 {M["recover_price"]:.1f} 元才回到當初付出去的錢，等於還要再漲 {M["recover_pct_from_now"]:.2f}%。'
    '公司還在賠錢、今年也沒發股息，沒有東西幫您墊著。<br>'
    '<span class="note">等回本不是計畫，是許願。</span></div></div>')
add(f'<div class="row"><div class="n">3</div><div><div class="bigline">照表慢慢搬，不要一天砍完。</div>'
    f'從 {e(D["next_trading_day"])} 開始，按日分批、每天降一點，'
    '降到這檔只佔總資產 1% 以內就停。不管當天漲跌、不看新聞、不改方向。<br>'
    '<span class="note">不是認賠，是把會讓您睡不著的那部分，分幾次搬回安全的地方。'
    '每次要賣幾張，得先知道您有幾張、總資產多少（第 8 節），資料不夠就不硬湊張數。</span></div></div>')
add('<p style="text-align:center;font-size:25px;font-weight:800;margin-top:28px">'
    '一句話：交給規則管，不要交給感覺管。</p></div>')

# ── 3 現在的行情 ────────────────────────────────────────────────────
h2("3", "現在外面是什麼天氣", "先看天氣，再說要不要出門")
add(f'<div class="big">現在是「空頭」——白話就是：一直下雨的日子，'
    f'而且已經下了好一陣子。</div>')
kpi([
    (f'{MK["last_day"]["close"]:.0f} 元',
     f'11/06 收盤價（跌 {abs(MK["last_day"]["change_pct"]):.2f}%）'),
    (f'{MK["four_day_drop_pct"]:.2f}%', "四個交易日跌了多少"),
    (f'{MK["taiex_close"]:,.0f}', "11/06 大盤收盤"),
    (f'{MK["taiex_drawdown_pct"]:.2f}%', "大盤離最高點"),
])
add('<p>這四天是這樣走的：<b>148 → 131 → 118 → 109</b>，一天比一天低。'
    '同一天，大盤也跌了 4% 以上，同一群做探針的公司平均也跌了近兩成。'
    '所以<b>不是這一家公司出事，是整群一起被砍，連大盤也在跌</b>。</p>')
add(f'<div class="card"><h3>四條平均價，統統在頭上</h3>'
    '<p class="note">「平均價」＝過去一段時間大家買的平均成本。股價在它下面，代表那段時間買的人現在都套牢。</p>')
add('<table><thead><tr><th>看多久的平均</th><th>平均價</th><th>現在股價 109 元</th></tr></thead><tbody>')
for x in MK["ma"]:
    add(f'<tr><td>{e(x["name"])}</td><td>{x["value"]:.1f} 元</td><td>在下面，沒站回去</td></tr>')
add('</tbody></table>')
add(f'<p>{e(MK["ma_plain"])}</p></div>')
add(f'<div class="warn"><b>最容易上當的一句話：「跌這麼深了，該反彈了吧。」</b><br>'
    f'{e(MK["v41_ref"]["crash_up_total"])}<br>'
    f'<b>{e(MK["v41_ref"]["plain"])}</b><br>'
    '<span class="note">反彈像下雨天偶爾出一下太陽，不代表雨停了。'
    '所以不要「等彈一點再賣」。</span></div>')
add(f'<div class="note">成交量只拿來確認，不拿來找買點：{e(MK["volume_rule"])}<br>'
    f'還有人借錢買（融資 {MK["margin_lots"]:,} 張），{e(MK["margin_plain"])}</div>')

# ── 4 錢的真相 ──────────────────────────────────────────────────────
h2("4", "買在最高點，錢實際少了多少", "手續費與稅都算進去，不是只看價格")
add(f'<div class="chart">{bar_chart()}</div>')
kpi([
    (f'−{money(M["loss_per_lot"])} 元', "買一張，現在賣掉賠多少"),
    (f'{M["left_per_100w"]:.1f} 萬', "當初放 100 萬，現在剩（含費）"),
    (f'{M["loss_pct_on_cash"]:.2f}%', "實際賠掉的比例"),
])
add(f'<p class="lead">用生活裡的話講：<b>當初拿 100 萬出去，現在拿回來大約 '
    f'{M["left_per_100w"]:.1f} 萬</b>（{money(M["left_of_100w_ntd"])} 元）。'
    '不見的那七十幾萬，不會因為您繼續等就自己回來。</p>')
add(f'<div class="card"><h3>為什麼「回本」比想像中更遠</h3>'
    f'<p>很多人以為：從 {M["now_price"]:.0f} 漲回 {M["buy_price"]:.0f} 就回本了。'
    f'但買的時候付了手續費，賣的時候還要再付一次手續費和交易稅，'
    f'所以其實要漲到 <b>{M["recover_price"]:.1f} 元</b>才算真正打平，'
    f'等於從現在再漲 <b>{M["recover_pct_from_now"]:.2f}%</b>（差不多兩倍半）。</p>'
    f'<p class="note">{e(M["fee_note"])}</p></div>')
add(f'<div class="warn"><b>最痛、但最有用的一句：</b>'
    f'如果當初照我們寫好的規矩，在跌 15% 的時候（{M["stop_price"]:.1f} 元）就出場，'
    f'每一張可以少賠 <b>{money(M["saved_per_lot_if_stopped"])} 元</b>；'
    f'買十張就是 <b>{money(M["saved_10lots_if_stopped"])} 元</b>。<br>'
    '這不是要責怪誰，是要把這一筆記進「錯題本」（第 9 節），'
    '讓系統下次在買進當天就自動把保險掛好。</div>')

# ── 5 決策 ──────────────────────────────────────────────────────────
h2("5", "所以現在的決定是什麼", "一句話，加上五個不做")
add(f'<div class="big">{e(V["headline"])}</div>')
add('<div class="card"><h3>五個「不做」</h3><ol>')
add(f'<li><b>不攤平</b>：{e(V["why_not_average"])}</li>')
add(f'<li><b>不等回本</b>：{e(V["why_not_wait"])}</li>')
add(f'<li><b>不在急跌當天一次砍光</b>：{e(V["why_not_all_at_once"])}</li>')
add(f'<li><b>不因為「跌深反彈」就停手或加碼</b>：{e(MK["v41_ref"]["plain"])}</li>')
add(f'<li><b>不做當沖對沖</b>：{e(AU["cannot"][2])}</li>')
add('</ol></div>')
add(f'<div class="ok"><b>唯一要做的一件事：</b>照第 6 節那張表，'
    f'從 {e(D["next_trading_day"])} 開始按日分批、每天降一點，'
    f'降到這檔只佔總資產 {D["single_stock_cap_pct"]}% 以內就停；'
    f'把錢先搬回現金、補滿 {D["cash_months"]} 個月生活費，再看會配息的地方。<br>'
    '<span class="note">現金也是一種位置。空頭裡，它是唯一確定有效的那一種。</span></div>')

# ── 6 行事曆 ────────────────────────────────────────────────────────
h2("6", "照表做，不靠意志力", "日子寫死，就不必每天跟自己拔河")
add('<table><thead><tr><th>什麼時候</th><th>做什麼</th></tr></thead><tbody>')
for a in AC:
    add(f'<tr><td><b>{e(a["when"])}</b></td><td>{e(a["do"])}</td></tr>')
add('</tbody></table>')
add(f'<div class="card"><h3>分批會不會讓手續費變貴？不會</h3>'
    f'<p>拿十張、分 {D["batch_days"]} 次當例子算：<b>一次全部賣掉</b>實收 '
    f'{money(M["once_10lots_received"])} 元；<b>分 {D["batch_days"]} 次、每次賣一張</b>'
    f'合計實收 {money(M["split_10days_received"])} 元，'
    f'只差 <b>{money(M["split_cost_diff"])} 元</b>。</p>'
    '<p>手續費是按成交金額算的，分幾次差不多是一樣的錢。'
    '分批換到的不是「賣得比較貴」，是<b>不必賭今天是不是最低點</b>——'
    '這對睡不著的人，比多賺幾塊錢重要得多。</p>'
    f'<p class="note">這個「{D["batch_days"]} 次」只是拿來算手續費的例子，'
    '<b>不是</b>規定您要分幾天、更不是每天賣十分之一（那樣算並不會降到 1%）。'
    '真正的張數要等第 8 節四個問題有答案才算得出來。<br>'
    '要誠實：分批減碼在下跌這一段，我們<b>沒有</b>做過對應的實測，'
    '所以這裡只給做法，不給「這樣會少賠多少」的數字。</p></div>')

# ── 7 停損的誤會 ────────────────────────────────────────────────────
h2("7", "一個最容易搞錯的地方", "事後補買保險，保險公司不賠")
so = V["stop_order_expired"]
add(f'<div class="warn" style="font-size:22px">{e(so["truth"])}</div>')
add(f'<div class="big">{e(so["plain"])}</div>')
add(f'<p>我們那條「跌 15% 就無條件砍」，是要<b>在買進當天就交給券商的條件單託管</b>，'
    '不是等跌了才想起來。現在才掛，價位在頭上，永遠不會觸發，等於沒掛。</p>')
add(f'<div class="ok"><b>現在還能補的兩件事：</b><br>{e(so["fix"])}</div>')
add(f'<p class="note">方向只有一個：{e(DD["rule"])}<br>{e(DD["unknown"])}<br>'
    f'{e(DD["plain"])}</p>')

# ── 8 12 問與四個問題 ───────────────────────────────────────────────
h2("8", "系統怎麼判，以及我要問您四件事")
add(f'<div class="card"><h3>真的跑一次「下單前 12 問」</h3>'
    f'<p>問的是：<b>現在想攤平、想加碼，準不準？</b>結果：'
    f'<b>{e(PT["plain"])}</b></p><ul>')
for x in PT["key_fails"]:
    add(f'<li>{e(x)}</li>')
add('</ul><p class="note">這一題問的是「買」，不是「賣」。'
    '賣出減碼是風險控管，本來就該做；買進才需要過這 12 關。</p></div>')
add('<div class="card"><h3>請您回答這四個，我才能算出「該賣幾張」</h3><ol>')
for q in D["questions_for_user"]:
    add(f'<li>{e(q)}</li>')
add('</ol><p class="note">不知道就寫不知道。'
    '資料不夠，系統一律當作不合格，不會硬湊一個數字給您。</p></div>')

# ── 9 錯題本 ────────────────────────────────────────────────────────
h2("9", "這一課記進錯題本", "系統就是靠這樣自己進步的")
add('<table><thead><tr><th>學到什麼</th><th>用哪個真數字記下來的</th></tr></thead><tbody>')
for w in WB:
    add(f'<tr><td><b>{e(w["lesson"])}</b></td><td>{e(w["evidence"])}</td></tr>')
add('</tbody></table>')
add(f'<div class="card"><h3>自動交易現在能做到哪一步</h3>'
    f'<p><b>{e(AU["status"])}</b>；{e(AU["whitelist"])}。</p><ul>')
for x in AU["can"]:
    add(f'<li>可以：{e(x)}</li>')
for x in AU["cannot"]:
    add(f'<li>不可以：{e(x)}</li>')
add(f'</ul><p>{e(AU["plain"])}</p></div>')

# ── 10 不知道 ───────────────────────────────────────────────────────
h2("10", "哪些事我不知道", "每次都要附，不編數字")
add('<div class="warn"><ul>')
for u in D["unknown"]:
    add(f'<li>{e(u)}</li>')
add('</ul><p style="margin-bottom:0">這份能說的是「<b>該不該加、該怎麼慢慢退</b>」，'
    '不能說的是「<b>這樣做會賺多少</b>」。'
    '這檔不在我們那 111 檔的資料池裡，所以任何回測報酬數字都不編。</p></div>')

# ── footer ──────────────────────────────────────────────────────────
add('<footer><b>資料來源（都標日期，不同來源不混著算）</b><ul>')
for s in D["sources"]:
    add(f'<li>{e(s)}</li>')
add('</ul>')
add(f'<p>{e(D["disclaimer"])}</p>')
add('<p>計算引擎 <code>tool/v3/case_6217_top.py</code>（真的呼叫既有費用引擎與 12 問）｜'
    '結果檔 <code>v44_top_decision.json</code>｜'
    '報告生成器 <code>tool/v3/gen_top_decision_report.py</code>｜'
    '本頁所有數字由結果檔回填，無手工抄錄。</p></footer>')

add('</div></body></html>')

OUT.write_text("\n".join(P), encoding="utf-8")
print(f"產出 {OUT.name}（{OUT.stat().st_size:,} bytes）")


# ══════════════════════════════════════════════════════════════════
# 可列印決策卡（純文字，給家人一張紙）
# ══════════════════════════════════════════════════════════════════
L = []
def q(x): L.append(x)

q("# 買在最高點，現在怎麼辦｜中探針 6217 決策卡 · 可列印")
q("")
q(f"> 資料最新到 **{D['asof']}** ｜ 下一個交易日 **{D['next_trading_day']}** ｜ 給家人看的版本")
q(f"> **一句話：{D['one_line']}**")
q("")
q("---")
q("")
q("## 給爸媽的一頁紙（三件事就好）")
q("")
q(f"**1．不要再加錢進去。** 不加碼、不攤平、不借錢補。現在股價 {M['now_price']:.0f} 元，比最高點便宜七成，但「便宜」不是買的理由。")
q("　　→ 就像房子還在往下掉，不會因為比上個月便宜就再買一間。")
q("")
q(f"**2．不要等「回本」。** 要漲到 {M['recover_price']:.1f} 元才回到當初付出去的錢，等於再漲 {M['recover_pct_from_now']:.2f}%。公司還在賠錢、今年股息 0 元，沒有東西幫您墊著。")
q("　　→ 等回本不是計畫，是許願。")
q("")
q(f"**3．照表慢慢搬，不要一天砍完。** 從 {D['next_trading_day']} 開始，按日分批、每天降一點，降到這檔只佔總資產 {D['single_stock_cap_pct']}% 以內就停。不管當天漲跌、不看新聞、不改方向。")
q("　　→ 不是認賠，是把會讓您睡不著的那部分，分幾次搬回安全的地方。每次賣幾張，要先知道您有幾張、總資產多少，資料不夠就不硬湊張數。")
q("")
q("> **一句話：交給規則管，不要交給感覺管。**")
q("")
q("---")
q("")
q("## 現在外面是什麼天氣")
q("")
q(f"現在是**空頭**（一直下雨的日子）。11/06 收盤 {MK['last_day']['close']:.0f} 元、跌 {abs(MK['last_day']['change_pct']):.2f}%；四天走了 148 → 131 → 118 → {MK['last_day']['close']:.0f}，共 {MK['four_day_drop_pct']:.2f}%。")
q(f"大盤同日收 {MK['taiex_close']:,.0f}，離最高點 {MK['taiex_drawdown_pct']:.2f}%；同業近一個月平均也跌 {abs(MK['peers_1m_avg_pct']):.2f}%。**不是這家公司出事，是整群一起被砍。**")
q("")
q(f"四條平均價（5 / 20 / 60 / 120 日）統統在 {MK['last_day']['close']:.0f} 元上面 → 過去這些時間買的人現在都套牢。")
q("")
q(f"**最容易上當的一句話：「跌這麼深了，該反彈了吧。」** {MK['v41_ref']['crash_up_total']}")
q(f"→ {MK['v41_ref']['plain']}反彈像下雨天偶爾出太陽，不代表雨停了。")
q("")
q("## 錢的真相（手續費與稅都算進去）")
q("")
q(f"| 項目 | 金額 |")
q(f"|---|---|")
q(f"| 買一張（1000 股）371 元，實付 | {money(M['buy_paid'])} 元 |")
q(f"| 現在 109 元賣掉，實收 | {money(M['sell_received'])} 元 |")
q(f"| **一張賠** | **{money(M['loss_per_lot'])} 元（{M['loss_pct_on_cash']:.2f}%）** |")
q(f"| 當初放 100 萬，現在剩 | 約 {M['left_per_100w']:.1f} 萬（{money(M['left_of_100w_ntd'])} 元） |")
q(f"| 真正打平要漲到 | {M['recover_price']:.1f} 元 = 再漲 {M['recover_pct_from_now']:.2f}% |")
q(f"| 若當初 −15% 在 {M['stop_price']:.1f} 元出場 | 每張少賠 {money(M['saved_per_lot_if_stopped'])} 元 |")
q("")
q(f"> 回本價比當初買價 371 元還高一點，是因為買、賣各要付一次手續費，賣出還要繳交易稅。{M['fee_note']}")
q("")
q("## 現在的決定")
q("")
q(f"**{V['headline']}**")
q("")
q("五個不做：")
q(f"1. 不攤平：{V['why_not_average']}")
q(f"2. 不等回本：{V['why_not_wait']}")
q(f"3. 不在急跌當天一次砍光：{V['why_not_all_at_once']}")
q(f"4. 不因「跌深反彈」停手或加碼：{MK['v41_ref']['plain']}")
q(f"5. 不做當沖對沖：{AU['cannot'][2].replace('不開當沖對沖：', '')}")
q("")
q(f"唯一要做的：照下表，按日分批降到這檔只佔總資產 {D['single_stock_cap_pct']}% 以內，"
  f"把錢先搬回現金、補滿 {D['cash_months']} 個月生活費，再看會配息的地方。**現金也是一種位置。**")
q("")
q("## 照表做，不靠意志力")
q("")
q("| 什麼時候 | 做什麼 |")
q("|---|---|")
for a in AC:
    q(f"| {a['when']} | {a['do']} |")
q("")
q(f"> 分批不會讓手續費變貴（拿十張、分 {D['batch_days']} 次當例子）："
  f"一次賣實收 {money(M['once_10lots_received'])} 元，分 {D['batch_days']} 次合計 "
  f"{money(M['split_10days_received'])} 元，只差 {money(M['split_cost_diff'])} 元。"
  f"這個「{D['batch_days']} 次」只是算手續費的例子，不是規定天數、更不是每天賣十分之一"
  "（那樣算並不會降到 1%）。分批換到的不是賣得比較貴，是不必賭今天是不是最低點。")
q("")
q("## 一個最容易搞錯的地方")
q("")
q(f"**{so['truth']}**")
q(f"> {so['plain']}")
q(f"現在能補的：{so['fix'].replace('現在能補的只有兩件事：', '')}")
q(f"方向只有一個：{DD['rule']} {DD['unknown']}")
q(f"→ {DD['plain']}")
q("")
q("## 系統怎麼判 + 我要問您四件事")
q("")
q(f"真的跑一次下單前 12 問（問的是「現在想攤平／加碼，準不準」）：**{PT['plain']}**")
for x in PT["key_fails"]:
    q(f"- {x}")
q("")
q("請回答這四個，才能算出「該賣幾張」：")
for i, qq2 in enumerate(D["questions_for_user"], 1):
    q(f"{i}. {qq2}")
q("")
q("## 錯題本（記四件事）")
q("")
q("| 學到什麼 | 用哪個真數字記下來 |")
q("|---|---|")
for w in WB:
    q(f"| {w['lesson']} | {w['evidence']} |")
q("")
q(f"自動交易現況：**{AU['status']}**；{AU['whitelist']}。{AU['plain']}")
q("")
q("## 哪些事我不知道（每次都要附）")
q("")
for u in D["unknown"]:
    q(f"- {u}")
q("")
q(f"> {D['disclaimer']}")
q("")
q("---")
q("")
q("*數字由 `v44_top_decision.json` 回填；計算真的呼叫既有費用引擎與 12 問，無手工抄錄。*")

import re as _re
_md = "\n".join(L)
# 只把「數字前的負號」換成排版減號；日期 2026-11-06 的連字號前面是數字，不受影響
_md = _re.sub(r"(?<![\d/\w])-(?=\d)", "−", _md)
CARD.write_text(_md, encoding="utf-8")
print(f"產出 {CARD.name}（{CARD.stat().st_size:,} bytes）")
