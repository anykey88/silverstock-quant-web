# -*- coding: utf-8 -*-
"""V4.2 報告生成器：淺底、大字、大白話。所有數字由 v42_self_improve.json 讀取。"""
import json
import os
from html import escape

PROJ = "/workspace/silverstock_quant_web"
D = json.load(open(os.path.join(PROJ, "v42_self_improve.json"), encoding="utf-8"))
OUT = "/workspace/V4.2_系统会自己进步.html"

# 結果檔裡少數殘留簡體字，統一成給長輩看的繁體（全部單字符鍵）
S2T = str.maketrans({
    "凑": "湊", "补": "補", "档": "檔", "买": "買", "卖": "賣",
    "减": "減", "码": "碼", "摊": "攤", "亏": "虧", "杆": "桿",
    "线": "線", "冲": "沖", "个": "個", "关": "關", "后": "後",
    "么": "麼", "为": "為", "从": "從", "这": "這", "还": "還",
    "来": "來", "对": "對", "时": "時", "间": "間", "开": "開",
    "门": "門", "问": "問", "题": "題", "让": "讓", "记": "記",
    "错": "錯", "变": "變", "动": "動", "会": "會", "运": "運",
    "转": "轉", "进": "進", "过": "過", "应": "應", "该": "該",
    "条": "條", "种": "種", "组": "組", "统": "統", "结": "結",
    "论": "論", "证": "證", "验": "驗", "测": "測", "试": "試",
    "实": "實", "际": "際", "场": "場", "盘": "盤", "单": "單",
    "张": "張", "亿": "億", "万": "萬", "钱": "錢", "价": "價",
    "费": "費", "税": "稅", "标": "標", "确": "確", "认": "認",
    "识": "識", "别": "別", "类": "類", "态": "態", "状": "狀",
    "卫": "衛", "层": "層", "长": "長", "辈": "輩", "岁": "歲",
    "体": "體", "检": "檢", "压": "壓", "帐": "帳", "账": "帳",
    "签": "簽", "额": "額", "断": "斷", "续": "續", "优": "優",
    "级": "級", "纪": "紀", "赚": "賺", "赔": "賠", "损": "損",
    "仓": "倉", "择": "擇", "选": "選", "数": "數", "据": "據",
    "涨": "漲", "网": "網", "当": "當",
})


# 長輩看不懂的術語，一律換成生活說法
TERM_REPL = [
    ("FeeConfig.for_symbol()", "讓程式自動判斷"),
    ("Calmar", "「風險換報酬」的分數"),
    ("MDD", "最深跌幅"),
    ("MA120", "半年線"),
    ("MA20", "月線"),
    ("樣本外", "換沒看過的資料再考一次"),
    ("樣本內", "舊資料"),
    ("3 折", "分三次"),
    ("最大回撤", "最深跌幅"),
    ("單因子對照", "一次只改一處的對照"),
    ("pp", "個百分點"),
    ("RSI", "一個冷熱指標"),
]


def plain_terms(s):
    s = str(s)
    for a, b in TERM_REPL:
        s = s.replace(a, b)
    return s


def zh(s):
    if not isinstance(s, str):
        return s
    return s.translate(S2T)


def e(s):
    return escape(zh(str(s)), quote=False)


def ep(s):
    """先換白話、再轉繁體、再跳脫。"""
    return escape(zh(plain_terms(s)), quote=False)


P = []
def add(x):
    P.append(x)


