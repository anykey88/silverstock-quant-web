// ============================================================================
// 個股詳情資料層（V2.7 新增）
// ----------------------------------------------------------------------------
// 設計：詳情頁不重複造輪子，直接組裝現有的兩個資料源——
//   · MarketRepository（assets/data/snapshot.json 的 111 檔歷史快照）：
//     日線、成交量、現金股利、單季 EPS、本益比／殖利率序列。
//   · FamilyListsService（family_lists.json 的 77 檔清單）：
//     即使不在快照內，也能給出「名稱／產業／收盤／殖利率／本益比／股淨比」基本資料。
//
// 離線優先：snapshot 內的標的給出完整詳情；不在快照內的 46 檔只顯示基本資料，
// 並標註「資料待補」（月營收 YoY 在快照中無對應資料集，一律標註待補）。
//
// 填息天數定義：以除息當月第一個交易日為除息日，往前取一日收盤為基準價 P0；
// 除息後股價會因扣息而下滑，紀錄「股價再度站回 P0 」所需的交易日數。
// 若 250 個交易日內未回到 P0，視為「未填息／觀察中」（回傳 null）。
// ============================================================================

import 'dart:math' as math;

import '../data/market_repository.dart';
import '../models/models.dart';
import '../services/family_lists.dart';

/// 單一年度現金股利紀錄
class DivRow {
  final int year;
  final double cash; // 每股現金股利
  final String exMonth; // 除息月份 yyyy-MM
  final int? fillDays; // 填息天數（null = 觀察中／未填息）

  const DivRow({
    required this.year,
    required this.cash,
    required this.exMonth,
    this.fillDays,
  });
}

/// 單一年度 EPS（完整年度，四個季度都公布）
class EpsYear {
  final int year;
  final double eps;

  const EpsYear({required this.year, required this.eps});
}

/// 殖利率區間（取快照中本益比序列裡的殖利率資料）
class YieldRange {
  final double min;
  final double max;
  final double avg;

  const YieldRange({required this.min, required this.max, required this.avg});
}

class StockDetail {
  final String id;
  final String name;
  final String industry;
  final String group;
  final double close;
  final double? yieldPct;
  final double? pe;
  final double? pb;

  /// 是否有歷史快照（決定是否顯示走勢／股利／EPS 等深資料）
  final bool hasSeries;

  final List<int> dates;
  final List<double> closes;
  final List<int> volumes;

  final List<DivRow> dividends;
  final YieldRange? yieldRange;
  final double? payoutRatio; // 最新完整年度 現金股利 ÷ 年度 EPS
  final List<EpsYear> epsYears;

  /// 月營收 YoY：快照無此資料集，固定 false（詳情頁顯示「資料待補」）
  final bool revenueAvailable = false;

  /// 資料來源：'snapshot'（完整）｜'basic'（僅清單基本資料）
  final String source;

  const StockDetail({
    required this.id,
    required this.name,
    required this.industry,
    required this.group,
    required this.close,
    required this.yieldPct,
    required this.pe,
    required this.pb,
    required this.hasSeries,
    required this.dates,
    required this.closes,
    required this.volumes,
    required this.dividends,
    required this.yieldRange,
    required this.payoutRatio,
    required this.epsYears,
    required this.source,
  });
}

class StockDetailService {
  /// 同步快取（同一 session 內多次進入同一檔不重算）
  static final Map<String, StockDetail> _cache = <String, StockDetail>{};

  /// 由 family_lists 找基本資料（77 檔都在這裡）
  static Future<FamilyItem?> _basic(String id) async {
    final data = await FamilyListsService.load();
    for (final L in data.lists) {
      for (final it in L.items) {
        if (it.id == id) return it;
      }
    }
    return null;
  }

  static int? _fillDays(StockSeries s, String ym, double cash) {
    if (s.closes.length < 2) return null;
    final target = int.parse(ym.replaceAll('-', '')) * 100 + 1; // yyyymm01
    final idx = s.indexOnOrAfter(target);
    if (idx < 1 || idx >= s.closes.length) return null;
    final p0 = s.closes[idx - 1]; // 除息前一日收盤（扣息前）
    if (p0 <= 0) return null;
    const window = 250;
    final end = math.min(s.closes.length, idx + window);
    for (var k = 1; k < end - idx; k++) {
      if (s.closes[idx + k] >= p0) return k; // 股價回到扣息前水位
    }
    return null; // 觀察期內未填息
  }

