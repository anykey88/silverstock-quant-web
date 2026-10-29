// SilverStock v2 — 個股客觀分析 CLI
//
// 用法：
//   dart run tool/v2_report.dart 2330
//   dart run tool/v2_report.dart 2330 --json
//
// 輸出順序刻意「結論在前、證據在後」：
//   摘要 → 訊號整合 → 歷史條件機率 → 估值 → 價位 → 財務 → 動能 → 籌碼 → 風險 → 失效條件

import 'dart:convert';
import 'dart:io';

import 'package:silverstock_quant_web/v2/conditional.dart';
import 'package:silverstock_quant_web/v2/data.dart';
import 'package:silverstock_quant_web/v2/financials.dart';
import 'package:silverstock_quant_web/v2/levels.dart';
import 'package:silverstock_quant_web/v2/momentum.dart';
import 'package:silverstock_quant_web/v2/parse.dart';
import 'package:silverstock_quant_web/v2/signals.dart';
import 'package:silverstock_quant_web/v2/stats.dart';
import 'package:silverstock_quant_web/v2/valuation.dart';

String f(num? v, [int d = 1]) => v == null ? '—' : v.toStringAsFixed(d);

void rule([String c = '─', int n = 72]) => print(c * n);

void head(String s) {
  print('');
  print('▍$s');
}

