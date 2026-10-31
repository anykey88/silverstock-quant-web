/// 融資融券資料的讀取端
// ---------------------------------------------------------------------------
/// 資料由 `tool/v2/build_margin.py` 在離線抓取後寫成 `assets/data/margin.json`。
/// 前端只讀，不再打 API —— 個股檔案頁一打開就要有東西，不能等網路。

import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

import '../v2/margin.dart';

class MarginStore {
  MarginStore._();
  static final MarginStore instance = MarginStore._();

  Map<String, List<MarginPoint>> _byId = <String, List<MarginPoint>>{};
  double _financeRatio = 0.60;
  String _generatedAt = '';
  bool _loaded = false;

  bool get isLoaded => _loaded;
  String get generatedAt => _generatedAt;
  double get financeRatio => _financeRatio;

  Future<void> ensureLoaded() async {
    if (_loaded) return;
    try {
      final raw = await rootBundle.loadString('assets/data/margin.json');
      final map = jsonDecode(raw) as Map<String, dynamic>;
      _financeRatio =
          (map['financeRatio'] as num?)?.toDouble() ?? 0.60;
      _generatedAt = (map['generatedAt'] as String?) ?? '';
      final data = (map['data'] as Map?) ?? const <String, dynamic>{};
      final tmp = <String, List<MarginPoint>>{};
      data.forEach((k, v) {
        final list = <MarginPoint>[];
        for (final row in (v as List)) {
          final m = row as Map<String, dynamic>;
          list.add(MarginPoint(
            date: (m['d'] as String?) ?? '',
            marginBal: (m['mb'] as num?)?.toInt() ?? 0,
            shortBal: (m['sb'] as num?)?.toInt() ?? 0,
            marginLimit: (m['ml'] as num?)?.toInt() ?? 0,
            shortLimit: (m['sl'] as num?)?.toInt() ?? 0,
          ));
        }
        tmp[k] = list;
      });
      _byId = tmp;
    } catch (_) {
      // 檔案不存在或格式不對都不該讓頁面炸掉，只是這一塊不顯示
      _byId = <String, List<MarginPoint>>{};
    }
    _loaded = true;
  }

  MarginProfile profile(String stockId, {double avgVolume20 = 0}) {
    if (!_loaded) return MarginProfile.empty;
    final rows = _byId[stockId];
    if (rows == null || rows.isEmpty) return MarginProfile.empty;
    return MarginEngine.build(stockId, rows,
        financeRatio: _financeRatio, avgVolume20: avgVolume20);
  }

  bool has(String stockId) => (_byId[stockId]?.isNotEmpty) ?? false;
}
