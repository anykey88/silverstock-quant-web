// ============================================================================
// 組合風險體檢（Portfolio Risk Checkup）
// ----------------------------------------------------------------------------
// 這個模組只做一件事：把「你手上這一籃股票」的結構攤開來看，指出它哪裡脆弱。
//
// 它不做的事（很重要）：
//   · 不預測漲跌
//   · 不給目標價
//   · 不叫你買或賣
// 因為「該不該賣」取決於你的資金用途、稅務、還有你半夜睡得著的程度，
// 這些不在資料裡。它只能告訴你「如果這裡出事，會是從哪裡開始」。
//
// 指標選擇的理由（台股適用）：
//   1. 集中度 HHI  — 台股散戶最常見的死法是「重壓一檔自己最熟的公司」
//   2. 產業集中    — 台股電子權重極高，很容易「以為分散、其實全在電子」
//   3. 52 週振幅   — 台股個股年振幅常 40%~80%，用振幅當波動代理比標準差直觀
//   4. 距高點回撤  — 存股族真正的痛點不是波動，是「抱了一年還在虧」
//   5. 估值分位    — 台股本益比區間穩定，百分位比絕對值有意義
//   6. 現金比重    — 空手也是一種部位；滿倉的人在崩盤時只能看著
//   7. 減碼名單衝突 — 你持有的股票正好在系統的減碼名單上，值得看一眼
// ============================================================================

import 'dart:math' as math;

/// 外部餵進來的個股屬性（由 UI 從每日精選 / 快照轉換）
class StockMeta {
  final String id;
  final String name;
  final String industry;
  final double close;
  final double perPctile; // 本益比位階 0~100
  final double yieldPct;
  final double high52;
  final double low52;
  final double trimScore; // 減碼評分，0 表示不在名單

  const StockMeta({
    required this.id,
    required this.name,
    this.industry = '未分類',
    this.close = 0,
    this.perPctile = 50,
    this.yieldPct = 0,
    this.high52 = 0,
    this.low52 = 0,
    this.trimScore = 0,
  });

  /// 52 週振幅（%）。沒有高低價時回 0，由上層標為「資料不足」。
  double get amplitudePct =>
      (high52 > 0 && low52 > 0) ? (high52 - low52) / ((high52 + low52) / 2) * 100 : 0;

  /// 距 52 週高點（%，負值代表仍在下方）
  double get fromHighPct => high52 > 0 && close > 0 ? (close / high52 - 1) * 100 : 0;
}

/// 引擎輸入：一筆持倉（股數 + 每股成本）
class HoldingInput {
  final int shares;
  final double avgCost;
  const HoldingInput(this.shares, this.avgCost);
}

class RiskMetric {
  final String label;
  final String value;
  final String hint;
  final RiskTone tone;
  const RiskMetric(this.label, this.value, this.hint, this.tone);
}

enum RiskTone { good, watch, warn }

class RiskHolding {
  final String id;
  final String name;
  final double weight; // %
  final double pnlPct;
  final double amplitudePct;
  final String industry;
  const RiskHolding(this.id, this.name, this.weight, this.pnlPct, this.amplitudePct, this.industry);
}

class PortfolioRisk {
  final int score; // 0~100，越高越脆弱
  final String level; // 穩健 / 偏集中 / 集中 / 高度集中
  final List<RiskMetric> metrics;
  final List<RiskHolding> holdings;
  final List<String> actions;
  final List<String> blindSpots; // 資料不足、無法評估的部分

  const PortfolioRisk({
    required this.score,
    required this.level,
    required this.metrics,
    required this.holdings,
    required this.actions,
    required this.blindSpots,
  });

  static const PortfolioRisk empty = PortfolioRisk(
    score: 0,
    level: '尚無持倉',
    metrics: <RiskMetric>[],
    holdings: <RiskHolding>[],
    actions: <String>[],
    blindSpots: <String>[],
  );
}

