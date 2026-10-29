// ============================================================================
// 市場觀察引擎（大盤溫度、產業溫度、歷史條件機率）
// ----------------------------------------------------------------------------
// 【重要邊界】這裡只做「描述現在的狀態」與「統計過去的分布」，
// 不做漲跌預測、不給目標點位、不推薦個股。
// 所有輸出都必須能追溯到公式，使用者可以自己驗算。
// ============================================================================

import 'dart:math' as math;

import '../data/market_repository.dart';
import '../models/models.dart';

/// 大盤體檢結果
class MarketPulse {
  final double close;
  final double chg1d; // 今日漲跌 %
  final double distMa60; // 距季線 %
  final double distMa240; // 距年線 %
  final double volRatio20; // 今日量 / 20 日均量
  final double vol20Pct; // 20 日年化波動率 %
  final int upCount;
  final int downCount;
  final double breadth; // 上漲家數占比 %
  final double tempScore; // 0-100
  final String state; // 偏冷 / 中性偏冷 / 中性 / 中性偏熱 / 偏熱
  final String stateNote;
  final List<IndustryPulse> industries;
  final List<ConditionStat> stats;

  MarketPulse({
    required this.close,
    required this.chg1d,
    required this.distMa60,
    required this.distMa240,
    required this.volRatio20,
    required this.vol20Pct,
    required this.upCount,
    required this.downCount,
    required this.breadth,
    required this.tempScore,
    required this.state,
    required this.stateNote,
    required this.industries,
    required this.stats,
  });
}

class IndustryPulse {
  final String name;
  final int count;
  final double chg20;
  final double chg60;
  final double avgYield;
  final double avgScore;
  final double avgMdd1y;
  IndustryPulse(this.name, this.count, this.chg20, this.chg60, this.avgYield,
      this.avgScore, this.avgMdd1y);
}

/// 歷史條件機率（過去在同樣條件下，之後的報酬分布）
class ConditionStat {
  final String label;
  final int samples;
  final double median20;
  final double median60;
  final double win20; // 正報酬比例 %
  final double win60;
  ConditionStat(this.label, this.samples, this.median20, this.median60,
      this.win20, this.win60);
}

class MarketAnalyzer {
  static MarketPulse? analyze(
    IndexSeries idx,
    List<StockSeries> stocks,
    List<ScreenedLite> scores,
  ) {
    if (idx.closes.length < 260) return null;
    final n = idx.closes.length;
    final close = idx.closes[n - 1];
    final prev = idx.closes[n - 2];
    final ma60 = _ma(idx.closes, 60);
    final ma240 = _ma(idx.closes, 240);

    final volToday = idx.volumes.isEmpty ? 0.0 : idx.volumes.last.toDouble();
    final volAvg20 = idx.volumes.isEmpty
        ? 0.0
        : idx.volumes
                .sublist(math.max(0, n - 21), n - 1)
                .fold<int>(0, (a, b) => a + b) /
            20.0;

    // 20 日年化波動
    final rets = <double>[];
    for (var i = n - 21; i < n; i++) {
      if (idx.closes[i - 1] > 0) {
        rets.add(idx.closes[i] / idx.closes[i - 1] - 1);
      }
    }
    final mean = rets.isEmpty ? 0.0 : rets.reduce((a, b) => a + b) / rets.length;
    final variance = rets.isEmpty
        ? 0.0
        : rets.map((e) => (e - mean) * (e - mean)).reduce((a, b) => a + b) /
            math.max(1, rets.length - 1);
    final vol20 = math.sqrt(variance) * math.sqrt(252) * 100;

    // 樣本內漲跌家數
    var up = 0, down = 0;
    for (final s in stocks) {
      final m = s.closes.length;
      if (m < 2) continue;
      if (s.closes[m - 1] > s.closes[m - 2]) {
        up++;
      } else if (s.closes[m - 1] < s.closes[m - 2]) {
        down++;
      }
    }
    final breadth = (up + down) == 0 ? 50.0 : up / (up + down) * 100;

    final dist60 = ma60 > 0 ? (close / ma60 - 1) * 100 : 0.0;
    final dist240 = ma240 > 0 ? (close / ma240 - 1) * 100 : 0.0;
    final vr = volAvg20 > 0 ? volToday / volAvg20 : 1.0;

    // ---- 溫度分數（純描述，不含預測）----
    // 位階 40 分：距年線 -25% → 0 分，+30% → 40 分
    final posScore = ((dist240 + 25) / 55 * 40).clamp(0, 40).toDouble();
    // 廣度 25 分
    final breadthScore = (breadth / 100 * 25).clamp(0, 25).toDouble();
    // 量能 15 分：量比 0.6 → 0，1.6 → 15
    final volScore = ((vr - 0.6) / 1.0 * 15).clamp(0, 15).toDouble();
    // 波動 20 分（越低越「安全」，但低波動也可能是暴風雨前）
    final volScore2 = (20 - (vol20 - 12) / 28 * 20).clamp(0, 20).toDouble();
    final temp = posScore + breadthScore + volScore + volScore2;

    String state;
    String note;
    if (temp >= 75) {
      state = '偏熱';
      note = '位階與量能都在相對高位，這種時候更需要事先寫好出場條件。';
    } else if (temp >= 58) {
      state = '中性偏熱';
      note = '市場情緒偏正向，追高的風險比低檔時高一些。';
    } else if (temp >= 42) {
      state = '中性';
      note = '位階與量能都在中間區間，適合按原本的紀律執行。';
    } else if (temp >= 25) {
      state = '中性偏冷';
      note = '位階偏低、量能偏弱，歷史上這種狀態常出現在盤整或修正段。';
    } else {
      state = '偏冷';
      note = '位階與量能都在低檔，歷史上這種時候的後續波動通常比較大。';
    }

    // ---- 產業溫度 ----
    final byIndustry = <String, List<StockSeries>>{};
    for (final s in stocks) {
      byIndustry.putIfAbsent(s.industry, () => <StockSeries>[]).add(s);
    }
    final scoreMap = <String, double>{for (final s in scores) s.id: s.score};
    final industries = <IndustryPulse>[];
    byIndustry.forEach((name, list) {
      var c20 = 0.0, c60 = 0.0, y = 0.0, sc = 0.0, mdd = 0.0;
      var cnt = 0;
      for (final s in list) {
        final m = s.closes.length;
        if (m < 65) continue;
        c20 += (s.closes[m - 1] / s.closes[m - 21] - 1) * 100;
        c60 += (s.closes[m - 1] / s.closes[m - 61] - 1) * 100;
        y += s.yieldAt(m - 1);
        sc += scoreMap[s.id] ?? 0;
        mdd += _mdd1y(s);
        cnt++;
      }
      if (cnt == 0) return;
      industries.add(IndustryPulse(name, cnt, c20 / cnt, c60 / cnt, y / cnt,
          sc / cnt, mdd / cnt));
    });
    industries.sort((a, b) => b.chg20.compareTo(a.chg20));

    return MarketPulse(
      close: close,
      chg1d: prev > 0 ? (close / prev - 1) * 100 : 0,
      distMa60: dist60,
      distMa240: dist240,
      volRatio20: vr,
      vol20Pct: vol20,
      upCount: up,
      downCount: down,
      breadth: breadth,
      tempScore: temp,
      state: state,
      stateNote: note,
      industries: industries,
      stats: _conditionStats(idx, 240),
    );
  }

