// ============================================================================
// 自選股清單
// ----------------------------------------------------------------------------
// 使用者用名稱搜尋找到代號之後，需要一個地方把它存起來，否則每次都要重搜。
// 這份清單同時也是「每日精選」在客戶端計算減碼提醒的依據。
//
// 存在 localStorage，不上傳、不同步。換裝置要重新加，但資料完全留在本機。
// ============================================================================

import 'dart:convert';
import 'dart:html' as html; // ignore: avoid_web_libraries_in_flutter
import 'dart:math' as math;

class WatchItem {
  final String id;
  final String name;
  final String industry;
  final String addedAt; // ISO8601
  final String note;

  const WatchItem({
    required this.id,
    required this.name,
    this.industry = '',
    this.addedAt = '',
    this.note = '',
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'ind': industry,
        'at': addedAt,
        'note': note,
      };

  factory WatchItem.fromJson(Map<String, dynamic> m) => WatchItem(
        id: (m['id'] ?? '').toString(),
        name: (m['name'] ?? '').toString(),
        industry: (m['ind'] ?? '').toString(),
        addedAt: (m['at'] ?? '').toString(),
        note: (m['note'] ?? '').toString(),
      );

  WatchItem copyWith({String? note}) => WatchItem(
        id: id,
        name: name,
        industry: industry,
        addedAt: addedAt,
        note: note ?? this.note,
      );
}

class WatchList {
  static const String _key = 'ssq_watchlist_v1';
  static const int maxItems = 200;

  static List<WatchItem> _cache = <WatchItem>[];
  static bool _loaded = false;

  static List<WatchItem> get all {
    _ensure();
    return List<WatchItem>.unmodifiable(_cache);
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
          .map((e) => WatchItem.fromJson((e as Map).cast<String, dynamic>()))
          .toList();
    } catch (_) {
      _cache = <WatchItem>[];
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

  static WatchItem? byId(String id) {
    _ensure();
    for (final e in _cache) {
      if (e.id == id) return e;
    }
    return null;
  }

  /// 加入自選。已在清單中則不重複加入。
  /// 回傳 true 表示這次真的新增了。
  static bool add(String id, String name, {String industry = ''}) {
    _ensure();
    if (contains(id)) return false;
    if (_cache.length >= maxItems) return false;
    _cache.insert(
      0,
      WatchItem(
        id: id,
        name: name,
        industry: industry,
        addedAt: DateTime.now().toIso8601String(),
      ),
    );
    _persist();
    return true;
  }

  /// 加到清單尾端（初始化時用，保持傳入順序）。
  /// 手動加入走 [add]，會排在最前面。
  static bool addLast(String id, String name, {String industry = ''}) {
    _ensure();
    if (contains(id)) return false;
    if (_cache.length >= maxItems) return false;
    _cache.add(WatchItem(
      id: id,
      name: name,
      industry: industry,
      addedAt: DateTime.now().toIso8601String(),
    ));
    _persist();
    return true;
  }

  static void remove(String id) {
    _ensure();
    _cache.removeWhere((e) => e.id == id);
    _persist();
  }

  static void toggle(String id, String name, {String industry = ''}) {
    if (contains(id)) {
      remove(id);
    } else {
      add(id, name, industry: industry);
    }
  }

  static void setNote(String id, String note) {
    _ensure();
    final i = _cache.indexWhere((e) => e.id == id);
    if (i < 0) return;
    _cache[i] = _cache[i].copyWith(note: note);
    _persist();
  }

  static void reorder(int oldIndex, int newIndex) {
    _ensure();
    final i = newIndex > oldIndex ? newIndex - 1 : newIndex;
    final item = _cache.removeAt(oldIndex);
    _cache.insert(math.min(i, _cache.length), item);
    _persist();
  }

  static void clear() {
    _cache = <WatchItem>[];
    _persist();
  }

  /// 匯出成純文字（給使用者備份或貼到別的地方）
  static String exportText() {
    _ensure();
    final buf = StringBuffer('SilverStock 自選股清單\n');
    buf.writeln('匯出時間：${DateTime.now().toIso8601String().substring(0, 16)}');
    buf.writeln('共 ${_cache.length} 檔\n');
    for (final e in _cache) {
      buf.writeln('${e.id}\t${e.name}\t${e.industry}'
          '${e.note.isEmpty ? '' : '\t${e.note}'}');
    }
    return buf.toString();
  }
}
