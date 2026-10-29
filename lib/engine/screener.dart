// ============================================================================
// 選股篩選與評分（個人自用版）
// ----------------------------------------------------------------------------
// 這是「規則式」評分：每個維度都有明確算式，不做黑箱預測。
//   · 殖利率 25 分：配息相對於股價的吸引力
//   · 評價   20 分：本益比相對「自己過去 5 年」的位階（不是跟別人比）
//   · 配息   20 分：連續配息年數 + 是否縮水
//   · 成長   20 分：近 3 個完整年度 EPS 的年複合成長
//   · 風險   15 分：近一年最大回撤（越小越好）
// 輸出分數 + 標籤 + 理由，讓使用者知道「為什麼是這個分數」。
// ============================================================================

import 'dart:math' as math;

import '../models/models.dart';

class ScreenerFilter {
  final Set<String> industries; // 空集合 = 全部產業
  final double minYield; // 殖利率下限 %
  final double? maxPer; // 本益比上限
  final int minDivYears; // 連續配息年數下限
  final double? maxDistMa60; // 距季線上限 %（負值＝要求跌破季線）
  final double? maxDrawdown1y; // 近一年最大回撤上限 %
  final double minScore; // 綜合評分下限
  final String sortBy; // score / yield / per / drawdown / eps

  const ScreenerFilter({
    this.industries = const <String>{},
    this.minYield = 0,
    this.maxPer,
    this.minDivYears = 0,
    this.maxDistMa60,
    this.maxDrawdown1y,
    this.minScore = 0,
    this.sortBy = 'score',
  });

  ScreenerFilter copyWith({
    Set<String>? industries,
    double? minYield,
    double? maxPer,
    bool clearMaxPer = false,
    int? minDivYears,
    double? maxDistMa60,
    bool clearDist = false,
    double? maxDrawdown1y,
    bool clearMdd = false,
    double? minScore,
    String? sortBy,
  }) {
    return ScreenerFilter(
      industries: industries ?? this.industries,
      minYield: minYield ?? this.minYield,
      maxPer: clearMaxPer ? null : (maxPer ?? this.maxPer),
      minDivYears: minDivYears ?? this.minDivYears,
      maxDistMa60: clearDist ? null : (maxDistMa60 ?? this.maxDistMa60),
      maxDrawdown1y: clearMdd ? null : (maxDrawdown1y ?? this.maxDrawdown1y),
      minScore: minScore ?? this.minScore,
      sortBy: sortBy ?? this.sortBy,
    );
  }
}

class ScreenedStock {
  final StockSeries series;
  final double close;
  final double yieldRate;
  final double? per;
  final double? perMedian;
  final double? perRatio;
  final int divStreak;
  final double? epsCagr3y;
  final double mdd1y;
  final double distMa60;
  final double score;
  final Map<String, double> parts; // 殖利率 / 評價 / 配息 / 成長 / 風險
  final String label;
  final List<String> reasons;

  ScreenedStock({
    required this.series,
    required this.close,
    required this.yieldRate,
    required this.per,
    required this.perMedian,
    required this.perRatio,
    required this.divStreak,
    required this.epsCagr3y,
    required this.mdd1y,
    required this.distMa60,
    required this.score,
    required this.parts,
    required this.label,
    required this.reasons,
  });
}

class Screener {
  /// 對全部標的打分（不套用篩選條件）
  static List<ScreenedStock> scoreAll(List<StockSeries> all) {
    final out = <ScreenedStock>[];
    for (final s in all) {
      if (s.closes.length < 90) continue;
      out.add(_scoreOne(s));
    }
    return out;
  }

