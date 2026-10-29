// ============================================================================
// 資料模型
// ----------------------------------------------------------------------------
// 【資料來源約束】本檔所有歷史資料皆來自 FinMind 公開 API 於建置期抓取的快照
// （assets/data/snapshot.json）。參賽 Demo 使用免費非商用授權，禁止直接用於售賣；
// 商業化必須採購 FinMind 商業授權。
// ============================================================================

class PerPoint {
  final String date; // yyyy-MM-dd
  final double yieldRate; // 殖利率 %
  final double per; // 本益比
  final double pbr; // 股價淨值比
  PerPoint(this.date, this.yieldRate, this.per, this.pbr);

  factory PerPoint.fromJson(List<dynamic> j) =>
      PerPoint(j[0] as String, (j[1] as num).toDouble(), (j[2] as num).toDouble(), (j[3] as num).toDouble());
}

class DivRecord {
  final String ym; // yyyy-MM（除息月份）
  final double amount; // 每股現金股利
  DivRecord(this.ym, this.amount);

  factory DivRecord.fromJson(List<dynamic> j) => DivRecord(j[0] as String, (j[1] as num).toDouble());
}

class QuarterEps {
  final String ym; // yyyy-MM
  final double eps; // 單季 EPS
  QuarterEps(this.ym, this.eps);

  factory QuarterEps.fromJson(List<dynamic> j) => QuarterEps(j[0] as String, (j[1] as num).toDouble());
}

/// 單一標的的歷史資料序列。
class StockSeries {
  final String id;
  final String name;
  final String industry;
  final List<int> dates; // yyyymmdd
  final List<double> closes;
  final List<int> volumes; // 成交量（張）
  final List<PerPoint> per;
  final List<DivRecord> dividends;
  final List<QuarterEps> eps;

  StockSeries({
    required this.id,
    required this.name,
    required this.industry,
    required this.dates,
    required this.closes,
    this.volumes = const <int>[],
    required this.per,
    required this.dividends,
    required this.eps,
  }) {
    _buildTtmDividend();
  }

  /// 近 12 個月每股現金股利（用於推估當下殖利率）
  late final List<double> _ttmDiv = List<double>.filled(dates.length, 0);

  void _buildTtmDividend() {
    // 把每筆股利的除息月份，對應到「該月第一個交易日」
    final exIdx = <int>[];
    final exAmt = <double>[];
    for (final d in dividends) {
      final ymInt = int.parse(d.ym.replaceAll('-', ''));
      final i = indexOnOrAfter(ymInt * 100 + 1);
      if (i >= 0) {
        exIdx.add(i);
        exAmt.add(d.amount);
      }
    }
    if (exIdx.isEmpty) return;
    var sum = 0.0;
    var lo = 0;
    for (var i = 0; i < dates.length; i++) {
      for (var k = 0; k < exIdx.length; k++) {
        if (exIdx[k] == i) sum += exAmt[k];
      }
      // 移除超過 365 天的股利
      final cutoff = _minusOneYear(dates[i]);
      while (lo < exIdx.length && dates[exIdx[lo]] < cutoff) {
        sum -= exAmt[lo];
        lo++;
      }
      _ttmDiv[i] = sum;
    }
  }

  static int _minusOneYear(int yyyymmdd) {
    final y = yyyymmdd ~/ 10000;
    final m = (yyyymmdd ~/ 100) % 100;
    final d = yyyymmdd % 100;
    return (y - 1) * 10000 + m * 100 + d;
  }

  int indexOnOrAfter(int yyyymmdd) {
    var lo = 0, hi = dates.length - 1, ans = -1;
    while (lo <= hi) {
      final mid = (lo + hi) >> 1;
      if (dates[mid] >= yyyymmdd) {
        ans = mid;
        hi = mid - 1;
      } else {
        lo = mid + 1;
      }
    }
    return ans;
  }

  int indexOnOrBefore(int yyyymmdd) {
    var lo = 0, hi = dates.length - 1, ans = -1;
    while (lo <= hi) {
      final mid = (lo + hi) >> 1;
      if (dates[mid] <= yyyymmdd) {
        ans = mid;
        lo = mid + 1;
      } else {
        hi = mid - 1;
      }
    }
    return ans;
  }

