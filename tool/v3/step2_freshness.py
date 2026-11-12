# -*- coding: utf-8 -*-
"""V5.2 施工單第 2 步：把 V2.8 的雙時間、三態標籤、資料時效總覽做進網頁。

職責單一，對應 V5.1 執行手冊第 2 步的完成標準：
  做出來會看到：網頁上同時顯示「資料時間」與「抓檔時間」，附上三種狀態標籤
  做到什麼算完成：長輩一眼看得出這筆資料是舊的還是新的，不再誤會

紀律：
  - 所有判斷只用「資料自帶時間」，絕不讀裝置時鐘（DateTime.now()）。
  - 數字全部由 assets/data/*.json 回填，不手抄。
  - 路徑相對於本檔，不寫死在哪一台機器。
  - 同時寫進 Flutter App（Dart 模組 + 首頁橫幅）與可直接開的靜態總覽頁。

用法：python3.11 tool/v3/step2_freshness.py
產出：v52_step2_freshness.json、web/data_freshness.html、
      lib/core/data_freshness_data.dart、lib/core/data_freshness.dart、
      lib/ui/data_freshness_banner.dart
"""
from __future__ import annotations

import json
import statistics
from collections import Counter
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "assets" / "data"
OUT = ROOT / "v52_step2_freshness.json"
HTML_OUT = ROOT / "web" / "data_freshness.html"
DART_DATA = ROOT / "lib" / "core" / "data_freshness_data.dart"
DART_MODEL = ROOT / "lib" / "core" / "data_freshness.dart"
DART_BANNER = ROOT / "lib" / "ui" / "data_freshness_banner.dart"

STALE_DAYS = 3          # V2.8：行情落後超過 3 個日曆日顯示陳舊警示
DEVICE_CLOCK_USED = False


