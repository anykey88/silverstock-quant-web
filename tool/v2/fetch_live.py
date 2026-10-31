#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓台股盘中即时报价，生成 assets/data/live.json。

为什么这条路走得通、而 FinMind 走不通：
  FinMind 的逐笔（TaiwanStockPriceTick）要付费等级，免费层直接 400。
  证交所 MIS（mis.twse.com.tw）是公开端点，不用 key、不限次数，
  但它**不返回 CORS 头**，浏览器 fetch 会被挡。
  所以改成：由 GitHub Actions 定时抓 → 写成同源 JSON → 前端读自己的文件。
  前端拿到的永远是静态档，不触犯跨域，也不需要任何后端。

限制（必须讲清楚，否则会误以为这是看盘软件）：
  1. Actions 的 cron 不保证准时，实测高峰可延迟 5～15 分钟。
     交易所撮合是秒级，这里最快也就是「几分钟前的价」。
  2. 免费额度：每次跑约 20～40 秒，一天 54 次约 30 分钟。
     Actions 每月免费 2000 分钟，够用但不是无限。
  3. 只抓清单里的股票，不做全市场。全市场要 1700 档，一次请求塞不下。
  4. 收盘后跑就是收盘价，不会有盘中跳动。

用法：
  python3 tool/v2/fetch_live.py                 # 抓预设清单
  python3 tool/v2/fetch_live.py --ids 2330 2317
  python3 tool/v2/fetch_live.py --source watchlist   # 读自选股清单
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SNAPSHOT = os.path.join(ROOT, "assets", "data", "snapshot.json")
PICKS = os.path.join(ROOT, "assets", "data", "daily_picks.json")
OUT = os.path.join(ROOT, "assets", "data", "live.json")

MIS = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
TPE = timezone(timedelta(hours=8))

# 一次请求最多约 30 档，超过就分批
BATCH = 25


def to_channel(sid):
    """上市 tse_、上柜 otc_。猜错也没关系，MIS 会自己忽略无效频道。"""
    return f"tse_{sid}.tw|otc_{sid}.tw"


def fetch_batch(ids):
    ch = "|".join(to_channel(s) for s in ids)
    url = f"{MIS}?ex_ch={ch}&json=1&delay=0"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; silverstock/2.2)",
            "Referer": "https://mis.twse.com.tw/stock/index.jsp",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read().decode("utf-8", "ignore")
    # MIS 有时会在 JSON 前面塞空行
    i = raw.find("{")
    if i < 0:
        return {}
    d = json.loads(raw[i:])
    out = {}
    for m in d.get("msgArray") or []:
        sid = m.get("c")
        if not sid:
            continue
        px = m.get("pz")
        # pz 为 "-" 代表这一分钟还没成交，退回昨收 z
        if px in (None, "-", ""):
            px = m.get("z")
        try:
            price = float(px)
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        try:
            prev = float(m.get("y") or 0)
        except (TypeError, ValueError):
            prev = 0
        out[sid] = {
            "name": m.get("n") or "",
            "p": round(price, 2),
            "prev": round(prev, 2),
            "open": m.get("o") or "",
            "high": m.get("h") or "",
            "low": m.get("l") or "",
            "vol": m.get("v") or "",
            "t": m.get("%") or "",          # 最后一笔成交时间
            "bid": (m.get("b") or "").split("_")[0],
            "ask": (m.get("a") or "").split("_")[0],
        }
    return out


def default_ids():
    ids = set()
    try:
        with open(SNAPSHOT, encoding="utf-8") as f:
            ids |= set(json.load(f)["stocks"].keys())
    except Exception:
        pass
    try:
        with open(PICKS, encoding="utf-8") as f:
            d = json.load(f)
        for key in ("buy", "trim", "all"):
            for row in d.get(key) or []:
                if isinstance(row, dict) and row.get("id"):
                    ids.add(str(row["id"]))
    except Exception:
        pass
    return sorted(ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", help="指定股票代号")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    ids = args.ids or default_ids()
    if not ids:
        print("没有可抓的标的", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(TPE)
    print(f"{now:%Y-%m-%d %H:%M:%S} 抓 {len(ids)} 档即时价")

    quotes = {}
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        try:
            got = fetch_batch(chunk)
            quotes.update(got)
            print(f"  [{i + len(chunk)}/{len(ids)}] +{len(got)}")
        except Exception as e:
            print(f"  ! 批次失败 {type(e).__name__}: {e}", file=sys.stderr)
        time.sleep(0.6)

    payload = {
        "asOf": now.strftime("%Y-%m-%d %H:%M:%S"),
        "session": "盤中" if (9 <= now.hour < 14) else "非交易時段",
        "data": quotes,
        "note": "證交所 MIS 即時報價，非逐筆；更新頻率受限於抓取排程。",
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"写入 {args.out}：{len(quotes)} 档")


if __name__ == "__main__":
    main()
