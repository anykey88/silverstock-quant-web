/// SilverStock v2 — 資料模型與 JSON 解析
///
/// 設計原則：純資料，不做任何 IO，不依賴 Flutter / dart:html。
/// 所有模型都對應 FinMind 公開資料集的原始欄位，避免二次加工導致失真。
library silverstock_v2.data;

// ---------------------------------------------------------------------------
// 行情
// ---------------------------------------------------------------------------

class Bar {
  final String date;
  final double open;
  final double high;
  final double low;
  final double close;
  final double volume; // 股
  final double money; // 元

  const Bar(this.date, this.open, this.high, this.low, this.close,
      this.volume, this.money);

  double get turnover => close * volume;
}

// ---------------------------------------------------------------------------
// 估值（PER / PBR / 殖利率）
// ---------------------------------------------------------------------------

class ValuationPoint {
  final String date;
  final double? per;
  final double? pbr;
  final double? yieldPct; // FinMind 回傳已是百分比（0.88 = 0.88%）

  const ValuationPoint(this.date, this.per, this.pbr, this.yieldPct);
}

// ---------------------------------------------------------------------------
// 財務（單季）
// ---------------------------------------------------------------------------

class Quarter {
  final String date; // 季末，如 2026-06-30
  final double revenue;
  final double? cogs;
  final double? gross;
  final double? operatingIncome;
  final double? netIncome; // 歸屬母公司
  final double? eps;

  const Quarter({
    required this.date,
    required this.revenue,
    this.cogs,
    this.gross,
    this.operatingIncome,
    this.netIncome,
    this.eps,
  });

  int get year => int.parse(date.substring(0, 4));
  int get month => int.parse(date.substring(5, 7));
  int get quarterNo => (month + 2) ~/ 3;

  String get label => '$year Q$quarterNo';

  /// 毛利率（%）
  double? get grossMargin {
    final g = gross ?? (cogs == null ? null : revenue - cogs!);
    if (g == null || revenue == 0) return null;
    return g / revenue * 100;
  }

  double? get operatingMargin {
    if (operatingIncome == null || revenue == 0) return null;
    return operatingIncome! / revenue * 100;
  }

  double? get netMargin {
    if (netIncome == null || revenue == 0) return null;
    return netIncome! / revenue * 100;
  }
}

class BalanceSheet {
  final String date;
  final double? totalAssets;
  final double? equity; // 歸屬母公司
  final double? currentAssets;
  final double? currentLiabilities;
  final double? inventories;
  final double? receivables;
  final double? cash;
  final double? ltDebt;
  final double? stDebt;

  const BalanceSheet({
    required this.date,
    this.totalAssets,
    this.equity,
    this.currentAssets,
    this.currentLiabilities,
    this.inventories,
    this.receivables,
    this.cash,
    this.ltDebt,
    this.stDebt,
  });

  /// 負債比（%）＝ (總資產 − 權益) / 總資產
  double? get debtRatio {
    if (totalAssets == null || equity == null || totalAssets == 0) return null;
    return (totalAssets! - equity!) / totalAssets! * 100;
  }

  double? get currentRatio {
    if (currentAssets == null || currentLiabilities == null) return null;
    if (currentLiabilities == 0) return null;
    return currentAssets! / currentLiabilities!;
  }
}

class CashFlow {
  final String date;
  final double? operating; // 營業活動淨現金流
  final double? capex; // 取得不動產廠房設備（正值表示支出）
  final double? depreciation;
  final double? interestExpense;

  const CashFlow({
    required this.date,
    this.operating,
    this.capex,
    this.depreciation,
    this.interestExpense,
  });

  /// 自由現金流 = 營業現金流 − 資本支出
  double? get freeCashFlow {
    if (operating == null) return null;
    final c = capex ?? 0;
    return operating! - c.abs();
  }
}

// ---------------------------------------------------------------------------
// 月營收
// ---------------------------------------------------------------------------

class MonthRevenue {
  final int year;
  final int month;
  final double revenue;

  const MonthRevenue(this.year, this.month, this.revenue);

  String get label => '$year-${month.toString().padLeft(2, '0')}';
}

// ---------------------------------------------------------------------------
// 三大法人（單位：股，轉張需 ÷1000）
// ---------------------------------------------------------------------------

class InstitutionalDay {
  final String date;
  final double foreignNet; // 外資含外資自營
  final double trustNet; // 投信
  final double dealerNet; // 自營

  const InstitutionalDay(this.date, this.foreignNet, this.trustNet, this.dealerNet);

  double get totalNet => foreignNet + trustNet + dealerNet;

  double get foreignNetLots => foreignNet / 1000;
  double get trustNetLots => trustNet / 1000;
  double get totalNetLots => totalNet / 1000;
}

// ---------------------------------------------------------------------------
// 股利
// ---------------------------------------------------------------------------

class DividendRecord {
  final String date;
  final String year; // 如 "115年第1季"
  final double cash; // 現金股利（元/股）
  final double stock; // 股票股利（元/股）
  final String exDate; // 除息交易日

  const DividendRecord({
    required this.date,
    required this.year,
    required this.cash,
    required this.stock,
    required this.exDate,
  });

  double get total => cash + stock;
}

// ---------------------------------------------------------------------------
// 公司基本資料
// ---------------------------------------------------------------------------

class CompanyInfo {
  final String stockId;
  final String name;
  final String industry;
  final String market; // 上市 / 上櫃
  final String startDate;

  const CompanyInfo({
    required this.stockId,
    required this.name,
    required this.industry,
    required this.market,
    required this.startDate,
  });
}

// ---------------------------------------------------------------------------
// 完整資料包
// ---------------------------------------------------------------------------

class StockDataset {
  final CompanyInfo info;
  final List<Bar> bars; // 由舊到新
  final List<ValuationPoint> valuations;
  final List<Quarter> quarters;
  final List<BalanceSheet> balanceSheets;
  final List<CashFlow> cashFlows;
  final List<MonthRevenue> monthRevenues;
  final List<InstitutionalDay> institutions;
  final List<DividendRecord> dividends;
  final String fetchedAt;

  const StockDataset({
    required this.info,
    required this.bars,
    required this.valuations,
    required this.quarters,
    required this.balanceSheets,
    required this.cashFlows,
    required this.monthRevenues,
    required this.institutions,
    required this.dividends,
    required this.fetchedAt,
  });

  Bar? get latest => bars.isEmpty ? null : bars.last;

  /// 近 N 個交易日
  List<Bar> tailBars(int n) =>
      bars.length <= n ? bars : bars.sublist(bars.length - n);

  /// 近 4 季 EPS 合計（TTM）
  double? get epsTtm {
    if (quarters.isEmpty) return null;
    final valid = quarters.where((q) => q.eps != null).toList();
    if (valid.isEmpty) return null;
    final take = valid.length >= 4 ? valid.sublist(valid.length - 4) : valid;
    return take.fold<double>(0, (s, q) => s + q.eps!);
  }

  /// 近 12 個月現金股利合計（以最近 4 筆有現金股利的紀錄估算年化）
  double get annualCashDividend {
    if (dividends.isEmpty) return 0;
    final sorted = [...dividends]..sort((a, b) => a.date.compareTo(b.date));
    final lastYear = sorted.last.date.substring(0, 4);
    final sameYear =
        sorted.where((d) => d.date.startsWith(lastYear)).toList();
    final pool = sameYear.isNotEmpty
        ? sameYear
        : sorted.sublist(sorted.length > 4 ? sorted.length - 4 : 0);
    return pool.fold<double>(0, (s, d) => s + d.cash);
  }
}
