/// SilverStock v2 — FinMind JSON → 領域模型
///
/// FinMind 的財報類資料集是長表（date, type, value），此處 pivot 成季度寬表。
/// 解析失敗一律回傳空集合，不拋錯、不補值——缺資料就讓上層顯示「無資料」。
library silverstock_v2.parse;

import 'dart:convert';

import 'data.dart';

double? _d(dynamic v) {
  if (v == null) return null;
  if (v is num) return v.toDouble();
  if (v is String) return double.tryParse(v);
  return null;
}

String _s(dynamic v) => v == null ? '' : v.toString();

StockDataset parseDatasetFromString(String raw) {
  final map = jsonDecode(raw) as Map<String, dynamic>;
  return parseDataset(map);
}

StockDataset parseDataset(Map<String, dynamic> root) {
  final sid = _s(root['stock_id']);
  final ds = (root['datasets'] as Map?)?.cast<String, dynamic>() ?? {};
  final infoRaw = (root['info'] as Map?)?.cast<String, dynamic>() ?? {};

  final info = CompanyInfo(
    stockId: sid,
    name: _s(infoRaw['stock_name']),
    industry: _s(infoRaw['industry_category']),
    market: _s(infoRaw['type']),
    startDate: _s(infoRaw['start_date']),
  );

  // --- 行情 ---------------------------------------------------------------
  final bars = <Bar>[];
  for (final r in (ds['TaiwanStockPrice'] as List? ?? const [])) {
    final m = (r as Map).cast<String, dynamic>();
    final close = _d(m['close']) ?? 0;
    final open = _d(m['open']) ?? close;
    final high = _d(m['max']) ?? close;
    final low = _d(m['min']) ?? close;
    if (close <= 0) continue; // 停牌日直接剔除，不補前值（會在報告中標註）
    bars.add(Bar(
      _s(m['date']),
      open,
      high,
      low,
      close,
      _d(m['Trading_Volume']) ?? 0,
      _d(m['Trading_money']) ?? 0,
    ));
  }
  bars.sort((a, b) => a.date.compareTo(b.date));

  // --- 估值 ---------------------------------------------------------------
  final vals = <ValuationPoint>[];
  for (final r in (ds['TaiwanStockPER'] as List? ?? const [])) {
    final m = (r as Map).cast<String, dynamic>();
    final y = _d(m['dividend_yield']);
    vals.add(ValuationPoint(
      _s(m['date']),
      _d(m['PER']),
      _d(m['PBR']),
      y == null ? null : y, // 已是百分比
    ));
  }
  vals.sort((a, b) => a.date.compareTo(b.date));

  // --- 財報：長表 pivot 成季度 ---------------------------------------------
  Map<String, Map<String, double>> pivot(List? rows) {
    final out = <String, Map<String, double>>{};
    for (final r in (rows ?? const [])) {
      final m = (r as Map).cast<String, dynamic>();
      final date = _s(m['date']);
      final type = _s(m['type']);
      final v = _d(m['value']);
      if (date.isEmpty || type.isEmpty || v == null) continue;
      out.putIfAbsent(date, () => <String, double>{})[type] = v;
    }
    return out;
  }

  final fsPivot = pivot(ds['TaiwanStockFinancialStatements'] as List?);
  final quarters = <Quarter>[];
  fsPivot.forEach((date, m) {
    final rev = m['Revenue'];
    if (rev == null) return;
    quarters.add(Quarter(
      date: date,
      revenue: rev,
      cogs: m['CostOfGoodsSold'],
      gross: m['GrossProfit'],
      operatingIncome: m['OperatingIncome'],
      netIncome: m['EquityAttributableToOwnersOfParent'] ?? m['IncomeAfterTaxes'],
      eps: m['EPS'],
    ));
  });
  quarters.sort((a, b) => a.date.compareTo(b.date));

  final bsPivot = pivot(ds['TaiwanStockBalanceSheet'] as List?);
  final balanceSheets = <BalanceSheet>[];
  bsPivot.forEach((date, m) {
    balanceSheets.add(BalanceSheet(
      date: date,
      totalAssets: m['TotalAssets'],
      equity: m['EquityAttributableToOwnersOfParent'],
      currentAssets: m['CurrentAssets'],
      currentLiabilities: m['CurrentLiabilities'],
      inventories: m['Inventories'],
      receivables: m['AccountsReceivableNet'],
      cash: m['CashAndCashEquivalents'],
      ltDebt: m['LongtermBorrowings'],
      stDebt: m['ShorttermBorrowings'],
    ));
  });
  balanceSheets.sort((a, b) => a.date.compareTo(b.date));

  final cfPivot = pivot(ds['TaiwanStockCashFlowsStatement'] as List?);
  final cashFlows = <CashFlow>[];
  cfPivot.forEach((date, m) {
    cashFlows.add(CashFlow(
      date: date,
      operating: m['CashFlowsFromOperatingActivities'] ??
          m['NetCashInflowFromOperatingActivities'],
      capex: m['PropertyAndPlantAndEquipment'],
      depreciation: m['Depreciation'],
      interestExpense: m['InterestExpense'],
    ));
  });
  cashFlows.sort((a, b) => a.date.compareTo(b.date));

  // --- 月營收 -------------------------------------------------------------
  final revs = <MonthRevenue>[];
  for (final r in (ds['TaiwanStockMonthRevenue'] as List? ?? const [])) {
    final m = (r as Map).cast<String, dynamic>();
    final rev = _d(m['revenue']);
    final mo = (m['revenue_month'] as num?)?.toInt();
    final yr = (m['revenue_year'] as num?)?.toInt();
    if (rev == null || mo == null || yr == null) continue;
    revs.add(MonthRevenue(yr, mo, rev));
  }
  revs.sort((a, b) => a.year != b.year
      ? a.year.compareTo(b.year)
      : a.month.compareTo(b.month));

  // --- 三大法人 -----------------------------------------------------------
  final instMap = <String, List<double>>{}; // date -> [foreign, trust, dealer]
  for (final r in (ds['TaiwanStockInstitutionalInvestorsBuySell'] as List? ??
      const [])) {
    final m = (r as Map).cast<String, dynamic>();
    final date = _s(m['date']);
    final name = _s(m['name']);
    final net = (_d(m['buy']) ?? 0) - (_d(m['sell']) ?? 0);
    final slot = instMap.putIfAbsent(date, () => [0, 0, 0]);
    if (name.startsWith('Foreign')) {
      slot[0] += net;
    } else if (name == 'Investment_Trust') {
      slot[1] += net;
    } else if (name.startsWith('Dealer')) {
      slot[2] += net;
    }
  }
  final institutions = instMap.entries
      .map((e) => InstitutionalDay(e.key, e.value[0], e.value[1], e.value[2]))
      .toList()
    ..sort((a, b) => a.date.compareTo(b.date));

  // --- 股利 ---------------------------------------------------------------
  final dividends = <DividendRecord>[];
  for (final r in (ds['TaiwanStockDividend'] as List? ?? const [])) {
    final m = (r as Map).cast<String, dynamic>();
    final cash = (_d(m['CashEarningsDistribution']) ?? 0) +
        (_d(m['CashStatutorySurplus']) ?? 0);
    final stock = (_d(m['StockEarningsDistribution']) ?? 0) +
        (_d(m['StockStatutorySurplus']) ?? 0);
    if (cash == 0 && stock == 0) continue;
    dividends.add(DividendRecord(
      date: _s(m['date']),
      year: _s(m['year']),
      cash: cash,
      stock: stock,
      exDate: _s(m['CashExDividendTradingDate']),
    ));
  }
  dividends.sort((a, b) => a.date.compareTo(b.date));

  return StockDataset(
    info: info,
    bars: bars,
    valuations: vals,
    quarters: quarters,
    balanceSheets: balanceSheets,
    cashFlows: cashFlows,
    monthRevenues: revs,
    institutions: institutions,
    dividends: dividends,
    fetchedAt: _s(root['fetched_at']),
  );
}
