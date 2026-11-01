// ============================================================================
// 我的持股清單（輕量、獨立於多帳戶系統）
// ----------------------------------------------------------------------------
// 用途：讓使用者快速記錄「現在手上持有什麼」——股票代號、股數、買進價格，
//       一眼看成本、現價、損益、佔比。純記帳，不下單、不預測。
//
// 與「投資帳戶」的差別：
//   · 投資帳戶是「多本帳＋模擬下單＋風險體檢」的完整系統，偏練習與家庭分帳。
//   · 這裡是單一清單、極簡錄入，只回答一個問題：「我現在持有這些，賺賠多少？」
//
// 資料存在本機 localStorage，不上傳、不同步。換裝置要重新輸入，但資料留在本機。
// ============================================================================

import 'dart:convert';
import 'dart:html' as html; // ignore: avoid_web_libraries_in_flutter

class Holding {
  final String id;
  final String name;
  final String industry;
  final int shares;
  final double costPrice; // 每股買進價格
  final String addedAt; // ISO8601
  final String note;

  const Holding({
    required this.id,
    required this.name,
    required this.industry,
    required this.shares,
    required this.costPrice,
    this.addedAt = '',
    this.note = '',
  });

  Map<String, dynamic> toJson() => <String, dynamic>{
        'id': id,
        'name': name,
        'ind': industry,
        'shares': shares,
        'cost': costPrice,
        'at': addedAt,
        'note': note,
      };

  factory Holding.fromJson(Map<String, dynamic> m) => Holding(
        id: (m['id'] ?? '').toString(),
        name: (m['name'] ?? '').toString(),
        industry: (m['ind'] ?? '').toString(),
        shares: (m['shares'] as num?)?.toInt() ?? 0,
        costPrice: (m['cost'] as num?)?.toDouble() ?? 0,
        addedAt: (m['at'] ?? '').toString(),
        note: (m['note'] ?? '').toString(),
      );

  Holding copyWith({
    String? name,
    String? industry,
    int? shares,
    double? costPrice,
    String? note,
    String? addedAt,
  }) =>
      Holding(
        id: id,
        name: name ?? this.name,
        industry: industry ?? this.industry,
        shares: shares ?? this.shares,
        costPrice: costPrice ?? this.costPrice,
        addedAt: addedAt ?? this.addedAt,
        note: note ?? this.note,
      );
}

class HoldingsStore {
  static const String _key = 'ssq_holdings_v1';
  static const int maxItems = 300;

  static List<Holding> _cache = <Holding>[];
  static bool _loaded = false;

  static List<Holding> get all {
    _ensure();
    return List<Holding>.unmodifiable(_cache);
  }

  static int get count {
    _ensure();
    return _cache.length;
  }

  static void _ensure() {
    if (_loaded) return;
    _loaded = true;
    try {
      final raw = html.window.localStorage[_key];
      if (raw == null || raw.isEmpty) return;
      final list = jsonDecode(raw) as List;
      _cache = list
          .map((e) => Holding.fromJson((e as Map).cast<String, dynamic>()))
          .toList();
    } catch (_) {
      _cache = <Holding>[];
    }
  }

  static void _persist() {
    try {
      html.window.localStorage[_key] =
          jsonEncode(_cache.map((e) => e.toJson()).toList());
    } catch (_) {
      // 超過配額時靜默失敗，不讓 UI 掛掉
    }
  }

  static bool contains(String id) {
    _ensure();
    return _cache.any((e) => e.id == id);
  }

  /// 新增一筆持股。已在清單中則改寫股數與成本（取加權平均成本）。
  /// 回傳 true 表示這次是新增。
  static bool add(Holding h) {
    _ensure();
    final i = _cache.indexWhere((e) => e.id == h.id);
    if (i < 0) {
      if (_cache.length >= maxItems) return false;
      _cache.insert(
        0,
        h.copyWith(addedAt: DateTime.now().toIso8601String()),
      );
    } else {
      final old = _cache[i];
      final newShares = old.shares + h.shares;
      final newCost = newShares > 0
          ? (old.costPrice * old.shares + h.costPrice * h.shares) / newShares
          : h.costPrice;
      _cache[i] = old.copyWith(
        shares: newShares,
        costPrice: newCost,
        name: h.name.isNotEmpty ? h.name : old.name,
        industry: h.industry.isNotEmpty ? h.industry : old.industry,
        note: h.note.isNotEmpty ? h.note : old.note,
      );
    }
    _persist();
    return i < 0;
  }

  static void update(Holding h) {
    _ensure();
    final i = _cache.indexWhere((e) => e.id == h.id);
    if (i < 0) return;
    _cache[i] = h;
    _persist();
  }

  static void remove(String id) {
    _ensure();
    _cache.removeWhere((e) => e.id == id);
    _persist();
  }

  static void clear() {
    _cache = <Holding>[];
    _persist();
  }

  /// 匯出 CSV（UTF-8 BOM，Excel 直接開）。含小計列。
  static String exportCsv(double Function(String) priceOf) {
    final buf = StringBuffer('﻿');
    buf.writeln('代號,名稱,產業,股數,買進價格,現價,市值,成本,損益,損益%');
    double totCost = 0;
    double totMv = 0;
    for (final h in all) {
      final px = priceOf(h.id);
      final mv = px * h.shares;
      final cost = h.costPrice * h.shares;
      final pnl = mv - cost;
      final pct = cost > 0 ? pnl / cost * 100 : 0;
      totCost += cost;
      totMv += mv;
      buf.writeln('${h.id},${h.name},${h.industry},${h.shares},'
          '${h.costPrice.toStringAsFixed(2)},${px > 0 ? px.toStringAsFixed(2) : ''},'
          '${mv.toStringAsFixed(0)},${cost.toStringAsFixed(0)},'
          '${pnl.toStringAsFixed(0)},${pct.toStringAsFixed(2)}');
    }
    final tp = totMv - totCost;
    final tpct = totCost > 0 ? tp / totCost * 100 : 0;
    buf.writeln('小計,,,,,,${totMv.toStringAsFixed(0)},'
        '${totCost.toStringAsFixed(0)},${tp.toStringAsFixed(0)},${tpct.toStringAsFixed(2)}');
    return buf.toString();
  }
}
