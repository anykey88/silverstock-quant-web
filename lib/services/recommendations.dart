// ============================================================================
// 建議記錄（助手精選池 + 使用者本地觀察）
// ----------------------------------------------------------------------------
// 資料來源：
//   · 助手精選池：assets/data/recommendations.json（由 tool/v2/build_recommendations.py
//     每日結合最新行情產出，含現價與狀態）。理由／類別／風險／買區減碼區由助手維護。
//   · 使用者本機觀察：localStorage（ssq_user_recs_v1），使用者自行新增，不上傳。
//
// 這不是買賣指令。狀態由「現價 vs 助手設定的買區／減碼區」自動判定，不預測漲跌。
// ============================================================================

import 'dart:convert';
import 'dart:html' as html; // ignore: avoid_web_libraries_in_flutter

import 'package:flutter/services.dart' show rootBundle;

class RecItem {
  final String id;
  final String name;
  final String industry;
  final String category;
  final String thesis;
  final String risk;
  final String riskNote;
  final String note;
  final double buyLow;
  final double buyHigh;
  final double trimLow;
  final double trimHigh;
  final double close;
  final String status; // 可建倉 / 觀察中 / 減碼觀察 / 資料不足
  final String tone; // buy / watch / trim / unknown
  final double gapPct;
  final bool isUser;
  final String updatedAt;

  const RecItem({
    required this.id,
    required this.name,
    required this.industry,
    required this.category,
    required this.thesis,
    required this.risk,
    required this.riskNote,
    required this.note,
    required this.buyLow,
    required this.buyHigh,
    required this.trimLow,
    required this.trimHigh,
    required this.close,
    required this.status,
    required this.tone,
    required this.gapPct,
    this.isUser = false,
    this.updatedAt = '',
  });
}

/// 使用者本機新增的觀察（不存在 asset，純本機）
class UserRec {
  final String id;
  final String name;
  final String industry;
  final String thesis;
  final String note;
  final double buyTarget;
  final String addedAt;

  const UserRec({
    required this.id,
    required this.name,
    required this.industry,
    this.thesis = '',
    this.note = '',
    this.buyTarget = 0,
    this.addedAt = '',
  });

  Map<String, dynamic> toJson() => <String, dynamic>{
        'id': id,
        'name': name,
        'ind': industry,
        'thesis': thesis,
        'note': note,
        'target': buyTarget,
        'at': addedAt,
      };

  factory UserRec.fromJson(Map<String, dynamic> m) => UserRec(
        id: (m['id'] ?? '').toString(),
        name: (m['name'] ?? '').toString(),
        industry: (m['ind'] ?? '').toString(),
        thesis: (m['thesis'] ?? '').toString(),
        note: (m['note'] ?? '').toString(),
        buyTarget: (m['target'] as num?)?.toDouble() ?? 0,
        addedAt: (m['at'] ?? '').toString(),
      );

  UserRec copyWith({
    String? name,
    String? industry,
    String? thesis,
    String? note,
    double? buyTarget,
    String? addedAt,
  }) =>
      UserRec(
        id: id,
        name: name ?? this.name,
        industry: industry ?? this.industry,
        thesis: thesis ?? this.thesis,
        note: note ?? this.note,
        buyTarget: buyTarget ?? this.buyTarget,
        addedAt: addedAt ?? this.addedAt,
      );
}

class UserRecStore {
  static const String _key = 'ssq_user_recs_v1';

  static List<UserRec> _cache = <UserRec>[];
  static bool _loaded = false;

  static List<UserRec> get all {
    _ensure();
    return List<UserRec>.unmodifiable(_cache);
  }

  static void _ensure() {
    if (_loaded) return;
    _loaded = true;
    try {
      final raw = html.window.localStorage[_key];
      if (raw == null || raw.isEmpty) return;
      final list = jsonDecode(raw) as List;
      _cache = list
          .map((e) => UserRec.fromJson((e as Map).cast<String, dynamic>()))
          .toList();
    } catch (_) {
      _cache = <UserRec>[];
    }
  }

  static void _persist() {
    try {
      html.window.localStorage[_key] =
          jsonEncode(_cache.map((e) => e.toJson()).toList());
    } catch (_) {}
  }

  static void add(UserRec r) {
    _ensure();
    final i = _cache.indexWhere((e) => e.id == r.id);
    if (i < 0) {
      _cache.insert(0, r.copyWith(addedAt: DateTime.now().toIso8601String()));
    } else {
      _cache[i] = r.copyWith(addedAt: _cache[i].addedAt);
    }
    _persist();
  }

