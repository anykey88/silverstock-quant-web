/// SilverStock v2 — 統計工具
///
/// 只做純計算：分位數、均值、標準差、ATR、線性斜率。
/// 所有函式皆為 deterministic，相同輸入必得相同輸出（可重現、可驗證）。
library silverstock_v2.stats;

import 'dart:math' as math;

import 'data.dart';

class Stats {
  /// 線性插值分位數。p ∈ [0,1]。
  /// 空集合回傳 null，呼叫端必須自行處理缺值（不預設 0，避免污染結論）。
  static double? percentile(List<double> values, double p) {
    if (values.isEmpty) return null;
    if (values.length == 1) return values.first;
    final sorted = [...values]..sort();
    final pos = (sorted.length - 1) * p.clamp(0.0, 1.0);
    final lo = pos.floor();
    final hi = pos.ceil();
    if (lo == hi) return sorted[lo];
    final w = pos - lo;
    return sorted[lo] * (1 - w) + sorted[hi] * w;
  }

  static double? mean(List<double> v) {
    if (v.isEmpty) return null;
    return v.reduce((a, b) => a + b) / v.length;
  }

  static double? median(List<double> v) => percentile(v, 0.5);

  static double? stdev(List<double> v) {
    if (v.length < 2) return null;
    final m = mean(v)!;
    final sq = v.map((x) => (x - m) * (x - m)).reduce((a, b) => a + b);
    return math.sqrt(sq / (v.length - 1));
  }

  /// 線性回歸斜率（每單位 x 的變化量）。用於趨勢方向判定。
  static double? slope(List<double> y) {
    if (y.length < 3) return null;
    final n = y.length;
    double sx = 0, sy = 0, sxy = 0, sxx = 0;
    for (var i = 0; i < n; i++) {
      sx += i;
      sy += y[i];
      sxy += i * y[i];
      sxx += i * i;
    }
    final denom = n * sxx - sx * sx;
    if (denom == 0) return null;
    return (n * sxy - sx * sy) / denom;
  }

  /// 年化波動率（%），以日報酬標準差 × √252。
  static double? annualizedVolatility(List<Bar> bars, {int window = 60}) {
    if (bars.length < window + 1) return null;
    final slice = bars.sublist(bars.length - window - 1);
    final rets = <double>[];
    for (var i = 1; i < slice.length; i++) {
      final prev = slice[i - 1].close;
      if (prev <= 0) continue;
      rets.add((slice[i].close - prev) / prev);
    }
    final sd = stdev(rets);
    if (sd == null) return null;
    return sd * math.sqrt(252) * 100;
  }

  /// 平均真實波幅 ATR(n)。回傳「元」，不是百分比。
  static double? atr(List<Bar> bars, {int n = 14}) {
    if (bars.length < n + 1) return null;
    final slice = bars.sublist(bars.length - n - 1);
    final trs = <double>[];
    for (var i = 1; i < slice.length; i++) {
      final h = slice[i].high, l = slice[i].low, pc = slice[i - 1].close;
      final tr = [h - l, (h - pc).abs(), (l - pc).abs()].reduce(math.max);
      trs.add(tr);
    }
    return mean(trs);
  }

  /// 簡單移動平均（取最後一筆）。
  static double? sma(List<Bar> bars, int n) {
    if (bars.length < n) return null;
    final slice = bars.sublist(bars.length - n);
    return mean(slice.map((b) => b.close).toList());
  }

  /// 最大回撤（%），以收盤價計。
  static double? maxDrawdown(List<double> closes) {
    if (closes.length < 2) return null;
    double peak = closes.first;
    double worst = 0;
    for (final c in closes) {
      if (c > peak) peak = c;
      if (peak <= 0) continue;
      final dd = (c - peak) / peak * 100;
      if (dd < worst) worst = dd;
    }
    return worst;
  }

  /// 把數值依 min..max 切成 bins 個區間，回傳每個區間內的元素索引。
  static List<List<int>> bucketize(
      List<double> values, int bins, double min, double max) {
    final out = List.generate(bins, (_) => <int>[]);
    if (max <= min) return out;
    final step = (max - min) / bins;
    for (var i = 0; i < values.length; i++) {
      var idx = ((values[i] - min) / step).floor();
      if (idx < 0) idx = 0;
      if (idx >= bins) idx = bins - 1;
      out[idx].add(i);
    }
    return out;
  }
}
