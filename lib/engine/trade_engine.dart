// ============================================================================
// 交易回測引擎（個人自用版）
// ----------------------------------------------------------------------------
// 與「存股累積型」回測不同，這裡是完整的**模擬交易**：
//   進場 → 加碼 → 停利 / 停損 / 條件出場 → 再進場，並計入手續費與證交稅。
//
// 重要：
// 1. 這是歷史資料的模擬，不是預測，也不構成投資建議。
// 2. 手續費預設 0.1425%（可打 6 折），證交稅 0.3%（ETF 0.1%）。
// 3. 除息以現金入帳，可選擇再投入。
// ============================================================================

import 'dart:math' as math;

import '../models/models.dart';
import '../models/trade_strategy.dart';

/// 一筆已完成的交易
class TradeRecord {
  final String entryDate;
  final String exitDate;
  final double entryPrice;
  final double exitPrice;
  final double shares;
  final double pnl;
  final double pnlPct;
  final int holdDays;
  final String reason; // 停利 / 停損 / 殖利率條件 / 期末持有
  final bool open; // 尚未平倉

  TradeRecord({
    required this.entryDate,
    required this.exitDate,
    required this.entryPrice,
    required this.exitPrice,
    required this.shares,
    required this.pnl,
    required this.pnlPct,
    required this.holdDays,
    required this.reason,
    this.open = false,
  });
}

class TradeResult {
  final String stockId;
  final String stockName;
  final String strategyName;
  final double totalCapital;
  final double finalEquity;
  final double cash;
  final double shares;
  final double avgCost;
  final double totalReturnPct;
  final double cagr;
  final double maxDrawdown;
  final double winRate;
  final double profitFactor;
  final int tradeCount;
  final int winCount;
  final int lossCount;
  final double avgHoldDays;
  final double avgPnlPct;
  final double bestTrade;
  final double worstTrade;
  final double dividendTotal;
  final double feeTotal;
  final double taxTotal;
  final bool holding;
  final List<TradeRecord> records;
  final List<NavPoint> equity;
  final List<String> logs; // 最近幾筆動作，方便除錯與展示

  TradeResult({
    required this.stockId,
    required this.stockName,
    required this.strategyName,
    required this.totalCapital,
    required this.finalEquity,
    required this.cash,
    required this.shares,
    required this.avgCost,
    required this.totalReturnPct,
    required this.cagr,
    required this.maxDrawdown,
    required this.winRate,
    required this.profitFactor,
    required this.tradeCount,
    required this.winCount,
    required this.lossCount,
    required this.avgHoldDays,
    required this.avgPnlPct,
    required this.bestTrade,
    required this.worstTrade,
    required this.dividendTotal,
    required this.feeTotal,
    required this.taxTotal,
    required this.holding,
    required this.records,
    required this.equity,
    required this.logs,
  });

  double get netProfit => finalEquity - totalCapital;
}