class PortfolioRiskEngine {
  /// [positions] 股數與成本；[cash] 現金；[metaOf] 取個股屬性（可能為 null）
  static PortfolioRisk build({
    required Map<String, HoldingInput> positions,
    required double cash,
    required StockMeta? Function(String id) metaOf,
  }) {
    if (positions.isEmpty) {
      return PortfolioRisk(
        score: 0,
        level: '尚無持倉',
        metrics: const <RiskMetric>[
          RiskMetric('持倉', '0 檔', '全部是現金。空手不會虧錢，但也沒有報酬。', RiskTone.good),
        ],
        holdings: const <RiskHolding>[],
        actions: const <String>[],
        blindSpots: const <String>[],
      );
    }

    // ---- 1. 逐檔估值與權重 ----
    final rows = <_Row>[];
    final blind = <String>[];
    var totalMv = 0.0;
    positions.forEach((id, p) {
      final m = metaOf(id);
      final px = (m != null && m.close > 0) ? m.close : p.avgCost;
      final mv = px * p.shares;
      totalMv += mv;
      rows.add(_Row(
        id: id,
        name: m?.name ?? id,
        mv: mv,
        shares: p.shares,
        avgCost: p.avgCost,
        price: px,
        meta: m,
      ));
      if (m == null) blind.add('$id：沒有個股屬性資料，未納入產業與波動評估');
    });
    final equity = totalMv + cash;
    if (equity <= 0) return PortfolioRisk.empty;

    for (final r in rows) {
      r.weight = r.mv / equity * 100;
    }
    rows.sort((a, b) => b.weight.compareTo(a.weight));

    // ---- 2. 集中度 ----
    double hhi = 0;
    for (final r in rows) {
      final w = r.weight / 100;
      hhi += w * w;
    }
    final maxW = rows.isEmpty ? 0.0 : rows.first.weight;
    final top3 = rows.take(3).fold<double>(0.0, (a, r) => a + r.weight);
    final effectiveN = hhi > 0 ? 1 / hhi : 0.0;

    // ---- 3. 產業集中 ----
    final indWeight = <String, double>{};
    for (final r in rows) {
      final ind = (r.meta?.industry ?? '').isEmpty ? '未分類' : r.meta!.industry;
      indWeight[ind] = (indWeight[ind] ?? 0) + r.weight;
    }
    final indSorted = indWeight.entries.toList()..sort((a, b) => b.value.compareTo(a.value));
    final maxInd = indSorted.isEmpty ? '' : indSorted.first.key;
    final maxIndW = indSorted.isEmpty ? 0.0 : indSorted.first.value;

    // ---- 4. 加權波動 / 回撤 / 估值 ----
    double wAmp = 0, wDraw = 0, wPer = 0, coveredW = 0;
    for (final r in rows) {
      final m = r.meta;
      if (m == null || m.high52 <= 0) continue;
      wAmp += m.amplitudePct * r.weight;
      wDraw += m.fromHighPct * r.weight;
      wPer += m.perPctile * r.weight;
      coveredW += r.weight;
    }
    final hasVol = coveredW > 0;
    final amp = hasVol ? wAmp / coveredW : 0.0;
    final draw = hasVol ? wDraw / coveredW : 0.0;
    final perPct = hasVol ? wPer / coveredW : 50.0;
    final cashRatio = cash / equity * 100;

    // ---- 5. 減碼名單衝突 ----
    final conflicts = rows.where((r) => (r.meta?.trimScore ?? 0) >= 15).toList();
    final conflictW = conflicts.fold<double>(0.0, (a, r) => a + r.weight);

    // ---- 6. 評分（越高越脆弱）----
    // 集中度 30 分：最大單一權重 15% 起扣，50% 滿分
    final sConc = _ramp(maxW, 15, 50) * 30;
    // 產業 20 分：單一產業 40% 起扣，80% 滿分
    final sInd = _ramp(maxIndW, 40, 80) * 20;
    // 波動 20 分：加權年振幅 35% 起扣，90% 滿分
    final sVol = hasVol ? _ramp(amp, 35, 90) * 20 : 10;
    // 估值 15 分：加權本益比位階 60 起扣，95 滿分
    final sVal = hasVol ? _ramp(perPct, 60, 95) * 15 : 7.5;
    // 現金 15 分：現金 <2% 滿分，>25% 零分（越滿倉越脆弱）
    final sCash = (1 - _ramp(cashRatio, 2, 25)) * 15;

    final score = (sConc + sInd + sVol + sVal + sCash).round().clamp(0, 100);
    final level = score >= 70
        ? '高度集中'
        : score >= 50
            ? '偏集中'
            : score >= 32
                ? '中等'
                : '相對分散';

    // ---- 7. 指標卡 ----
    final metrics = <RiskMetric>[
      RiskMetric(
        '最大單一持股',
        '${maxW.toStringAsFixed(1)}%',
        '${rows.first.name}・權重超過 30% 時，它的漲跌就等於你的績效',
        maxW >= 35 ? RiskTone.warn : (maxW >= 22 ? RiskTone.watch : RiskTone.good),
      ),
      RiskMetric(
        '前三大合計',
        '${top3.toStringAsFixed(1)}%',
        '等效持股 ${effectiveN.toStringAsFixed(1)} 檔（HHI ${hhi.toStringAsFixed(3)}）',
        top3 >= 75 ? RiskTone.warn : (top3 >= 55 ? RiskTone.watch : RiskTone.good),
      ),
      RiskMetric(
        '最大產業',
        '${maxIndW.toStringAsFixed(1)}%',
        maxInd.isEmpty ? '—' : '$maxInd・台股電子權重高，容易「以為分散其實沒有」',
        maxIndW >= 60 ? RiskTone.warn : (maxIndW >= 45 ? RiskTone.watch : RiskTone.good),
      ),
      RiskMetric(
        '加權年振幅',
        hasVol ? '${amp.toStringAsFixed(0)}%' : '資料不足',
        '以 52 週高低價估算，代表這籃股票「一年大概會晃多大」',
        !hasVol ? RiskTone.watch : (amp >= 70 ? RiskTone.warn : (amp >= 50 ? RiskTone.watch : RiskTone.good)),
      ),
      RiskMetric(
        '距 52 週高點',
        hasVol ? '${draw.toStringAsFixed(1)}%' : '資料不足',
        draw <= -25 ? '整體仍在明顯回檔中，帳面壓力會持續' : '多數持股接近年內高位',
        !hasVol ? RiskTone.watch : (draw <= -25 ? RiskTone.warn : RiskTone.good),
      ),
      RiskMetric(
        '加權估值位階',
        hasVol ? '${perPct.toStringAsFixed(0)} 分位' : '資料不足',
        perPct >= 80 ? '整體偏貴，未來的報酬空間被先借走了' : '估值仍在合理區間',
        !hasVol ? RiskTone.watch : (perPct >= 80 ? RiskTone.warn : (perPct >= 65 ? RiskTone.watch : RiskTone.good)),
      ),
      RiskMetric(
        '現金比重',
        '${cashRatio.toStringAsFixed(1)}%',
        cashRatio < 3 ? '幾乎滿倉，遇到急殺只能看著' : (cashRatio > 40 ? '現金偏多，機會成本要自己衡量' : '保留了一定的加碼彈性'),
        cashRatio < 3 ? RiskTone.warn : (cashRatio < 8 ? RiskTone.watch : RiskTone.good),
      ),
      RiskMetric(
        '減碼名單衝突',
        '${conflicts.length} 檔 / ${conflictW.toStringAsFixed(1)}%',
        conflicts.isEmpty ? '目前持有的股票都不在減碼名單上' : '這些股票的估值或動能已進入系統的警戒區',
        conflicts.isEmpty ? RiskTone.good : (conflictW >= 20 ? RiskTone.warn : RiskTone.watch),
      ),
    ];

    // ---- 8. 具體動作（描述結構，不是買賣指令）----
    final actions = <String>[];
    if (maxW >= 35) {
      actions.add('${rows.first.name} 佔 ${maxW.toStringAsFixed(1)}%。'
          '如果你當初設定的上限是 20%，現在是「獲利把它推上去」還是「你一直加碼」？'
          '前者叫紀律失守，後者叫信念加碼——兩者的處理方式完全不同。');
    }
    if (maxIndW >= 55) {
      actions.add('$maxInd 產業佔 ${maxIndW.toStringAsFixed(1)}%。'
          '同一產業的公司會一起被同一個景氣循環帶走，分散效果有限。'
          '要真正分散，得往「驅動力不同」的產業找，而不是在同產業裡多買兩檔。');
    }
    if (amp >= 65) {
      actions.add('加權年振幅 ${amp.toStringAsFixed(0)}%。'
          '用「最壞情況它會腰斬」去回推自己受不受得了，比用「它應該會漲」去推算合理。');
    }
    if (cashRatio < 5) {
      actions.add('現金只剩 ${cashRatio.toStringAsFixed(1)}%。'
          '滿倉不是錯，但要接受「接下來半年只能領股息、不能加碼」這個事實。');
    }
    if (conflicts.isNotEmpty) {
      final names = conflicts.take(3).map((r) => '${r.name}(${r.id})').join('、');
      actions.add('$names 在減碼名單上。'
          '去看一眼「減碼理由」是估值過高、動能轉弱、還是財報轉差——'
          '只有第三種才需要你認真考慮部位。');
    }
    if (draw <= -20) {
      actions.add('整體距年內高點 ${draw.toStringAsFixed(0)}%。'
          '這個階段最容易做的錯事是「攤平到沒子彈」，其次是「全部砍在最低點」。'
          '先確認每一檔的買進理由還在不在，再決定要不要動作。');
    }
    if (actions.isEmpty) {
      actions.add('結構上沒有明顯破口。維持原本的配置，把注意力放在「出場條件有沒有變」而不是「今天漲還跌」。');
    }

    final holdings = rows
        .map((r) => RiskHolding(
              r.id,
              r.name.isEmpty ? r.id : r.name,
              r.weight,
              r.avgCost > 0 ? (r.price - r.avgCost) / r.avgCost * 100 : 0,
              r.meta?.amplitudePct ?? 0,
              (r.meta?.industry ?? '').isEmpty ? '未分類' : r.meta!.industry,
            ))
        .toList();

    return PortfolioRisk(
      score: score,
      level: level,
      metrics: metrics,
      holdings: holdings,
      actions: actions,
      blindSpots: blind,
    );
  }

