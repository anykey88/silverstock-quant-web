/// SilverStock v2 — 歷史條件機率（個股版）
///
/// 這是本工具唯一「接近未來」的東西，但它不是預測，是**統計描述**：
///   「過去 5 年裡，當本益比落在同樣的區間時，之後 20／60 個交易日的報酬分布長什麼樣」
///
/// 三個必須揭露的限制（寫進輸出，不隱藏）：
///   1. 樣本重疊：相鄰交易日條件高度相關，有效樣本遠小於表面樣本數
///   2. 期間偏誤：若過去 5 年是多頭，任何條件下的正報酬比例都會偏高
///   3. 結構變化：公司體質、產業地位改變後，過去的分布未必適用
library silverstock_v2.conditional;

import 'dart:math' as math;

import 'data.dart';
import 'stats.dart';

class ConditionalBucket {
  final String label; // 條件描述
  final int sampleSize;
  final double? median20;
  final double? median60;
  final double? winRate20; // 正報酬比例（%）
  final double? winRate60;
  final double? p25of60; // 60 日報酬的 25 分位（悲觀情境）
  final double? p75of60; // 75 分位（樂觀情境）
  final String horizonNote;

  const ConditionalBucket({
    required this.label,
    required this.sampleSize,
    required this.median20,
    required this.median60,
    required this.winRate20,
    required this.winRate60,
    required this.p25of60,
    required this.p75of60,
    required this.horizonNote,
  });
}

class ConditionalReport {
  final List<ConditionalBucket> buckets;
  final String? currentBucket; // 當前落在哪一組
  final int totalSamples;
  final List<String> caveats;

  const ConditionalReport({
    required this.buckets,
    required this.currentBucket,
    required this.totalSamples,
    required this.caveats,
  });

  ConditionalBucket? get current {
    if (currentBucket == null) return null;
    for (final b in buckets) {
      if (b.label == currentBucket) return b;
    }
    return null;
  }
}

class ConditionalEngine {
  static ConditionalReport build(
    StockDataset d,
    double? currentPer,
    List<double?> perBands, {
    int horizons = 2,
  }) {
    // perBands = [P10, P25, P50, P75, P90]
    final caveats = <String>[
      '相鄰交易日的條件高度重複，有效樣本數遠小於表面樣本數。',
      '若統計期間整體為多頭（或空頭），任何條件下的報酬分布都會被該期間主導。',
      '公司體質或產業地位改變後，過去的分布未必適用於現在。',
    ];

    final p25 = perBands.length > 1 ? perBands[1] : null;
    final p75 = perBands.length > 3 ? perBands[3] : null;

    // 建立 date -> bar index
    final idxOf = <String, int>{};
    for (var i = 0; i < d.bars.length; i++) {
      idxOf[d.bars[i].date] = i;
    }

    final cheap20 = <double>[], cheap60 = <double>[];
    final mid20 = <double>[], mid60 = <double>[];
    final rich20 = <double>[], rich60 = <double>[];

    String? currentBucket;
    if (currentPer != null && p25 != null && p75 != null) {
      currentBucket = currentPer < p25
          ? 'PE 低於 25 分位（歷史相對便宜）'
          : (currentPer <= p75
              ? 'PE 介於 25–75 分位（歷史中間）'
              : 'PE 高於 75 分位（歷史相對偏貴）');
    }

    var used = 0;
    for (final v in d.valuations) {
      final per = v.per;
      if (per == null || per <= 0) continue;
      if (p25 == null || p75 == null) continue;
      final i = idxOf[v.date];
      if (i == null) continue;

      final r20 = _forwardReturn(d.bars, i, 20);
      final r60 = _forwardReturn(d.bars, i, 60);
      if (r20 == null && r60 == null) continue;
      used++;

      final isCheap = per < p25;
      final isRich = per > p75;

      if (r20 != null) {
        if (isCheap) {
          cheap20.add(r20);
        } else if (isRich) {
          rich20.add(r20);
        } else {
          mid20.add(r20);
        }
      }
      if (r60 != null) {
        if (isCheap) {
          cheap60.add(r60);
        } else if (isRich) {
          rich60.add(r60);
        } else {
          mid60.add(r60);
        }
      }
    }

    ConditionalBucket make(
        String label, List<double> r20, List<double> r60) {
      return ConditionalBucket(
        label: label,
        sampleSize: math.max(r20.length, r60.length),
        median20: Stats.median(r20),
        median60: Stats.median(r60),
        winRate20: _winRate(r20),
        winRate60: _winRate(r60),
        p25of60: Stats.percentile(r60, 0.25),
        p75of60: Stats.percentile(r60, 0.75),
        horizonNote: '樣本 20 日 ${r20.length} 筆、60 日 ${r60.length} 筆',
      );
    }

    final buckets = [
      make('PE 低於 25 分位（歷史相對便宜）', cheap20, cheap60),
      make('PE 介於 25–75 分位（歷史中間）', mid20, mid60),
      make('PE 高於 75 分位（歷史相對偏貴）', rich20, rich60),
    ];

    return ConditionalReport(
      buckets: buckets,
      currentBucket: currentBucket,
      totalSamples: used,
      caveats: caveats,
    );
  }

  /// 從第 i 個交易日收盤算起，往後 h 個交易日的報酬（%）
  static double? _forwardReturn(List<Bar> bars, int i, int h) {
    final j = i + h;
    if (j >= bars.length) return null;
    final base = bars[i].close;
    if (base <= 0) return null;
    return (bars[j].close - base) / base * 100;
  }

  static double? _winRate(List<double> rs) {
    if (rs.isEmpty) return null;
    final wins = rs.where((x) => x > 0).length;
    return wins / rs.length * 100;
  }
}
