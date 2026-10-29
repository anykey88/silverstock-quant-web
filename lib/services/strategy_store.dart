// ============================================================================
// 交易策略儲存（localStorage）
// ----------------------------------------------------------------------------
// 內建 3 套模板永遠存在；使用者可編輯（以同 id 覆蓋）或新增自訂策略。
// 全部資料只存在本機瀏覽器。
// ============================================================================

import 'dart:convert';
import 'dart:html' as html; // ignore: avoid_web_libraries_in_flutter

import '../models/trade_strategy.dart';

class StrategyStore {
  static const String _key = 'ssq_strategies_v1';

  static List<TradeStrategy> _custom() {
    try {
      final raw = html.window.localStorage[_key];
      if (raw == null || raw.isEmpty) return <TradeStrategy>[];
      final arr = jsonDecode(raw) as List;
      return arr
          .map((e) => TradeStrategy.fromJson((e as Map).cast<String, dynamic>()))
          .toList();
    } catch (_) {
      return <TradeStrategy>[];
    }
  }

  static void _write(List<TradeStrategy> list) {
    html.window.localStorage[_key] =
        jsonEncode(list.map((e) => e.toJson()).toList());
  }

  /// 全部策略：內建模板（若被覆蓋則用覆蓋版）+ 自訂策略
  static List<TradeStrategy> all() {
    final custom = _custom();
    final byId = <String, TradeStrategy>{for (final s in custom) s.id: s};
    final out = <TradeStrategy>[];
    for (final p in TradeStrategyPresets.build()) {
      out.add(byId[p.id] ?? p);
      byId.remove(p.id);
    }
    out.addAll(byId.values);
    return out;
  }

  static TradeStrategy? byId(String id) {
    for (final s in all()) {
      if (s.id == id) return s;
    }
    return null;
  }

  static void save(TradeStrategy s) {
    final custom = _custom();
    final i = custom.indexWhere((e) => e.id == s.id);
    if (i >= 0) {
      custom[i] = s;
    } else {
      custom.add(s);
    }
    _write(custom);
  }

  static void remove(String id) {
    final custom = _custom()..removeWhere((e) => e.id == id);
    _write(custom);
  }

  static bool isPreset(String id) =>
      TradeStrategyPresets.build().any((e) => e.id == id);

  static int count() => all().length;
}
