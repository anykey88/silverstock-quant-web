// ============================================================================
// 量化回測引擎（對應「量化回測 Agent」）
// ----------------------------------------------------------------------------
// 【合規約束】
// 1. 只做「歷史資料模擬」，不接券商、不下單、不預測。
// 2. 全部結果僅描述過去，不代表未來；圖表強制疊加「歷史回測不等於未來收益」水印。
// 3. 三套策略都是「分批投入並持有」的模擬，不含放空、融資、當沖等操作。
// ============================================================================

import 'dart:math' as math;

import '../core/constants.dart';
import '../models/models.dart';

class BacktestEngine {
  /// 執行單一策略的歷史模擬。
  /// 回傳 null 表示該策略對這個標的無適用資料（例如 ETF 沒有本益比資料）。
  static BacktestResult? run(
    StockSeries s,
    StrategyDef strat,
    DateTime start,
    DateTime end, {
    double budget = kMonthlyBudget,
  }) {
    final startInt = start.year * 10000 + start.month * 100 + start.day;
    final endInt = end.year * 10000 + end.month * 100 + end.day;
    final iStart = s.indexOnOrAfter(startInt);
    final iEnd = s.indexOnOrBefore(endInt);
    if (iStart < 0 || iEnd <= iStart + 20) return null;

    // 每月第一個交易日為投入日
    final buyIdx = <int>[];
    var lastYm = -1;
    for (var i = iStart; i <= iEnd; i++) {
      final ym = s.dates[i] ~/ 100;
      if (ym != lastYm) {
        buyIdx.add(i);
        lastYm = ym;
      }
    }

    // 除息事件：對應到該月第一個交易日
    final divByIndex = <int, double>{};
    for (final d in s.dividends) {
      final i = s.indexOnOrAfter(int.parse(d.ym.replaceAll('-', '')) * 100 + 1);
      if (i >= iStart && i <= iEnd) {
        divByIndex[i] = (divByIndex[i] ?? 0) + d.amount;
      }
    }

    // 低本益比策略需要本益比資料
    final perMed = s.perMedian;
    if (strat.id == 'low_per' && perMed == null) return null;

    // 季線（60 日均線）逐日計算
    final ma60 = List<double>.filled(s.closes.length, 0);
    var running = 0.0;
    for (var i = 0; i < s.closes.length; i++) {
      running += s.closes[i];
      if (i >= 60) running -= s.closes[i - 60];
      ma60[i] = i >= 59 ? running / 60 : s.closes[i];
    }

    var shares = 0.0;
    var cash = 0.0; // 累積現金股利
    var units = 0.0; // 投入單位（用於計算淨值，避免分期投入扭曲報酬率）
    var invested = 0.0;
    var dividendCash = 0.0;
    var boostMonths = 0;
    var pauseMonths = 0;
    final navDaily = <double>[];
    final navLabel = <String>[];
    final buyAmounts = <double>[];

    final buySet = buyIdx.toSet();
    for (var i = iStart; i <= iEnd; i++) {
      if (buySet.contains(i)) {
        final mult = _multiplier(s, strat, i, ma60, perMed);
        if (mult <= 0) {
          pauseMonths++;
        } else {
          final amount = budget * mult;
          if (mult > 1.0) boostMonths++;
          final valueBefore = shares * s.closes[i] + cash;
          if (units <= 0 || valueBefore <= 0) {
            units = amount; // 起始淨值設為 1
          } else {
            units += amount * units / valueBefore;
          }
          shares += amount / s.closes[i];
          invested += amount;
          buyAmounts.add(amount);
        }
      }
      final d = divByIndex[i];
      if (d != null && shares > 0) {
        cash += shares * d;
        dividendCash += shares * d;
      }
      final value = shares * s.closes[i] + cash;
      final nav = units > 0 ? value / units : 1.0;
      navDaily.add(nav);
      navLabel.add(_label(s.dates[i]));
    }

    if (invested <= 0 || shares <= 0) return null;

    final finalValue = shares * s.closes[iEnd] + cash;

    // 最大回撤（以淨值計）
    var peak = navDaily.first;
    var mdd = 0.0;
    for (final v in navDaily) {
      if (v > peak) peak = v;
      final dd = peak <= 0 ? 0.0 : (peak - v) / peak;
      if (dd > mdd) mdd = dd;
    }

    // 年度勝率：每年最後一個淨值 vs 前一年最後一個淨值
    final yearEndNav = <int, double>{};
    var lastYear = -1;
    for (var k = 0; k < navDaily.length; k++) {
      final y = s.dates[iStart + k] ~/ 10000;
      if (y != lastYear) lastYear = y;
      yearEndNav[y] = navDaily[k];
    }
    var win = 0, total = 0;
    final yearsList = yearEndNav.keys.toList()..sort();
    for (var k = 1; k < yearsList.length; k++) {
      total++;
      if (yearEndNav[yearsList[k]]! > yearEndNav[yearsList[k - 1]]!) win++;
    }

    // 年化內部報酬率（IRR）：把每筆投入的時點都算進去
    final flows = <double>[]; // 負值=投入，正值=期末價值
    final times = <double>[];
    // 依實際投入日重算現金流
    var bi = 0;
    for (var i = iStart; i <= iEnd; i++) {
      if (buySet.contains(i)) {
        final mult = _multiplier(s, strat, i, ma60, perMed);
        if (mult > 0 && bi < buyAmounts.length) {
          flows.add(-buyAmounts[bi]);
          times.add((i - iStart) / 252.0);
          bi++;
        }
      }
    }
    flows.add(finalValue);
    times.add((iEnd - iStart) / 252.0);
    final irr = _irr(flows, times);

    // 每月取樣畫曲線（最多約 70 點）
    final step = math.max(1, navDaily.length ~/ 70);
    final navPts = <NavPoint>[];
    for (var k = 0; k < navDaily.length; k += step) {
      navPts.add(NavPoint(navLabel[k], navDaily[k], (navDaily[k] - 1) * 100));
    }
    if (navPts.isEmpty || navPts.last.label != navLabel.last) {
      navPts.add(NavPoint(navLabel.last, navDaily.last, (navDaily.last - 1) * 100));
    }

    return BacktestResult(
      strategyId: strat.id,
      strategyName: strat.name,
      months: buyIdx.length,
      totalInvested: invested,
      finalValue: finalValue,
      dividendCash: dividendCash,
      shares: shares,
      irr: irr * 100,
      maxDrawdown: mdd * 100,
      winRate: total == 0 ? 0 : win / total,
      winYears: win,
      totalYears: total,
      nav: navPts,
      startPrice: s.closes[iStart],
      endPrice: s.closes[iEnd],
      avgCost: invested / shares,
      boostMonths: boostMonths,
      pauseMonths: pauseMonths,
    );
  }

