"""V5.1 執行手冊生成器：讀 v51_execution.json → 繁體淺底大字 HTML + 可列印決策卡 MD。

規矩（V4.2 起）：數字一律讀檔回填、不手抄；資料不夠寫不知道；長輩版術語立刻白話解釋。
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
D = json.loads((ROOT / "v51_execution.json").read_text(encoding="utf-8"))

OUT_HTML = WORKSPACE / "V5.1_怎么执行.html"
OUT_MD = WORKSPACE / "V5.1_怎么执行决策卡.md"
OUT_REPO = ROOT / "docs" / "V5.1_EXECUTION.md"

T = D["truth"]
TD = T["techdebt"]
DS = T["dataset"]
TODAY = D["today"]
ROAD = D["roadmap"]
PILES = D["piles"]

H: list[str] = []
L: list[str] = []


def e(x) -> str:
    return html.escape(str(x), quote=True)


def add(s: str) -> None:
    H.append(s)


def q(s: str = "") -> None:
    L.append(s)


def h2(no: str, title: str, sub: str = "") -> None:
    add(f'<h2><span class="no">{e(no)}</span>{e(title)}'
        + (f'<small>{e(sub)}</small>' if sub else "") + '</h2>')


def card(kind: str, title: str, body: str) -> None:
    add(f'<div class="card {kind}"><div class="ct">{e(title)}</div>'
        f'<div class="cb">{body}</div></div>')


def kpi(items) -> None:
    add('<div class="kpis">')
    for v, lab in items:
        add(f'<div class="kpi"><div class="kv">{e(v)}</div><div class="kl">{e(lab)}</div></div>')
    add('</div>')


CSS = """
:root{--bg:#faf8f2;--card:#fffdf7;--ink:#2b2a26;--mut:#6b675c;--line:#e3ded0;
--ok:#2f6b4f;--okbg:#eaf3ec;--warn:#a35a1c;--warnbg:#fbf0e2;--red:#a33b34;--redbg:#fbeceb;
--blue:#2c5d78;--bluebg:#e9f1f6;--accent:#8a6d3b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;
font-size:21px;line-height:1.95;letter-spacing:.02em}
.wrap{max-width:1000px;margin:0 auto;padding:38px 30px 90px}
header{border-bottom:3px solid var(--ink);padding-bottom:26px;margin-bottom:34px}
.kicker{font-size:17px;color:var(--mut);letter-spacing:.18em}
h1{font-size:42px;line-height:1.35;margin:14px 0 10px}
.sub{font-size:20px;color:var(--mut);margin:0}
.lead{font-size:26px;line-height:1.8;background:var(--bluebg);border-left:9px solid var(--blue);
padding:22px 26px;border-radius:0 12px 12px 0;margin:30px 0;font-weight:700}
h2{font-size:31px;margin:64px 0 22px;padding-bottom:12px;border-bottom:2px solid var(--line);
display:flex;align-items:baseline;gap:16px;line-height:1.4;flex-wrap:wrap}
h2 .no{background:var(--ink);color:#fff;border-radius:50%;width:46px;height:46px;min-width:46px;
display:inline-flex;align-items:center;justify-content:center;font-size:22px;flex:none}
h2 small{font-size:17px;color:var(--mut);font-weight:normal;margin-left:auto}
h3{font-size:24px;margin:34px 0 12px}
p{margin:14px 0}
.note{font-size:18px;color:var(--mut);line-height:1.85}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:26px 0}
.kpi{background:var(--card);border:2px solid var(--line);border-radius:14px;padding:20px 12px;text-align:center}
.kv{font-size:31px;font-weight:800;color:var(--blue);line-height:1.3}
.kl{font-size:16px;color:var(--mut);margin-top:8px;line-height:1.5}
.onepager{background:var(--card);border:3px solid var(--ink);border-radius:14px;padding:28px 32px;margin:34px 0}
.onepager h3{font-size:27px;margin:0 0 20px;border-bottom:2px solid var(--line);padding-bottom:12px}
.row{display:flex;gap:18px;margin:20px 0;align-items:flex-start}
.row .n{background:var(--accent);color:#fff;border-radius:50%;width:42px;height:42px;min-width:42px;
display:inline-flex;align-items:center;justify-content:center;font-size:21px;font-weight:800}
.bigline{font-size:25px;font-weight:700;line-height:1.6}
.card{border-radius:12px;padding:22px 26px;margin:24px 0;font-size:20px}
.card .ct{font-size:23px;font-weight:700;margin-bottom:10px}
.card .cb{line-height:1.9}
.card.ok{background:var(--okbg);border-left:8px solid var(--ok)}
.card.warn{background:var(--warnbg);border-left:8px solid var(--warn)}
.card.red{background:var(--redbg);border-left:8px solid var(--red)}
.card.blue{background:var(--bluebg);border-left:8px solid var(--blue)}
table{width:100%;border-collapse:collapse;margin:20px 0;font-size:18px;background:var(--card)}
th{background:#efe9da;text-align:left;padding:12px 14px;border:1px solid var(--line);font-size:17px}
td{padding:12px 14px;border:1px solid var(--line);vertical-align:top;line-height:1.75}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.pile{border-radius:12px;padding:22px 26px;margin:20px 0}
.pile .ph{font-size:24px;font-weight:700;margin-bottom:8px}
.pile ul{margin:10px 0 0;padding-left:26px}
.pile li{margin:8px 0}
.pile.now{background:var(--okbg);border-left:8px solid var(--ok)}
.pile.you{background:var(--warnbg);border-left:8px solid var(--warn)}
.pile.later{background:var(--redbg);border-left:8px solid var(--red)}
.step{background:var(--card);border:2px solid var(--line);border-radius:12px;padding:20px 24px;margin:18px 0}
.step .sh{font-size:23px;font-weight:700;margin-bottom:10px}
.step .tag{display:inline-block;background:var(--ink);color:#fff;border-radius:20px;
padding:3px 14px;font-size:16px;margin-right:10px}
.step .tag.go{background:var(--ok)}
.step .tag.wait{background:var(--warn)}
.step .tag.stop{background:var(--red)}
.step dl{margin:8px 0}
.step dt{font-weight:700;color:var(--mut);font-size:17px;margin-top:8px}
.step dd{margin:2px 0 0}
footer{border-top:2px solid var(--line);margin-top:60px;padding-top:22px;font-size:17px;color:var(--mut)}
code{background:#efe9da;padding:2px 7px;border-radius:5px;font-size:17px}
"""


def build_html() -> None:
    add('<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">')
    add('<meta name="viewport" content="width=device-width, initial-scale=1">')
    add(f'<title>{e(D["title"])}</title><style>{CSS}</style></head><body><div class="wrap">')

    add('<header>')
    add('<div class="kicker">台海股投資接續系統・執行手冊</div>')
    add(f'<h1>{e(D["title"])}</h1>')
    add(f'<p class="sub">{e(D["generated_at"])} 產出｜接續 V5.0 規格｜'
        f'現況仍是練習帳，沒連券商、沒下過任何一張單</p>')
    add(f'<div class="lead"><b>一句話：</b>{e(D["one_line"])}</div>')
    add('</header>')

    # 給爸媽的一頁紙
    add('<div class="onepager"><h3>給爸媽的一頁紙（只要記三件事）</h3>')
    three = [
        ("一、先別急著問「要不要花錢」。",
         "這一套到今天都還在紙上練習，沒有連券商、沒有花過一塊錢真錢。"
         "就像學開車先在空地練，還沒上路。"),
        ("二、這份不是機器，是一張「施工單」。",
         "它寫清楚：哪幾件現在就能做、哪幾件要您本人去辦、哪幾件還不能碰。"
         "照順序做，不必一次全部動手。"),
        ("三、今天已經真的做了一件。",
         f"把「每次靠人肉眼檢查」改成「交給程式自動檢查」，"
         f"第一次跑就抓到前面漏掉的一個字，改回源頭後重跑，"
         f"{TODAY['n_checks']} 項全部通過。系統進步是變誠實，不是變大膽。"),
    ]
    for i, (big, small) in enumerate(three, 1):
        add(f'<div class="row"><div class="n">{i}</div><div>'
            f'<div class="bigline">{e(big)}</div>{e(small)}</div></div>')
    add('</div>')

    # KPI
    kpi([
        (f"{T['n_py_now']} 支", "本版即時重掃的程式"),
        (f"{TODAY['n_checks']} 項", f"今天自動體檢，失敗 {TODAY['n_fail_after']} 項"),
        (f"{T['gates_passed']}／{T['gates_total']} 關", "升級五關只過第一關"),
        (f"{sum(1 for r in ROAD if r['can_start_now'])}／{len(ROAD)} 步", "今天就能開始，不用等"),
    ])

    # 1 定調
    h2("1", "先講清楚：這是施工單，不是一台機器", "很多人會在這裡誤會")
    add('<p>V5.0 那份規格，是把前面二十個版本收成一張「接著做」的地圖。'
        '地圖不會自己帶您走到終點，<b>要有人照著一步一步做</b>。'
        '就像裝潢房子先有一張順序表：先水電、再泥作、最後才家具；'
        '不是按一個鈕，房子就自己好。</p>')
    add('<p>所以「怎麼執行」真正的問題不是「程式要怎麼跑」，'
        '而是：<b>這七件事，誰做、先做哪一件、做到什麼才算完成、現在卡在哪。</b>'
        '下面全部照這個順序回答。</p>')
    card("blue", "現在的真實狀態（每次都要先講）",
         f"資料池 {DS['n_stocks']} 檔、大盤 {DS['index_bars']:,} 天"
         f"（{DS['range'][0]}～{DS['range'][1]}，抓檔日 {DS['captured_at']}）；"
         f"每季獲利只有 {DS['with_quarterly_eps']}/{DS['n_stocks']} 檔有，"
         f"另有 {DS['n_missing_fields']} 樣資料完全沒有。"
         f"現在是<b>練習帳</b>：只在紙上記帳，不花真錢；"
         f"升級五關只過 {T['gates_passed']} 關，其餘 {T['gates_total']-T['gates_passed']} 關還沒開始。")

    # 2 今天第一件事
    h2("2", "今天第一件事，已經做完了", "不用錢、不用連線、不用通行證")
    add(f'<p>{e(TODAY["why_first"])}</p>')
    card("ok", e(TODAY["title"]),
         f'第一步先寫了 <code>tool/v3/auto_check.py</code>：'
         f'把前面四版每次手寫的七項檢查，固化成一支可以重跑的程式，'
         f'而且路徑改成「相對於自己」，不再寫死在哪一台機器上。'
         f'這是 V5.0 技術債裡明寫「沒有一支自動體檢程式」的那一項。')
    add('<h3>第一次跑就抓到東西</h3>')
    add('<table><tr><th>做了什麼</th><th>結果</th></tr>')
    add(f'<tr><td>對幾份檔、跑了幾項</td><td class="num">'
        f'{TODAY["n_files"]} 份／{TODAY["n_checks"]} 項</td></tr>')
    add(f'<tr><td>第一次跑失敗</td><td class="num">{TODAY["n_fail_before"]} 項</td></tr>')
    add(f'<tr><td>抓到前面四版漏掉的一處</td><td>有一處把「託」寫成了簡體字</td></tr>')
    add(f'<tr><td>怎麼改</td><td>改回最源頭那支程式後重跑，不是只改報告表面</td></tr>')
    add(f'<tr><td>另一個字「划不划算」</td><td>台灣本來就寫「划」，列為白名單，不誤改</td></tr>')
    add(f'<tr><td>重跑後</td><td class="num">失敗 {TODAY["n_fail_after"]} 項，全部通過</td></tr>')
    add('</table>')
    card("warn", "要誠實", e(TODAY["honest"]))
    add(f'<p class="note">技術版保留檔名與代號，所以「術語檢查」那一項對技術版不適用；'
        f'這 {TODAY["n_not_applicable"]} 項不算失敗，是刻意跳過。</p>')

    # 3 三堆
    h2("3", "七件事，分成三堆", "先挑不用等人的那一堆做")
    for p in PILES:
        add(f'<div class="pile {p["id"]}"><div class="ph">{e(p["title"])}（{p["n"]} 件）</div>')
        add(f'<div>{e(p["plain"])}</div><ul>')
        for it in p["items"]:
            add(f'<li>{e(it)}</li>')
        add('</ul></div>')
    card("blue", "這裡最容易卡住的地方",
         '很多人一看第一步「要辦新通行證」就整件停下來。'
         '其實<b>第二步到第五步不用通行證、不用錢、不用連券商</b>，本機現在就能先做。'
         '像下雨天不能曬被子，但家裡抽屜還是能整理——不必等晴天。')

    # 4 七步
    h2("4", "照表做：七步逐一寫清楚", "誰做、做到什麼算完成、卡在哪")
    tagmap = {"現在就能做": ("go", "現在就能做"),
              "只有您能做": ("wait", "等您本人去辦"),
              "還不能做": ("stop", "還不能碰")}
    for r in ROAD:
        tag, tagtxt = tagmap[r["pile"]]
        add('<div class="step">')
        add(f'<div class="sh"><span class="tag {tag}">{e(tagtxt)}</span>'
            f'第 {r["step"]} 步（{e(r["order"])}）｜{e(r["who"])}</div>')
        add(f'<p style="font-size:22px;font-weight:700;margin:6px 0 12px">{e(r["do"])}</p>')
        add('<dl>')
        add(f'<dt>白話</dt><dd>{e(r["who_plain"])}</dd>')
        add(f'<dt>為什麼現在做</dt><dd>{e(r["why"])}</dd>')
        add(f'<dt>做出來會看到什麼</dt><dd>{e(r["output"])}</dd>')
        add(f'<dt>做到什麼才算完成</dt><dd>{e(r["done_when"])}</dd>')
        add(f'<dt>現在卡在哪</dt><dd>{e(r["blocked_by"])}</dd>')
        add(f'<dt>要等誰</dt><dd>{e(r["depends"])}</dd>')
        add('</dl></div>')

    # 5 不要停擺
    h2("5", "不要因為第一步卡住，就全部停擺", "這版最想提醒的一句")
    add('<p>七步裡真正「只有您本人能做」的只有兩件：'
        '<b>辦一張新的通行證</b>、<b>決定要不要補資料、資料從哪裡來</b>。'
        '最後一步還要您本人簽名、做連線測試、實盤盯十天，那是更後來的事。</p>')
    add('<p>其餘四步是整理功夫：把雙時間標籤做進網頁、把一次改三處拆開、'
        '圖改成每天記一筆、換多段輪流考。'
        '這四件<b>都不碰真錢、不連券商、不需要任何憑證</b>，'
        '照 V4.2 定的規矩「一次只改一處、改完立刻重跑對照」就能往下走。</p>')
    card("ok", "一句話",
         "先做不用等人的，不是在跳過第一步；是把能先整理的整理好，"
         "等通行證辦下來，一次就推得乾乾淨淨。")

    # 6 怎麼算做完
    h2("6", "怎麼算「做完」", "不靠感覺，靠這五條")
    add('<table><tr><th style="width:60px">第幾條</th><th>驗收標準</th></tr>')
    for i, a in enumerate(D["accept"], 1):
        add(f'<tr><td class="num">{i}</td><td>{e(a)}</td></tr>')
    add('</table>')
    add(f'<p class="note">後面 {T["n_versions"]} 個版本、'
        f'{T["n_result_files"]} 份結果檔、{T["n_report_files"]} 份報告都還在，'
        f'新的改動要能跟舊的對得上，才算真的做完，不是「看起來有改」。</p>')

    # 7 還不能做
    h2("7", "現在還「不能」做的五件事", "卡著，不是忘了")
    add('<table><tr><th>不能做的事</th><th>為什麼</th></tr>')
    for c in D["cannot"]:
        add(f'<tr><td>{e(c["thing"])}</td><td>{e(c["why"])}</td></tr>')
    add('</table>')
    card("red", "規矩沒變",
         '資料不夠就當不合格、沒答的題算不過、升級要人簽名，'
         '程式不能自己宣布「我夠格了」。'
         f'中探針要連續 {T["min_bars"]:,} 根日線才准進正式評分，'
         '外部目前只找到 4 根，所以到今天仍是「不知道」。')

    # 8 不知道
    h2("8", "我還不知道，要請您回答", "不知道就不硬湊")
    add('<ul style="font-size:20px;line-height:2">')
    for u in D["unknown"]:
        add(f'<li>{e(u)}</li>')
    add('</ul>')
    card("warn", "最急的兩題",
         '① 這檔佔家裡全部資產大概幾成？不知道就算不出「該留幾股」，'
         '所以前面只給方向與節奏，不硬湊張數。'
         '② 是不是融資買的、維持率多少？'
         '若是，追繳比股價更急，請先打電話問營業員。')

    # 9 錯題本
    h2("9", "交給系統的三道新錯題", "V4.2 的自修規矩")
    add('<table><tr><th>學到什麼</th><th>證據</th></tr>')
    for w in D["wrongbook_new"]:
        add(f'<tr><td>{e(w["lesson"])}</td><td>{e(w["evidence"])}</td></tr>')
    add('</table>')
    add(f'<p class="note">另外還發現 V4.3 與幾份結果檔有同一個簡體字，'
        f'這輪<b>刻意不改</b>：按「一次只做一件、各驗一次」留到下一輪，'
        f'避免再犯 V4.0 那次「一次改三處，說不清是誰有功勞」。'
        f'目前說話規矩 {T["n_speak_rules"]} 條、下單前 {T["n_pretrade_questions"]} 問，都沒改。</p>')

    # 10 誠實狀態
    h2("10", "誠實狀態與提醒", "每一版都要附")
    add(f'<div class="card blue"><div class="ct">即時重掃，不是引用舊快照</div>'
        f'<div class="cb">V5.0 盤點當時是 {T["n_py_at_v50"]} 支／'
        f'{T["n_lines_at_v50"]:,} 行；本版又新增了 '
        f'{T["n_py_now"] - T["n_py_at_v50"]} 支整理用的程式（自動體檢、執行盤點、手冊生成器），'
        f'即時重掃是 <b>{T["n_py_now"]} 支／{T["n_lines_now"]:,} 行</b>。'
        f'未推送 {T["n_untracked_now"]} 項（V5.0 當時 {T["n_untracked_at_v50"]} 項），'
        f'舊通行證已撤銷，要辦新的才能推；<b>憑證絕對不進倉庫</b>。'
        f'技術債仍在：{TD["n_modules_with_abs_path"]} 支把位置寫死、'
        f'{TD["n_generators"]} 支生成器各自寫輸出位置、'
        f'結果檔散在兩處（倉庫 {TD["n_result_in_repo"]} 份／外層 {TD["n_result_in_root"]} 份）。</div></div>')
    card("red", "提醒", e(D["disclaimer"]))

    add('<footer>')
    add(f'<p>來源：{e("、".join(D["sources"]))}。</p>')
    add(f'<p>{e(D["generated_at"])} 產出。方法與風險控管示範，不是買賣建議。</p>')
    add('</footer>')
    add('</div></body></html>')


def build_md() -> None:
    q(f"# {D['title']}")
    q("")
    q(f"> **一句話：{D['one_line']}**")
    q("")
    q(f"{D['generated_at']} 產出｜接續 V5.0 規格｜現況仍是練習帳，沒連券商、沒下過任何一張單")
    q("")
    q("---")
    q("")
    q("## 給爸媽的一頁紙（只要記三件事）")
    q("")
    q("**1．先別急著問「要不要花錢」。** 這一套到今天都還在紙上練習，"
      "沒有連券商、沒有花過一塊錢真錢。就像學開車先在空地練，還沒上路。")
    q("")
    q("**2．這份不是機器，是一張「施工單」。** 它寫清楚：哪幾件現在就能做、"
      "哪幾件要您本人去辦、哪幾件還不能碰。照順序做，不必一次全部動手。")
    q("")
    q(f"**3．今天已經真的做了一件。** 把「每次靠人肉眼檢查」改成「交給程式自動檢查」，"
      f"第一次跑就抓到前面漏掉的一個字，改回源頭後重跑，{TODAY['n_checks']} 項全部通過。"
      "系統進步是變誠實，不是變大膽。")
    q("")
    q("---")
    q("")
    q("## 先看現在的真實狀態（不算章節）")
    q("")
    q(f"- 資料池 {DS['n_stocks']} 檔、大盤 {DS['index_bars']:,} 天"
      f"（{DS['range'][0]}～{DS['range'][1]}，抓檔日 {DS['captured_at']}）")
    q(f"- 每季獲利只有 {DS['with_quarterly_eps']}/{DS['n_stocks']} 檔有；"
      f"另有 {DS['n_missing_fields']} 樣資料完全沒有")
    q(f"- 本版即時重掃 {T['n_py_now']} 支／{T['n_lines_now']:,} 行"
      f"（V5.0 當時 {T['n_py_at_v50']} 支／{T['n_lines_at_v50']:,} 行）")
    q(f"- 升級五關只過 {T['gates_passed']}／{T['gates_total']} 關；"
      f"七步中 {sum(1 for r in ROAD if r['can_start_now'])} 步今天就能開始")
    q(f"- 未推送 {T['n_untracked_now']} 項；憑證絕對不進倉庫")
    q("")
    q("## 1．先講清楚：這是施工單，不是一台機器")
    q("")
    q("V5.0 是把前面二十個版本收成一張「接著做」的地圖。地圖不會自己帶您走到終點，"
      "**要有人照著一步一步做**。就像裝潢房子先有順序表：先水電、再泥作、最後才家具；"
      "不是按一個鈕，房子就自己好。")
    q("")
    q("所以「怎麼執行」真正的問題不是「程式要怎麼跑」，而是："
      "**這七件事，誰做、先做哪一件、做到什麼才算完成、現在卡在哪。**")
    q("")
    q("## 2．今天第一件事，已經做完了")
    q("")
    q(TODAY["why_first"])
    q("")
    q(f"寫了 `tool/v3/auto_check.py`，把前面四版每次手寫的七項檢查固化成可重跑的程式，"
      f"路徑改成相對於自己。對 **{TODAY['n_files']} 份檔跑了 {TODAY['n_checks']} 項**。")
    q("")
    q("| 做了什麼 | 結果 |")
    q("|---|---|")
    q(f"| 第一次跑失敗 | {TODAY['n_fail_before']} 項 |")
    q("| 抓到前面四版漏掉的一處 | 有一處把「託」寫成了簡體字 |")
    q("| 怎麼改 | 改回最源頭那支程式後重跑，不是只改報告表面 |")
    q("| 「划不划算」的「划」 | 台灣本來就寫「划」，列白名單，不誤改 |")
    q(f"| 重跑後 | 失敗 {TODAY['n_fail_after']} 項，全部通過 |")
    q("")
    q(f"> 要誠實：{TODAY['honest']}")
    q("")
    q(f"> 技術版保留檔名與代號，術語檢查那一項不適用；"
      f"這 {TODAY['n_not_applicable']} 項不算失敗，是刻意跳過。")
    q("")
    q("## 3．七件事，分成三堆")
    q("")
    for p in PILES:
        q(f"### {p['title']}（{p['n']} 件）")
        q("")
        q(p["plain"])
        q("")
        for it in p["items"]:
            q(f"- {it}")
        q("")
    q("> 很多人一看第一步「要辦新通行證」就整件停下來。"
      "其實第二步到第五步不用通行證、不用錢、不用連券商，本機現在就能先做。"
      "像下雨天不能曬被子，但家裡抽屜還是能整理——不必等晴天。")
    q("")
    q("## 4．照表做：七步逐一寫清楚")
    q("")
    tagmap = {"現在就能做": "現在就能做",
              "只有您能做": "等您本人去辦",
              "還不能做": "還不能碰"}
    for r in ROAD:
        q(f"### 第 {r['step']} 步（{r['order']}）｜{r['who']}｜{tagmap[r['pile']]}")
        q("")
        q(f"**要做的事：{r['do']}**")
        q("")
        q(f"- 白話：{r['who_plain']}")
        q(f"- 為什麼現在做：{r['why']}")
        q(f"- 做出來會看到：{r['output']}")
        q(f"- 做到什麼算完成：{r['done_when']}")
        q(f"- 現在卡在哪：{r['blocked_by']}")
        q(f"- 要等誰：{r['depends']}")
        q("")
    q("## 5．不要因為第一步卡住，就全部停擺")
    q("")
    q("七步裡真正「只有您本人能做」的只有兩件：**辦一張新的通行證**、"
      "**決定要不要補資料、資料從哪裡來**。最後一步還要您本人簽名、做連線測試、"
      "實盤盯十天，那是更後來的事。")
    q("")
    q("其餘四步是整理功夫，都不碰真錢、不連券商、不需要任何憑證，"
      "照「一次只改一處、改完立刻重跑對照」就能往下走。")
    q("")
    q("> **先做不用等人的，不是在跳過第一步；是把能先整理的整理好，"
      "等通行證辦下來，一次就推得乾乾淨淨。**")
    q("")
    q("## 6．怎麼算「做完」")
    q("")
    q("| 第幾條 | 驗收標準 |")
    q("|---:|---|")
    for i, a in enumerate(D["accept"], 1):
        q(f"| {i} | {a} |")
    q("")
    q(f"> 後面 {T['n_versions']} 個版本、{T['n_result_files']} 份結果檔、"
      f"{T['n_report_files']} 份報告都還在，新的改動要能跟舊的對得上，才算真的做完。")
    q("")
    q("## 7．現在還「不能」做的五件事")
    q("")
    q("| 不能做的事 | 為什麼 |")
    q("|---|---|")
    for c in D["cannot"]:
        q(f"| {c['thing']} | {c['why']} |")
    q("")
    q(f"> 規矩沒變：資料不夠就當不合格、沒答的題算不過、升級要人簽名。")
    q(f"> 中探針要連續 {T['min_bars']:,} 根日線才准進正式評分，"
      "外部目前只找到 4 根，所以到今天仍是「不知道」。")
    q("")
    q("## 8．我還不知道，要請您回答")
    q("")
    for u in D["unknown"]:
        q(f"- {u}")
    q("")
    q("> **最急的兩題**：① 這檔佔家裡全部資產大概幾成？不知道就算不出「該留幾股」。"
      "② 是不是融資買的、維持率多少？若是，追繳比股價更急，請先打電話問營業員。")
    q("")
    q("## 9．交給系統的三道新錯題")
    q("")
    q("| 學到什麼 | 證據 |")
    q("|---|---|")
    for w in D["wrongbook_new"]:
        q(f"| {w['lesson']} | {w['evidence']} |")
    q("")
    q("> 另外還發現 V4.3 與幾份結果檔有同一個簡體字，這輪**刻意不改**："
      "按「一次只做一件、各驗一次」留到下一輪，避免再犯「一次改三處，說不清是誰有功勞」。")
    q(f"> 目前說話規矩 {T['n_speak_rules']} 條、下單前 {T['n_pretrade_questions']} 問，都沒改。")
    q("")
    q("## 10．誠實狀態與提醒")
    q("")
    q(f"- 技術債仍在：{TD['n_modules_with_abs_path']} 支把位置寫死、"
      f"{TD['n_generators']} 支生成器各自寫輸出位置、"
      f"結果檔散在兩處（倉庫 {TD['n_result_in_repo']} 份／外層 {TD['n_result_in_root']} 份）")
    q(f"- 升級五關：")
    for g in T["gates"]:
        q(f"  - {g['id']} {g['state']}：{g['condition']}")
    q("")
    q(f"> **提醒：{D['disclaimer']}**")
    q("")
    q("---")
    q("")
    q(f"來源：{'、'.join(D['sources'])}。{D['generated_at']} 產出。")


def main() -> None:
    build_html()
    build_md()
    OUT_HTML.write_text("\n".join(H), encoding="utf-8")
    md = "\n".join(L)
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_REPO.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPO.write_text(md, encoding="utf-8")
    print(f"產出 {OUT_HTML.name}（{OUT_HTML.stat().st_size:,} B）")
    print(f"產出 {OUT_MD.name}（{OUT_MD.stat().st_size:,} B）")
    print(f"產出 docs/{OUT_REPO.name}（{OUT_REPO.stat().st_size:,} B）")


if __name__ == "__main__":
    main()
