#!/usr/bin/env python3
# ============================================================================
# 每日掃描後，依「助手精選池」(recommendations_curated.json) 結合最新行情，
# 產出給 App 讀取的 assets/data/recommendations.json。
#
# 設計：
#   · 理由 / 類別 / 風險 / 買區減碼區（參考價位）由助手在 curated 檔維護。
#   · 現價與「狀態」每天由本腳本結合 daily_picks（最新收盤）或 snapshot 重新計算，
#     實現「保持更新」：價格跌進買區就標記「可建倉」，漲進減碼區就標記「減碼觀察」。
#   · 狀態判定以助手設定的買區／減碼區為準，不預測漲跌。
# ============================================================================
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(HERE, 'assets', 'data')


def load_json(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def snapshot_prices():
    d = load_json('snapshot.json')
    out = {}
    if not d:
        return out
    stocks = d.get('stocks', {})
    for sid, s in stocks.items():
        closes = s.get('closes', []) or []
        if not closes:
            continue
        n = min(252, len(closes))
        last = closes[-1]
        low = min(closes[-n:])
        high = max(closes[-n:])
        out[sid] = {'close': last, 'low52': low, 'high52': high}
    return out


def daily_picks_map():
    d = load_json('daily_picks.json')
    out = {}
    if not d:
        return out
    for it in (d.get('all') or []):
        out[it.get('id')] = it
    return out


def compute_status(close, buy_high, buy_low, trim_low, trim_high):
    if close <= 0:
        return '資料不足', 'unknown'
    if buy_high and close <= buy_high:
        return '可建倉', 'buy'
    if trim_low and close >= trim_low:
        return '減碼觀察', 'trim'
    return '觀察中', 'watch'


def auto_zones(sp):
    """curated 沒給區間時，從 52w 粗略推算，避免缺欄。"""
    if not sp:
        return 0, 0, 0, 0
    lo, hi = sp['low52'], sp['high52']
    if not lo or not hi or hi <= lo:
        return 0, 0, 0, 0
    buy_high = round(lo * 1.12, 2)
    buy_low = round(lo * 1.0, 2)
    trim_low = round(hi * 0.92, 2)
    trim_high = round(hi * 1.0, 2)
    return buy_low, buy_high, trim_low, trim_high


def main():
    curated = load_json('recommendations_curated.json')
    if not curated:
        print('recommendations_curated.json 不存在，跳過', file=sys.stderr)
        sys.exit(0)

    snaps = snapshot_prices()
    picks = daily_picks_map()
    today = date.today().isoformat()

    items = []
    for it in curated.get('items', []):
        sid = it.get('id', '')
        sp = snaps.get(sid)
        pk = picks.get(sid)

        # 現價：優先用每日掃描（最新收盤），否則用快照
        close = 0.0
        if pk and pk.get('close'):
            close = float(pk['close'])
        elif sp:
            close = float(sp['close'])

        buy_low = float(it.get('buyLow') or 0)
        buy_high = float(it.get('buyHigh') or 0)
        trim_low = float(it.get('trimLow') or 0)
        trim_high = float(it.get('trimHigh') or 0)
        if buy_high <= 0 or trim_low <= 0:
            a, b, c, e = auto_zones(sp)
            buy_low = buy_low or a
            buy_high = buy_high or b
            trim_low = trim_low or c
            trim_high = trim_high or e

        status, tone = compute_status(close, buy_high, buy_low, trim_low, trim_high)
        gap = 0.0
        if buy_high and close:
            gap = (close / buy_high - 1) * 100

        items.append({
            'id': sid,
            'name': it.get('name', ''),
            'industry': it.get('industry', ''),
            'category': it.get('category', ''),
            'thesis': it.get('thesis', ''),
            'risk': it.get('risk', ''),
            'riskNote': it.get('riskNote', ''),
            'note': it.get('note', ''),
            'buyLow': buy_low,
            'buyHigh': buy_high,
            'trimLow': trim_low,
            'trimHigh': trim_high,
            'close': close,
            'status': status,
            'tone': tone,
            'gapPct': round(gap, 2),
        })

    out = {
        'generated_at': today,
        'updated_at': curated.get('updated_at', today),
        'source': 'curated+ci',
        'note': curated.get('note', ''),
        'items': items,
    }

    out_path = os.path.join(DATA, 'recommendations.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'已產出 recommendations.json：{len(items)} 檔，日期 {today}')


if __name__ == '__main__':
    main()