  static double _multiplier(
      StockSeries s, StrategyDef strat, int i, List<double> ma60, double? perMed) {
    switch (strat.id) {
      case 'yield_dca':
        final y = s.yieldAt(i);
        if (y >= 5.0) return 2.0;
        if (y >= 4.0) return 1.5;
        return 1.0;
      case 'ma_batch':
        final r = s.closes[i] / (ma60[i] <= 0 ? s.closes[i] : ma60[i]);
        if (r <= 0.90) return 3.0;
        if (r <= 0.95) return 2.0;
        return 1.0;
      case 'low_per':
        final p = s.perAt(i);
        if (p == null || perMed == null || perMed <= 0) return 0;
        final ratio = p / perMed;
        if (ratio <= 0.85) return 2.0;
        if (ratio <= 1.00) return 1.0;
        if (ratio <= 1.10) return 0.5;
        return 0;
      default:
        return 1.0;
    }
  }

  static String _label(int yyyymmdd) {
    final y = yyyymmdd ~/ 10000;
    final m = (yyyymmdd ~/ 100) % 100;
    return '$y/${m.toString().padLeft(2, '0')}';
  }

  /// 以二分法求解年化 IRR
  static double _irr(List<double> flows, List<double> times) {
    double f(double r) {
      var sum = 0.0;
      for (var i = 0; i < flows.length; i++) {
        sum += flows[i] / math.pow(1 + r, times[i]);
      }
      return sum;
    }

    var lo = -0.95, hi = 3.0;
    if (f(lo) * f(hi) > 0) return 0;
    for (var k = 0; k < 200; k++) {
      final mid = (lo + hi) / 2;
      if (f(lo) * f(mid) <= 0) {
        hi = mid;
      } else {
        lo = mid;
      }
    }
    return (lo + hi) / 2;
  }
}