  /// 當日推估殖利率（近 12 個月現金股利 ÷ 收盤價）
  double yieldAt(int i) {
    if (i < 0 || i >= closes.length || closes[i] <= 0) return 0;
    return _ttmDiv[i] / closes[i] * 100;
  }

  /// 當日本益比（取當月或之前最近一筆 FinMind PER 資料；ETF 無此資料回傳 null）
  double? perAt(int i) {
    if (per.isEmpty || i < 0) return null;
    final target = dates[i] ~/ 100; // yyyymm
    PerPoint? hit;
    for (final p in per) {
      final ym = int.parse(p.date.substring(0, 7).replaceAll('-', ''));
      if (ym <= target && p.per > 0) {
        hit = p;
      } else if (ym > target) {
        break;
      }
    }
    return hit?.per;
  }

  /// 最近一筆本益比資料
  PerPoint? get latestPer => per.isEmpty ? null : per.last;

  /// 近 5 年本益比中位數（用於低本益比檢視策略）
  double? get perMedian {
    final vals = per.where((p) => p.per > 0).map((p) => p.per).toList()..sort();
    if (vals.length < 6) return null;
    return vals[vals.length ~/ 2];
  }

  Map<int, List<double>> get _epsByYear {
    final m = <int, List<double>>{};
    for (final q in eps) {
      final y = int.parse(q.ym.substring(0, 4));
      m.putIfAbsent(y, () => <double>[]).add(q.eps);
    }
    return m;
  }

  /// 完整年度 EPS（只計入四個季度都公布的年度，避免把「今年只公布到 Q2」誤當全年）
  Map<int, double> get annualEps {
    final m = <int, double>{};
    _epsByYear.forEach((y, v) {
      if (v.length >= 4) m[y] = v.fold<double>(0, (a, b) => a + b);
    });
    return m;
  }

  /// 未滿一年的年度累計 EPS（例如今年只公布到第 2 季）
  Map<int, double> get partialYearEps {
    final m = <int, double>{};
    _epsByYear.forEach((y, v) {
      if (v.length < 4) m[y] = v.fold<double>(0, (a, b) => a + b);
    });
    return m;
  }

  int quartersOf(int year) => _epsByYear[year]?.length ?? 0;

  /// 最近 n 日平均成交量（張）
  double avgVolume(int n) {
    if (volumes.isEmpty) return 0;
    final from = volumes.length > n ? volumes.length - n : 0;
    final slice = volumes.sublist(from);
    return slice.reduce((a, b) => a + b) / slice.length;
  }

  /// 近 4 季 EPS 合計（TTM）
  double? get ttmEps {
    if (eps.length < 4) return null;
    final last4 = eps.sublist(eps.length - 4);
    return last4.fold<double>(0, (a, b) => a + b.eps);
  }

  factory StockSeries.fromJson(String id, Map<String, dynamic> j) {
    return StockSeries(
      id: id,
      name: j['name'] as String,
      industry: j['industry'] as String,
      dates: (j['dates'] as List).map((e) => e as int).toList(),
      closes: (j['closes'] as List).map((e) => (e as num).toDouble()).toList(),
      volumes: (j['volumes'] as List?)?.map((e) => (e as num).toInt()).toList() ??
          const <int>[],
      per: (j['perSeries'] as List).map((e) => PerPoint.fromJson(e as List)).toList(),
      dividends: (j['dividends'] as List).map((e) => DivRecord.fromJson(e as List)).toList(),
      eps: (j['quarterlyEps'] as List).map((e) => QuarterEps.fromJson(e as List)).toList(),
    );
  }

  String get firstDateText => fmtYmd(dates.first);
  String get lastDateText => fmtYmd(dates.last);

  /// yyyymmdd → yyyy/M/d（公開工具，供 Agent 層輸出報告文字使用）
  static String fmtYmd(int yyyymmdd) {
    final y = yyyymmdd ~/ 10000;
    final m = (yyyymmdd ~/ 100) % 100;
    final d = yyyymmdd % 100;
    return '$y/$m/$d';
  }
}

