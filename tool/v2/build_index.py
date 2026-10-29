#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SilverStock v2 — 建立全市場代號／名稱索引

用途：讓前端可以「輸入名稱的任何片段」就找到股票代號，不必先知道代號。
輸出：assets/data/stock_index.json

兩個設計重點：

1. 格式壓縮（陣列而非物件）。3000+ 筆資料，欄位名重複 3000 次沒有意義。
2. 同時存繁體名、簡體名，以及一張「繁→簡」字元對照表。
   使用者在中國大陸常用簡體輸入法打「台积电」，但台股官方名稱是「台積電」。
   前端拿這張表把查詢字串正規化成簡體，再與簡體名比對，兩個方向都通。
"""

import json
import os
import sys
import urllib.request
from datetime import date

API = "https://api.finmindtrade.com/api/v4/data"
OUT = "assets/data/stock_index.json"

# 興櫃（emerging）流動性差、無漲跌幅限制，保留供查詢但不列入每日候選池
KEEP = {"twse", "tpex", "emerging"}


def fetch_info(token=None):
    params = "?dataset=TaiwanStockInfo"
    if token:
        params += f"&token={token}"
    req = urllib.request.Request(API + params, headers={"User-Agent": "SilverStock/2.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode("utf-8"))
    if payload.get("status") != 200:
        raise RuntimeError(payload.get("msg"))
    return payload["data"]


def main():
    try:
        from opencc import OpenCC
        cc = OpenCC("t2s")
    except ImportError:
        print("需要 opencc：pip install opencc-python-reimplemented", file=sys.stderr)
        sys.exit(1)

    token = os.environ.get("FINMIND_TOKEN")
    print("[1/4] 抓取 TaiwanStockInfo")
    rows = fetch_info(token)
    print(f"      原始 {len(rows)} 筆")

    print("[2/4] 去重（同代號取最新一筆）")
    latest = {}
    for r in rows:
        sid = (r.get("stock_id") or "").strip()
        if not sid or r.get("type") not in KEEP:
            continue
        d = r.get("date") or ""
        if sid not in latest or d > latest[sid]["date"]:
            latest[sid] = r
    print(f"      去重後 {len(latest)} 檔")

    print("[3/4] 產生簡體名與繁簡對照表")
    out_rows = []
    char_map = {}
    for sid, r in sorted(latest.items()):
        trad = (r.get("stock_name") or "").strip()
        simp = cc.convert(trad)
        # 逐字比對，記錄差異（只收繁→簡方向）
        if len(trad) == len(simp):
            for a, b in zip(trad, simp):
                if a != b:
                    char_map[a] = b
        out_rows.append([
            sid,
            trad,
            (r.get("industry_category") or "").strip(),
            r.get("type"),
            simp,
        ])
    print(f"      對照表 {len(char_map)} 個字")

    bundle = {
        "v": date.today().isoformat(),
        "cols": ["id", "name", "ind", "mkt", "sname"],
        "rows": out_rows,
        # 繁→簡 單字對照，前端用來把查詢正規化
        "t2s": char_map,
        "note": "資料來源 FinMind 公開 API；僅供個人研究，商業使用須取得授權。",
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, separators=(",", ":"))

    size = os.path.getsize(OUT)
    print(f"[4/4] 寫入 {OUT}  ({size/1024:.0f} KB, {len(out_rows)} 檔)")


if __name__ == "__main__":
    main()