  static void remove(String id) {
    _ensure();
    _cache.removeWhere((e) => e.id == id);
    _persist();
  }

  static void clear() {
    _cache = <UserRec>[];
    _persist();
  }
}

class RecommendationsData {
  final List<RecItem> items;
  final String note;
  final String updatedAt;
  final String generatedAt;
  final bool ok;

  const RecommendationsData({
    required this.items,
    required this.note,
    required this.updatedAt,
    required this.generatedAt,
    this.ok = true,
  });
}

class RecommendationsService {
  static const List<String> _categoryOrder = <String>[
    '防禦核心',
    '高股息ETF',
    '逆向收息',
    '衛星觀察',
    '我的觀察',
  ];

  static RecommendationsData? _cache;
  static bool _tried = false;

  static List<String> get categoryOrder => _categoryOrder;

  static Future<RecommendationsData> load() async {
    if (_cache != null) return _cache!;
    if (_tried) return _cache ?? const RecommendationsData(
        items: <RecItem>[], note: '', updatedAt: '', generatedAt: '', ok: false);
    _tried = true;

    final items = <RecItem>[];

    // 助手精選池
    try {
      final raw = await rootBundle
          .loadString('assets/data/recommendations.json');
      final m = jsonDecode(raw) as Map<String, dynamic>;
      final list = (m['items'] as List?) ?? const [];
      for (final e in list) {
        final j = (e as Map).cast<String, dynamic>();
        items.add(RecItem(
          id: (j['id'] ?? '').toString(),
          name: (j['name'] ?? '').toString(),
          industry: (j['industry'] ?? '').toString(),
          category: (j['category'] ?? '').toString(),
          thesis: (j['thesis'] ?? '').toString(),
          risk: (j['risk'] ?? '').toString(),
          riskNote: (j['riskNote'] ?? '').toString(),
          note: (j['note'] ?? '').toString(),
          buyLow: (j['buyLow'] as num?)?.toDouble() ?? 0,
          buyHigh: (j['buyHigh'] as num?)?.toDouble() ?? 0,
          trimLow: (j['trimLow'] as num?)?.toDouble() ?? 0,
          trimHigh: (j['trimHigh'] as num?)?.toDouble() ?? 0,
          close: (j['close'] as num?)?.toDouble() ?? 0,
          status: (j['status'] ?? '資料不足').toString(),
          tone: (j['tone'] ?? 'unknown').toString(),
          gapPct: (j['gapPct'] as num?)?.toDouble() ?? 0,
          isUser: false,
          updatedAt: (m['updated_at'] ?? '').toString(),
        ));
      }
      _cache = RecommendationsData(
        items: items,
        note: (m['note'] ?? '').toString(),
        updatedAt: (m['updated_at'] ?? '').toString(),
        generatedAt: (m['generated_at'] ?? '').toString(),
        ok: true,
      );
    } catch (_) {
      _cache = const RecommendationsData(
          items: <RecItem>[], note: '', updatedAt: '', generatedAt: '', ok: false);
    }

    return _cache!;
  }

  /// 把本機使用者觀察合併進去（狀態依現價 vs 目標價計算）
  static List<RecItem> withUserRecs(
      List<RecItem> curated, double Function(String) priceOf) {
    final out = <RecItem>[];
    for (final c in curated) out.add(c);

    for (final u in UserRecStore.all) {
      final px = priceOf(u.id);
      String status = '觀察中';
      String tone = 'watch';
      double gap = 0;
      if (u.buyTarget > 0 && px > 0) {
        gap = (px / u.buyTarget - 1) * 100;
        if (px <= u.buyTarget) {
          status = '可建倉';
          tone = 'buy';
        } else {
          status = '觀察中';
          tone = 'watch';
        }
      }
      out.add(RecItem(
        id: u.id,
        name: u.name,
        industry: u.industry,
        category: '我的觀察',
        thesis: u.thesis,
        risk: '',
        riskNote: '',
        note: u.note,
        buyLow: 0,
        buyHigh: u.buyTarget,
        trimLow: 0,
        trimHigh: 0,
        close: px,
        status: status,
        tone: tone,
        gapPct: gap,
        isUser: true,
        updatedAt: u.addedAt,
      ));
    }
    return out;
  }

  static List<RecItem> byCategory(List<RecItem> items, String category) =>
      items.where((e) => e.category == category).toList();
}