  /// 歷史條件機率：指數在年線之上 / 之下的後續 20、60 日報酬分布
  static List<ConditionStat> _conditionStats(IndexSeries idx, int maLen) {
    final out = <ConditionStat>[];
    for (final above in <bool>[true, false]) {
      final r20 = <double>[];
      final r60 = <double>[];
      for (var i = maLen; i < idx.closes.length; i++) {
        final ma = idx.closes
                .sublist(i - maLen + 1, i + 1)
                .reduce((a, b) => a + b) /
            maLen;
        final cond = above ? idx.closes[i] >= ma : idx.closes[i] < ma;
        if (!cond) continue;
        if (i + 20 < idx.closes.length) {
          r20.add((idx.closes[i + 20] / idx.closes[i] - 1) * 100);
        }
        if (i + 60 < idx.closes.length) {
          r60.add((idx.closes[i + 60] / idx.closes[i] - 1) * 100);
        }
      }
      if (r20.isEmpty) continue;
      out.add(ConditionStat(
        above ? '指數在年線之上' : '指數在年線之下',
        r20.length,
        _median(r20),
        _median(r60),
        r20.where((e) => e > 0).length / r20.length * 100,
        r60.isEmpty
            ? 0
            : r60.where((e) => e > 0).length / r60.length * 100,
      ));
    }
    return out;
  }

  static double _ma(List<double> v, int n) {
    final from = v.length > n ? v.length - n : 0;
    return v.sublist(from).reduce((a, b) => a + b) / (v.length - from);
  }

  static double _median(List<double> v) {
    if (v.isEmpty) return 0;
    final s = List<double>.from(v)..sort();
    return s[s.length ~/ 2];
  }

  static double _mdd1y(StockSeries s) {
    final from = math.max(0, s.closes.length - 252);
    var peak = s.closes[from];
    var mdd = 0.0;
    for (var i = from; i < s.closes.length; i++) {
      if (s.closes[i] > peak) peak = s.closes[i];
      final dd = peak <= 0 ? 0.0 : (peak - s.closes[i]) / peak;
      if (dd > mdd) mdd = dd;
    }
    return mdd * 100;
  }
}

/// 只帶 id / score 的輕量結構，避免 screener 與本檔互相依賴
class ScreenedLite {
  final String id;
  final double score;
  ScreenedLite(this.id, this.score);
}
