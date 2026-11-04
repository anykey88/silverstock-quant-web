#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""產出 assets/data/family_lists.json（家族三份清單）。

設計：
  · 名單成員（誰在媽媽／爸爸／建議清單）由 tool/v2/family_lists_src.json 維護，
    助手改名單只改這個檔，不碰程式。
  · 現價／漲跌每天由證交所 MIS 公開端點抓取（不用 key、不限次數），
    與 fetch_live.py 同一條路；抓不到時退回 src 裡記錄的收盤價，不會開天窗。
  · 殖利率／本益比／股淨比變動慢，沿用 src 記錄值；若 daily_picks.json 有同檔
    則優先採用掃描結果（更新鮮）。

用法：
  python3 tool/v2/build_family_lists.py
  python3 tool/v2/build_family_lists.py --no-fetch     # 只重整、不連網
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "assets", "data")
SRC = os.path.join(ROOT, "tool", "v2", "family_lists_src.json")
OUT = os.path.join(DATA, "family_lists.json")

MIS = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
BATCH = 25


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def to_channel(sid):
    return f"tse_{sid}.tw|otc_{sid}.tw"


def fetch_batch(ids):
    ch = "|".join(to_channel(s) for s in ids)
    url = f"{MIS}?ex_ch={ch}&json=1&delay=0"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; silverstock/2.6)",
            "Referer": "https://mis.twse.com.tw/stock/index.jsp",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read().decode("utf-8", "ignore")
    i = raw.find("{")
    if i < 0:
        return {}
    d = json.loads(raw[i:])
    out = {}
    for m in d.get("msgArray") or []:
        sid = (m.get("c") or "").strip()
        if not sid:
            continue
        px = m.get("z")
        if px in (None, "-", ""):
            px = m.get("pz")
        try:
            price = float(px)
        except (TypeError, ValueError):
            continue
        try:
            prev = float(m.get("y"))
        except (TypeError, ValueError):
            prev = 0.0
        out[sid] = {"close": price, "prev": prev}
    return out


def fetch_all(ids):
    got = {}
    ids = sorted(set(ids))
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        try:
            got.update(fetch_batch(chunk))
        except Exception as e:  # noqa: BLE001
            print(f"[warn] 批次 {chunk[0]}… 抓取失敗：{e}", file=sys.stderr)
    return got


def picks_map():
    d = load_json(os.path.join(DATA, "daily_picks.json")) or {}
    out = {}
    for it in (d.get("all") or []):
        out[it.get("id")] = it
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true", help="不連網，只用 src 記錄值")
    args = ap.parse_args()

    src = load_json(SRC)
    if not src:
        print("family_lists_src.json 不存在，跳過", file=sys.stderr)
        sys.exit(0)

    all_ids = []
    for L in src.get("lists", []):
        for it in L.get("items", []):
            all_ids.append(it["id"])

    quotes = {} if args.no_fetch else fetch_all(all_ids)
    picks = picks_map()
    today = date.today().isoformat()

    lists_out = []
    for L in src.get("lists", []):
        items = []
        for it in L.get("items", []):
            sid = it["id"]
            q = quotes.get(sid)
            pk = picks.get(sid)

            # 現價只用「當日 MIS 成交價」；沒開盤／抓不到就沿用清單記錄值，
            # 避免不同日期的價格混在一起（曾出現 close 與 change 對不上的情況）。
            close = it.get("close")
            prev = None
            if q:
                close = q["close"]
                prev = q["prev"] or None
            if prev is None and it.get("change") is not None and close is not None:
                prev = close - float(it["change"])

            change = None
            pct = None
            if close is not None and prev:
                change = round(close - prev, 2)
                pct = round((close / prev - 1) * 100, 2)
            elif it.get("change") is not None:
                change = it.get("change")
                pct = it.get("pct")

            yield_v = it.get("yield")
            pe_v = it.get("pe")
            pb_v = it.get("pb")
            if pk:
                yield_v = pk.get("yield", yield_v)
                pe_v = pk.get("pe", pe_v)
                pb_v = pk.get("pb", pb_v)

            row = {
                "id": sid,
                "name": it.get("name", ""),
                "industry": it.get("industry", ""),
                "category": it.get("category", ""),
                "group": it.get("group", ""),
                "close": close,
                "change": change,
                "pct": pct,
                "yield": yield_v,
                "pe": pe_v,
                "pb": pb_v,
                "live": bool(q),
            }
            if it.get("status") is not None:
                row["status"] = it.get("status", "")
            items.append(row)

        lists_out.append({
            "key": L.get("key", ""),
            "title": L.get("title", ""),
            "subtitle": L.get("subtitle", ""),
            "note": L.get("note", ""),
            "items": items,
        })

    out = {
        "generated_at": today,
        "updated_at": src.get("updated_at", today),
        "source": "src+mis",
        "note": src.get("note", ""),
        "lists": lists_out,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    total = sum(len(L["items"]) for L in lists_out)
    live = sum(1 for L in lists_out for it in L["items"] if it.get("live"))
    print(f"已產出 family_lists.json：{len(lists_out)} 份清單／{total} 檔，"
          f"即時報價 {live} 檔，日期 {today}")


if __name__ == "__main__":
    main()