CSS = """
:root{--ink:#1c2733;--sub:#4b5a68;--line:#d9d2c2;--paper:#f8f5ec;
      --gold:#a8791f;--goldbg:#fff5d9;--green:#1f6b45;--greenbg:#e6f3ea;
      --red:#a12c2c;--redbg:#fbe9e7;--amber:#8a5a08;--amberbg:#fdf0d5;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
     font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei","Heiti TC",sans-serif;
     font-size:19px;line-height:1.95;-webkit-font-smoothing:antialiased}
.wrap{max-width:960px;margin:0 auto;padding:44px 34px 90px}
header{border-bottom:3px solid var(--ink);padding-bottom:26px;margin-bottom:34px}
.kicker{font-size:15px;letter-spacing:2px;color:var(--gold);font-weight:700}
h1{font-size:52px;line-height:1.2;margin:10px 0 6px;letter-spacing:1px}
.lead{font-size:27px;font-weight:700;margin:0 0 18px;color:var(--ink)}
.meta{font-size:15px;color:var(--sub)}
h2{font-size:31px;margin:56px 0 16px;padding-bottom:10px;border-bottom:2px solid var(--line);
   display:flex;align-items:center;gap:14px}
h2 .no{background:var(--ink);color:#fff;width:42px;height:42px;border-radius:50%;
       display:inline-flex;align-items:center;justify-content:center;font-size:21px;flex:none}
h3{font-size:23px;margin:30px 0 10px}
p{margin:12px 0}
.one{background:var(--goldbg);border-left:8px solid var(--gold);padding:20px 24px;
     font-size:25px;font-weight:700;line-height:1.7;margin:20px 0 26px;border-radius:0 8px 8px 0}
.small{font-size:16px;color:var(--sub)}
.kpis{display:flex;gap:14px;flex-wrap:wrap;margin:22px 0}
.kpi{flex:1;min-width:170px;background:#fff;border:2px solid var(--line);border-radius:10px;
     padding:16px 18px;text-align:center}
.kpi .n{font-size:40px;font-weight:800;color:var(--gold);line-height:1.2}
.kpi .l{font-size:16px;color:var(--sub);margin-top:4px}
table{width:100%;border-collapse:collapse;margin:18px 0;font-size:17px;background:#fff}
th,td{border:1px solid var(--line);padding:12px 14px;text-align:left;vertical-align:top}
th{background:#efe9d9;font-weight:700}
td b{color:var(--gold)}
.pair{display:grid;grid-template-columns:1fr 1.35fr;gap:0;border:1px solid var(--line);
      border-radius:8px;overflow:hidden;margin:10px 0;background:#fff}
.pair>div{padding:12px 16px}
.pair .h{background:#fdf1ef;color:var(--red);font-weight:700;border-right:1px solid var(--line)}
.pair .s{color:var(--green);font-weight:600}
.pair .pm{grid-column:1/-1;background:#f4f1e7;font-size:16px;color:var(--sub);
          border-top:1px solid var(--line);padding:7px 16px}
.story{background:#fff;border:2px solid var(--line);border-radius:10px;padding:20px 24px;margin:18px 0}
.story .t{font-size:23px;font-weight:800;color:var(--gold);margin-bottom:6px}
.story .big{font-size:27px;font-weight:800;margin:10px 0}
.story .les{background:var(--greenbg);color:var(--green);padding:10px 16px;
            border-radius:6px;font-weight:700;margin-top:12px}
.warn{background:var(--amberbg);border-left:7px solid var(--amber);padding:16px 20px;
      margin:18px 0;border-radius:0 8px 8px 0}
.badge{display:inline-block;padding:3px 12px;border-radius:20px;font-size:15px;
       font-weight:700;white-space:nowrap}
.b-green{background:var(--greenbg);color:var(--green)}
.b-amber{background:var(--amberbg);color:var(--amber)}
.b-red{background:var(--redbg);color:var(--red)}
.rule{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px 18px;margin:10px 0}
.rule .rn{font-size:20px;font-weight:700}
.rule .rp{color:var(--sub);font-size:17px;margin-top:3px}
.rule .re{font-size:16px;color:var(--gold);margin-top:6px}
.gates{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}
.gate{flex:1;min-width:220px;background:#fff;border:2px solid var(--ink);border-radius:10px;padding:16px}
.gate .g{font-size:15px;color:var(--gold);font-weight:800;letter-spacing:1px}
.gate .gn{font-size:22px;font-weight:800;margin:4px 0}
.steps{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0}
.step{flex:1;min-width:135px;background:#fff;border:2px solid var(--line);border-radius:10px;
      padding:14px 12px;text-align:center}
.step .sn{background:var(--ink);color:#fff;width:34px;height:34px;border-radius:50%;
          display:inline-flex;align-items:center;justify-content:center;font-weight:800}
.step .stt{font-size:21px;font-weight:800;margin:6px 0}
.step .sp{font-size:15px;color:var(--sub);line-height:1.6}
.onepager{background:#fff;border:3px solid var(--ink);border-radius:6px;
          padding:34px 38px;margin:24px 0;font-size:22px;line-height:2.0}
.onepager h2{border:none;font-size:30px;margin:0 0 14px;padding:0}
.onepager .big3{font-size:26px;font-weight:800;margin:16px 0 8px}
.onepager .foot{font-size:17px;color:var(--sub);border-top:1px dashed var(--line);
                margin-top:22px;padding-top:14px}
footer{margin-top:60px;border-top:2px solid var(--line);padding-top:18px;
       font-size:15px;color:var(--sub)}
@media print{body{background:#fff}.wrap{padding:0}h2{page-break-after:avoid}
             .story,.rule,.onepager{page-break-inside:avoid}}
@media(max-width:700px){.wrap{padding:22px 16px}h1{font-size:38px}
   .pair{grid-template-columns:1fr}.pair .h{border-right:none;border-bottom:1px solid var(--line)}
   .lead,.one{font-size:22px}table{font-size:15px}}
"""


