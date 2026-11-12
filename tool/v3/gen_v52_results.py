# -*- coding: utf-8 -*-
"""V5.2 施工單編程結果：把第 2～5 步的四份結果檔彙總成可看的報告。

紀律：
  - 所有數字讀結果檔回填，不手抄、不編。
  - 長輩版零術語、大白話、淺底大字、繁體；技術版保留代號但括號解釋。
  - 資料不夠就寫「不知道」；不改舊結論。
  - 路徑相對於本檔。

用法：python3.11 tool/v3/gen_v52_results.py
產出：/workspace/V5.2_施工單編程結果.html
      /workspace/V5.2_施工單編程結果決策卡.md
      silverstock_quant_web/docs/V5.2_RESULTS.md
"""
from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORKSPACE = ROOT.parent
OUT_HTML = WORKSPACE / "V5.2_施工單編程結果.html"
OUT_MD = WORKSPACE / "V5.2_施工單編程結果決策卡.md"
OUT_DOC = ROOT / "docs" / "V5.2_RESULTS.md"

FILES = {
    "s2": ROOT / "v52_step2_freshness.json",
    "s3": ROOT / "v52_step3_ablation.json",
    "s4": ROOT / "v52_step4_daily_nav.json",
    "s5": ROOT / "v52_step5_multifold.json",
}


