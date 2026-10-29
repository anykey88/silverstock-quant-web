/// SilverStock v2 — 價位結構（支撐／壓力／波動）
///
/// 全部由歷史成交資料計算，不含任何主觀畫線：
///   1. 成交量分布（Volume Profile）→ POC、價值區上下緣
///   2. 前高前低（60／120／250 日）
///   3. 均線（MA20／60／120／240）
///   4. ATR(14) → 波動幅度，用於停損距離與加碼間距
///   5. 跳空缺口（未回補者優先）
///
/// 這些價位的意義是「過去籌碼換手最密集的地方」，不是「一定會漲到那裡」。
library silverstock_v2.levels;

import 'data.dart';
import 'stats.dart';

class Gap {
  final String date;
  final double lower;
  final double upper;
  final bool up;
  final bool filled;

  const Gap(this.date, this.lower, this.upper, this.up, this.filled);

  double get size => upper - lower;
}

class VolumeNode {
  final double price; // 該檔中值
  final double volume;
  const VolumeNode(this.price, this.volume);
}

class LevelMap {
  final double? poc;
  final double? valueAreaHigh;
  final double? valueAreaLow;
  final double? high60, high120, high250;
  final double? low60, low120, low250;
  final double? ma20, ma60, ma120, ma240;
  final double? atr14;
  final double? atrPct; // ATR / 現價
  final List<Gap> openGaps;
  final List<VolumeNode> nodes;
  final int profileDays;

  const LevelMap({
    required this.poc,
    required this.valueAreaHigh,
    required this.valueAreaLow,
    required this.high60,
    required this.high120,
    required this.high250,
    required this.low60,
    required this.low120,
    required this.low250,
    required this.ma20,
    required this.ma60,
    required this.ma120,
    required this.ma240,
    required this.atr14,
    required this.atrPct,
    required this.openGaps,
    required this.nodes,
    required this.profileDays,
  });
}

class LevelEngine {
  static LevelMap build(StockDataset d, {int profileDays = 250, int bins = 50}) {
    final bars = d.tailBars(profileDays);
    final close = bars.isEmpty ? null : bars.last.close;

    // --- 成交量分布 ---------------------------------------------------------
    double? poc;
    double? vah;
    double? val;
    var nodes = <VolumeNode>[];

    if (bars.length >= 30) {
      final typical = bars.map((b) => (b.high + b.low + b.close) / 3).toList();
      final mn = typical.reduce((a, b) => a < b ? a : b);
      final mx = typical.reduce((a, b) => a > b ? a : b);
      if (mx > mn) {
        final step = (mx - mn) / bins;
        final vols = List<double>.filled(bins, 0);
        for (var i = 0; i < bars.length; i++) {
          var idx = ((typical[i] - mn) / step).floor();
          if (idx < 0) idx = 0;
          if (idx >= bins) idx = bins - 1;
          vols[idx] += bars[i].volume;
        }
        nodes = List.generate(
          bins,
          (i) => VolumeNode(mn + step * (i + 0.5), vols[i]),
        );

        var pocIdx = 0;
        for (var i = 1; i < bins; i++) {
          if (vols[i] > vols[pocIdx]) pocIdx = i;
        }
        poc = nodes[pocIdx].price;

        // 價值區：由 POC 向兩側擴張，累計至 70% 成交量
        final total = vols.fold<double>(0, (a, b) => a + b);
        final target = total * 0.70;
        var acc = vols[pocIdx];
        var lo = pocIdx, hi = pocIdx;
        while (acc < target && (lo > 0 || hi < bins - 1)) {
          final left = lo > 0 ? vols[lo - 1] : -1.0;
          final right = hi < bins - 1 ? vols[hi + 1] : -1.0;
          if (right >= left) {
            hi++;
            acc += vols[hi];
          } else {
            lo--;
            acc += vols[lo];
          }
        }
        val = nodes[lo].price;
        vah = nodes[hi].price;
      }
    }

    final n = d.bars;
    double? hi(int days) => n.length < days
        ? null
        : n.sublist(n.length - days).map((b) => b.high).reduce((a, b) => a > b ? a : b);
    double? lo(int days) => n.length < days
        ? null
        : n.sublist(n.length - days).map((b) => b.low).reduce((a, b) => a < b ? a : b);

    final atr = Stats.atr(n, n: 14);

    return LevelMap(
      poc: poc,
      valueAreaHigh: vah,
      valueAreaLow: val,
      high60: hi(60),
      high120: hi(120),
      high250: hi(250),
      low60: lo(60),
      low120: lo(120),
      low250: lo(250),
      ma20: Stats.sma(n, 20),
      ma60: Stats.sma(n, 60),
      ma120: Stats.sma(n, 120),
      ma240: Stats.sma(n, 240),
      atr14: atr,
      atrPct: (atr != null && close != null && close > 0) ? atr / close * 100 : null,
      openGaps: _openGaps(n, close),
      nodes: nodes,
      profileDays: bars.length,
    );
  }

  /// 找出近 250 日內尚未回補的跳空缺口。
  static List<Gap> _openGaps(List<Bar> bars, double? close) {
    if (bars.length < 2) return const [];
    final from = bars.length > 250 ? bars.length - 250 : 0;
    final out = <Gap>[];
    for (var i = from + 1; i < bars.length; i++) {
      final prev = bars[i - 1];
      final cur = bars[i];
      Gap? g;
      if (cur.low > prev.high) {
        g = Gap(cur.date, prev.high, cur.low, true, false);
      } else if (cur.high < prev.low) {
        g = Gap(cur.date, cur.high, prev.low, false, false);
      }
      if (g == null) continue;
      // 檢查後續是否回補
      var filled = false;
      for (var j = i + 1; j < bars.length; j++) {
        if (g.up && bars[j].low <= g.lower) {
          filled = true;
          break;
        }
        if (!g.up && bars[j].high >= g.upper) {
          filled = true;
          break;
        }
      }
      if (!filled) out.add(g);
    }
    // 只留最近 6 個，依日期新到舊
    out.sort((a, b) => b.date.compareTo(a.date));
    return out.take(6).toList();
  }
}