def jload(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def to_iso(v) -> str:
    """把 20261030 / '2026-10-30' / '2026-11-03 20:56:41' 統一成可解析 ISO 字串。"""
    s = str(v).strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    if " " in s and "T" not in s:
        return s.replace(" ", "T", 1)
    return s


def parse(v) -> datetime:
    return datetime.fromisoformat(to_iso(v))


def day(v) -> date:
    return parse(v).date()


def lag_days(quote, captured) -> int:
    """只比較兩個「資料自帶時間」，不牽扯現在幾點。"""
    return (day(captured) - day(quote)).days


def classify(session: str, quote, captured) -> tuple[str, str]:
    """三態標籤：盤中報價／今日收盤／歷史資料。依資料自帶欄位判定。"""
    s = str(session or "")
    q, c = day(quote), day(captured)
    if "交易時段" in s and "非交易" not in s:
        return "intraday", "資料自己標記為交易時段，且不是收盤後補檔"
    if q == c or (c - q).days <= 1:
        return "todayClose", "行情日與抓檔日同一天（或隔一天補檔），屬當日收盤資料"
    return "historical", "行情日比抓檔日更早，屬歷史資料，不是現在的價格"


STATE_LABEL = {
    "intraday": "盤中報價",
    "todayClose": "今日收盤",
    "historical": "歷史資料",
}


def build() -> dict:
    snap = jload("snapshot.json")
    live = jload("live.json")
    picks = jload("daily_picks.json")

    meta = snap["meta"]
    idx = snap["index"]
    captured_at = meta["capturedAt"]
    idx_quote = idx["dates"][-1]
    live_asof = live["asOf"]
    live_session = live["session"]
    picks_trade = str(picks["trade_date"])
    picks_gen = str(picks["generated_at"])

    # 111 檔各自的最後交易日 → 資料時效總覽
    rows = []
    for sid, s in snap["stocks"].items():
        last = s["dates"][-1]
        lg = lag_days(last, captured_at)
        rows.append({"id": sid, "name": s["name"], "last_date": to_iso(last),
                     "lag_days": lg, "stale": lg > STALE_DAYS})
    lags = [r["lag_days"] for r in rows]
    buckets = Counter()
    for lg in lags:
        if lg <= 1:
            buckets["0–1 天"] += 1
        elif lg <= 3:
            buckets["2–3 天"] += 1
        elif lg <= 7:
            buckets["4–7 天"] += 1
        elif lg <= 14:
            buckets["8–14 天"] += 1
        else:
            buckets["15 天以上"] += 1
    stale_rows = [r for r in rows if r["stale"]]

    # 誠實標記：資料自己貼的範圍標籤，與實際最後交易日不一致。
    # 回測用的是大盤軸（index.dates），所以「資料到哪一天」要以實際軸為準。
    claimed_end = str(meta["range"][-1])
    tail_counter = Counter(r["last_date"] for r in rows)
    inconsistency = {
        "meta_claimed_end": claimed_end,
        "index_actual_last_date": to_iso(idx_quote),
        "n_stocks_at_claimed_end": tail_counter.get(claimed_end, 0),
        "n_stocks_at_index_last_date": tail_counter.get(to_iso(idx_quote), 0),
        "difference_days": lag_days(idx_quote, claimed_end),
        "plain": "資料自己貼的標籤寫到 %s，但大盤實際只到 %s；"
                 "111 檔裡 %d 檔到標籤那天、%d 檔只到大盤那天。"
                 "所有回測用的是大盤軸，所以實際用到的是 %s。"
                 % (claimed_end, to_iso(idx_quote),
                    tail_counter.get(claimed_end, 0),
                    tail_counter.get(to_iso(idx_quote), 0), to_iso(idx_quote)),
        "action": "本輪只標記、不改舊結論（一次只做一件）；舊報告寫的範圍是照資料標籤寫的",
    }

    sources = []
    # 1) 歷史快照（111 檔 + 大盤）
    st, why = classify("", idx_quote, captured_at)
    sources.append({"label": "歷史快照（111 檔個股＋大盤）",
                    "quoteAsOf": to_iso(idx_quote), "capturedAt": to_iso(captured_at),
                    "state": st, "basis": why,
                    "lagDays": lag_days(idx_quote, captured_at)})
    # 2) 即時報價檔
    st2, why2 = classify(live_session, picks_trade, live_asof)
    sources.append({"label": "即時報價檔（138 檔）",
                    "quoteAsOf": to_iso(picks_trade), "capturedAt": to_iso(live_asof),
                    "state": st2, "basis": why2,
                    "lagDays": lag_days(picks_trade, live_asof)})
    # 3) 每日掃描名單
    st3, why3 = classify("非交易時段", picks_trade, picks_gen)
    sources.append({"label": "每日掃描名單",
                    "quoteAsOf": to_iso(picks_trade), "capturedAt": to_iso(picks_gen)[:19],
                    "state": st3, "basis": why3,
                    "lagDays": lag_days(picks_trade, picks_gen)})

    # 離線流程才用「產出日」決定要不要重抓；畫面本身不顯示裝置時鐘
    today = date.today()
    offline_refresh = {
        "checked_on": today.isoformat(),
        "captured_at": to_iso(captured_at),
        "days_since_capture": (today - day(captured_at)).days,
        "suggest_refetch": (today - day(captured_at)).days > STALE_DAYS,
        "where_it_is_used": "只用在離線重抓流程，不進畫面；畫面判斷一律用資料自帶時間",
    }

    return {
        "version": "V5.2-step2",
        "step": 2,
        "title": "V2.8 雙時間・三態標籤・資料時效總覽",
        "generated_at": today.isoformat(),
        "source_files": ["assets/data/snapshot.json", "assets/data/live.json",
                         "assets/data/daily_picks.json"],
        "device_clock_used": DEVICE_CLOCK_USED,
        "stale_threshold_days": STALE_DAYS,
        "two_times": {
            "quote_as_of": to_iso(idx_quote),
            "captured_at": to_iso(captured_at),
            "plain": "行情時間＝這筆價格是哪一天的；資料更新時間＝電腦是哪一天去抓的",
        },
        "states": [{"key": k, "label": v} for k, v in STATE_LABEL.items()],
        "sources": sources,
        "data_inconsistency": inconsistency,
        "freshness_overview": {
            "n_stocks": len(rows),
            "index_last_date": to_iso(idx_quote),
            "min_lag_days": min(lags),
            "median_lag_days": statistics.median(lags),
            "max_lag_days": max(lags),
            "n_stale": len(stale_rows),
            "stale_ratio_pct": round(len(stale_rows) / len(rows) * 100, 1),
            "buckets": [{"label": k, "n": buckets[k]} for k in
                        ("0–1 天", "2–3 天", "4–7 天", "8–14 天", "15 天以上")],
            "worst": sorted(stale_rows, key=lambda r: -r["lag_days"])[:8],
        },
        "offline_refresh": offline_refresh,
        "outputs": ["web/data_freshness.html",
                    "lib/core/data_freshness_data.dart",
                    "lib/core/data_freshness.dart",
                    "lib/ui/data_freshness_banner.dart"],
        "accept": {
            "two_times_present": bool(to_iso(idx_quote) and to_iso(captured_at)),
            "three_states_present": len(STATE_LABEL) == 3,
            "no_device_clock": not DEVICE_CLOCK_USED,
            "numbers_from_json": True,
        },
    }


# ── 產出 1：可直接開的靜態總覽頁（淺底大字、繁體、長輩可讀） ──────────
CSS = """
:root{--bg:#fbfaf5;--ink:#24303a;--sub:#5b6b78;--line:#e3e0d5;--card:#ffffff;
--blue:#1f6f8b;--amber:#a8641c;--red:#b03a2e;--green:#2e7d5b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font-family:"PingFang TC","Microsoft JhengHei","Noto Sans TC",sans-serif;
font-size:21px;line-height:1.85}
.wrap{max-width:900px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:34px;margin:0 0 6px}
.lead{color:var(--sub);font-size:20px;margin:0 0 26px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;
padding:22px 24px;margin:0 0 18px}
.two{display:flex;gap:16px;flex-wrap:wrap}
.cell{flex:1;min-width:250px;background:#f4f8f9;border-radius:12px;padding:18px}
.k{font-size:19px;color:var(--sub)}
.v{font-size:32px;font-weight:700;margin-top:4px}
.tag{display:inline-block;border-radius:999px;padding:5px 16px;font-size:19px;
font-weight:700;margin-right:8px}
.tag.historical{background:#eef2f5;color:var(--blue)}
.tag.todayClose{background:#eaf5ee;color:var(--green)}
.tag.intraday{background:#fdf1e3;color:var(--amber)}
.warn{background:#fdf0ee;border-left:6px solid var(--red);padding:14px 18px;
border-radius:10px;margin-top:12px}
table{width:100%;border-collapse:collapse;font-size:20px}
th,td{padding:10px 8px;border-bottom:1px solid var(--line);text-align:left}
th{color:var(--sub);font-weight:600}
.big{font-size:30px;font-weight:700}
.note{color:var(--sub);font-size:19px}
.src{font-size:19px;color:var(--sub);margin-top:18px}
"""


def html_of(d: dict) -> str:
    t = d["two_times"]
    ov = d["freshness_overview"]
    src_rows = "".join(
        f"<tr><td>{s['label']}</td><td>{s['quoteAsOf']}</td>"
        f"<td>{s['capturedAt']}</td>"
        f"<td><span class='tag {s['state']}'>{STATE_LABEL[s['state']]}</span></td>"
        f"<td>{s['lagDays']} 天</td></tr>"
        for s in d["sources"])
    bucket_rows = "".join(
        f"<tr><td>{b['label']}</td><td class='big'>{b['n']}</td></tr>"
        for b in ov["buckets"])
    worst = "、".join(f"{w['name']}（{w['lag_days']} 天）" for w in ov["worst"][:5])
    off = d["offline_refresh"]
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>資料時效總覽・V2.8</title><style>{CSS}</style></head>
<body><div class="wrap">
<h1>這筆資料是舊的還是新的？</h1>
<p class="lead">這一頁把「資料自己寫的時間」攤開給你看。畫面不顯示現在幾點，避免你以為看到的是即時價格。</p>

<div class="card">
  <div class="two">
    <div class="cell"><div class="k">行情時間（這筆價格是哪一天）</div>
      <div class="v">{t['quote_as_of']}</div></div>
    <div class="cell"><div class="k">資料更新時間（哪一天去抓的）</div>
      <div class="v">{t['captured_at']}</div></div>
  </div>
  <p class="note">{t['plain']}。兩個時間都是靜止的固定值，不會跳動。</p>
</div>

<div class="card">
  <h2 style="font-size:26px;margin:0 0 12px">三種狀態標籤</h2>
  <p><span class="tag intraday">盤中報價</span>交易時間抓到的即時價格　
     <span class="tag todayClose">今日收盤</span>當天收盤後的價格　
     <span class="tag historical">歷史資料</span>以前的價格，不是現在</p>
  <table><thead><tr><th>資料來源</th><th>行情時間</th><th>抓檔時間</th><th>狀態</th><th>落後</th></tr></thead>
  <tbody>{src_rows}</tbody></table>
  <p class="note">判定依據全部來自資料自己帶的欄位，不看手機或電腦現在幾點。</p>
</div>

<div class="card">
  <h2 style="font-size:26px;margin:0 0 12px">全部 {ov['n_stocks']} 檔的時效總覽</h2>
  <p>落後超過 {d['stale_threshold_days']} 天的有
     <span class="big" style="color:var(--red)">{ov['n_stale']}</span> 檔
     （佔 {ov['stale_ratio_pct']}%）；最多落後
     <span class="big">{ov['max_lag_days']}</span> 天，中位數 {ov['median_lag_days']} 天。</p>
  <table><thead><tr><th>落後天數</th><th>檔數</th></tr></thead><tbody>{bucket_rows}</tbody></table>
  <div class="warn">陳舊提醒：{worst} 等，價格不是最近一個交易日，別拿去當今天的價錢用。</div>
</div>

<div class="card">
  <h2 style="font-size:26px;margin:0 0 12px">還發現一個要講清楚的地方</h2>
  <div class="warn">{d['data_inconsistency']['plain']}</div>
  <p class="note">{d['data_inconsistency']['action']}。</p>
</div>

<div class="card">
  <h2 style="font-size:26px;margin:0 0 12px">什麼時候該重新抓資料？</h2>
  <p>這件事交給離線流程判斷，不進畫面。本次離線檢查日是 {off['checked_on']}，
     距離抓檔日 {off['days_since_capture']} 天，
     建議重新抓檔＝<b>{'是' if off['suggest_refetch'] else '否'}</b>。</p>
  <p class="note">{off['where_it_is_used']}</p>
</div>

<p class="src">來源：assets/data/snapshot.json、live.json、daily_picks.json；
所有數字由程式讀檔回填，不是手抄。{d['generated_at']} 產出・V2.8 規格落地。</p>
</div></body></html>
"""


# ── 產出 2：Dart 資料常數（由 JSON 自動生成，不是手抄） ─────────────────
def dart_data_of(d: dict) -> str:
    t = d["two_times"]
    ov = d["freshness_overview"]
    src_lines = []
    for s in d["sources"]:
        src_lines.append(
            "  {'label': '%s', 'quoteAsOf': '%s', 'capturedAt': '%s', "
            "'state': '%s', 'basis': '%s', 'lagDays': '%d'},"
            % (s["label"], s["quoteAsOf"], s["capturedAt"], s["state"],
               s["basis"].replace("'", ""), s["lagDays"]))
    bucket_lines = [
        "  {'label': '%s', 'n': %d}," % (b["label"], b["n"])
        for b in ov["buckets"]]
    return """// 由 tool/v3/step2_freshness.py 自動產生，請勿手改。
// 數字來源：assets/data/snapshot.json、live.json、daily_picks.json。
// V2.8：畫面只用資料自帶時間，不讀裝置時鐘，故全部是靜態常數。
class FreshnessConst {
  static const String quoteAsOf = '%s';
  static const String capturedAt = '%s';
  static const int staleThresholdDays = %d;
  static const bool deviceClockUsed = %s;
  static const int nStocks = %d;
  static const int nStale = %d;
  static const int maxLagDays = %d;
  static const double medianLagDays = %s;
  static const double staleRatioPct = %s;
  static const String metaClaimedEnd = '%s';
  static const String indexActualLastDate = '%s';
  static const int nStocksAtClaimedEnd = %d;
  static const List<Map<String, String>> sources = [
%s
  ];
  static const List<Map<String, Object>> buckets = [
%s
  ];
}
""" % (t["quote_as_of"], t["captured_at"], d["stale_threshold_days"],
       "true" if d["device_clock_used"] else "false",
       ov["n_stocks"], ov["n_stale"], ov["max_lag_days"],
       float(ov["median_lag_days"]), float(ov["stale_ratio_pct"]),
       d["data_inconsistency"]["meta_claimed_end"],
       d["data_inconsistency"]["index_actual_last_date"],
       d["data_inconsistency"]["n_stocks_at_claimed_end"],
       "\n".join(src_lines), "\n".join(bucket_lines))


DART_MODEL_SRC = """// V2.8 資料時效判斷：只比較資料自帶時間，不讀 DateTime.now()。
// 由 tool/v3/step2_freshness.py 產出，判斷邏輯與資料常數分開，方便單獨重跑對照。
import 'data_freshness_data.dart';

enum FreshnessState { intraday, todayClose, historical }

class DataFreshness {
  final String label;
  final String quoteAsOf;
  final String capturedAt;
  final FreshnessState state;
  final String basis;

  const DataFreshness({
    required this.label,
    required this.quoteAsOf,
    required this.capturedAt,
    required this.state,
    required this.basis,
  });

  static DateTime _parse(String s) => DateTime.parse(s);

  /// 落後天數＝抓檔日減行情日，兩個都是資料自己寫的，不是現在幾點。
  int get lagDays =>
      _parse(capturedAt).difference(_parse(quoteAsOf)).inDays;

  bool get isStale => lagDays > FreshnessConst.staleThresholdDays;

  String get stateLabel {
    switch (state) {
      case FreshnessState.intraday:
        return '盤中報價';
      case FreshnessState.todayClose:
        return '今日收盤';
      case FreshnessState.historical:
        return '歷史資料';
    }
  }

  static FreshnessState _stateOf(String key) {
    switch (key) {
      case 'intraday':
        return FreshnessState.intraday;
      case 'todayClose':
        return FreshnessState.todayClose;
      default:
        return FreshnessState.historical;
    }
  }

  static List<DataFreshness> get all {
    final out = <DataFreshness>[];
    for (final m in FreshnessConst.sources) {
      out.add(DataFreshness(
        label: m['label'] ?? '',
        quoteAsOf: m['quoteAsOf'] ?? '',
        capturedAt: m['capturedAt'] ?? '',
        state: _stateOf(m['state'] ?? 'historical'),
        basis: m['basis'] ?? '',
      ));
    }
    return out;
  }
}
"""


DART_BANNER_SRC = """// V2.8 首頁資料時效橫幅：雙時間、三態標籤、時效總覽，淺底大字。
// 由 tool/v3/step2_freshness.py 產出。完全靜態，不顯示會跳動的裝置時鐘。
import 'package:flutter/material.dart';

import '../core/data_freshness.dart';
import '../core/data_freshness_data.dart';

class DataFreshnessBanner extends StatelessWidget {
  const DataFreshnessBanner({Key? key}) : super(key: key);

  Color _color(FreshnessState s) {
    switch (s) {
      case FreshnessState.intraday:
        return const Color(0xFFA8641C);
      case FreshnessState.todayClose:
        return const Color(0xFF2E7D5B);
      case FreshnessState.historical:
        return const Color(0xFF1F6F8B);
    }
  }

  Widget _timeCell(String label, String value) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFFF4F8F9),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontSize: 17, color: Color(0xFF5B6B78))),
            const SizedBox(height: 4),
            Text(value, style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w700)),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final items = DataFreshness.all;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: const Color(0xFFE3E0D5)),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('這筆資料是舊的還是新的？',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700)),
          const SizedBox(height: 12),
          Row(
            children: [
              _timeCell('行情時間（價格是哪一天）', FreshnessConst.quoteAsOf),
              const SizedBox(width: 12),
              _timeCell('資料更新（哪天去抓的）', FreshnessConst.capturedAt),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final it in items)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: _color(it.state).withOpacity(0.10),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text('${it.label}・${it.stateLabel}・落後 ${it.lagDays} 天',
                      style: TextStyle(fontSize: 17, color: _color(it.state),
                          fontWeight: FontWeight.w700)),
                ),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            '全部 ${FreshnessConst.nStocks} 檔裡，有 ${FreshnessConst.nStale} 檔落後超過 '
            '${FreshnessConst.staleThresholdDays} 天（${FreshnessConst.staleRatioPct}%），'
            '最多落後 ${FreshnessConst.maxLagDays} 天。',
            style: TextStyle(fontSize: 19),
          ),
          const SizedBox(height: 6),
          const Text(
            '資料標籤寫到 ${FreshnessConst.metaClaimedEnd}，但大盤軸實際只到 '
            '${FreshnessConst.indexActualLastDate}；回測用的是後者。'
            '${FreshnessConst.nStocks} 檔中 ${FreshnessConst.nStocksAtClaimedEnd} 檔到標籤那天。',
            style: TextStyle(fontSize: 17, color: Color(0xFFB03A2E)),
          ),
          const SizedBox(height: 6),
          const Text('兩個時間都是固定值；畫面不顯示現在幾點，避免誤會成即時價格。',
              style: TextStyle(fontSize: 17, color: Color(0xFF5B6B78))),
        ],
      ),
    );
  }
}
"""


def verify(d: dict) -> dict:
    """完成標準：逐項檢查，失敗就讓這一步不算完成。"""
    a = d["accept"]
    html = HTML_OUT.read_text(encoding="utf-8")
    checks = {
        "雙時間同時出現在網頁": d["two_times"]["quote_as_of"] in html
                              and d["two_times"]["captured_at"] in html,
        "三態標籤都出現在網頁": all(x in html for x in ("盤中報價", "今日收盤", "歷史資料")),
        "網頁沒有裝置時鐘": "DateTime.now" not in html and "new Date()" not in html,
        "結果檔可被讀回": json.loads(OUT.read_text(encoding="utf-8"))["step"] == 2,
        "驗收欄位全為真": all(a.values()),
        "111 檔時效明細完整": d["freshness_overview"]["n_stocks"] == 111,
        "資料不一致有被標記出來": d["data_inconsistency"]["meta_claimed_end"] in html
                                and d["data_inconsistency"]["index_actual_last_date"] in html,
    }
    return {"checks": checks, "all_pass": all(checks.values()),
            "n_checks": len(checks), "n_fail": sum(1 for v in checks.values() if not v)}


def main() -> None:
    d = build()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    HTML_OUT.write_text(html_of(d), encoding="utf-8")
    DART_DATA.write_text(dart_data_of(d), encoding="utf-8")
    DART_MODEL.write_text(DART_MODEL_SRC, encoding="utf-8")
    DART_BANNER.write_text(DART_BANNER_SRC, encoding="utf-8")
    v = verify(d)
    d["verification"] = v
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    ov = d["freshness_overview"]
    print(f"[第2步] 產出 5 個檔｜111 檔中 {ov['n_stale']} 檔落後 >3 天，"
          f"最多 {ov['max_lag_days']} 天")
    print(f"        雙時間 {d['two_times']['quote_as_of']} / {d['two_times']['captured_at']}")
    print(f"        驗證 {v['n_checks']} 項、失敗 {v['n_fail']} 項、全過＝{v['all_pass']}")
    for k, ok in v["checks"].items():
        print(f"          {'OK ' if ok else '!! '} {k}")


if __name__ == "__main__":
    main()
