#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓台股融资融券余额，生成前端用的 assets/data/margin.json。

为什么单独一支脚本：
  融资融券是「筹码面」资料，跟 v2 扫描用的价格／财报是两套节奏。
  它更新频率固定（每日收盘后），不需要参与每日选股扫描，
  但个股档案页要能马上看到 —— 所以独立抓、独立存。

用法：
  python3 tool/v2/build_margin.py                 # 抓快照里的 33 档
  python3 tool/v2/build_margin.py --days 400      # 抓更长的历史
  python3 tool/v2/build_margin.py --ids 2330 2317 # 只抓指定几档
"""

import argparse
import json
import os
import sys
import time
from datetime import date, timedelta

import urllib.request

API = "https://api.finmindtrade.com/api/v4/data"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SNAPSHOT = os.path.join(ROOT, "assets", "data", "snapshot.json")
OUT = os.path.join(ROOT, "assets", "data", "margin.json")

# 融资成数：上市 60%、上柜 50%。这里无法从 FinMind 直接取得上市别，
# 统一以 60% 计算「最乐观的追缴价」，并在前端注明上柜股会再低。
FINANCE_RATIO = 0.60


def fetch(sid, start, token=None, retry=3):
    url = f"{API}?dataset=TaiwanStockMarginPurchaseShortSale&data_id={sid}&start_date={start}"
    if token:
        url += f"&token={token}"
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "silverstock/2.2"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode("utf-8"))
            if d.get("status") != 200:
                if i == retry - 1:
                    print(f"  ! {sid} {d.get('msg')}", file=sys.stderr)
                    return []
                time.sleep(2)
                continue
            return d.get("data") or []
        except Exception as e:
            if i == retry - 1:
                print(f"  ! {sid} {type(e).__name__}", file=sys.stderr)
                return []
            time.sleep(2)
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=250, help="回溯天数（默认 250，约一年）")
    ap.add_argument("--ids", nargs="*", help="指定股票代号，不给就抓快照里的全部")
    ap.add_argument("--delay", type=float, default=0.3, help="每档间隔秒数")
    args = ap.parse_args()

    if args.ids:
        ids = args.ids
    else:
        with open(SNAPSHOT, encoding="utf-8") as f:
            snap = json.load(f)
        ids = sorted(snap["stocks"].keys())

    start = (date.today() - timedelta(days=args.days)).isoformat()
    token = os.environ.get("FINMIND_TOKEN")
    print(f"抓取 {len(ids)} 档，起日 {start}")

    out = {}
    for n, sid in enumerate(ids, 1):
        rows = fetch(sid, start, token)
        if not rows:
            continue
        series = []
        for r in rows:
            series.append({
                "d": r["date"],
                "mb": r.get("MarginPurchaseTodayBalance") or 0,   # 融资今日余额（张）
                "sb": r.get("ShortSaleTodayBalance") or 0,       # 融券今日余额（张）
                "ml": r.get("MarginPurchaseLimit") or 0,         # 融资限额（张）
                "sl": r.get("ShortSaleLimit") or 0,             # 融券限额（张）
            })
        out[sid] = series
        print(f"  [{n}/{len(ids)}] {sid} {len(series)} 笔", flush=True)
        time.sleep(args.delay)

    payload = {
        "generatedAt": date.today().isoformat(),
        "financeRatio": FINANCE_RATIO,
        "note": "融资成数以 60% 计（上市）；上柜股多為 50%，追缴价会再低一些。",
        "data": out,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    size = os.path.getsize(OUT) / 1024
    print(f"\n写入 {OUT}（{len(out)} 档，{size:.0f} KB）")


if __name__ == "__main__":
    main()