  static List<ScreenedStock> filter(List<ScreenedStock> scored, ScreenerFilter f) {
    var list = scored.where((e) {
      if (f.industries.isNotEmpty && !f.industries.contains(e.series.industry)) {
        return false;
      }
      if (e.yieldRate < f.minYield) return false;
      if (f.maxPer != null && e.per != null && e.per! > f.maxPer!) return false;
      if (e.divStreak < f.minDivYears) return false;
      if (f.maxDistMa60 != null && e.distMa60 > f.maxDistMa60!) return false;
      if (f.maxDrawdown1y != null && e.mdd1y > f.maxDrawdown1y!) return false;
      if (e.score < f.minScore) return false;
      return true;
    }).toList();

    switch (f.sortBy) {
      case 'yield':
        list.sort((a, b) => b.yieldRate.compareTo(a.yieldRate));
        break;
      case 'per':
        list.sort((a, b) => (a.per ?? 9999).compareTo(b.per ?? 9999));
        break;
      case 'drawdown':
        list.sort((a, b) => a.mdd1y.compareTo(b.mdd1y));
        break;
      case 'eps':
        list.sort((a, b) => (b.epsCagr3y ?? -999).compareTo(a.epsCagr3y ?? -999));
        break;
      default:
        list.sort((a, b) => b.score.compareTo(a.score));
    }
    return list;
  }

  static ScreenedStock _scoreOne(StockSeries s) {
    final i = s.closes.length - 1;
    final close = s.closes[i];
    final y = s.yieldAt(i);
    final per = s.latestPer?.per;
    final perMed = s.perMedian;
    final perRatio = (per != null && perMed != null && perMed > 0) ? per / perMed : null;

    // 連續配息年數（以除息年份計，允許同一年多次）
    final years = s.dividends.map((d) => int.parse(d.ym.substring(0, 4))).toSet().toList()
      ..sort();
    var streak = 0;
    if (years.isNotEmpty) {
      var y0 = years.last;
      final set = years.toSet();
      while (set.contains(y0)) {
        streak++;
        y0--;
      }
      // 若最近一年尚未除息（例如今年還沒配），往前一年多算一次
      if (streak == 1 && set.contains(years.last - 1)) streak = 0;
    }

    // 近 3 個完整年度 EPS 年複合成長
    final annual = s.annualEps;
    final ys = annual.keys.toList()..sort();
    double? epsCagr;
    if (ys.length >= 3) {
      final last3 = ys.sublist(ys.length - 3);
      final first = annual[last3.first]!;
      final last = annual[last3.last]!;
      if (first > 0 && last > 0) {
        epsCagr = (math.pow(last / first, 1 / 2).toDouble() - 1) * 100;
      } else if (last <= 0) {
        epsCagr = -100;
      }
    }

    // 近一年最大回撤
    final from = math.max(0, s.closes.length - 252);
    var peak = s.closes[from];
    var mdd = 0.0;
    for (var k = from; k < s.closes.length; k++) {
      if (s.closes[k] > peak) peak = s.closes[k];
      final dd = peak <= 0 ? 0.0 : (peak - s.closes[k]) / peak;
      if (dd > mdd) mdd = dd;
    }
    final mdd1y = mdd * 100;

    // 距季線
    final from60 = math.max(0, s.closes.length - 60);
    final ma60 = s.closes.sublist(from60).reduce((a, b) => a + b) /
        (s.closes.length - from60);
    final distMa60 = ma60 <= 0 ? 0.0 : (close / ma60 - 1) * 100;

    // ---- 五個維度 ----
    final sYield = _scoreYield(y);
    final sPer = _scorePer(perRatio);
    final sDiv = _scoreDiv(streak, s.dividends);
    final sGrowth = _scoreGrowth(epsCagr);
    final sRisk = _scoreRisk(mdd1y);

    final total = sYield * 0.25 + sPer * 0.20 + sDiv * 0.20 + sGrowth * 0.20 + sRisk * 0.15;

    final parts = <String, double>{
      '殖利率': sYield,
      '評價': sPer,
      '配息': sDiv,
      '成長': sGrowth,
      '風險': sRisk,
    };

    // ---- 標籤與理由 ----
    String label;
    if (total >= 80) {
      label = '優先關注';
    } else if (total >= 65) {
      label = '可分批投入';
    } else if (total >= 50) {
      label = '觀察名單';
    } else {
      label = '暫緩';
    }

    final reasons = <String>[];
    if (y > 0) {
      reasons.add('殖利率 ${y.toStringAsFixed(2)}%'
          '${y >= 5 ? '，配息相對股價有吸引力' : (y >= 3 ? '，配息中等' : '，配息偏低')}');
    }
    if (perRatio != null) {
      final word = perRatio <= 0.85
          ? '低於'
          : (perRatio <= 1.05 ? '接近' : '高於');
      reasons.add('本益比 ${per!.toStringAsFixed(1)} 倍，$word自身 5 年中位數 '
          '${perMed!.toStringAsFixed(1)} 倍（位階 ${(perRatio * 100).toStringAsFixed(0)}%）');
    } else {
      reasons.add('ETF 無本益比資料，評價分以中性計');
    }
    if (streak > 0) {
      reasons.add('連續配息 $streak 年${streak >= 5 ? '，配息紀錄穩定' : ''}');
    } else {
      reasons.add('近兩年配息紀錄不完整');
    }
    if (epsCagr != null) {
      reasons.add(epsCagr >= 0
          ? '近 3 年 EPS 年複合成長 ${epsCagr.toStringAsFixed(1)}%'
          : '近 3 年 EPS 年複合成長 ${epsCagr.toStringAsFixed(1)}%（衰退）');
    }
    reasons.add('近一年最大回撤 ${mdd1y.toStringAsFixed(1)}%'
        '${mdd1y >= 35 ? '，波動偏大，投入節奏要放慢' : ''}');
    reasons.add('目前股價${distMa60 >= 0 ? '高於' : '低於'}季線 ${distMa60.abs().toStringAsFixed(1)}%');

    return ScreenedStock(
      series: s,
      close: close,
      yieldRate: y,
      per: per,
      perMedian: perMed,
      perRatio: perRatio,
      divStreak: streak,
      epsCagr3y: epsCagr,
      mdd1y: mdd1y,
      distMa60: distMa60,
      score: total,
      parts: parts,
      label: label,
      reasons: reasons,
    );
  }

