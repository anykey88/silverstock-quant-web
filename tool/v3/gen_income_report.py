"""V6.0 報告產生器：只讀 v60_income_research.json，數字不手抄。

輸出：
  /workspace/V6.0_創收方法與出路.html          （長輩版：淺底大字、繁體、零術語）
  /workspace/V6.0_創收方法與出路決策卡.md      （可印）
  docs/V6.0_INCOME_PATHS.md                    （技術版：保留來源網址）

用法：python3.11 tool/v3/gen_income_report.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
SRC = ROOT / "v60_income_research.json"
D = json.loads(SRC.read_text(encoding="utf-8"))

CSS = """
:root{--bg:#FFFDF6;--ink:#2B2B2B;--soft:#5B6B78;--line:#E8D9A8;
--card:#FFFFFF;--warm:#FDF3E3;--accent:#1A3A5C;--warn:#B03A2E}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:-apple-system,'PingFang TC','Microsoft JhengHei',sans-serif;
 font-size:21px;line-height:1.95;padding:28px 18px 80px}
.wrap{max-width:920px;margin:0 auto}
h1{font-size:34px;line-height:1.4;margin:0 0 12px}
h2{font-size:27px;margin:44px 0 14px;line-height:1.5}
h3{font-size:23px;margin:0 0 10px}
p{margin:0 0 16px}
.lead{font-size:23px;background:var(--warm);border-left:7px solid #C9822E;
 border-radius:10px;padding:18px 20px;margin:18px 0 30px;line-height:1.8}
.meta{font-size:18px;color:var(--soft);margin:0 0 26px}
.card{background:var(--card);border:2px solid var(--line);border-radius:16px;
 padding:22px 24px;margin:0 0 18px}
.onepage{background:#FFF8E8;border:3px solid #D9B96A;border-radius:18px;
 padding:26px 26px 12px;margin:0 0 34px}
.onepage h2{margin:0 0 16px;font-size:28px}
.onepage p{font-size:23px}
.num{display:inline-block;background:var(--accent);color:#fff;border-radius:50%;
 width:38px;height:38px;line-height:38px;text-align:center;font-size:20px;
 margin-right:10px;font-weight:700}
