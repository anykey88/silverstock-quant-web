// ============================================================================
// 全市場股票索引（代號／名稱搜尋）
// ----------------------------------------------------------------------------
// 目的：使用者不必先知道代號。輸入「台積」「積電」「台积电」「2330」都能找到。
//
// 三個關鍵設計：
//   1. 索引存在 asset（assets/data/stock_index.json，約 184KB，3171 檔），
//      一次載入、之後純記憶體比對，不打任何 API。
//   2. 附一張繁→簡字元對照表。大陸常用簡體輸入法打「台积电」，
//      但台股官方名稱是「台積電」——查詢與名稱都先正規化成簡體再比對。
//   3. 排序不是「符合就好」，而是分等級：完全符合 > 前綴 > 包含，
//      同等級時上市優先於上櫃、上櫃優先於興櫃，名稱短的優先。
// ============================================================================

import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

class StockBrief {
  final String id;
  final String name; // 繁體（官方名稱）
  final String simpName; // 簡體
  final String industry;
  final String market; // twse / tpex / emerging

  const StockBrief(this.id, this.name, this.simpName, this.industry, this.market);

  String get marketLabel {
    switch (market) {
      case 'twse':
        return '上市';
      case 'tpex':
        return '上櫃';
      case 'emerging':
        return '興櫃';
      default:
        return market;
    }
  }

  bool get isEtf =>
      industry.contains('ETF') ||
      industry.contains('ETN') ||
      id.startsWith('00') ||
      name.contains('ETF');
}

class StockIndex {
  StockIndex._();
  static final StockIndex instance = StockIndex._();

  final List<StockBrief> _all = <StockBrief>[];
  final Map<String, String> _t2s = <String, String>{};
  final Map<String, StockBrief> _byId = <String, StockBrief>{};
  bool _loaded = false;
  String _version = '';

  bool get isLoaded => _loaded;
  int get count => _all.length;
  String get version => _version;

  Future<void> ensureLoaded() async {
    if (_loaded) return;
    try {
      final raw = await rootBundle.loadString('assets/data/stock_index.json');
      final m = jsonDecode(raw) as Map<String, dynamic>;
      _version = (m['v'] ?? '').toString();
      final t2s = (m['t2s'] as Map?)?.cast<String, dynamic>() ?? {};
      _t2s
        ..clear()
        ..addAll(t2s.map((k, v) => MapEntry(k, v.toString())));
      final rows = (m['rows'] as List?) ?? const [];
      final list = <StockBrief>[];
      for (final r in rows) {
        final a = (r as List);
        if (a.length < 5) continue;
        final b = StockBrief(
          a[0].toString(),
          a[1].toString(),
          a[4].toString(),
          a[2].toString(),
          a[3].toString(),
        );
        list.add(b);
        _byId[b.id] = b;
      }
      _all
        ..clear()
        ..addAll(list);
      _loaded = true;
    } catch (_) {
      _loaded = true; // 失敗就當作空索引，不要讓整個 App 卡住
    }
  }

  StockBrief? byId(String id) => _byId[id.trim().toUpperCase()];

  /// 把字串正規化成簡體，讓繁簡兩種輸入站在同一基準上比對。
  String normalize(String s) {
    final buf = StringBuffer();
    for (final ch in s.split('')) {
      buf.write(_t2s[ch] ?? ch);
    }
    return buf.toString();
  }

  /// 搜尋。回傳依相關度排序的結果（最多 [limit] 筆）。
  List<StockBrief> search(String query, {int limit = 40}) {
    final raw = query.trim().toUpperCase();
    if (raw.isEmpty || _all.isEmpty) return const [];

    final q = normalize(raw);
    final qUpper = raw;
    final hits = <_Hit>[];

    for (final s in _all) {
      final nameS = s.simpName.toUpperCase();
      final idUpper = s.id.toUpperCase();
      final ind = normalize(s.industry);

      int score = 0;
      if (idUpper == qUpper) {
        score = 1000;
      } else if (nameS == q) {
        score = 950;
      } else if (idUpper.startsWith(qUpper)) {
        score = 850;
      } else if (nameS.startsWith(q)) {
        score = 800;
      } else if (nameS.contains(q)) {
        score = 650;
      } else if (idUpper.contains(qUpper) && qUpper.length >= 3) {
        score = 550;
      } else if (ind.contains(q) && q.length >= 2) {
        score = 400;
      }

      if (score == 0) continue;

      // 同等級時的次序：上市 > 上櫃 > 興櫃；非 ETF 優先；名稱短的優先
      final mktRank = s.market == 'twse' ? 0 : (s.market == 'tpex' ? 1 : 2);
      final etfPenalty = s.isEtf ? 1 : 0;
      score -= mktRank * 4 + etfPenalty * 3 + (s.name.length > 6 ? 2 : 0);

      hits.add(_Hit(s, score));
    }

    hits.sort((a, b) {
      final c = b.score.compareTo(a.score);
      if (c != 0) return c;
      return a.stock.id.compareTo(b.stock.id);
    });

    return hits.take(limit).map((h) => h.stock).toList();
  }
}

class _Hit {
  final StockBrief stock;
  final int score;
  _Hit(this.stock, this.score);
}
