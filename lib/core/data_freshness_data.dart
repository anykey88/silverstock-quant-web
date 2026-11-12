// 由 tool/v3/step2_freshness.py 自動產生，請勿手改。
// 數字來源：assets/data/snapshot.json、live.json、daily_picks.json。
// V2.8：畫面只用資料自帶時間，不讀裝置時鐘，故全部是靜態常數。
class FreshnessConst {
  static const String quoteAsOf = '2026-10-22';
  static const String capturedAt = '2026-10-31';
  static const int staleThresholdDays = 3;
  static const bool deviceClockUsed = false;
  static const int nStocks = 111;
  static const int nStale = 33;
  static const int maxLagDays = 9;
  static const double medianLagDays = 1.0;
  static const double staleRatioPct = 29.7;
  static const String metaClaimedEnd = '2026-10-30';
  static const String indexActualLastDate = '2026-10-22';
  static const int nStocksAtClaimedEnd = 78;
  static const List<Map<String, String>> sources = [
  {'label': '歷史快照（111 檔個股＋大盤）', 'quoteAsOf': '2026-10-22', 'capturedAt': '2026-10-31', 'state': 'historical', 'basis': '行情日比抓檔日更早，屬歷史資料，不是現在的價格', 'lagDays': '9'},
  {'label': '即時報價檔（138 檔）', 'quoteAsOf': '2026-11-03', 'capturedAt': '2026-11-03T20:56:41', 'state': 'todayClose', 'basis': '行情日與抓檔日同一天（或隔一天補檔），屬當日收盤資料', 'lagDays': '0'},
  {'label': '每日掃描名單', 'quoteAsOf': '2026-11-03', 'capturedAt': '2026-11-03T15:19:06', 'state': 'todayClose', 'basis': '行情日與抓檔日同一天（或隔一天補檔），屬當日收盤資料', 'lagDays': '0'},
  ];
  static const List<Map<String, Object>> buckets = [
  {'label': '0–1 天', 'n': 78},
  {'label': '2–3 天', 'n': 0},
  {'label': '4–7 天', 'n': 0},
  {'label': '8–14 天', 'n': 33},
  {'label': '15 天以上', 'n': 0},
  ];
}