  static double _scoreYield(double y) {
    if (y >= 6) return 100;
    if (y >= 5) return 88;
    if (y >= 4) return 74;
    if (y >= 3) return 56;
    if (y >= 2) return 38;
    if (y >= 1) return 22;
    return 8;
  }

  static double _scorePer(double? ratio) {
    if (ratio == null) return 60; // ETF 或無資料：中性
    if (ratio <= 0.75) return 100;
    if (ratio <= 0.85) return 92;
    if (ratio <= 1.00) return 78;
    if (ratio <= 1.15) return 58;
    if (ratio <= 1.35) return 36;
    if (ratio <= 1.60) return 20;
    return 8;
  }

  static double _scoreDiv(int streak, List<DivRecord> divs) {
    var base = 0.0;
    if (streak >= 5) {
      base = 95;
    } else if (streak == 4) {
      base = 80;
    } else if (streak == 3) {
      base = 65;
    } else if (streak == 2) {
      base = 45;
    } else if (streak == 1) {
      base = 30;
    } else {
      return 15;
    }
    // 最近一次配息若明顯縮水，扣分
    if (divs.length >= 2) {
      final last = divs.last.amount;
      final prev = divs[divs.length - 2].amount;
      if (prev > 0 && last < prev * 0.7) base -= 25;
    }
    return base.clamp(0, 100).toDouble();
  }

  static double _scoreGrowth(double? cagr) {
    if (cagr == null) return 55;
    if (cagr >= 20) return 100;
    if (cagr >= 12) return 82;
    if (cagr >= 5) return 66;
    if (cagr >= 0) return 52;
    if (cagr >= -10) return 30;
    return 10;
  }

  static double _scoreRisk(double mdd) {
    if (mdd <= 15) return 100;
    if (mdd <= 22) return 82;
    if (mdd <= 30) return 64;
    if (mdd <= 40) return 42;
    if (mdd <= 50) return 24;
    return 10;
  }
}
