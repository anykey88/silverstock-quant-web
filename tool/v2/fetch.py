#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SilverStock v2 — 個股全維度資料抓取（FinMind 公開 API）

用法：
    python3 tool/v2/fetch.py 2330
    python3 tool/v2/fetch.py 2330 --out tool/v2/data

輸出：單一 JSON，含 9 個資料集，供 Dart 計算層讀取（不依賴 dart:html）。
注意：免費額度 300 次/小時（匿名）、600 次/小時（註冊）。本腳本一次約 9 個請求。
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

API = "https://api.finmindtrade.com/api/v4/data"

# 每個資料集抓多久（年）
LOOKBACK = {
    "TaiwanStockPrice": 6,
    "TaiwanStockPER": 6,
    "TaiwanStockDividend": 12,
    "TaiwanStockFinancialStatements": 6,
    "TaiwanStockBalanceSheet": 6,
    "TaiwanStockCashFlowsStatement": 6,
    "TaiwanStockMonthRevenue": 7,
    "TaiwanStockInstitutionalInvestorsBuySell": 2,
}


def fetch(dataset, stock_id, start_date, token=None, retries=3):
    params = {"dataset": dataset, "data_id": stock_id, "start_date": start_date}
    if token:
        params["token"] = token
    url = API + "?" + urllib.parse.urlencode(params)

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SilverStock/2.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.loads(r.read().decode("utf-8"))
            if payload.get("status") != 200:
                raise RuntimeError(f"{dataset}: {payload.get('msg')}")
            return payload.get("data", [])
        except Exception as e:
            if attempt == retries - 1:
                print(f"  ! {dataset} 失敗: {e}", file=sys.stderr)
                return []
            time.sleep(2 * (attempt + 1))
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stock_id")
    ap.add_argument("--out", default="tool/v2/data")
    ap.add_argument("--token", default=os.environ.get("FINMIND_TOKEN"))
    args = ap.parse_args()

    sid = args.stock_id.strip()
    today = date.today()

    print(f"[1/2] 抓取 {sid} 基本資料")
    info = fetch("TaiwanStockInfo", sid, "1970-01-01", args.token)
    info = [r for r in info if r.get("stock_id") == sid]

    print(f"[2/2] 抓取 {sid} 九个資料集")
    data = {}
    for ds, years in LOOKBACK.items():
        start = (today - timedelta(days=365 * years + 30)).isoformat()
        rows = fetch(ds, sid, start, args.token)
        data[ds] = rows
        print(f"  - {ds:44s} {len(rows):6d} 筆")

    bundle = {
        "stock_id": sid,
        "fetched_at": today.isoformat(),
        "info": info[0] if info else {},
        "datasets": data,
        "meta": {
            "source": "FinMind 公開 API v4",
            "license": "Free 方案，僅限非商業使用；商業化須採購 FinMind 商業授權",
            "lookback_years": LOOKBACK,
        },
    }

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{sid}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, separators=(",", ":"))

    size = os.path.getsize(path)
    print(f"\n寫入 {path}  ({size/1024:.0f} KB)")
    print(f"公司：{bundle['info'].get('stock_name','?')} / {bundle['info'].get('industry_category','?')}")


if __name__ == "__main__":
    main()