class TradeEngine {
  static TradeResult? run(
    StockSeries s,
    TradeStrategy st,
    DateTime start,
    DateTime end, {
    bool isEtf = false,
  }) {
    final startInt = start.year * 10000 + start.month * 100 + start.day;
    final endInt = end.year * 10000 + end.month * 100 + end.day;
    final iStart = s.indexOnOrAfter(startInt);
    var iEnd = s.indexOnOrBefore(endInt);
    if (iEnd < 0 || iEnd >= s.dates.length) iEnd = s.dates.length - 1;
    if (iStart < 0 || iEnd <= iStart + 60) return null;

    final n = iEnd + 1;

    // ---- 預先算好逐日指標 ----
    final ma60 = List<double>.filled(n, 0);
    var run60 = 0.0;
    for (var i = 0; i < n; i++) {
      run60 += s.closes[i];
      if (i >= 60) run60 -= s.closes[i - 60];
      ma60[i] = i >= 59 ? run60 / 60 : s.closes[i];
    }

    final rsiArr = List<double>.filled(n, 50);
    var gain = 0.0, loss = 0.0;
    const period = 14;
    for (var i = 1; i < n; i++) {
      final ch = s.closes[i] - s.closes[i - 1];
      if (i <= period) {
        if (ch >= 0) {
          gain += ch;
        } else {
          loss -= ch;
        }
        if (i == period) {
          gain /= period;
          loss /= period;
          rsiArr[i] = loss == 0 ? 100 : 100 - 100 / (1 + gain / loss);
        }
      } else {
        gain = (gain * (period - 1) + (ch > 0 ? ch : 0)) / period;
        loss = (loss * (period - 1) + (ch < 0 ? -ch : 0)) / period;
        rsiArr[i] = loss == 0 ? 100 : 100 - 100 / (1 + gain / loss);
      }
    }

    // ---- 進場檢查日（依頻率）----
    final checkDays = <int>{};
    if (st.frequency == 'daily') {
      for (var i = iStart; i <= iEnd; i++) {
        checkDays.add(i);
      }
    } else if (st.frequency == 'monthly') {
      var last = -1;
      for (var i = iStart; i <= iEnd; i++) {
        final ym = s.dates[i] ~/ 100;
        if (ym != last) {
          checkDays.add(i);
          last = ym;
        }
      }
    } else {
      // 每週第一個交易日
      var lastKey = '';
      for (var i = iStart; i <= iEnd; i++) {
        final d = _dt(s.dates[i]);
        final key = '${d.year}-${_weekOfYear(d)}';
        if (key != lastKey) {
          checkDays.add(i);
          lastKey = key;
        }
      }
    }

    // ---- 除息事件 ----
    final divByIndex = <int, double>{};
    for (final d in s.dividends) {
      final i = s.indexOnOrAfter(int.parse(d.ym.replaceAll('-', '')) * 100 + 1);
      if (i >= iStart && i <= iEnd) {
        divByIndex[i] = (divByIndex[i] ?? 0) + d.amount;
      }
    }

    // ---- 回測狀態 ----
    final feeRate = 0.001425 * st.feeDiscount;
    final taxRate = isEtf ? 0.001 : 0.003;
    final perMed = s.perMedian;

    var cash = st.totalCapital;
    var shares = 0.0;
    var avgCost = 0.0; // 每股平均成本（含手續費）
    var adds = 0;
    var lastEntryPrice = 0.0;
    var entryIndex = -1;
    var entryDate = '';
    var dividends = 0.0, fees = 0.0, taxes = 0.0;
    final records = <TradeRecord>[];
    final equity = <NavPoint>[];
    final logs = <String>[];

    double positionValue(int i) => shares * s.closes[i];
    double maxPositionValue() => st.totalCapital * st.maxPositionPct / 100;

    bool canEnter(int i) {
      if (st.entryYieldMin != null && s.yieldAt(i) < st.entryYieldMin!) return false;
      if (st.entryPerRatio != null && perMed != null) {
        final per = s.perAt(i);
        if (per != null && per > perMed * st.entryPerRatio!) return false;
      }
      if (st.maMode == 'below') {
        final limit = ma60[i] * (1 - st.maPct / 100);
        if (s.closes[i] > limit) return false;
      } else if (st.maMode == 'above') {
        final floor = ma60[i] * (1 + st.maPct / 100);
        if (s.closes[i] < floor) return false;
      }
      if (st.entryRsiMax != null && rsiArr[i] > st.entryRsiMax!) return false;
      return true;
    }

    void buy(int i, String reason, {bool isAdd = false}) {
      final room = maxPositionValue() - positionValue(i);
      var amount = math.min(st.trancheAmount, math.min(cash, room));
      if (amount < st.trancheAmount * 0.3) return;
      final fee = amount * feeRate;
      final gross = amount - fee;
      final qty = gross / s.closes[i];
      if (qty <= 0) return;
      final newShares = shares + qty;
      avgCost = (avgCost * shares + amount) / newShares;
      shares = newShares;
      cash -= amount;
      fees += fee;
      lastEntryPrice = s.closes[i];
      if (entryIndex < 0) {
        entryIndex = i;
        entryDate = StockSeries.fmtYmd(s.dates[i]);
      }
      if (isAdd) adds++;
      if (logs.length < 40) {
        logs.add('${StockSeries.fmtYmd(s.dates[i])} $reason '
            '${s.closes[i].toStringAsFixed(2)} 元 × ${qty.toStringAsFixed(0)} 股');
      }
    }

    void sell(int i, String reason) {
      if (shares <= 0) return;
      final gross = shares * s.closes[i];
      final fee = gross * feeRate;
      final tax = gross * taxRate;
      final net = gross - fee - tax;
      cash += net;
      fees += fee;
      taxes += tax;
      final cost = avgCost * shares;
      final pnl = net - cost;
      final holdDays = entryIndex >= 0 ? i - entryIndex : 0;
      records.add(TradeRecord(
        entryDate: entryDate,
        exitDate: StockSeries.fmtYmd(s.dates[i]),
        entryPrice: entryIndex >= 0 ? s.closes[entryIndex] : avgCost,
        exitPrice: s.closes[i],
        shares: shares,
        pnl: pnl,
        pnlPct: cost <= 0 ? 0 : pnl / cost * 100,
        holdDays: holdDays,
        reason: reason,
      ));
      if (logs.length < 40) {
        logs.add('${StockSeries.fmtYmd(s.dates[i])} $reason '
            '${s.closes[i].toStringAsFixed(2)} 元，損益 ${pnl >= 0 ? '+' : ''}${pnl.toStringAsFixed(0)} 元');
      }
      shares = 0;
      avgCost = 0;
      adds = 0;
      lastEntryPrice = 0;
      entryIndex = -1;
      entryDate = '';
    }

    for (var i = iStart; i <= iEnd; i++) {
      final price = s.closes[i];

      // 1) 除息
      final div = divByIndex[i];
      if (div != null && shares > 0) {
        final amount = shares * div;
        dividends += amount;
        cash += amount;
        if (st.reinvestDividend) {
          final fee = amount * feeRate;
          shares += (amount - fee) / price;
          fees += fee;
        }
      }

      // 2) 出場優先於進場（風控先行）
      if (shares > 0) {
        final retPct = avgCost <= 0 ? 0.0 : (price - avgCost) / avgCost * 100;
        if (st.stopLossPct != null && retPct <= -st.stopLossPct!) {
          sell(i, '停損（${retPct.toStringAsFixed(1)}%）');
        } else if (st.takeProfitPct != null && retPct >= st.takeProfitPct!) {
          sell(i, '停利（+${retPct.toStringAsFixed(1)}%）');
        } else if (st.exitYieldBelow != null && s.yieldAt(i) < st.exitYieldBelow!) {
          sell(i, '殖利率跌破 ${st.exitYieldBelow!.toStringAsFixed(1)}%');
        } else if (st.addOnDropPct > 0 &&
            adds < st.maxAdds &&
            lastEntryPrice > 0 &&
            price <= lastEntryPrice * (1 - st.addOnDropPct / 100)) {
          buy(i, '加碼（跌 ${st.addOnDropPct.toStringAsFixed(0)}%）', isAdd: true);
        }
      }

      // 3) 進場
      if (shares <= 0 && checkDays.contains(i) && canEnter(i)) {
        buy(i, '進場');
      }

      // 4) 記錄淨值
      final eq = cash + shares * price;
      equity.add(NavPoint(_label(s.dates[i]), eq, (eq / st.totalCapital - 1) * 100));
    }

    final finalEquity = cash + shares * s.closes[iEnd];
    final holding = shares > 0;

    // 期末未平倉 → 記一筆未實現
    if (holding) {
      final gross = shares * s.closes[iEnd];
      final cost = avgCost * shares;
      records.add(TradeRecord(
        entryDate: entryDate,
        exitDate: '${StockSeries.fmtYmd(s.dates[iEnd])}（未平倉）',
        entryPrice: entryIndex >= 0 ? s.closes[entryIndex] : avgCost,
        exitPrice: s.closes[iEnd],
        shares: shares,
        pnl: gross - cost,
        pnlPct: cost <= 0 ? 0 : (gross - cost) / cost * 100,
        holdDays: entryIndex >= 0 ? iEnd - entryIndex : 0,
        reason: '期末仍持有',
        open: true,
      ));
    }

    // ---- 統計 ----
    final closed = records.where((r) => !r.open).toList();
    final win = closed.where((r) => r.pnl > 0).length;
    final lose = closed.where((r) => r.pnl <= 0).length;
    final grossWin = closed.where((r) => r.pnl > 0).fold<double>(0, (a, b) => a + b.pnl);
    final grossLoss = closed.where((r) => r.pnl <= 0).fold<double>(0, (a, b) => a - b.pnl);

    var peak = equity.isEmpty ? st.totalCapital : equity.first.nav;
    var mdd = 0.0;
    for (final p in equity) {
      if (p.nav > peak) peak = p.nav;
      final dd = peak <= 0 ? 0.0 : (peak - p.nav) / peak;
      if (dd > mdd) mdd = dd;
    }

    final years = (iEnd - iStart) / 252.0;
    final cagr = years <= 0
        ? 0.0
        : (math.pow(finalEquity / st.totalCapital, 1 / years).toDouble() - 1) * 100;

    // 曲線抽樣（最多 70 點）
    final step = math.max(1, equity.length ~/ 70);
    final curve = <NavPoint>[];
    for (var k = 0; k < equity.length; k += step) {
      curve.add(equity[k]);
    }
    if (curve.isEmpty || curve.last.label != equity.last.label) curve.add(equity.last);

    return TradeResult(
      stockId: s.id,
      stockName: s.name,
      strategyName: st.name,
      totalCapital: st.totalCapital,
      finalEquity: finalEquity,
      cash: cash,
      shares: shares,
      avgCost: avgCost,
      totalReturnPct: (finalEquity / st.totalCapital - 1) * 100,
      cagr: cagr,
      maxDrawdown: mdd * 100,
      winRate: closed.isEmpty ? 0 : win / closed.length,
      profitFactor: grossLoss <= 0 ? (grossWin > 0 ? 99 : 0) : grossWin / grossLoss,
      tradeCount: closed.length,
      winCount: win,
      lossCount: lose,
      avgHoldDays: closed.isEmpty
          ? 0
          : closed.fold<double>(0, (a, b) => a + b.holdDays) / closed.length,
      avgPnlPct: closed.isEmpty
          ? 0
          : closed.fold<double>(0, (a, b) => a + b.pnlPct) / closed.length,
      bestTrade: closed.isEmpty ? 0 : closed.map((r) => r.pnlPct).reduce(math.max),
      worstTrade: closed.isEmpty ? 0 : closed.map((r) => r.pnlPct).reduce(math.min),
      dividendTotal: dividends,
      feeTotal: fees,
      taxTotal: taxes,
      holding: holding,
      records: records,
      equity: curve,
      logs: logs,
    );
  }

  static DateTime _dt(int ymd) => DateTime(ymd ~/ 10000, (ymd ~/ 100) % 100, ymd % 100);

  static int _weekOfYear(DateTime d) {
    final firstDay = DateTime(d.year, 1, 1);
    return ((d.difference(firstDay).inDays + firstDay.weekday - 1) / 7).floor() + 1;
  }

  static String _label(int ymd) {
    final y = ymd ~/ 10000;
    final m = (ymd ~/ 100) % 100;
    return '$y/${m.toString().padLeft(2, '0')}';
  }
}