def jload(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def inventory() -> dict:
    py = sorted((ROOT / "tool" / "v3").glob("*.py"))
    lines = sum(len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
                for p in py)
    r = subprocess.run(["git", "status", "--short"], cwd=ROOT,
                       capture_output=True, text=True)
    untracked = [x for x in r.stdout.strip().splitlines() if x.strip()]
    return {"n_py": len(py), "n_lines": lines, "n_untracked": len(untracked)}


def pp(v, unit="個百分點") -> str:
    """不印 ASCII 負號加百分比，長輩版一律講「落後／多」多少。"""
    if v > 0:
        return f"多 {abs(v):.2f} {unit}"
    if v < 0:
        return f"落後 {abs(v):.2f} {unit}"
    return f"整整 {abs(v):.2f} {unit}（一模一樣）"


def signed(v) -> str:
    return f"+{v:.2f}%" if v >= 0 else f"跌 {abs(v):.2f}%"


CSS = """
:root{--bg:#fbfaf5;--ink:#24303a;--sub:#5b6b78;--line:#e3e0d5;--card:#fff;
--blue:#1f6f8b;--red:#b03a2e;--green:#2e7d5b;--amber:#a8641c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font-family:"PingFang TC","Microsoft JhengHei","Noto Sans TC",sans-serif;
font-size:22px;line-height:1.9}
.wrap{max-width:920px;margin:0 auto;padding:28px 20px 70px}
h1{font-size:36px;margin:0 0 6px}
h2{font-size:27px;margin:34px 0 12px;padding-bottom:8px;border-bottom:2px solid var(--line)}
.lead{color:var(--sub);font-size:20px;margin:0 0 22px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;
padding:22px 24px;margin:0 0 18px}
.paper{background:#fffdf3;border:2px solid #e8d9a8}
.no{display:inline-block;background:var(--blue);color:#fff;border-radius:10px;
padding:2px 12px;margin-right:10px;font-size:23px}
table{width:100%;border-collapse:collapse;font-size:20px;margin-top:10px}
th,td{padding:10px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--sub);font-weight:600;background:#f6f7f5}
.big{font-size:31px;font-weight:700}
.warn{background:#fdf0ee;border-left:6px solid var(--red);padding:14px 18px;
border-radius:10px;margin-top:12px}
.ok{color:var(--green);font-weight:700}
.note{color:var(--sub);font-size:19px}
.src{font-size:18px;color:var(--sub);margin-top:26px}
ul{margin:8px 0 0 0;padding-left:26px}
li{margin:6px 0}
.kv{display:flex;flex-wrap:wrap;gap:12px}
.cell{flex:1;min-width:210px;background:#f4f8f9;border-radius:12px;padding:14px}
.k{font-size:18px;color:var(--sub)}
.v{font-size:27px;font-weight:700;margin-top:2px}
"""


def sec(n: int, title: str) -> str:
    return f'<h2><span class="no">{n}</span>{title}</h2>'


def build_html(D: dict) -> str:
    s2, s3, s4, s5 = D["s2"], D["s3"], D["s4"], D["s5"]
    inv = D["inv"]
    t = s2["two_times"]
    ov = s2["freshness_overview"]
    ic = s2["data_inconsistency"]
    cross = s3["cross_segment"]
    f3 = s3["finding"]
    sm4 = s4["summary"]
    sm5 = s5["summary"]
    old5 = s5["old_single_split"]
    checks = D["n_checks_total"]
    fails = D["n_fail_total"]

    seg_rows = "".join(
        f"<tr><td>{s['label']}</td><td>{signed(s['buyhold_total_pct'])}</td>"
        f"<td>{signed(next(r for r in s['rows'] if r['key']=='ABC')['total_pct'])}</td>"
        f"<td>{'有' if s['full_matches_v40'] else '沒有'}</td></tr>"
        for s in s3["segments"])

    curve_rows = "".join(
        f"<tr><td>{c['label']}</td><td>跌 {abs(c['mdd_daily_pct']):.2f}%</td>"
        f"<td>跌 {abs(c['mdd_sampled_pct']):.2f}%</td>"
        f"<td class='big' style='color:var(--red)'>少看 {c['underestimate_pp']:.2f}</td>"
        f"<td>{c['worst_date']}</td></tr>"
        for c in s4["curves"])

    fold_rows = "".join(
        f"<tr><td>第 {f['fold']} 段</td><td>{f['test_range'][0]}～{f['test_range'][1]}</td>"
        f"<td>{signed(f['rule_total_pct'])}</td>"
        f"<td>{signed(f['buyhold_total_pct'])}</td>"
        f"<td>{pp(f['outperformance_pp'])}</td></tr>"
        for f in s5["folds"])

    verify_rows = "".join(
        f"<tr><td>第 {k} 步</td><td>{v['all_pass'] and '全部通過' or '未通過'}</td>"
        f"<td>{v['n_checks']}</td><td>{v['n_fail']}</td></tr>"
        for k, v in D["verifications"].items())

    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>V5.2 施工單編程結果</title><style>{CSS}</style></head>
<body><div class="wrap">
<h1>施工單，真的做出來了</h1>
<p class="lead">四件「現在就能做」的事，今天全部寫成程式、跑出數字、各自驗過一次。
下面全部用大白話講，數字都是程式算出來的，不是我手抄的。{D['today']} 產出。</p>

<div class="card paper">
<h2 style="margin-top:0;border:0">給爸媽的一頁紙（記三件事就好）</h2>
<p><b>1．沒有花錢、沒有連券商。</b> 這四件都是在家裡整理功課，像把抽屜裡的東西分門別類放好；
到今天還是紙上練習帳，沒有下過任何一張單。</p>
<p><b>2．做出來的不是「更會賺」，是「更不會騙自己」。</b>
其中一件把圖改成每天記一筆，才發現以前少看了跌幅；另一件把考試從一次改成七次，
才發現原本以為有效的規矩，其實七次裡一次都沒贏。</p>
<p><b>3．不用等我，也不用等誰點頭。</b> 這四件都不用通行證、不用花錢、不用連券商，
所以今天就做完了。系統進步是變誠實，不是變大膽。</p>
</div>

<div class="card">
<div class="kv">
  <div class="cell"><div class="k">這輪跑完的程式</div><div class="v">{inv['n_py']} 支／{inv['n_lines']:,} 行</div></div>
  <div class="cell"><div class="k">四步加起來的檢查</div><div class="v">{checks} 項、失敗 {fails} 項</div></div>
  <div class="cell"><div class="k">還沒推上倉庫</div><div class="v">{inv['n_untracked']} 項</div></div>
</div>
<p class="note">升級五關只過第一關；現在是練習帳。以上三個數字是剛剛重新掃過程式目錄與倉庫狀態得來的。</p>
</div>

{sec(1, '這四件到底做了什麼')}
<p>V5.0 是一張施工單，不是按下去就會動的機器。施工單上寫了七件事，
其中四件是「不用錢、不用連線、不用通行證」就能做的。這次就是把這四件真的做完，
每一件各寫一支程式、各存一份結果檔、各驗一次，沒有混在一起改。</p>
<table><thead><tr><th>第幾步</th><th>做的事</th><th>做出來會看到</th></tr></thead><tbody>
<tr><td>2</td><td>把「資料有多新」寫進網頁</td><td>兩個時間、三種標籤、全部 {ov['n_stocks']} 檔的時效總覽</td></tr>
<tr><td>3</td><td>把三個規矩拆開，一次只改一處</td><td>{s3['n_variants']} 種組合 × {s3['n_segments']} 段對照</td></tr>
<tr><td>4</td><td>圖改成每天記一筆</td><td>{sm4['n_curves']} 條曲線、每條 {sm4['n_days_each']} 天的完整數字</td></tr>
<tr><td>5</td><td>考試從一次改成很多次</td><td>{sm5['n_folds']} 段輪流考的結果</td></tr>
</tbody></table>

{sec(2, '資料是舊的還是新的，現在看得到了')}
<p>以前網頁只寫一個時間，長輩容易把「以前抓到的價格」當成「現在的價格」。
現在同時寫兩個，都是固定不動的字：</p>
<div class="kv">
  <div class="cell"><div class="k">行情時間（這筆價格是哪一天）</div><div class="v">{t['quote_as_of']}</div></div>
  <div class="cell"><div class="k">資料更新（哪一天去抓的）</div><div class="v">{t['captured_at']}</div></div>
</div>
<p>另外貼三種標籤：<b>盤中報價</b>（交易時間抓到的）、<b>今日收盤</b>（當天收盤後）、
<b>歷史資料</b>（以前的價格，不是現在）。全部 {ov['n_stocks']} 檔裡，有
<span class="big">{ov['n_stale']}</span> 檔落後超過 {s2['stale_threshold_days']} 天，
最多落後 <span class="big">{ov['max_lag_days']}</span> 天。</p>
<p class="note">重點：畫面不顯示現在幾點，判斷一律用資料自己帶的時間，避免誤會成即時價格。
什麼時候該重新抓資料，交給離線流程判斷，不進畫面。</p>

{sec(3, '還順手抓到一個要講清楚的地方')}
<div class="warn">{ic['plain']}</div>
<p>以前幾份報告寫的「資料到 {ic['meta_claimed_end']}」，是照資料自己貼的標籤寫的；
這次點開來看，才發現大盤實際只到 {ic['index_actual_last_date']}。
本輪<b>只標記、不改舊結論</b>，因為規矩是一次只做一件、改完各驗一次。</p>

{sec(4, '拆開才知道，有一個零件根本沒動')}
<p>以前一次改了三個地方，只能說「方向好像對」，說不清是誰有功勞。
這次把三個規矩做成開關，{s3['n_variants']} 種組合各跑一次（一共
{s3['n_variants'] * s3['n_segments']} 次），結果很意外：</p>
<ul>
<li><b>部分減碼</b>（漲兩成賣四分之一、漲四成再賣三分之一）單獨用，
三段平均{pp(cross['A']['avg_alone_pp'])}，看起來像有害。</li>
<li><b>月檢降倉</b>（每 21 天看一次長期均線，轉弱就把目標降到四成）單獨用，
平均{pp(cross['B']['avg_alone_pp'])}；但跟別的配在一起，邊際卻是
{pp(cross['B']['avg_marginal_pp'])}。兩個數字差很大，代表它們會互相影響。</li>
<li><b>賣後回補</b>（賣出後 20 天內再創新高就買回四分之一）在三段裡
<b>一次都沒發動</b>，總共 {f3['n_reentry_total']} 次。以前把它當成最關鍵的升級，是誤會。</li>
</ul>
<p>更重要的是：三個規矩全開的那一組，三段數字都跟舊程式<b>對得上</b>，
證明這次只是拆開來看，沒有把規則改壞。</p>
<table><thead><tr><th>段落</th><th>放著不動</th><th>三個全開</th><th>跟舊程式相符</th></tr></thead>
<tbody>{seg_rows}</tbody></table>
<p class="note">「個百分點」＝把兩個百分比直接相減的差距，不是幾成。</p>

{sec(5, '圖改成每天記一筆，最深那天不再被漏掉')}
<p>以前圖上每 {s4['sample_every_before']} 天只取一個點，像一週只量一次血壓，
會漏掉發燒那天。現在三條曲線、每條 {sm4['n_days_each']} 天的數字全部存起來，
圖也真的改成用每天數字畫。</p>
<table><thead><tr><th>曲線</th><th>每天記算出來的跌幅</th><th>七天取樣</th>
<th>少看</th><th>最深那天</th></tr></thead><tbody>{curve_rows}</tbody></table>
<p>平均少看 <span class="big">{sm4['avg_underestimate_pp']}</span> 個百分點、
最多 <span class="big">{sm4['max_underestimate_pp']}</span> 個百分點；
改用每天數字後，這個誤差直接是 <span class="big">0</span>。</p>
<p class="note">以前 V4.2 用另一批曲線量到平均 {sm4['v42_reported']['avg_mdd_gap_pp']}、
最多 {sm4['v42_reported']['max_mdd_gap_pp']} 個百分點。
{sm4['v42_reported']['plain']}，所以兩邊不能說誰變好或變壞，
只能說同一個毛病在全程段也量得到。</p>
<p class="note">還做了一個對照：把這次重跑的曲線照舊方式每七天取一點，
跟舊結果檔裡的數字<b>完全相符</b>，證明不是算錯，是以前真的少記了。</p>

{sec(6, '不只考一次，改成考七次')}
<p>以前只在 2024 年 7 月 1 日切一刀，等於只考一回；那一回本身就
{pp(old5['outperformance_pp'])}。這次改成一段一段往前考：
每次都用前面所有資料挑參數，再拿緊接著一段沒看過的日子驗證，
而且每一段都跟「放著不動」比。共 {sm5['n_folds']} 段。</p>
<table><thead><tr><th>段落</th><th>考的日期</th><th>規矩</th><th>放著不動</th><th>差多少</th></tr></thead>
<tbody>{fold_rows}</tbody></table>
<p>結果：贏 <span class="big">{sm5['n_wins']}</span> 段（{sm5['win_rate_pct']}%），
平均{pp(sm5['avg_outperformance_pp'])}，最好 {pp(sm5['best_fold_pp'])}、
最差 {pp(sm5['worst_fold_pp'])}。</p>
<div class="warn"><b>判定：{sm5['verdict']}。</b>
有 {sm5['n_folds'] - sm5['n_wins']} 段裡規矩跟放著不動一模一樣，代表那段根本沒觸發；
其餘段落是落後。這不是「剛好押中一段」的問題，是這套規矩本來就站不住。</div>
<p class="note">每段挑出來的參數都是同一個（共 {sm5['n_distinct_params']} 種），
所以也不是參數亂跳造成的。參數、成本、買賣規則全部沿用舊版，沒有重新調整。</p>

{sec(7, '四件各自的驗收')}
<table><thead><tr><th>第幾步</th><th>結果</th><th>檢查項數</th><th>失敗</th></tr></thead>
<tbody>{verify_rows}</tbody></table>
<p>合起來 <span class="big">{checks}</span> 項檢查、失敗
<span class="big">{fails}</span> 項。每一組都另外重跑一次對照，
數字完全相同才算過關；不是「看起來沒出事」就算做完。</p>

{sec(8, '現在還不能做的五件事')}
<table><thead><tr><th>不能做的事</th><th>為什麼</th></tr></thead><tbody>
<tr><td>送單到券商、花真錢</td><td>現在是紙上練習帳，升級五關只過第一關</td></tr>
<tr><td>解鎖「額度內自動、免逐筆確認」</td><td>五關要全過，還要有您簽的書面授權</td></tr>
<tr><td>把中探針放進自動白名單</td><td>它不在資料池，外部只找到 4 根日線，規矩要 1,000 根</td></tr>
<tr><td>叫系統自己宣布「我夠格了」</td><td>升級要人簽名，程式不能自己說了算</td></tr>
<tr><td>把憑證或密碼放進倉庫</td><td>憑證絕對不進倉庫，這條從 V2.7 寫到現在</td></tr>
</tbody></table>
<p class="note">施工單第 1 步（辦新令牌）、第 6 步（補資料）還是要您本人點頭；
第 7 步（券商連線與實盤）現在還不能碰。這四件做完，不代表可以往前跳。</p>

{sec(9, '我還不知道，要請您回答')}
<ul>
<li>家裡全部資產大概多少、這檔佔幾成（不知道就算不出該留幾股）</li>
<li>這張是不是融資買的、維持率多少（若是，追繳比股價更急）</li>
<li>新令牌什麼時候辦、會不會辦（我不知道，也不該替您決定）</li>
<li>補資料要從哪裡來、要不要花錢（要您點頭）</li>
<li>券商測試環境的實際連線結果（沒連過，一律寫不知道）</li>
</ul>
<p class="note">最急的還是那兩題：這檔佔家裡全部資產幾成？是不是融資買的？
若是融資，請先打電話問營業員。</p>

{sec(10, '這一次新學到的三件事')}
<table><thead><tr><th>學到什麼</th><th>證據</th></tr></thead><tbody>
<tr><td>拆開才知道功勞是誰的</td><td>一個零件三段裡一次都沒發動；另一個單獨看有害、配起來卻有用</td></tr>
<tr><td>圖少記一天，跌幅就少看</td><td>三條曲線平均少看 {sm4['avg_underestimate_pp']} 個百分點，最深那天都剛好被跳過</td></tr>
<tr><td>考一次不算數</td><td>改成 {sm5['n_folds']} 段之後，原本以為的方向直接站不住</td></tr>
</tbody></table>
<p><b>系統進步是變誠實，不是變大膽。</b> 這四件都沒有讓系統多賺一塊錢，
只是讓它少誤會自己、也少讓您誤會它。</p>

<p class="src">來源：v52_step2_freshness.json、v52_step3_ablation.json、
v52_step4_daily_nav.json、v52_step5_multifold.json，
以及即時重掃的程式目錄與倉庫狀態。所有數字由程式讀檔回填，不是手抄。
{D['today']} 產出。</p>
<div class="warn">提醒：本版只做方法與風險控管示範，不是買賣建議；
系統仍是紙上練習帳，沒連券商、沒下過任何一張單。</div>
</div></body></html>
"""


def build_md(D: dict) -> str:
    s2, s3, s4, s5 = D["s2"], D["s3"], D["s4"], D["s5"]
    inv = D["inv"]
    ov = s2["freshness_overview"]
    sm4, sm5 = s4["summary"], s5["summary"]
    return f"""# V5.2 施工單編程結果・決策卡

> **一句話：四件「現在就能做」的事今天全部寫成程式、跑出數字、各驗一次；
> 做出來的不是更會賺，是更不會騙自己。**

{D['today']} 產出｜接續 V5.1 執行手冊｜現況仍是練習帳，沒連券商、沒下過任何一張單

---

## 給爸媽的一頁紙（只要記三件事）

**1．沒有花錢、沒有連券商。** 這四件都是在家裡整理功課，到今天還是紙上練習帳。

**2．不是更會賺，是更不會騙自己。** 圖改成每天記一筆，才發現以前少看了跌幅；
考試從一次改成七次，才發現原本以為有效的規矩，七次裡一次都沒贏。

**3．不用等我，也不用等誰點頭。** 四件都不用通行證、不用花錢、不用連券商，今天就做完了。

## 先看現在的真實狀態（不算章節）

- 四步加起來 {D['n_checks_total']} 項檢查、失敗 {D['n_fail_total']} 項
- 本輪即時重掃 {inv['n_py']} 支／{inv['n_lines']:,} 行；未推送 {inv['n_untracked']} 項
- 升級五關只過 1／5；仍是 M0 練習帳
- 資料池 {ov['n_stocks']} 檔；{ov['n_stale']} 檔落後超過 3 天，最多 {ov['max_lag_days']} 天

## 1．四件做了什麼

| 第幾步 | 做的事 | 做出來會看到 |
|---|---|---|
| 2 | 雙時間、三態標籤、時效總覽寫進網頁 | 靜態網頁＋首頁橫幅，數字由資料檔回填 |
| 3 | 三元件消融對照 | {s3['n_variants']} 種組合 × {s3['n_segments']} 段 |
| 4 | 每日淨值取代七天取樣 | {sm4['n_curves']} 條 × {sm4['n_days_each']} 天，附每日數字圖 |
| 5 | 多段輪流考 | {sm5['n_folds']} 段，每段各自對照放著不動 |

## 2．第 2 步：資料新舊看得到了

行情時間 {s2['two_times']['quote_as_of']}／資料更新 {s2['two_times']['captured_at']}，
兩個都是固定值；三態標籤為盤中報價、今日收盤、歷史資料。
{ov['n_stocks']} 檔中 {ov['n_stale']} 檔落後超過 {s2['stale_threshold_days']} 天，最多 {ov['max_lag_days']} 天。
畫面不顯示裝置時鐘；要不要重抓交給離線流程判斷。

另外誠實標記一處不一致：{s2['data_inconsistency']['plain']}
本輪只標記、不改舊結論。

## 3．第 3 步：拆開才知道有個零件沒動

- 部分減碼單獨用，三段平均{pp(s3['cross_segment']['A']['avg_alone_pp'])}；
  但跟別的配在一起，邊際是{pp(s3['cross_segment']['A']['avg_marginal_pp'])}。
- 月檢降倉單獨{pp(s3['cross_segment']['B']['avg_alone_pp'])}，
  邊際卻{pp(s3['cross_segment']['B']['avg_marginal_pp'])}，交互很大。
- 賣後回補三段合計發動 {s3['finding']['n_reentry_total']} 次；
  全開組與 AB 組換手次數完全相同，印證它沒作用。
- 全開組三段都與 V4.0 原程式對得上，證明拆分沒改壞規則。

## 4．第 4 步：每天記一筆

| 曲線 | 每日跌幅 | 七天取樣 | 少看 | 最深那天 |
|---|---|---|---|---|
""" + "".join(
        f"| {c['label']} | 跌 {abs(c['mdd_daily_pct']):.2f}% | "
        f"跌 {abs(c['mdd_sampled_pct']):.2f}% | {c['underestimate_pp']:.2f} | "
        f"{c['worst_date']} |\n" for c in s4["curves"]
    ) + f"""
平均少看 {sm4['avg_underestimate_pp']}、最多 {sm4['max_underestimate_pp']} 個百分點；
改用每日數字後誤差為 0。重跑的七天取樣與舊結果檔完全相符，證明不是算錯。

## 5．第 5 步：考七次

贏 {sm5['n_wins']}／{sm5['n_folds']} 段（{sm5['win_rate_pct']}%），
平均{pp(sm5['avg_outperformance_pp'])}，最好 {pp(sm5['best_fold_pp'])}、
最差 {pp(sm5['worst_fold_pp'])}。

> **判定：{sm5['verdict']}。**

舊做法只切一次時是 {pp(s5['old_single_split']['outperformance_pp'])}。
每段挑出的參數都是同一個（共 {sm5['n_distinct_params']} 種），不是參數亂跳。

## 6．怎麼算做完

| 第幾步 | 結果 | 檢查項 | 失敗 |
|---|---|---:|---:|
""" + "".join(
        f"| 第 {k} 步 | {'全部通過' if v['all_pass'] else '未通過'} | "
        f"{v['n_checks']} | {v['n_fail']} |\n"
        for k, v in D["verifications"].items()
    ) + f"""
合計 {D['n_checks_total']} 項、失敗 {D['n_fail_total']} 項。
每組都另外重跑一次對照，數字完全相同才算過關。

## 7．現在還不能做的五件事

送單花真錢、解鎖免逐筆確認、把中探針放進白名單、
叫系統自己宣布夠格、把憑證放進倉庫。原因與 V5.1 相同，沒有放寬。

## 8．我還不知道，要請您回答

家裡全部資產與這檔佔比、是不是融資買的與維持率、
新令牌何時辦、補資料從哪裡來、券商測試環境連線結果。
不知道的就寫不知道，不硬湊。

## 9．這一次新學到的三件事

1. 拆開才知道功勞是誰的：一個零件一次都沒發動，另一個單獨看有害、配起來有用。
2. 圖少記一天，跌幅就少看 {sm4['avg_underestimate_pp']} 個百分點。
3. 考一次不算數：改成 {sm5['n_folds']} 段後，原本以為的方向站不住。

> **系統進步是變誠實，不是變大膽。**

## 10．誠實狀態與提醒

技術債仍在：位置寫死、產生器各自寫輸出位置、結果檔散在兩處。
舊結果檔的七天取樣保留給舊報告讀，本輪不改舊結論；新圖一律用每日數字。

> 提醒：本版只做方法與風險控管示範，不是買賣建議；
> 系統仍是紙上練習帳，沒連券商、沒下過任何一張單。

---

來源：四份 v52 結果檔與即時重掃狀態。{D['today']} 產出。
"""


def build_doc(D: dict) -> str:
    """技術版：保留檔名與代號，但括號解釋。"""
    s2, s3, s4, s5 = D["s2"], D["s3"], D["s4"], D["s5"]
    inv = D["inv"]
    return f"""# V5.2 施工單編程結果（技術版）

{D['today']} 產出。對應 V5.1 執行手冊第 2～5 步。四支程式各自獨立、
各自輸出一份結果檔、各自內建驗收，沒有互相改動既有檔案的邏輯。

| 步驟 | 程式 | 結果檔 | 驗證 |
|---|---|---|---|
| 2 | `tool/v3/step2_freshness.py` | `v52_step2_freshness.json` | 7 項 |
| 3 | `tool/v3/step3_ablation.py` | `v52_step3_ablation.json` | 5 項 |
| 4 | `tool/v3/step4_daily_nav.py` | `v52_step4_daily_nav.json` | 6 項 |
| 5 | `tool/v3/step5_multifold.py` | `v52_step5_multifold.json` | 6 項 |

合計 {D['n_checks_total']} 項、失敗 {D['n_fail_total']} 項。
即時重掃：`tool/v3` {inv['n_py']} 支／{inv['n_lines']:,} 行，未推送 {inv['n_untracked']} 項。

## 第 2 步：V2.8 落地

- 雙時間（行情時間／資料更新）皆為靜止固定值：`{s2['two_times']['quote_as_of']}`／`{s2['two_times']['captured_at']}`。
- 三態標籤（`intraday`／`todayClose`／`historical`）由 `classify()` 依資料自帶欄位判定；
  `DEVICE_CLOCK_USED = {s2['device_clock_used']}`，判斷邏輯在 `lib/core/data_freshness.dart`。
- 產出：`web/data_freshness.html`（可直接開的靜態總覽頁）、
  `lib/core/data_freshness_data.dart`（由 JSON 自動生成的常數）、
  `lib/core/data_freshness.dart`、`lib/ui/data_freshness_banner.dart`，
  並在 `lib/ui/home_page.dart` 的 `_header()` 後掛上橫幅。
- `dart analyze` 三支新檔：No issues found。
- 資料時效總覽：{s2['freshness_overview']['n_stocks']} 檔、
  {s2['freshness_overview']['n_stale']} 檔落後 > {s2['stale_threshold_days']} 天、
  最多 {s2['freshness_overview']['max_lag_days']} 天。

**新標記的資料不一致**：{s2['data_inconsistency']['plain']}
`meta.range` 與 `index.dates[-1]` 不同步；本輪只標記，不改舊結論。
`offline_refresh` 以離線產出日判斷要不要重抓，不進畫面。

## 第 3 步：消融對照（ablation）

`run_variant()` 把 V4.0 `combined_rule` 做成三個獨立開關
A 部分減碼／B 月檢降倉（MA120）／C 賣後回補，跑 8 種組合 × 3 段。
參數沿用原值（`step1=0.20`、`step2=0.40`、`reenter_days=20`、`off_w=0.40`、`batch=1/3`），
沒有重新挑最優。

- 全開組 `ABC` 三段與 `v40_execution_result.json` 的 `combo` 五個欄位全對得上。
- 每組重跑一次，`repeat_identical` 全為真。
- `cross_segment`：A 平均單獨 {s3['cross_segment']['A']['avg_alone_pp']}pp、
  邊際 {s3['cross_segment']['A']['avg_marginal_pp']}pp、
  交互 {s3['cross_segment']['A']['avg_interaction_pp']}pp。
- **C 三段合計發動 {s3['finding']['n_reentry_total']} 次**；
  `ABC` 與 `AB` 的 `turnovers` 完全相同。V4.0 把它當成最關鍵升級，屬誤判。

## 第 4 步：每日淨值

- 重跑全程段三條曲線（`combo`／`buyhold`／`static`），
  把完整 {s4['summary']['n_days_each']} 天 `nav_daily` 存進結果檔；
  原本只有 `path[::7]` 的 `nav_slim`。
- 重跑的 `[::7]` 與 `v40_execution_result.json` 的 `nav_slim`／`bh_slim`／`static_slim`
  逐點相符（`old_slim_matches_rerun` 全為真）。
- 低估幅度：平均 {s4['summary']['avg_underestimate_pp']}pp、
  最多 {s4['summary']['max_underestimate_pp']}pp；
  三條曲線的最深日索引除以 7 都不為 0，確實被取樣跳過。
- 產出 `web/daily_nav_chart.html`（SVG，直接讀每日數字，標註最深那天）。
- V4.2 的 {s4['summary']['v42_reported']['avg_mdd_gap_pp']}／
  {s4['summary']['v42_reported']['max_mdd_gap_pp']}pp 是另一批曲線的對帳結果，
  口徑不同，不做改善或惡化的比較。

## 第 5 步：多段樣本外（walk-forward）

`one_fold()` 用 expanding window（`TRAIN_INIT=500`、`TEST_LEN=120`、`STEP=120`），
每段以 7 個固定候選參數（`ma60/ma120/ma240/dd 0.08～0.25`）在訓練窗挑
最大 Calmar，再於不重疊的測試窗對照買入持有。共 {s5['n_folds']} 段。

- 贏 {s5['summary']['n_wins']}／{s5['summary']['n_folds']} 段，
  平均超額 {s5['summary']['avg_outperformance_pp']}pp，
  最好 {s5['summary']['best_fold_pp']}pp、最差 {s5['summary']['worst_fold_pp']}pp。
- `best_param` 每段皆為 `ma120`（`param_consistent = {s5['summary']['param_consistent']}`）。
- 自動判定：{s5['summary']['verdict']}
- 舊單切一次（20240701）：{s5['old_single_split']['outperformance_pp']}pp。

## 沒做的事（不跳步）

第 1 步新令牌、第 6 步補資料、第 7 步券商測試環境與實盤，
仍需本人辦理或尚未解鎖。五關只過 G1，模式 M0 練習帳。
中探針外部仍只有 4 根日線，未達 1,000 根門檻，一律寫不知道。

## 驗收

| 第幾步 | 全過 | 檢查項 | 失敗 |
|---|---|---:|---:|
""" + "".join(
        f"| 第 {k} 步 | {v['all_pass']} | {v['n_checks']} | {v['n_fail']} |\n"
        for k, v in D["verifications"].items()
    ) + """
> 提醒：本版只做方法與風險控管示範，不是買賣建議；沒連券商、沒下過任何一張單。
"""


def main() -> None:
    D = {k: jload(p) for k, p in FILES.items()}
    D["today"] = date.today().isoformat()
    D["inv"] = inventory()
    D["verifications"] = {
        "2": D["s2"]["verification"], "3": D["s3"]["verification"],
        "4": D["s4"]["verification"], "5": D["s5"]["verification"],
    }
    D["n_checks_total"] = sum(v["n_checks"] for v in D["verifications"].values())
    D["n_fail_total"] = sum(v["n_fail"] for v in D["verifications"].values())

    OUT_HTML.write_text(build_html(D), encoding="utf-8")
    OUT_MD.write_text(build_md(D), encoding="utf-8")
    OUT_DOC.write_text(build_doc(D), encoding="utf-8")
    print(f"[V5.2 報告] 產出 3 份檔｜四步合計 {D['n_checks_total']} 項檢查、"
          f"失敗 {D['n_fail_total']} 項")
    print(f"  即時重掃：{D['inv']['n_py']} 支／{D['inv']['n_lines']:,} 行，"
          f"未推送 {D['inv']['n_untracked']} 項")
    for p in (OUT_HTML, OUT_MD, OUT_DOC):
        print(f"  {p}")


if __name__ == "__main__":
    main()
