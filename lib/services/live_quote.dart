/// 盤中即時報價的讀取端
// ---------------------------------------------------------------------------
/// 檔案由 `tool/v2/fetch_live.py`（GitHub Actions 排程）抓證交所 MIS 產生。
/// 前端只讀同源靜態檔，不直接打證交所——MIS 沒有 CORS 頭，瀏覽器會被擋。
///
/// 什麼時候會拿到「不是今天」的價：Actions 沒跑、或跑失敗、或你離線。
/// 所以這裡一定要把 asOf 帶到畫面上，讓使用者自己判斷這個價有多新。

import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

class LiveQuote {
  final String id;
  final String name;
  final double price;
  final double prevClose;
  final String time;

  const LiveQuote({
    required this.id,
    required this.name,
    required this.price,
    required this.prevClose,
    required this.time,
  });

  bool get hasPrev => prevClose > 0;

  double get changePct => hasPrev ? (price / prevClose - 1) * 100 : 0;
}

class LiveStore {
  LiveStore._();
  static final LiveStore instance = LiveStore._();

  Map<String, LiveQuote> _byId = <String, LiveQuote>{};
  String _asOf = '';
  String _session = '';
  bool _loaded = false;

  bool get isLoaded => _loaded;
  String get asOf => _asOf;
  String get session => _session;
  bool get hasAny => _byId.isNotEmpty;

  Future<void> ensureLoaded() async {
    if (_loaded) return;
    try {
      final raw = await rootBundle.loadString('assets/data/live.json');
      final map = jsonDecode(raw) as Map<String, dynamic>;
      _asOf = (map['asOf'] as String?) ?? '';
      _session = (map['session'] as String?) ?? '';
      final data = (map['data'] as Map?) ?? const <String, dynamic>{};
      final tmp = <String, LiveQuote>{};
      data.forEach((k, v) {
        final m = v as Map<String, dynamic>;
        final p = (m['p'] as num?)?.toDouble() ?? 0;
        if (p <= 0) return;
        tmp[k] = LiveQuote(
          id: k,
          name: (m['name'] as String?) ?? '',
          price: p,
          prevClose: (m['prev'] as num?)?.toDouble() ?? 0,
          time: (m['t'] as String?) ?? '',
        );
      });
      _byId = tmp;
    } catch (_) {
      _byId = <String, LiveQuote>{};
    }
    _loaded = true;
  }

  LiveQuote? quote(String id) => _byId[id];

  /// asOf 是不是今天（台北時間）。不是今天就不該標「即時」。
  bool get isToday {
    if (_asOf.length < 10) return false;
    final now = DateTime.now();
    final today = '${now.year.toString().padLeft(4, '0')}-'
        '${now.month.toString().padLeft(2, '0')}-'
        '${now.day.toString().padLeft(2, '0')}';
    return _asOf.startsWith(today);
  }
}
