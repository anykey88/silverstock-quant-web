// ============================================================================
// 技術指標計算（對應「技術指標 Agent」）
// ----------------------------------------------------------------------------
// 此處只輸出「數值」，不輸出買賣訊號、評分或建議。
// 只計算長輩常用的 4 組指標：MA、KD、RSI、MACD，其餘冷門指標一律不實作。
// ============================================================================

import '../models/models.dart';

class Indicators {
  /// 簡單移動平均（取最後 n 筆）
  static double sma(List<double> closes, int n) {
    if (closes.isEmpty) return 0;
    final from = closes.length > n ? closes.length - n : 0;
    final slice = closes.sublist(from);
    return slice.reduce((a, b) => a + b) / slice.length;
  }

  /// KD（9,3,3）
  static List<double> kd(List<double> closes, {int n = 9}) {
    if (closes.length < n) return <double>[50, 50];
    var k = 50.0, d = 50.0;
    for (var i = n - 1; i < closes.length; i++) {
      final window = closes.sublist(i - n + 1, i + 1);
      final hi = window.reduce((a, b) => a > b ? a : b);
      final lo = window.reduce((a, b) => a < b ? a : b);
      final rsv = hi == lo ? 50.0 : (closes[i] - lo) / (hi - lo) * 100;
      k = 2 / 3 * k + 1 / 3 * rsv;
      d = 2 / 3 * d + 1 / 3 * k;
    }
    return <double>[k, d];
  }

  /// RSI（Wilder 平滑，預設 14 日）
  static double rsi(List<double> closes, {int n = 14}) {
    if (closes.length < n + 1) return 50;
    var gain = 0.0, loss = 0.0;
    for (var i = 1; i <= n; i++) {
      final ch = closes[i] - closes[i - 1];
      if (ch >= 0) {
        gain += ch;
      } else {
        loss -= ch;
      }
    }
    gain /= n;
    loss /= n;
    for (var i = n + 1; i < closes.length; i++) {
      final ch = closes[i] - closes[i - 1];
      gain = (gain * (n - 1) + (ch > 0 ? ch : 0)) / n;
      loss = (loss * (n - 1) + (ch < 0 ? -ch : 0)) / n;
    }
    if (loss == 0) return 100;
    final rs = gain / loss;
    return 100 - 100 / (1 + rs);
  }

  /// MACD（12,26,9）
  static List<double> macd(List<double> closes) {
    if (closes.length < 27) return <double>[0, 0, 0];
    final ema12 = _ema(closes, 12);
    final ema26 = _ema(closes, 26);
    final difSeries = <double>[];
    // 逐日計算 DIF，才能再算 DEA
    double e12 = closes[0], e26 = closes[0];
    const a12 = 2 / 13, a26 = 2 / 27;
    for (var i = 0; i < closes.length; i++) {
      e12 = i == 0 ? closes[0] : e12 + a12 * (closes[i] - e12);
      e26 = i == 0 ? closes[0] : e26 + a26 * (closes[i] - e26);
      difSeries.add(e12 - e26);
    }
    final dea = _ema(difSeries, 9);
    final dif = ema12 - ema26;
    return <double>[dif, dea, dif - dea];
  }

  static double _ema(List<double> v, int n) {
    if (v.isEmpty) return 0;
    final a = 2 / (n + 1);
    var e = v[0];
    for (var i = 1; i < v.length; i++) {
      e = e + a * (v[i] - e);
    }
    return e;
  }

  static TechnicalReport build(StockSeries s, {int? endIndex}) {
    final end = endIndex ?? s.closes.length;
    final closes = s.closes.sublist(0, end);
    final kdVal = kd(closes);
    final m = macd(closes);
    return TechnicalReport(
      ma5: sma(closes, 5),
      ma20: sma(closes, 20),
      ma60: sma(closes, 60),
      k: kdVal[0],
      d: kdVal[1],
      rsi: rsi(closes),
      dif: m[0],
      dea: m[1],
      macd: m[2],
      lastClose: closes.isEmpty ? 0 : closes.last,
    );
  }
}