def kpi(items):
    add('<div class="kpis">')
    for n, l in items:
        add(f'<div class="kpi"><div class="n">{e(n)}</div><div class="l">{e(l)}</div></div>')
    add("</div>")


def build():
    ERR = D["error_ledger"]
    REC = D["reconcile"]
    GAPS = D["gaps"]
    GR = D["grading"]
    LP = D["loop"]
    FF, PF, SS = LP["fee_fix"], LP["patch_fix"], LP["sensitivity"]
    DM = D["discipline_map"]
    BD = D["boundaries"]
    MT = D["maintenance"]
    CF = D["conflicts"]
    SR = D["speak_rules"]
    VH = D["version_history"]

    add("<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'>")
    add("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    add("<title>V4.2 系統會自己進步</title>")
    add(f"<style>{CSS}</style></head><body><div class='wrap'>")

    add("<header>")
    add("<div class='kicker'>給家人看的版本 · 第 4.2 版 · 模擬盤</div>")
    add("<h1>系統會自己進步</h1>")
    add("<p class='lead'>您不用管住自己，讓規矩管住錢。</p>")
    add("<div class='one'>人會累、會怕、會貪，機器不會。<br>所以不要靠意志力，要靠一張寫死的規矩。</div>")
    add(f"<p class='small'>資料：{e(GAPS['n_stocks'])} 檔台股、{e(GAPS['n_bars'])} 根日線（含息、含手續費與稅）。"
        f"這一版刻意改成<b>淺底、大字、短句</b>，就是要讓長輩看得舒服。"
        f"現況仍是 M0 模擬盤，沒有連富邦、沒有下過任何一張單。</p>")
    add("</header>")

    # ── 1
    add("<h2><span class='no'>1</span>一句話講明白</h2>")
    add("<div class='one'>不是讓電腦變聰明，是讓電腦變誠實。</div>")
    add("<p>您說自律不夠，這不是缺點，是<b>人之常情</b>。所以方法不能放在腦子裡，要放在程式裡："
        "該賣就賣、該停就停，不用您當下點頭。下面八件事，左邊是人常犯的，右邊是系統替您擋住的。</p>")
    for m in DM:
        add("<div class='pair'>")
        add(f"<div class='h'>人：{e(m['human'])}</div>")
        add(f"<div class='s'>系統：{ep(m['system'])}<br><span class='small'>{ep(m['number'])}</span></div>")
        add(f"<div class='pm'>{e(m['plain'])}</div></div>")
    add("<p class='small'>白話說：<b>手會抖，規矩不會。</b>把紀律交出去，人只要每個月看一眼就好。</p>")

    # ── 2
    add("<h2><span class='no'>2</span>系統學的是什麼？先講清楚</h2>")
    add("<div class='one'>它學的不是「明天會漲還是跌」，<br>是「我哪裡算錯了、下次不要再錯」。</div>")
    add("<p>這句很重要，因為「找到最佳方法」這句話要改一下：<b>最佳不是賺最多，是換一張沒看過的考卷還站得住</b>。"
        "我們曾經一次試了 7 套方法，換到新資料考，"
        f"<b>{e(GR['claims'][4]['evidence']['beat_zero_n'])}／{e(GR['claims'][4]['evidence']['n_strategies'])}</b> 套跑贏「買著不要動」。"
        "所以系統不追最會賺的，只留最不會害人的。</p>")
    add("<table><tr><th>系統做得到</th><th>系統做不到</th><th>白話</th></tr>")
    for b in BD:
        add(f"<tr><td>{e(b['can'])}</td><td>{e(b['cannot'])}</td><td><b>{e(b['plain'])}</b></td></tr>")
    add("</table>")

    add("<h3>前後講的話好像不一樣？其實是比的東西不同</h3>")
    add("<p>長輩最容易在這裡被搞混。系統會把前提補回來，不會硬說自己前後都對：</p>")
    for c in CF:
        add("<div class='rule'>")
        add(f"<div class='rn'>A 說：{ep(c['a'])}　／　B 說：{ep(c['b'])}</div>")
        add(f"<div class='rp'>{ep(c['why'])}</div>")
        add(f"<div class='re'>白話：{e(c['plain'])}</div></div>")

    # ── 3
    add("<h2><span class='no'>3</span>三個真的發生過的故事</h2>")
    add("<p>下面不是舉例，是這六版裡<b>真的算錯、真的改掉</b>的事。每一個都有數字。</p>")

    add("<div class='story'>")
    add("<div class='t'>故事一：一支股票的「身分」填錯了</div>")
    add(f"<p>把 0050 當成一般個股課 3‰ 交易稅，其實 ETF 只要 1‰。以 {int(FF['amount_ntd']):,} 元買賣一次來回：</p>")
    add(f"<div class='big'>{e(FF['wrong_cost_ntd'])} 元 → {e(FF['right_cost_ntd'])} 元，差 {e(FF['diff_ntd'])} 元</div>")
    add(f"<p class='small'>改對之後，全部對照表的數字都要重算一次。</p>")
    add(f"<div class='les'>白話：{e(FF['plain'])}</div></div>")

    add("<div class='story'>")
    add("<div class='t'>故事二：賺一點就全部賣掉，後面整段沒吃到</div>")
    add(f"<div class='big'>設價全賣 {e(PF['before_pct'])}%　｜　放著不動 {e(PF['buyhold_pct'])}%　｜　改過後 {e(PF['after_pct'])}%</div>")
    add(f"<p>補上規矩之後救回 <b>{e(PF['recovered_pp'])} 個百分點</b>，"
        f"還是落後放著不動 {e(PF['still_behind_pp'])} 個百分點——"
        "但跌得淺很多，睡得安穩。升級不是換一套新方法，是補一個漏洞。</p>")
    add(f"<div class='warn'><b>要誠實說：</b>{ep(PF['caveat'])}<br>{e(PF['plain'])}</div>")
    add(f"<div class='les'>白話：賣掉之後如果又往上走，就買回一點，不要賭氣不回頭。</div></div>")

    add("<div class='story'>")
    add("<div class='t'>故事三：以為找到最強的參數</div>")
    add(f"<p>只把「幾天檢查一次」從 {e(SS['best_days'])} 天改成 {e(SS['worst_days'])} 天，其他都沒動：</p>")
    add(f"<div class='big'>分數 {e(SS['best_calmar'])} → {e(SS['worst_calmar'])}，掉了 {e(SS['drop'])}</div>")
    add("<p class='small'>（這個分數叫「風險換報酬」：賺多少、除以最多賠多少，越高越划算。）</p>")
    add(f"<div class='les'>白話：{e(SS['plain'])}</div></div>")

    # ── 4
    add("<h2><span class='no'>4</span>錯題本：它不擦掉自己犯的錯</h2>")
    add("<div class='one'>人會忘，檔案不會。<br>每一次算錯都留下來，下版再驗一次。</div>")
    kpi([(len(ERR), "記下來的錯"),
         (f"{REC['total_pct_consistent_n']}/{REC['total_pct_checked_n']}", "數字重算對得上"),
         (GAPS["n_missing"], "還缺資料的項目"),
         (REC["max_mdd_gap_pp"], "新抓到的誤差（百分點）")])
    add(f"<p>這 {len(ERR)} 筆不是別人挑出來的，絕大部分是<b>系統自己把數字重算一遍對不上</b>才抓到的。分類如下：</p>")
    kinds = D["error_kind_counts"]
    mx = max(kinds.values())
    for k, v in sorted(kinds.items(), key=lambda x: -x[1]):
        w = int(v / mx * 100)
        add(f"<div style='margin:6px 0;font-size:17px'><b>{e(k)}類 {v} 筆</b>"
            f"<div style='background:#efe9d9;height:14px;border-radius:7px;margin-top:3px'>"
            f"<div style='background:#a8791f;width:{w}%;height:14px;border-radius:7px'></div></div></div>")

    add("<h3>挑六筆最生活化的</h3>")
    picks = [0, 3, 8, 12, 17, 20]
    for i in picks:
        x = ERR[i]
        add("<div class='rule'>")
        add(f"<div class='rn'>{e(x['ver'])}｜{e(x['what'])}</div>")
        add(f"<div class='rp'>怎麼發現：{e(x['found'])}　→　改成：{ep(x['fix'])}</div>")
        add(f"<div class='re'>白話：{e(x['plain'])}</div></div>")

    add(f"<div class='warn'><b>這一版自己又抓到兩個新問題：</b><br>"
        f"① {ep(REC['new_finding'])}——{e(REC['new_finding_plain'])}"
        f"（平均差 {e(REC['avg_mdd_gap_pp'])} 個百分點）。<br>"
        f"② 上一版說「只加一句」，其實一次改了三處（{ep(ERR[19]['what'])}）。<br>"
        f"這就是「持續找問題」的意思：<b>連自己上一版講過的話也要拿來對帳</b>。</div>")

    # ── 5
    add("<h2><span class='no'>5</span>三道安檢門：一條規矩要過關才能寫進去</h2>")
    add("<div class='one'>想改方法可以，<br>但要留下「改前、改後」，還要過三關。</div>")
    add("<div class='gates'>")
    for g in GR["gates"]:
        add(f"<div class='gate'><div class='g'>{e(g['id'])}</div><div class='gn'>{e(g['name'])}</div>"
            f"<p class='small'>{e(g['plain'])}</p><p class='small' style='color:#a12c2c'>"
            f"{e(g['fail_plain'])}</p></div>")
    add("</div>")
    add("<p>把目前所有規矩逐條拿去過關，結果是這樣：</p>")
    EV = {
        "calmar": ("風險換報酬", ""), "mdd_pct": ("最深跌", "%"),
        "ann_pct": ("每年平均", "%"), "allin_calmar": ("梭哈評分", ""),
        "allin_mdd_pct": ("梭哈最深跌", "%"), "n_configs": ("比過幾種配置", " 種"),
        "in_sample_calmar": ("舊資料評分", ""),
        "out_sample_calmar": ("新資料評分", ""),
        "out_sample_vs_bh_pp": ("跟放著不動的差額", "pp"),
        "sensitivity_spread": ("改參數的落差", ""),
        "n_strategies": ("一共試了", " 套"), "beat_zero_n": ("跑贏的只有", " 套"),
        "buy_hold_mean": ("買著不動平均", "%"), "static_pct": ("全賣不回補", "%"),
        "max_excess_pct": ("超額（最好一組）", "%"),
        "min_excess_pct": ("超額（最差一組）", "%"),
        "n_buckets": ("分了", " 組"), "top_lever_loss_pct": ("高點 2 倍、30 天", "%"),
        "n_rules": ("比過幾條規則", " 條"), "combo_pct": ("改過後", "%"),
    }
    for c in GR["claims"]:
        v = c["verdict"]
        cls = "b-green" if v.startswith("可進") else ("b-amber" if "觀察" in v else "b-red")
        ev = c["evidence"]
        bits = []
        for k, (lab, unit) in EV.items():
            val = ev.get(k)
            if val is None:
                continue
            bits.append(f"{lab}：{val}" if isinstance(val, str) else f"{lab} {val}{unit}")
        if ev.get("caveat"):
            bits.append("提醒：" + str(ev["caveat"]))
        add("<div class='rule'>")
        add(f"<div class='rn'><span class='badge {cls}'>{e(v)}</span>　{ep(c['rule'])}"
            f"<span class='small'>（{e(c['version'])}）</span></div>")
        add(f"<div class='rp'>{e(c['plain'])}</div>")
        add(f"<div class='re'>為什麼：{ep(c['reason'])}</div>")
        if bits:
            add(f"<div class='small'>數字：{ep('、'.join(bits))}</div>")
        add("</div>")
    vc = GR["verdict_counts"]
    vc_text = "、".join("{} {} 條".format(k, v) for k, v in vc.items())
    add(f"<p class='small'>合計：{e(vc_text)}。"
        "<b>被判「不准用」的不是沒用，是還不夠可靠</b>——先放著觀察，不寫進自動交易。</p>")

    # ── 6
    add("<h2><span class='no'>6</span>升級怎麼走：六步，一次只改一處</h2>")
    add("<div class='one'>改太快，錯了都不知道錯在哪。<br>所以一次只動一個地方。</div>")
    add("<div class='steps'>")
    for s in LP["steps"]:
        add(f"<div class='step'><div class='sn'>{s['step']}</div>"
            f"<div class='stt'>{e(s['name'])}</div><div class='sp'>{e(s['plain'])}</div></div>")
    add("</div>")
    add("<div class='warn'><b>上一版自己就犯了第 3 步。</b>"
        f"{ep(PF['caveat'])}<br>所以下一版要做的不是再加新功能，"
        "是<b>把三處拆開、一次只改一處，慢慢看究竟是誰有功勞</b>。</div>")

    # ── 7
    add("<h2><span class='no'>7</span>靠日曆，不靠意志力</h2>")
    add("<div class='one'>沒自律的人最需要的不是決心，<br>是固定時間自動跑的檢查。</div>")
    add("<table><tr><th>什麼時候</th><th>做什麼</th><th>白話</th></tr>")
    for m in MT:
        add(f"<tr><td><b>{e(m['when'])}</b></td><td>{ep(m['what'])}"
            f"<br><span class='small'>{e(m['who'])}</span></td><td>{e(m['plain'])}</td></tr>")
    add("</table>")
    add("<p class='small'>注意「每次想改方法」那一列：<b>系統會跑、會算、會記，但最後要人簽名才算數</b>。"
        "這道門不改，系統再聰明也不會自己把權限放寬。</p>")

    add("<h3>這一路是怎麼走過來的</h3>")
    add("<table><tr><th>版本</th><th>做了什麼</th><th>學到一句話</th></tr>")
    for v in VH:
        add(f"<tr><td><b>{e(v['ver'])}</b></td><td>{ep(v['did'])}</td><td>{ep(v['learned'])}</td></tr>")
    add("</table>")
    add("<p class='small'>每一版都站在上一版的錯上面，不是重新發明一套。</p>")

    # ── 8 一頁紙
    add("<h2><span class='no'>8</span>給爸媽的一頁紙（可列印）</h2>")
    add("<div class='onepager'>")
    add("<h2>只要記三件事</h2>")
    add("<div class='big3'>一、錢分四桶放，不要一次全買。</div>")
    add("<p>現金、高股息、大盤指數、少許個股，各放各的。行情再好也不梭哈。</p>")
    add("<div class='big3'>二、跌了不要全部賣掉，也不要加碼攤平。</div>")
    add("<p>賺了先拿一點回來放口袋；賣掉後如果又漲，買回一點就好。不貪、不怕。</p>")
    add("<div class='big3'>三、系統會替我們記帳、對帳、改錯。</div>")
    add("<p>算錯它會自己抓出來，改了會留下改前改後。我們不用盯盤，每個月看一眼就夠。</p>")
    add("<div class='warn' style='font-size:20px'><b>還有一句最重要的：</b>"
        "資料不夠的事，系統會老實說「不知道」，不會亂猜。它不會算命，也不會保證賺錢。</div>")
    add("<div class='foot'>現況：模擬練習，還沒有用真錢下單。　"
        "要真的開始，得先由本人簽授權、決定能賠多少，這一步系統不會替我們做。</div>")
    add("</div>")

    # ── 9
    add("<h2><span class='no'>9</span>往後說話的規矩，還有這次哪裡可能錯</h2>")
    add("<h3>往後每一版都照這八條寫</h3>")
    add("<table><tr><th>#</th><th>規矩</th><th>白話</th></tr>")
    for r in SR:
        add(f"<tr><td><b>{r['no']}</b></td><td>{e(r['rule'])}</td><td>{e(r['plain'])}</td></tr>")
    add("</table>")

    add("<h3>這次哪裡可能錯（先自首，別等人來抓）</h3>")
    limits = [
        "資料只有一段罕見的大多頭，<b>空頭看得不夠</b>；所有「不要賣」的規矩都被高估了。",
        f"有 {GAPS['n_missing']} 項資料沒有（當日開高低、真實換手率、籌碼、國際股市、總經、債券黃金…），"
        "這些問題現在<b>不能回答</b>，系統直接說不知道。",
        f"圖上每 7 日取一個點，會漏掉最深的那天，跌幅平均被低估 {REC['avg_mdd_gap_pp']} 個百分點、"
        f"最多 {REC['max_mdd_gap_pp']} 個百分點。",
        "升級版一次改了三處，還沒拆開一處一處驗，所以不能說是哪一條有效。",
        "「可靠度分級」的三道閘是我們自己訂的標準，不是市場給的保證。",
        "全部是模擬盤，沒有連富邦、沒有下一張單；系統會犯錯，只是它會把錯記下來。",
    ]
    for x in limits:
        add(f"<p>· {zh(x)}</p>")

    add("<footer>")
    add("V4.2｜家人自用、模擬盤 M0｜所有數字由 v42_self_improve.json 程式回填，不憑印象手寫。<br>")
    add("引擎 tool/v3/self_improve.py　·　報告 gen_self_improve_report.py　·　結果 v42_self_improve.json<br>")
    add(f"產生時間 {e(D['meta']['generated_at'])}　·　{D['meta']['scope']}")
    add("</footer>")

    add("</div></body></html>")

    html = "".join(P)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("寫出", OUT, len(html), "chars")


if __name__ == "__main__":
    build()