void main(List<String> args) {
  final sid = args.isNotEmpty && !args.first.startsWith('--') ? args.first : '2330';
  final asJson = args.contains('--json');
  final path = 'tool/v2/data/$sid.json';

  final file = File(path);
  if (!file.existsSync()) {
    stderr.writeln('找不到 $path');
    stderr.writeln('請先執行：python3 tool/v2/fetch.py $sid');
    exit(1);
  }

  final d = parseDatasetFromString(file.readAsStringSync());
  final close = d.latest?.close ?? 0;

  final vp = ValuationEngine.profile(d, years: 5);
  final peLevels = ValuationEngine.peLevels(d, vp);
  final yieldLevels = ValuationEngine.yieldLevels(d);
  final pbrLevels = ValuationEngine.pbrLevels(d, vp);
  final lv = LevelEngine.build(d);
  final fq = FinancialEngine.build(d);
  final mo = MomentumEngine.build(d);
  final cr = ConditionalEngine.build(
      d, vp.currentPer, [vp.perP10, vp.perP25, vp.perP50, vp.perP75, vp.perP90]);
  final sg = SignalEngine.build(d: d, vp: vp, fq: fq, mo: mo, lv: lv);

  if (asJson) {
    print(const JsonEncoder.withIndent('  ').convert({
      'stock_id': d.info.stockId,
      'name': d.info.name,
      'industry': d.info.industry,
      'close': close,
      'data_as_of': d.fetchedAt,
      'position': sg.positionLabel,
      'valuation': {
        'per': vp.currentPer,
        'per_percentile': vp.perPercentile,
        'pbr': vp.currentPbr,
        'yield': vp.currentYield,
        'yield_percentile': vp.yieldPercentile,
        'per_bands_p10_p25_p50_p75_p90':
            [vp.perP10, vp.perP25, vp.perP50, vp.perP75, vp.perP90],
        'yield_bands_p10_p25_p50_p75':
            [vp.yieldP10, vp.yieldP25, vp.yieldP50, vp.yieldP75],
      },
      'price_levels': {
        'by_per': peLevels
            .map((e) => {'label': e.label, 'price': e.price, 'basis': e.basis})
            .toList(),
        'by_yield': yieldLevels
            .map((e) => {'label': e.label, 'price': e.price, 'basis': e.basis})
            .toList(),
        'by_pbr': pbrLevels
            .map((e) => {'label': e.label, 'price': e.price, 'basis': e.basis})
            .toList(),
      },
      'structure': {
        'poc': lv.poc,
        'value_area': [lv.valueAreaLow, lv.valueAreaHigh],
        'ma20': lv.ma20,
        'ma60': lv.ma60,
        'ma120': lv.ma120,
        'ma240': lv.ma240,
        'high250': lv.high250,
        'low250': lv.low250,
        'atr14': lv.atr14,
        'atr_pct': lv.atrPct,
      },
      'financial': {
        'score': fq.score,
        'grade': fq.grade,
        'roe': fq.roe,
        'gross_margin': fq.grossMargin,
        'operating_margin': fq.operatingMargin,
        'debt_ratio': fq.debtRatio,
        'fcf': fq.freeCashFlow,
        'payout': fq.payoutRatio,
        'checks': fq.items
            .map((i) => {
                  'name': i.name,
                  'value': i.value,
                  'verdict': i.verdict.name,
                })
            .toList(),
      },
      'momentum': {
        'stage': mo.stageLabel,
        'latest_yoy': mo.latestYoY,
        'yoy_3m': mo.threeMonthYoY,
        'ytd_yoy': mo.ytdYoY,
        'streak': mo.positiveStreak,
      },
      'conditional': {
        'current_bucket': cr.currentBucket,
        'buckets': cr.buckets
            .map((b) => {
                  'label': b.label,
                  'samples': b.sampleSize,
                  'median20': b.median20,
                  'median60': b.median60,
                  'win_rate60': b.winRate60,
                  'p25_60': b.p25of60,
                  'p75_60': b.p75of60,
                })
            .toList(),
        'caveats': cr.caveats,
      },
      'signals': sg.signals
          .map((s) => {'title': s.title, 'detail': s.detail, 'tone': s.tone.name})
          .toList(),
      'invalidation': sg.invalidation,
    }));
    return;
  }

  // ===== 摘要 =====
  print('');
  rule('═');
  print('  ${d.info.name}（${d.info.stockId}）   ${d.info.industry} / ${d.info.market}');
  print('  現價 ${close.toStringAsFixed(2)} 元 ｜ 資料截止 ${d.fetchedAt} ｜ ${d.bars.length} 交易日');
  rule('═');

  final peMid = peLevels
      .where((e) => e.label.contains('50 分位'))
      .map((e) => e.price)
      .firstWhere((x) => x != null, orElse: () => null);
  final gapToMid =
      (peMid != null && peMid > 0) ? (close - peMid) / peMid * 100 : null;

  print('');
  print('  ▸ ${sg.positionLabel}');
  print('  ▸ 營收動能：${mo.stageLabel}（近 3 月 YoY ${f(mo.threeMonthYoY)}%）');
  print('  ▸ 估值：本益比 ${f(vp.currentPer, 1)} 倍，歷史 ${f(vp.perPercentile, 0)} 百分位');
  if (gapToMid != null) {
    print('  ▸ 現價距「PE 中位數價位」${peMid!.toStringAsFixed(0)} 元 '
        '${gapToMid >= 0 ? "高" : "低"} ${gapToMid.abs().toStringAsFixed(1)}%');
  }

  // ===== 一、訊號整合 =====
  head('一、訊號整合（先把矛盾的證據擺在一起）');
  print('  ${sg.positionLabel}：${sg.positionDetail}');
  print('');
  for (final s in sg.signals) {
    final mark = s.tone == SignalTone.conflict
        ? '⚡'
        : s.tone == SignalTone.caution
            ? '△'
            : s.tone == SignalTone.positive
                ? '○'
                : '·';
    print('  $mark ${s.title}');
    print('    ${s.detail}');
  }

  // ===== 二、歷史條件機率 =====
  head('二、歷史條件機率（同樣的估值，過去後來怎麼走）');
  print('  當前位置：${cr.currentBucket ?? "無法判定"}');
  print('');
  print('  ${"條件".padRight(30)}${"樣本".padLeft(6)}${"20日中位".padLeft(10)}${"60日中位".padLeft(10)}${"60日勝率".padLeft(10)}');
  for (final b in cr.buckets) {
    final isNow = b.label == cr.currentBucket ? '◀' : ' ';
    print('  ${b.label.padRight(30)}${b.sampleSize.toString().padLeft(6)}'
        '${(b.median20 == null ? "—" : "${b.median20!.toStringAsFixed(1)}%").padLeft(10)}'
        '${(b.median60 == null ? "—" : "${b.median60!.toStringAsFixed(1)}%").padLeft(10)}'
        '${(b.winRate60 == null ? "—" : "${b.winRate60!.toStringAsFixed(0)}%").padLeft(10)} $isNow');
  }
  final cur = cr.current;
  if (cur != null && cur.median60 != null) {
    print('');
    print('  當前這組的 60 日報酬分布：25 分位 ${f(cur.p25of60)}% ／ 中位數 '
        '${f(cur.median60)}% ／ 75 分位 ${f(cur.p75of60)}%');
    print('  （${cur.horizonNote}）');
  }
  print('');
  for (final c in cr.caveats) {
    print('  ⚠ $c');
  }

  // ===== 三、估值分位 =====
  head('三、估值分位（${vp.windowLabel}，${vp.sampleDays} 個交易日）');
  print('  本益比      ${f(vp.currentPer, 2)} 倍   → 歷史 ${f(vp.perPercentile, 0)} 百分位');
  print('  股價淨值比  ${f(vp.currentPbr, 2)} 倍');
  print('  殖利率      ${f(vp.currentYield, 2)}%     → 歷史 ${f(vp.yieldPercentile, 0)} 百分位'
      '${(vp.yieldPercentile ?? 50) < 30 ? "（偏低，表示價格偏貴）" : (vp.yieldPercentile ?? 50) > 70 ? "（偏高，表示價格相對便宜）" : ""}');
  print('');
  print('  PE 分位     P10 ${f(vp.perP10)}   P25 ${f(vp.perP25)}   P50 ${f(vp.perP50)}   '
      'P75 ${f(vp.perP75)}   P90 ${f(vp.perP90)}');
  print('  殖利率分位  P10 ${f(vp.yieldP10, 2)}%  P25 ${f(vp.yieldP25, 2)}%  P50 ${f(vp.yieldP50, 2)}%  '
      'P75 ${f(vp.yieldP75, 2)}%  P90 ${f(vp.yieldP90, 2)}%');
  print('  PBR 分位    P10 ${f(vp.pbrP10, 2)}   P25 ${f(vp.pbrP25, 2)}   P50 ${f(vp.pbrP50, 2)}   '
      'P75 ${f(vp.pbrP75, 2)}   P90 ${f(vp.pbrP90, 2)}');

  // ===== 四、價位反推 =====
  head('四、價位反推（歷史倍數 × 已公布基本面，可自行複算）');
  print('  EPS(TTM) ${f(d.epsTtm, 2)} 元   年現金股利 ${f(d.annualCashDividend, 2)} 元');
  print('');
  print('  ${"本益比法".padRight(28)}${"價位".padLeft(9)}   計算式');
  for (final e in peLevels) {
    print('  ${e.label.padRight(28)}'
        '${(e.price == null ? "不適用" : e.price!.toStringAsFixed(0)).padLeft(9)}   ${e.basis}');
  }
  final peCaveat = peLevels.isNotEmpty ? peLevels.first.caveat : null;
  if (peCaveat != null) print('  ⚠ $peCaveat');

  if (yieldLevels.isNotEmpty && yieldLevels.first.price != null) {
    print('');
    print('  ${"殖利率法".padRight(28)}${"價位".padLeft(9)}   計算式');
    for (final e in yieldLevels) {
      print('  ${e.label.padRight(28)}'
          '${(e.price == null ? "不適用" : e.price!.toStringAsFixed(0)).padLeft(9)}   ${e.basis}');
    }
    final yCaveat = yieldLevels.first.caveat;
    if (yCaveat != null) print('  ⚠ $yCaveat');
  }

  if (pbrLevels.isNotEmpty && pbrLevels.first.price != null) {
    print('');
    print('  ${"股價淨值比法".padRight(28)}${"價位".padLeft(9)}   計算式');
    for (final e in pbrLevels) {
      print('  ${e.label.padRight(28)}'
          '${(e.price == null ? "不適用" : e.price!.toStringAsFixed(0)).padLeft(9)}   ${e.basis}');
    }
  }

  // ===== 五、價位結構 =====
  head('五、價位結構（過去 ${lv.profileDays} 日成交分布）');
  print('  成交密集區 POC   ${f(lv.poc, 0)} 元    ← 過去一年換手最多次的價位');
  print('  價值區           ${f(lv.valueAreaLow, 0)} ～ ${f(lv.valueAreaHigh, 0)} 元    ← 涵蓋 70% 成交量');
  print('  近 250 日高低    ${f(lv.low250, 0)} ～ ${f(lv.high250, 0)} 元');
  print('  均線             MA20 ${f(lv.ma20, 0)}  MA60 ${f(lv.ma60, 0)}  '
      'MA120 ${f(lv.ma120, 0)}  MA240 ${f(lv.ma240, 0)}');
  print('  ATR(14)          ${f(lv.atr14, 1)} 元（${f(lv.atrPct)}%）← 一日正常波動');
  if (lv.openGaps.isNotEmpty) {
    print('  未回補缺口：');
    for (final g in lv.openGaps.take(4)) {
      print('    ${g.date}  ${g.up ? "向上" : "向下"}  '
          '${g.lower.toStringAsFixed(0)} ～ ${g.upper.toStringAsFixed(0)}');
    }
  }

  // ===== 六、財務 =====
  head('六、財務品質  ${fq.score == null ? "" : "${fq.goodCount}/${fq.scoredCount} 項通過 = ${fq.score} 分"}  ${fq.grade}');
  for (final it in fq.items) {
    final mark = it.verdict == Verdict.good
        ? '✓'
        : it.verdict == Verdict.bad
            ? '✗'
            : '·';
    print('  $mark ${it.name.padRight(30)}${(it.value ?? '—').padLeft(13)}   ${it.threshold}');
  }

  // ===== 七、動能 =====
  head('七、營收動能  ${mo.stageLabel}（最新 ${mo.lastMonth ?? "—"}）');
  print('  單月 YoY ${f(mo.latestYoY)}%   近 3 月平均 ${f(mo.threeMonthYoY)}%   '
      '今年累計 ${f(mo.ytdYoY)}%');
  print('  單月 MoM ${f(mo.latestMoM)}%（台股季節性強，僅供參考）');
  print('  連續年增 ${mo.positiveStreak} 個月   3MA/12MA ${f(mo.shortVsLong, 3)}');
  for (final e in mo.evidence) {
    print('  · $e');
  }

  // ===== 八、籌碼 =====
  if (d.institutions.isNotEmpty) {
    head('八、籌碼（單位：張）');
    final t20 = d.institutions.length >= 20
        ? d.institutions.sublist(d.institutions.length - 20)
        : d.institutions;
    final t60 = d.institutions.length >= 60
        ? d.institutions.sublist(d.institutions.length - 60)
        : d.institutions;
    double sum(List<InstitutionalDay> xs, double Function(InstitutionalDay) k) =>
        xs.fold<double>(0, (s, x) => s + k(x)) / 1000;
    print('  外資   20 日 ${sum(t20, (x) => x.foreignNet).toStringAsFixed(0).padLeft(10)}   '
        '60 日 ${sum(t60, (x) => x.foreignNet).toStringAsFixed(0).padLeft(10)}');
    print('  投信   20 日 ${sum(t20, (x) => x.trustNet).toStringAsFixed(0).padLeft(10)}   '
        '60 日 ${sum(t60, (x) => x.trustNet).toStringAsFixed(0).padLeft(10)}');
    print('  自營   20 日 ${sum(t20, (x) => x.dealerNet).toStringAsFixed(0).padLeft(10)}   '
        '60 日 ${sum(t60, (x) => x.dealerNet).toStringAsFixed(0).padLeft(10)}');
  }

  // ===== 九、風險 =====
  final vol = Stats.annualizedVolatility(d.bars);
  final dd = Stats.maxDrawdown(d.tailBars(250).map((b) => b.close).toList());
  head('九、風險');
  print('  年化波動率 ${f(vol)}%   近 250 日最大回撤 ${f(dd)}%');
  if (lv.atrPct != null) {
    print('  以 ATR 衡量，單日波動超過 ${(lv.atrPct! * 2).toStringAsFixed(1)}% 屬異常。');
  }

  // ===== 十、觀察與失效 =====
  head('十、該盯什麼 / 什麼情況下以上判讀失效');
  print('  觀察重點：');
  for (final w in sg.watchPoints) {
    print('    · $w');
  }
  print('');
  print('  失效條件（出現任一項，上面的判讀就要重做）：');
  for (final i in sg.invalidation) {
    print('    · $i');
  }

  print('');
  rule('═');
  print('  本報告僅整理公開歷史資料，不構成投資建議。價位皆為歷史統計反推，');
  print('  不代表未來會到達。資料來源：FinMind 公開 API（非商業授權）。');
  rule('═');
  print('');
}
