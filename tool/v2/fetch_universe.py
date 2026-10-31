#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v2.4 候選池擴充：把 tool/v2/universe.json（約111檔）中「尚未在 snapshot 的檔」抓取並合併。
只抓 3 個接口（Price/PER/Dividend），滿足防禦逆向收息策略所需欄位：
  價格序列、殖利率、PER、PBR、連續配息記錄、產業分類。
免費匿名額度 300/h；本腳本約 78 檔 × 3 = 234 次，含限流容錯。
"""
import json, time, os, sys, threading
from concurrent.futures import ThreadPoolExecutor
import urllib.request, urllib.parse

BASE = "https://api.finmindtrade.com/api/v4/data"
START = "2021-06-01"
END = "2026-10-31"

here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
uni = json.load(open(os.path.join(here, "tool/v2/universe.json"), encoding="utf-8"))
STOCKS = [(s["id"], s["name"], s["industry"]) for s in uni["universe"]]

snap = json.load(open(os.path.join(here, "assets/data/snapshot.json"), encoding="utf-8"))
existing = set(snap["stocks"].keys())
print("现有", len(existing), " | 目标", len(STOCKS), " | 待抓新增", len([s for s in STOCKS if s[0] not in existing]), flush=True)


def get(dataset, data_id, start, end=None, tries=5):
    q = {"dataset": dataset, "data_id": data_id, "start_date": start}
    if end:
        q["end_date"] = end
    url = BASE + "?" + urllib.parse.urlencode(q)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SilverStock/2.4"})
            with urllib.request.urlopen(req, timeout=90) as r:
                j = json.loads(r.read().decode("utf-8"))
            if j.get("status") == 200:
                return j.get("data", [])
            msg = str(j.get("msg", ""))
            if "rate" in msg.lower() or j.get("status") == 429:
                print("  ! 限流, sleep 60s 重試", file=sys.stderr)
                time.sleep(60)
                continue
            print("  ! status", j.get("status"), msg, file=sys.stderr)
        except Exception as e:
            print("  ! err", e, file=sys.stderr)
        time.sleep(3 + i * 3)
    return []


def clean_series(dates, closes, dividends):
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
new_items = [s for s in STOCKS if s[0] not in existing]
total_new = len(new_items)


def fetch_stock(item):
    sid, name, industry = item
    if sid in existing:
        return sid, None
    price = get("TaiwanStockPrice", sid, START, END)
    per = get("TaiwanStockPER", sid, START, END)
    div = get("TaiwanStockDividend", sid, "2021-01-01", END)
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

    fixed, splits = clean_series(dates, closes, div_list)
    for sp in splits:
        d, f = sp["date"], sp["factor"]
        for i, dt in enumerate(dates):
            if dt < d:
                volumes[i] = volumes[i] * f

    result = {
        "id": sid, "name": name, "industry": industry,
        "dates": dates, "closes": closes, "volumes": volumes,
        "perSeries": per_series, "dividends": div_list, "quarterlyEps": [],
        "latest": per_series[-1] if per_series else None,
        "cleaning": {"filled": fixed, "splits": splits},
    }
    with _lock:
        _done[0] += 1
        print(f"[{_done[0]}/{total_new}] {sid} {name} price {len(price)} per {len(per)} "
              f"div {len(div)} split {len(splits)}", flush=True)
    return sid, result


with ThreadPoolExecutor(max_workers=4) as ex:
    for sid, res in ex.map(fetch_stock, new_items):
        if res is not None:
            out[sid] = res

merged = dict(snap["stocks"])
merged.update(out)
# 用 universe 的 industry 統一覆蓋所有檔（含 existing 33 檔），確保標籤一致，
# 否則防禦預設的「排除半導體/電子零組件」會漏掉舊檔的「電子製造/電腦及週邊」。
uni_map = {s["id"]: s["industry"] for s in uni["universe"]}
for sid in merged:
    if sid in uni_map:
        merged[sid]["industry"] = uni_map[sid]
snap["stocks"] = merged
snap["meta"]["universe"] = len(merged)
snap["meta"]["capturedAt"] = "2026-10-31"
snap["meta"]["range"] = [START, "2026-10-30"]
p = os.path.join(here, "assets/data/snapshot.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump(snap, f, ensure_ascii=False, separators=(",", ":"))
print("written", p, "| 合并後", len(merged), "檔 (本次新增", len(out), ")", flush=True)
for k, v in out.items():
    print(k, v["name"], "收盤", v["closes"][-1], "殖利率",
          (v["perSeries"][-1][1] if v["perSeries"] else None),
          "配息年數", len(set(d[0][:4] for d in v["dividends"])), flush=True)
