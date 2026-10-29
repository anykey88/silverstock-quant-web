// ============================================================================
// 每日掃描結果（買進觀察／減碼觀察）
// ----------------------------------------------------------------------------
// 資料由 tool/v2_scan.dart 於每日收盤後產生（GitHub Actions 定時執行），
// 內容是「量化條件篩選結果」，不是投資建議。前端只負責呈現與導流。
//
// 為什麼要放在 asset 而不是即時抓：
//   1. 130 檔 × 4 個資料集要 500+ 次 API 請求，一小時額度只有 300～600 次，
//      瀏覽器端做不到，也不該讓使用者的手機去承擔。
//   2. 名單每天只變一次，重複計算沒有意義。
//   3. 放在 asset 代表開頁就有，不必等。
// ============================================================================

import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

class PickItem {
  final String id;
  final String name;
  final String industry;
  final double close;
  final double? per;
  final double? yieldPct;
  final double? perPct;
  final int? finScore;
  final double? revYoY;
  final int revStreak;
  final String stage;
  final double? ma60;
  final double? high52;
  final double? low52;
  final double turnover;
  final double buyLow;
  final double buyHigh;
  final double trimLow;
  final double trimHigh;
  final double buyScore;
  final double trimScore;
  final List<String> buyReasons;
  final List<String> trimReasons;
  final List<String> triggers;
  final List<String> gates;
  final List<String> caveats;
  final String basis; // 價格區間的推算依據
  final bool volatileEps; // 近四季 EPS 波動劇烈，區間可信度低

  const PickItem({
    required this.id,
    required this.name,
    required this.industry,
    required this.close,
    required this.per,
    required this.yieldPct,
    required this.perPct,
    required this.finScore,
    required this.revYoY,
    required this.revStreak,
    required this.stage,
    required this.ma60,
    required this.high52,
    required this.low52,
    required this.turnover,
    required this.buyLow,
    required this.buyHigh,
    required this.trimLow,
    required this.trimHigh,
    required this.buyScore,
    required this.trimScore,
    required this.buyReasons,
    required this.trimReasons,
    required this.triggers,
    required this.gates,
    required this.caveats,
    required this.basis,
    required this.volatileEps,
  });

  static double? _d(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString());
  }

  static List<String> _ls(dynamic v) =>
      ((v as List?) ?? const []).map((e) => e.toString()).toList();

  factory PickItem.fromJson(Map<String, dynamic> m) => PickItem(
        id: (m['id'] ?? '').toString(),
        name: (m['name'] ?? '').toString(),
        industry: (m['ind'] ?? '').toString(),
        close: _d(m['close']) ?? 0,
        per: _d(m['per']),
        yieldPct: _d(m['yield']),
        perPct: _d(m['perPct']),
        finScore: (m['finScore'] as num?)?.toInt(),
        revYoY: _d(m['revYoY']),
        revStreak: (m['revStreak'] as num?)?.toInt() ?? 0,
        stage: (m['stage'] ?? '').toString(),
        ma60: _d(m['ma60']),
        high52: _d(m['high52']),
        low52: _d(m['low52']),
        turnover: _d(m['turnover']) ?? 0,
        buyLow: _d(m['buyLow']) ?? 0,
        buyHigh: _d(m['buyHigh']) ?? 0,
        trimLow: _d(m['trimLow']) ?? 0,
        trimHigh: _d(m['trimHigh']) ?? 0,
        buyScore: _d(m['buyScore']) ?? 0,
        trimScore: _d(m['trimScore']) ?? 0,
        buyReasons: _ls(m['buyReasons']),
        trimReasons: _ls(m['trimReasons']),
        triggers: _ls(m['triggers']),
        gates: _ls(m['gates']),
        caveats: _ls(m['caveats']),
        basis: (m['basis'] ?? '').toString(),
        volatileEps: m['volatileEps'] == true,
      );

  /// 現價相對買區的位置
  /// -1 = 高於買區，0 = 在買區內，1 = 低於買區
  int get buyZoneState {
    if (close > buyHigh) return -1;
    if (close < buyLow) return 1;
    return 0;
  }

  String get buyZoneLabel {
    switch (buyZoneState) {
      case 0:
        return '已進入買區';
      case 1:
        return '低於買區';
      default:
        return '高於買區';
    }
  }

  /// 距買區上緣還差幾 %
  double? get gapToBuyZone {
    if (buyHigh <= 0 || close <= 0) return null;
    if (buyZoneState == 0) return 0;
    return (close / buyHigh - 1) * 100;
  }
}

class ExcludedItem {
  final String id;
  final String name;
  final String reason;
  const ExcludedItem(this.id, this.name, this.reason);
}

class DailyPicks {
  final String generatedAt;
  final String tradeDate;
  final int universe;
  final int analyzed;
  final Map<String, String> method;
  final List<PickItem> buy;
  final List<PickItem> trim;
  final List<PickItem> all;
  final List<ExcludedItem> excluded;

  const DailyPicks({
    required this.generatedAt,
    required this.tradeDate,
    required this.universe,
    required this.analyzed,
    required this.method,
    required this.buy,
    required this.trim,
    required this.all,
    required this.excluded,
  });

  static DailyPicks? _cache;
  static bool _tried = false;

  /// 載入每日名單。沒有檔案或格式錯誤時回傳 null（前端顯示「尚未產生」）。
  static Future<DailyPicks?> load() async {
    if (_cache != null) return _cache;
    if (_tried) return _cache;
    _tried = true;
    try {
      final raw = await rootBundle.loadString('assets/data/daily_picks.json');
      final m = jsonDecode(raw) as Map<String, dynamic>;
      List<PickItem> parse(String key) => ((m[key] as List?) ?? const [])
          .map((e) => PickItem.fromJson((e as Map).cast<String, dynamic>()))
          .toList();
      final meth = (m['method'] as Map?)?.cast<String, dynamic>() ?? {};
      _cache = DailyPicks(
        generatedAt: (m['generated_at'] ?? '').toString(),
        tradeDate: (m['trade_date'] ?? '').toString(),
        universe: (m['universe'] as num?)?.toInt() ?? 0,
        analyzed: (m['analyzed'] as num?)?.toInt() ?? 0,
        method: meth.map((k, v) => MapEntry(k, v.toString())),
        buy: parse('buy'),
        trim: parse('trim'),
        all: parse('all'),
        excluded: ((m['excluded'] as List?) ?? const [])
            .map((e) => ExcludedItem(
                  (e as Map)['id'].toString(),
                  (e['name'] ?? '').toString(),
                  (e['reason'] ?? '').toString(),
                ))
            .toList(),
      );
      return _cache;
    } catch (_) {
      return null;
    }
  }

  bool get isEmpty => buy.isEmpty && trim.isEmpty;

  PickItem? byId(String id) {
    for (final p in all) {
      if (p.id == id) return p;
    }
    return null;
  }
}