  /// 把 value 映射到 0~1：低於 lo 為 0，高於 hi 為 1
  static double _ramp(double v, double lo, double hi) {
    if (hi <= lo) return 0;
    return ((v - lo) / (hi - lo)).clamp(0.0, 1.0).toDouble();
  }
}

class _Row {
  final String id;
  final String name;
  final double mv;
  final int shares;
  final double avgCost;
  final double price;
  final StockMeta? meta;
  double weight = 0;

  _Row({
    required this.id,
    required this.name,
    required this.mv,
    required this.shares,
    required this.avgCost,
    required this.price,
    required this.meta,
  });

  double get pnlPct => avgCost > 0 ? (price - avgCost) / avgCost * 100 : 0;
}

/// 兩檔股票的日報酬相關係數（需要等長序列；不足 30 筆回 null）
/// 用途：檢查「你以為分散的兩檔，其實同步漲跌」。
double? correlation(List<double> a, List<double> b) {
  final n = math.min(a.length, b.length);
  if (n < 30) return null;
  final x = a.sublist(a.length - n);
  final y = b.sublist(b.length - n);
  double sx = 0, sy = 0, sxx = 0, syy = 0, sxy = 0;
  for (var i = 0; i < n; i++) {
    sx += x[i];
    sy += y[i];
    sxx += x[i] * x[i];
    syy += y[i] * y[i];
    sxy += x[i] * y[i];
  }
  final cov = sxy / n - (sx / n) * (sy / n);
  final vx = sxx / n - (sx / n) * (sx / n);
  final vy = syy / n - (sy / n) * (sy / n);
  if (vx <= 0 || vy <= 0) return null;
  return cov / math.sqrt(vx * vy);
}

/// 日報酬序列
List<double> dailyReturns(List<double> closes) {
  final out = <double>[];
  for (var i = 1; i < closes.length; i++) {
    if (closes[i - 1] <= 0) continue;
    out.add(closes[i] / closes[i - 1] - 1);
  }
  return out;
}