/// 回測淨值曲線的一個點
class NavPoint {
  final String label; // yyyy/MM
  final double nav; // 淨值（起始 1.0）
  final double cumReturn; // 累積報酬率 %
  NavPoint(this.label, this.nav, this.cumReturn);
}

/// 單一策略的回測結果（僅歷史模擬，不代表未來）
class BacktestResult {
  final String strategyId;
  final String strategyName;
  final int months;
  final double totalInvested;
  final double finalValue;
  final double dividendCash;
  final double shares;
  final double irr; // 年化（內部報酬率）
  final double maxDrawdown; // 正值百分比
  final double winRate; // 0~1
  final int winYears;
  final int totalYears;
  final List<NavPoint> nav;
  final double startPrice;
  final double endPrice;
  final double avgCost; // 平均每股投入成本
  final int boostMonths; // 加碼（多投入）月份數
  final int pauseMonths; // 該月不投入的月份數

  BacktestResult({
    required this.strategyId,
    required this.strategyName,
    required this.months,
    required this.totalInvested,
    required this.finalValue,
    required this.dividendCash,
    required this.shares,
    required this.irr,
    required this.maxDrawdown,
    required this.winRate,
    required this.winYears,
    required this.totalYears,
    required this.nav,
    required this.startPrice,
    required this.endPrice,
    required this.avgCost,
    this.boostMonths = 0,
    this.pauseMonths = 0,
  });

  double get profit => finalValue - totalInvested;
  double get totalReturnPct => totalInvested <= 0 ? 0 : (finalValue / totalInvested - 1) * 100;
}

/// 風險提示（規則偵測，非主觀判斷）
class RiskItem {
  final String level; // 'high' | 'watch'
  final String title;
  final String detail;
  RiskItem(this.level, this.title, this.detail);
}

/// 基本面摘要（Agent 1 輸出，不含任何投資判斷）
class FundamentalReport {
  final double? yieldRate;
  final double? per;
  final double? pbr;
  final double? ttmEps;
  final Map<int, double> annualEps;
  final Map<int, double> partialEps;
  final List<DivRecord> recentDividends;
  final List<RiskItem> risks;
  final String perDate;
  FundamentalReport({
    required this.yieldRate,
    required this.per,
    required this.pbr,
    required this.ttmEps,
    required this.annualEps,
    this.partialEps = const <int, double>{},
    required this.recentDividends,
    required this.risks,
    required this.perDate,
  });
}

/// 技術指標（Agent 2 輸出，僅數值，不給買賣訊號）
class TechnicalReport {
  final double ma5, ma20, ma60;
  final double k, d, rsi, dif, dea, macd;
  final double lastClose;
  TechnicalReport({
    required this.ma5,
    required this.ma20,
    required this.ma60,
    required this.k,
    required this.d,
    required this.rsi,
    required this.dif,
    required this.dea,
    required this.macd,
    required this.lastClose,
  });
}

/// 合規風控結果（Agent 5 輸出）
class ComplianceResult {
  final bool passed;
  final bool blocked;
  final List<String> rewrittenTerms;
  final List<String> alerts;
  final String text; // 已改寫並附上免責聲明的文本
  ComplianceResult({
    required this.passed,
    required this.blocked,
    required this.rewrittenTerms,
    required this.alerts,
    required this.text,
  });
}

/// 一份完整報告（前端渲染 + localStorage 存檔用）
class ReportBundle {
  final String id;
  final String stockId;
  final String stockName;
  final String strategyId;
  final String strategyName;
  final int years;
  final String startDate;
  final String endDate;
  final String createdAt;
  final FundamentalReport? fundamental;
  final TechnicalReport? technical;
  final BacktestResult? primary;
  final Map<String, BacktestResult> comparison; // 三套策略對照
  final String narrative; // 大白話報告
  final String speechScript; // 語音播報稿
  final ComplianceResult? compliance;
  ReportBundle({
    required this.id,
    required this.stockId,
    required this.stockName,
    required this.strategyId,
    required this.strategyName,
    required this.years,
    required this.startDate,
    required this.endDate,
    required this.createdAt,
    this.fundamental,
    this.technical,
    this.primary,
    this.comparison = const {},
    this.narrative = '',
    this.speechScript = '',
    this.compliance,
  });
}
