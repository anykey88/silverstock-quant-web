// ============================================================================
// 三份觀察清單（清單甲／清單乙／共同關注）
// ----------------------------------------------------------------------------
// 資料來源：assets/data/family_lists.json
//   · 名單成員由 tool/v2/family_lists_src.json 維護（助手改清單只改這個檔）。
//   · 現價／漲跌由 tool/v2/build_family_lists.py 每日抓證交所 MIS 覆寫；
//     抓不到（未開盤、休市）就沿用清單記錄的收盤價，並標記 live=false。
//   · 殖利率／本益比／股淨比變動慢，沿用清單記錄值。
//
// 這裡只是「把自選標的整理成一份看得懂的清單」，不是買賣建議。
// ============================================================================

import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

class FamilyItem {
  final String id;
  final String name;
  final String industry;
  final String category;
  final String group;
  final String status;
  final double close;
  final double change;
  final double pct;
  final double? yieldPct;
  final double? pe;
  final double? pb;
  final bool live;

  const FamilyItem({
    required this.id,
    required this.name,
    required this.industry,
    required this.category,
    required this.group,
    required this.status,
    required this.close,
    required this.change,
    required this.pct,
    required this.yieldPct,
    required this.pe,
    required this.pb,
    required this.live,
  });
}

class FamilyList {
  final String key;
  final String title;
  final String subtitle;
  final String note;
  final List<FamilyItem> items;

  const FamilyList({
    required this.key,
    required this.title,
    required this.subtitle,
    required this.note,
    required this.items,
  });
}

class FamilyListsData {
  final List<FamilyList> lists;
  final String note;
  final String updatedAt;
  final String generatedAt;
  final bool ok;

  const FamilyListsData({
    required this.lists,
    required this.note,
    required this.updatedAt,
    required this.generatedAt,
    this.ok = true,
  });
}

class FamilyListsService {
  static FamilyListsData? _cache;
  static bool _tried = false;

  static double _d(dynamic v) => (v as num?)?.toDouble() ?? 0;

  static double? _dn(dynamic v) => (v as num?)?.toDouble();

  static Future<FamilyListsData> load() async {
    if (_cache != null) return _cache!;
    if (_tried) {
      return _cache ??
          const FamilyListsData(
            lists: <FamilyList>[],
            note: '',
            updatedAt: '',
            generatedAt: '',
            ok: false,
          );
    }
    _tried = true;

    try {
      final raw =
          await rootBundle.loadString('assets/data/family_lists.json');
      final m = jsonDecode(raw) as Map<String, dynamic>;
      final lists = <FamilyList>[];
      for (final e in (m['lists'] as List?) ?? const []) {
        final j = (e as Map).cast<String, dynamic>();
        final items = <FamilyItem>[];
        for (final x in (j['items'] as List?) ?? const []) {
          final k = (x as Map).cast<String, dynamic>();
          items.add(FamilyItem(
            id: (k['id'] ?? '').toString(),
            name: (k['name'] ?? '').toString(),
            industry: (k['industry'] ?? '').toString(),
            category: (k['category'] ?? '').toString(),
            group: (k['group'] ?? '').toString(),
            status: (k['status'] ?? '').toString(),
            close: _d(k['close']),
            change: _d(k['change']),
            pct: _d(k['pct']),
            yieldPct: _dn(k['yield']),
            pe: _dn(k['pe']),
            pb: _dn(k['pb']),
            live: k['live'] == true,
          ));
        }
        lists.add(FamilyList(
          key: (j['key'] ?? '').toString(),
          title: (j['title'] ?? '').toString(),
          subtitle: (j['subtitle'] ?? '').toString(),
          note: (j['note'] ?? '').toString(),
          items: items,
        ));
      }
      _cache = FamilyListsData(
        lists: lists,
        note: (m['note'] ?? '').toString(),
        updatedAt: (m['updated_at'] ?? '').toString(),
        generatedAt: (m['generated_at'] ?? '').toString(),
        ok: true,
      );
    } catch (_) {
      _cache = const FamilyListsData(
        lists: <FamilyList>[],
        note: '',
        updatedAt: '',
        generatedAt: '',
        ok: false,
      );
    }
    return _cache!;
  }
}