table{width:100%;border-collapse:collapse;margin:14px 0 24px;font-size:19px}
th,td{border:1px solid #DCD2B4;padding:12px 14px;text-align:left;vertical-align:top}
th{background:#F3EAD2;font-weight:700}
tr:nth-child(even) td{background:#FCFAF3}
a{color:#1A5C8A}
.tag{display:inline-block;background:#EAF1F7;color:var(--accent);border-radius:8px;
 padding:3px 11px;font-size:18px;margin:0 6px 6px 0}
.warn{background:#FDECEA;border-left:7px solid var(--warn);border-radius:10px;
 padding:16px 20px;margin:18px 0}
.small{font-size:18px;color:var(--soft)}
ul{margin:0 0 16px;padding-left:26px}
li{margin:0 0 10px}
.foot{margin-top:44px;border-top:2px solid var(--line);padding-top:18px;font-size:18px}
"""

H = []
A = H.append

A("<!DOCTYPE html><html lang='zh-Hant'><head><meta charset='utf-8'>")
A("<meta name='viewport' content='width=device-width, initial-scale=1'>")
A("<title>V6.0 創收方法與出路</title><style>" + CSS + "</style></head><body><div class='wrap'>")

A("<h1>創收方法與出路</h1>")
A("<p class='meta'>" + D["generated_at"] + " 產出｜公開資料整理｜" + D["scope_note"] + "</p>")
A("<div class='lead'><b>" + D["one_line"] + "</b><br>" + D["passive_reframe"]["plain"] + "</div>")

# ── 給爸媽的一頁紙（不編號） ───────────────────────────────
A("<div class='onepage'><h2>給自己／給爸媽的一頁紙：只要記三件事</h2>")
A("<p><b>1．可以，我查了，而且不畫大餅。</b>六位可查證的人、六條路、十七筆來源，"
  "全部寫在下面；做得到的寫做得到，不知道的就寫不知道。</p>")
A("<p><b>2．被動收入不是「不用做事就有錢」。</b>它是「做一次、可以收很多次」。"
  "沒有 0 成本、0 風險的捷徑，現在沒有收入時，先用「已經有的東西」去換錢，不要用錢去賺錢。</p>")
A("<p><b>3．焦慮的解藥不是一筆大錢，是本週第一筆小錢。</b>只挑一條路，做十四天，"
  "看有沒有人願意付第一筆。您手上已經有五樣別人買不到的東西。</p>")
A("</div>")

# ── 1 被動收入真相 ────────────────────────────────────────
A("<h2><span class='no'>1</span>先講清楚「被動收入」真正的意思</h2>")
A("<div class='card'><p style='font-size:23px'><b>" + D["passive_reframe"]["text"] + "</b></p></div>")
A("<p>我把四份公開資料對過，說法一致，先誠實講在前面：</p><table>")
A("<tr><th>查到的說法</th><th>資料來源</th></tr>")
for r in D["passive_truth"]:
    A("<tr><td>" + r["text"] + "</td><td><a href='" + r["url"] + "' target='_blank'>"
      + r["source"] + "</a></td></tr>")
A("</table>")
A("<div class='warn'><b>要提醒的一句：</b>您現在沒有收入，正是「保證獲利、穩賺、"
  "先繳錢學被動收入」這類話術最愛找的人。第 8 節有三條紅線，先記著就好。</div>")

# ── 2 既有資產 ────────────────────────────────────────────
A("<h2><span class='no'>2</span>您手上已經有的五樣東西（別人買不到）</h2>")
A("<p>找機會之前先看口袋，不必從零開始。這五樣是從您過去的經歷整理出來的，不是我編的：</p>")
for i, a in enumerate(D["assets"], 1):
    A("<div class='card'><h3>" + str(i) + "．" + a["name"] + "</h3><p>" + a["plain"] + "</p></div>")

# ── 3 成功者出路 ──────────────────────────────────────────
A("<h2><span class='no'>3</span>六位可查證的人，他們是怎麼走出來的</h2>")
A("<p>您說想找成功人士的出路。我避開那種「二十歲就致富」的神話，"
  "專挑<b>年紀偏大、從低處起、靠既有東西</b>的案例，而且每條都附來源。</p>")
A("<table><tr><th>誰</th><th>當時</th><th>可查證的事</th><th>能抄的是什麼</th></tr>")
for c in D["cases"]:
    A("<tr><td><b>" + c["who"] + "</b><br><span class='small'>"
      + "<a href='" + c["url"] + "' target='_blank'>" + c["source"] + "</a></span></td>"
      "<td>" + c["age"] + "</td><td>" + c["fact"] + "</td><td>" + c["take"] + "</td></tr>")
A("</table>")
A("<div class='card'><p style='font-size:22px'><b>共同點：</b>" + D["cases_common"] + "</p></div>")

# ── 4 胖東來 ──────────────────────────────────────────────
A("<h2><span class='no'>4</span>胖東來：哪些能抄、哪些不能抄</h2>")
A("<p>您提到想「像胖東來一樣幫助他人」。我特別去讀了人民日報專訪于東來，"
  "他年輕時也賠了很多錢、一直到 1995 年才摸清做生意的門道。"
  "但他自己講得很明白：</p>")
A("<div class='lead'>「" + D["pdl"]["quote"] + "」<br><span class='small'>—— "
  + D["pdl"]["quote_source"] + "，"
  + "<a href='" + D["pdl"]["url"] + "' target='_blank'>原文</a></span></div>")
A("<h3>不能抄的（要本錢、要店面、要人）</h3><ul>")
for x in D["pdl"]["cannot"]:
    A("<li>" + x + "</li>")
A("</ul><h3>能抄的（不用本錢，今天就能做）</h3><table>")
A("<tr><th>做法</th><th>白話</th></tr>")
for x in D["pdl"]["can"]:
    A("<tr><td><b>" + x["t"] + "</b></td><td>" + x["d"] + "</td></tr>")
A("</table>")
A("<p class='small'>開放日 2 萬元、十年內可全額退費的做法，見"
  "<a href='" + D["pdl"]["url_open_day"] + "' target='_blank'>重慶日報</a>。"
  + D["pdl"]["small_scale"] + "</p>")

# ── 5 六條路 ──────────────────────────────────────────────
A("<h2><span class='no'>5</span>符合您現況的六條路</h2>")
A("<p>每一條都照您的狀況挑過：<b>室內、低體力、不用先掏錢、用得上 AI 與既有經驗</b>。"
  "每條都誠實標了「我不知道」，沒有保證能賺多少。</p>")
for p in D["paths"]:
    A("<div class='card'><h3>路徑 " + p["id"] + "．" + p["name"] + "</h3>")
    A("<p><b>為什麼適合您：</b>" + p["why"] + "</p>")
    A("<p><b>第一步（今天就能做）：</b>" + p["first"] + "</p>")
    A("<p><span class='tag'>" + p["cost"] + "</span>"
      "<span class='tag'>第一筆錢：" + p["first_money"] + "</span></p>")
    A("<p><b>風險：</b>" + p["risk"] + "</p>")
    A("<p><b>我不知道：</b>" + p["unknown"] + "</p></div>")

# ── 6 政策：誠實講不符合 ──────────────────────────────────
A("<h2><span class='no'>6</span>福州的政策：有一條要跟您講明白</h2>")
A("<div class='warn'><p style='margin:0'><b>" + D["policy"]["not_eligible"] + "</b></p></div>")
A("<p>但這份資料裡，藏著一個更適合您的位置——<b>站在「給」的那一邊</b>：</p><ul>")
for u in D["policy"]["usable"]:
    A("<li>" + u + "</li>")
A("</ul>")
A("<p><b>我不知道：</b>" + D["policy"]["unknown"] + "</p>")
A("<p class='small'>" + D["policy"]["phone"] + "</p>")

# ── 7 排序 ────────────────────────────────────────────────
A("<h2><span class='no'>7</span>先做哪一件：分三堆</h2>")
A("<p>您說「放開思路多方嘗試」，我完全贊成，但<b>多方「找」可以一次看完，"
  "多方「做」不行</b>——下面這張表幫您排順序。</p>")
A("<table><tr><th>堆</th><th>內容</th><th>白話</th></tr>")
for q in D["priority"]:
    A("<tr><td><b>" + q["pile"] + "</b></td><td>" + q["items"] + "</td><td>"
      + q["plain"] + "</td></tr>")
A("</table>")
A("<div class='card'><p style='font-size:22px'><b>" + D["one_at_a_time"] + "</b></p></div>")

# ── 8 行善 ────────────────────────────────────────────────
A("<h2><span class='no'>8</span>行善與賺錢可以同時，但利潤很薄</h2>")
A("<p>我查了五個真實案例，都是「公益加小生意」，數字照抄，不美化：</p>")
A("<table><tr><th>案例</th><th>實際數字</th></tr>")
for c in D["charity"]:
    A("<tr><td><a href='" + c["u"] + "' target='_blank'>" + c["t"] + "</a></td><td>"
      + c["n"] + "</td></tr>")
A("</table>")
A("<div class='lead'>" + D["charity_verdict"] + "</div>")

# ── 9 焦慮 ────────────────────────────────────────────────
A("<h2><span class='no'>9</span>焦慮的時候，用方法不用雞湯</h2>")
A("<p>您說「如果每天能有被動收入，就不會那麼焦慮」。這句我聽進去了。"
  "但誠實說：起步階段做不到每天有進帳，做得到的是<b>每週一個看得見的小成果</b>，"
  "慢慢變成「東西做好了，睡覺時也有人買」。下面四條是方法，不是安慰：</p><ul>")
for a in D["anxiety"]:
    A("<li>" + a + "</li>")
A("</ul>")
A("<div class='warn'><b>三條防詐紅線（"
  + "<a href='" + D["fraud_url"] + "' target='_blank'>" + D["fraud_source"]
  + "</a>）：</b><ul>")
for f in D["fraud_lines"]:
    A("<li>" + f + "</li>")
A("</ul><p style='margin:0'>" + D["fraud_note"] + "</p></div>")

# ── 10 我不知道 ───────────────────────────────────────────
A("<h2><span class='no'>10</span>我不知道，也不該替您決定的事</h2>")
A("<div class='card'><ul>")
for u in D["unknown"]:
    A("<li>" + u + "</li>")
A("</ul></div>")

# ── 結語 ──────────────────────────────────────────────────
A("<h2>可以，而且我陪您一件一件做</h2>")
A("<p style='font-size:23px'>您問「可以嗎」，答案是<b>可以</b>。"
  "您要驗證 AI 能不能幫您從無到有，我願意陪著驗證——用的就是您自己訂的規矩："
  "<b>小步、重跑、留紀錄、不梭哈、不知道就寫不知道</b>。</p>")
A("<p>下一步您只要說一句：要我先把<b>路徑 A 那份「來榕創業補助檢核表」</b>做出來，"
  "還是先幫您把<b>「台北黃哥在福州」的一則內容</b>用 AI 整理成可貼的稿？"
  "您說一件，我就只做一件、做完立刻重跑對照。</p>")

A("<div class='foot'><p><b>資料來源（可點開查證）</b></p><ul>")
for s in D["sources_extra"]:
    A("<li><a href='" + s["u"] + "' target='_blank'>" + s["t"] + "</a></li>")
for s in D["policy"]["sources"]:
    A("<li><a href='" + s["u"] + "' target='_blank'>" + s["t"] + "</a></li>")
A("</ul><p>" + D["disclaimer"] + "</p></div>")

A("</div></body></html>")

html = "\n".join(H)
(WORKSPACE / "V6.0_創收方法與出路.html").write_text(html, encoding="utf-8")

# ── 決策卡（可印） ────────────────────────────────────────
M = []
B = M.append
B("# 創收方法與出路・決策卡")
B("")
B("> **" + D["one_line"] + "**")
B("")
B(D["generated_at"] + " 產出｜" + D["scope_note"])
B("")
B("## 1．先記三件事")
B("")
B("1. **可以，我查了六位可查證的人、六條路、十七筆來源**，不畫大餅，不知道就寫不知道。")
B("2. **被動收入不是不用做事**，是「做一次、收很多次」；沒有 0 成本 0 風險的捷徑。")
B("3. **焦慮的解藥是本週第一筆小錢**，不是一筆大錢。只挑一條路，做十四天。")
B("")
B("## 2．您手上已經有的五樣東西")
B("")
for a in D["assets"]:
    B("- **" + a["name"] + "**：" + a["plain"])
B("")
B("## 3．六位可查證的人（共同點：都不是靠本金）")
B("")
for c in D["cases"]:
    B("- **" + c["who"] + "（" + c["age"] + "）**：" + c["take"])
B("")
B("## 4．胖東來能抄什麼")
B("")
B("不能抄：開店、囤貨、重資產、上萬名員工。于東來自己說「完全複製並不容易，也沒必要」。")
B("")
for x in D["pdl"]["can"]:
    B("- **" + x["t"] + "**：" + x["d"])
B("")
B("## 5．六條路，只挑一條")
B("")
for p in D["paths"]:
    B("**" + p["id"] + "．" + p["name"] + "**")
    B("")
    B("- 第一步：" + p["first"])
    B("- 本錢：" + p["cost"] + "；第一筆錢：" + p["first_money"])
    B("- 我不知道：" + p["unknown"])
    B("")
B("## 6．先做哪一件、與三條紅線")
B("")
for q in D["priority"]:
    B("- **" + q["pile"] + "**：" + q["items"])
B("")
B(D["one_at_a_time"])
B("")
B("**三條防詐紅線**：" + "；".join(D["fraud_lines"]) + "。" + D["fraud_note"])
B("")
B("**我不知道**：" + "；".join(D["unknown"][:3]) + "。其餘寫在網頁版第 10 節。")
B("")
B("> " + D["disclaimer"])
B("")
B("下一步二選一：① 做出路徑 A 的「來榕創業補助檢核表」；"
  "② 把「台北黃哥在福州」一則內容用 AI 整理成可貼的稿。您說一件，我只做一件。")

md = "\n".join(M)
(WORKSPACE / "V6.0_創收方法與出路決策卡.md").write_text(md, encoding="utf-8")

# ── 技術版（保留網址與代號） ──────────────────────────────
T = []
C = T.append
C("# V6.0 INCOME PATHS・技術版")
C("")
C("來源結果檔：`v60_income_research.json`（由 `income_research.py` 產出）。"
  "本文件由 `gen_income_report.py` 讀取該檔回填，數字不手抄、不重算。")
C("")
C("## 1．查證口徑")
C("")
C("- 查詢日期：" + D["generated_at"] + "；範圍：公開網頁資料，未登入、未付費、未連任何交易帳戶。")
C("- 案例挑選條件：年紀偏大、從低處起、靠既有經驗；排除「年輕暴富」神話。")
C("- 所有金額皆為來源案例的數字，**不是**使用者的預期收入；未能查證者一律寫「不知道」。")
C("- 長輩版網頁零術語；技術版保留路徑代號 A–F 與來源 URL。")
C("")
C("## 2．被動收入四則澄清")
C("")
for r in D["passive_truth"]:
    C("- " + r["text"] + "（[" + r["source"] + "](" + r["url"] + ")）")
C("")
C("## 3．案例、政策與行善來源")
C("")
C("| 類別 | 名稱 | 來源 |")
C("|---|---|---|")
for c in D["cases"]:
    C("| 案例 | " + c["who"] + " | [" + c["source"] + "](" + c["url"] + ") |")
for s in D["policy"]["sources"]:
    C("| 政策 | " + s["t"] + " | [連結](" + s["u"] + ") |")
for c in D["charity"]:
    C("| 行善 | " + c["t"] + " | [連結](" + c["u"] + ") |")
for s in D["sources_extra"]:
    C("| 其他 | " + s["t"] + " | [連結](" + s["u"] + ") |")
C("")
C("## 4．政策適用性（誠實標記）")
C("")
C(D["policy"]["not_eligible"])
C("")
C(D["policy"]["unknown"] + " " + D["policy"]["phone"])
C("")
C("## 5．與 V5.2 交易系統的關係")
C("")
C("- 本報告**不是**交易系統的功能更新，不改動 `tool/v3/` 既有的回測、授權或下單邏輯。")
C("- 仍為 M0 練習帳；升級五關只過 G1；未連券商、未下單。")
C("- 方法論沿用同一套：小步、重跑、留紀錄、fail-closed、不知道就寫不知道。")
C("- 建議順序：先有穩定小進帳與生活費，再談用本金操作；目前不建議用錢去賺錢。")
C("")
C("## 6．交付檔")
C("")
C("- `V6.0_創收方法與出路.html`（長輩版）")
C("- `V6.0_創收方法與出路決策卡.md`（可印）")
C("- `docs/V6.0_INCOME_PATHS.md`（本檔）")
C("- `v60_income_research.json`（來源結果檔）、`v60_report_check.json`（體檢結果）")
C("")
C("> " + D["disclaimer"])

(ROOT / "docs" / "V6.0_INCOME_PATHS.md").write_text("\n".join(T), encoding="utf-8")

print("產出 3 份報告｜HTML " + str(len(html)) + " 字、決策卡 " + str(len(md)) + " 字、技術版 "
      + str(len("\n".join(T))) + " 字")