  static Future<StockDetail> load(String id) async {
    final hit = _cache[id];
    if (hit != null) return hit;

    await MarketRepository.instance.ensureLoaded();
    final basic = await _basic(id);
    final s = MarketRepository.instance.series(id);

    final name = basic?.name ?? s?.name ?? id;
    final industry = basic?.industry ?? s?.industry ?? '';
    final group = basic?.group ?? '';
    final close = basic?.close ?? (s != null && s.closes.isNotEmpty ? s.closes.last : 0);
    final yieldPct = basic?.yieldPct;
    final pe = basic?.pe;
    final pb = basic?.pb;

    if (s == null) {
      // 不在快照內：只給基本資料
      final d = StockDetail(
        id: id,
        name: name,
        industry: industry,
        group: group,
        close: close,
        yieldPct: yieldPct,
        pe: pe,
        pb: pb,
        hasSeries: false,
        dates: const <int>[],
        closes: const <double>[],
        volumes: const <int>[],
        dividends: const <DivRow>[],
        yieldRange: null,
        payoutRatio: null,
        epsYears: const <EpsYear>[],
        source: 'basic',
      );
      _cache[id] = d;
      return d;
    }

    // 走勢視窗：近 500 個交易日（約 2 年）
    const window = 500;
    final from = s.closes.length > window ? s.closes.length - window : 0;
    final dates = s.dates.sublist(from);
    final closes = s.closes.sublist(from);
    final volumes = s.volumes.isEmpty
        ? List<int>.filled(s.closes.length - from, 0)
        : s.volumes.sublist(from);

    // 現金股利 + 填息天數（取近 12 筆）
    final dividends = <DivRow>[];
    final divByYear = <int, double>{};
    final sortedDiv = List<DivRecord>.from(s.dividends)
      ..sort((a, b) => a.ym.compareTo(b.ym));
    for (final d in sortedDiv) {
      final year = int.parse(d.ym.substring(0, 4));
      divByYear[year] = (divByYear[year] ?? 0) + d.amount;
      dividends.add(DivRow(
        year: year,
        cash: d.amount,
        exMonth: d.ym,
        fillDays: _fillDays(s, d.ym, d.amount),
      ));
    }
    if (dividends.length > 12) {
      dividends.removeRange(0, dividends.length - 12);
    }

    // 殖利率區間（來自本益比序列的 yieldRate）
    final ylds = s.per.where((p) => p.yieldRate > 0).map((p) => p.yieldRate).toList();
    final yieldRange = ylds.length >= 2
        ? YieldRange(
            min: ylds.reduce((a, b) => a < b ? a : b),
            max: ylds.reduce((a, b) => a > b ? a : b),
            avg: ylds.reduce((a, b) => a + b) / ylds.length,
          )
        : null;

    // 年度 EPS（完整年度）
    final epsYears = s.annualEps.entries
        .map((e) => EpsYear(year: e.key, eps: e.value))
        .toList()
      ..sort((a, b) => a.year.compareTo(b.year));

    // 配息率：最新完整年度 現金股利 ÷ 年度 EPS
    double? payoutRatio;
    final yearsWithEps = epsYears.where((e) => divByYear.containsKey(e.year)).toList();
    if (yearsWithEps.isNotEmpty) {
      final y = yearsWithEps.last;
      if (y.eps > 0) payoutRatio = divByYear[y.year]! / y.eps * 100;
    }

    final detail = StockDetail(
      id: id,
      name: name,
      industry: industry,
      group: group,
      close: close,
      yieldPct: yieldPct,
      pe: pe,
      pb: pb,
      hasSeries: true,
      dates: dates,
      closes: closes,
      volumes: volumes,
      dividends: dividends,
      yieldRange: yieldRange,
      payoutRatio: payoutRatio,
      epsYears: epsYears,
      source: 'snapshot',
    );
    _cache[id] = detail;
    return detail;
  }
}
