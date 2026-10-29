#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
建置期脚本：抓取 FinMind 公开历史数据，生成 Flutter 应用内置的离线数据快照。
仅用于个人使用与 WorkBuddy 1024 造物挑战参赛演示。
商业化需采购 FinMind 商业授权，禁止把免费 API 用于售卖。

输出 snapshot.json：
  meta                      资料说明
  stocks[代號]               dates / closes / perSeries / dividends / quarterlyEps / industry
"""
import json, time, urllib.request, urllib.parse, os, sys, threading
from concurrent.futures import ThreadPoolExecutor

BASE = "https://api.finmindtrade.com/api/v4/data"
START = "2021-06-01"
END = "2026-10-24"

# (代號, 名稱, 產業分類)  —— 選股篩選用的樣本池
STOCKS = [
    ("2330", "台積電", "半導體"),
    ("2454", "聯發科", "半導體"),
    ("2303", "聯電", "半導體"),
    ("3711", "日月光投控", "半導體"),
    ("2308", "台達電", "電子零組件"),
    ("2317", "鴻海", "電子製造"),
    ("2357", "華碩", "電腦及週邊"),
    ("2382", "廣達", "電腦及週邊"),
    ("3231", "緯創", "電腦及週邊"),
    ("2412", "中華電", "電信"),
    ("3045", "台灣大", "電信"),
    ("4904", "遠傳", "電信"),
    ("2884", "玉山金", "金融"),
    ("2881", "富邦金", "金融"),
    ("2882", "國泰金", "金融"),
    ("2891", "中信金", "金融"),
    ("2886", "兆豐金", "金融"),
    ("2892", "第一金", "金融"),
    ("2885", "元大金", "金融"),
    ("2880", "華南金", "金融"),
    ("5871", "中租-KY", "金融"),
    ("1101", "台泥", "傳產"),
    ("1102", "亞泥", "傳產"),
    ("2002", "中鋼", "傳產"),
    ("1301", "台塑", "傳產"),
    ("1303", "南亞", "傳產"),
    ("1216", "統一", "傳產"),
    ("2912", "統一超", "傳產"),
    ("2207", "和泰車", "傳產"),
    ("6505", "台塑化", "傳產"),
    ("0050", "元大台灣50", "ETF"),
    ("0056", "元大高股息", "ETF"),
    ("00878", "國泰永續高股息", "ETF"),
]


def get(dataset, data_id, start, end=None, tries=4):
    q = {"dataset": dataset, "data_id": data_id, "start_date": start}
    if end:
        q["end_date"] = end
    url = BASE + "?" + urllib.parse.urlencode(q)
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                j = json.loads(r.read().decode("utf-8"))
            if j.get("status") == 200:
                return j.get("data", [])
            print("  ! status", j.get("status"), j.get("msg"), file=sys.stderr)
        except Exception as e:
            print("  ! err", e, file=sys.stderr)
        time.sleep(2 + i * 3)
    return []


def clean_series(dates, closes, dividends):
    """补零 + 股票分割回溯调整（比例 < 0.75 视为分割）"""
    fixed = 0
    for i in range(len(closes)):
        if closes[i] <= 0:
            closes[i] = closes[i - 1] if i > 0 else next((x for x in closes if x > 0), 1.0)
            fixed += 1
    splits = []
    for i in range(1, len(closes)):
        r = closes[i] / closes[i - 1]
        if r < 0.75:
            f = round(1 / r)
            if 2 <= f <= 10 and abs(1 / r - f) / f < 0.08:
                for j in range(i):
                    closes[j] = round(closes[j] * r, 4)
                ym = dates[i] // 100
                for rec in dividends:
                    if int(rec[0].replace('-', '')) < ym:
                        rec[1] = round(rec[1] * r, 4)
                splits.append({"date": dates[i], "factor": f})
    return fixed, splits


out = {}
_lock = threading.Lock()
_done = [0]


def fetch_stock(item):
    sid, name, industry = item
    price = get("TaiwanStockPrice", sid, START, END)
    per = get("TaiwanStockPER", sid, START, END)
    div = get("TaiwanStockDividend", sid, "2021-01-01", END)
    fin = get("TaiwanStockFinancialStatements", sid, "2021-01-01", END)
    if not price:
        with _lock:
            print(f"   !! {sid} {name} 无价格资料，跳过", flush=True)
        return sid, None

    dates, closes, volumes = [], [], []
    for row in price:
        try:
            dates.append(int(row["date"].replace("-", "")))
            closes.append(round(float(row["close"]), 2))
            volumes.append(int(float(row.get("Trading_Volume") or 0) / 1000))
        except Exception:
            pass

    per_series, seen = [], set()
    for row in per:
        ym = row["date"][:7]
        if ym in seen or row.get("PER") is None:
            continue
        seen.add(ym)
        per_series.append([
            row["date"],
            round(float(row.get("dividend_yield") or 0), 2),
            round(float(row.get("PER") or 0), 2),
            round(float(row.get("PBR") or 0), 2),
        ])

    divs = {}
    for row in div:
        cash = float(row.get("CashEarningsDistribution") or 0) + float(row.get("CashStatutorySurplus") or 0)
        if cash <= 0:
            continue
        key = row.get("CashExDividendTradingDate") or row.get("date") or ""
        if len(key) < 7:
            continue
        k = key[:7]
        divs[k] = round(divs.get(k, 0) + cash, 4)
    div_list = [[k, v] for k, v in sorted(divs.items())]

    eps_q = {}
    for row in fin:
        if row.get("type") != "EPS":
            continue
        v = row.get("value")
        if v is None:
            continue
        eps_q[row["date"][:7]] = round(float(v), 2)
    quarterly_eps = [[k, v] for k, v in sorted(eps_q.items())]

    fixed, splits = clean_series(dates, closes, div_list)
    # 分割時成交量同步放大（1 分 4 → 歷史成交量 ×4）
    for sp in splits:
        d = sp["date"]
        f = sp["factor"]
        for i, dt in enumerate(dates):
            if dt < d:
                volumes[i] = volumes[i] * f

    result = {
        "id": sid,
        "name": name,
        "industry": industry,
        "dates": dates,
        "closes": closes,
        "volumes": volumes,
        "perSeries": per_series,
        "dividends": div_list,
        "quarterlyEps": quarterly_eps,
        "latest": per_series[-1] if per_series else None,
        "cleaning": {"filled": fixed, "splits": splits},
    }
    with _lock:
        _done[0] += 1
        print(f"[{_done[0]}/{len(STOCKS)}] {sid} {name}  price {len(price)} per {len(per)} "
              f"div {len(div)} fin {len(fin)} split {len(splits)}", flush=True)
    return sid, result

print("fetch TAIEX 加權指數", flush=True)
idx_rows = get("TaiwanStockPrice", "TAIEX", START, END)
idx_dates, idx_closes, idx_vol = [], [], []
for row in idx_rows:
    try:
        idx_dates.append(int(row["date"].replace("-", "")))
        idx_closes.append(round(float(row["close"]), 2))
        idx_vol.append(int(float(row.get("Trading_Volume") or 0) / 1000))
    except Exception:
        pass
print("  TAIEX rows", len(idx_dates), flush=True)

with ThreadPoolExecutor(max_workers=5) as ex:
    for sid, res in ex.map(fetch_stock, STOCKS):
        if res is not None:
            out[sid] = res

root = {
    "meta": {
        "source": "FinMind 公開歷史資料 API v4（TaiwanStockPrice / TaiwanStockPER / TaiwanStockDividend / TaiwanStockFinancialStatements）",
        "capturedAt": "2026-10-24",
        "range": [START, "2026-10-22"],
        "universe": len(out),
        "license": "FinMind 免費非商用授權，僅限個人使用與本次 WorkBuddy 1024 造物挑戰參賽 Demo；商業化需採購 FinMind 商業授權，禁止直接將免費 API 用於售賣。",
        "cleaning": "1) 收盤價為 0 的缺值以前一交易日遞補；2) 已做股票分割回溯調整（例如 0050 於 2025-06-18 1 分 4，歷史價格與股利同步調整），未做股利還原（股利以現金另計）。",
        "disclaimer": "本資料僅供歷史回測與選股研究使用，不構成投資建議。",
    },
    "index": {
        "id": "TAIEX",
        "name": "加權指數",
        "dates": idx_dates,
        "closes": idx_closes,
        "volumes": idx_vol,
    },
    "stocks": out,
}

here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(here, "assets", "data", "snapshot.json")
os.makedirs(os.path.dirname(p), exist_ok=True)
with open(p, "w", encoding="utf-8") as f:
    json.dump(root, f, ensure_ascii=False, separators=(",", ":"))
print("written", p, os.path.getsize(p), "bytes,", len(out), "stocks")
for k, v in out.items():
    print(k, v["name"], len(v["dates"]), v["closes"][0], v["closes"][-1],
          "per", len(v["perSeries"]), "div", len(v["dividends"]),
          "epsQ", len(v["quarterlyEps"]), v["cleaning"])
