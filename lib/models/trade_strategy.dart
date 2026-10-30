// ============================================================================
// 交易策略模型（個人自用版）
// ----------------------------------------------------------------------------
// 一組策略 = 進場條件 + 加碼規則 + 出場規則 + 資金與成本設定。
// 全部參數可存成 JSON 放進 localStorage，也可以匯出/匯入。
//
// 這裡是「模擬交易」用的參數；回測結果只代表過去。
// ============================================================================

class TradeStrategy {
  final String id;
  final String name;
  final String note;

  // ---- 進場條件（可留空表示不設該條件；多條件為 AND）----
  final double? entryYieldMin; // 殖利率 >= X%
  final double? entryPerRatio; // 本益比 <= 自身 5 年中位數 × ratio
  final String maMode; // 'any' = 不看季線 / 'below' = 要低於季線 / 'above' = 要高於季線
  final double maPct; // 季線幅度（%），例如 below + 5 = 低於季線 5% 以上
  final double? entryRsiMax; // RSI <= X

  // ---- 加碼規則 ----
  final double addOnDropPct; // 每再跌 X% 加一份（0 = 不加碼）
  final int maxAdds; // 最多加碼次數

  // ---- 出場規則 ----
  final double? takeProfitPct; // 停利 +X%
  final double? stopLossPct; // 停損 -X%
  final double? exitYieldBelow; // 殖利率跌破 X% 出場

  // ---- 資金與成本 ----
  final double totalCapital; // 投入本金（新台幣）
  final double trancheAmount; // 每次投入金額
  final double maxPositionPct; // 單一標的持倉上限（佔本金 %）
  final double feeDiscount; // 手續費折扣（0.6 = 6 折）
  final bool reinvestDividend; // 股息再投入
  final String frequency; // daily / weekly / monthly（檢查進場的頻率）

  const TradeStrategy({
    required this.id,
    required this.name,
    this.note = '',
    this.entryYieldMin,
    this.entryPerRatio,
    this.maMode = 'any',
    this.maPct = 0,
    this.entryRsiMax,
    this.addOnDropPct = 0,
    this.maxAdds = 0,
    this.takeProfitPct,
    this.stopLossPct,
    this.exitYieldBelow,
    this.totalCapital = 500000,
    this.trancheAmount = 50000,
    this.maxPositionPct = 100,
    this.feeDiscount = 0.6,
    this.reinvestDividend = false,
    this.frequency = 'weekly',
  });

  TradeStrategy copyWith({
    String? name,
    String? note,
    double? entryYieldMin,
    double? entryPerRatio,
    String? maMode,
    double? maPct,
    double? entryRsiMax,
    double? addOnDropPct,
    int? maxAdds,
    double? takeProfitPct,
    double? stopLossPct,
    double? exitYieldBelow,
    double? totalCapital,
    double? trancheAmount,
    double? maxPositionPct,
    double? feeDiscount,
    bool? reinvestDividend,
    String? frequency,
    bool clearYield = false,
    bool clearPer = false,
    bool clearRsi = false,
    bool clearTp = false,
    bool clearSl = false,
    bool clearExitYield = false,
  }) {
    return TradeStrategy(
      id: id,
      name: name ?? this.name,
      note: note ?? this.note,
      entryYieldMin: clearYield ? null : (entryYieldMin ?? this.entryYieldMin),
      entryPerRatio: clearPer ? null : (entryPerRatio ?? this.entryPerRatio),
      maMode: maMode ?? this.maMode,
      maPct: maPct ?? this.maPct,
      entryRsiMax: clearRsi ? null : (entryRsiMax ?? this.entryRsiMax),
      addOnDropPct: addOnDropPct ?? this.addOnDropPct,
      maxAdds: maxAdds ?? this.maxAdds,
      takeProfitPct: clearTp ? null : (takeProfitPct ?? this.takeProfitPct),
      stopLossPct: clearSl ? null : (stopLossPct ?? this.stopLossPct),
      exitYieldBelow: clearExitYield ? null : (exitYieldBelow ?? this.exitYieldBelow),
      totalCapital: totalCapital ?? this.totalCapital,
      trancheAmount: trancheAmount ?? this.trancheAmount,
      maxPositionPct: maxPositionPct ?? this.maxPositionPct,
      feeDiscount: feeDiscount ?? this.feeDiscount,
      reinvestDividend: reinvestDividend ?? this.reinvestDividend,
      frequency: frequency ?? this.frequency,
    );
  }

  Map<String, dynamic> toJson() => <String, dynamic>{
        'id': id,
        'name': name,
        'note': note,
        'entryYieldMin': entryYieldMin,
        'entryPerRatio': entryPerRatio,
        'maMode': maMode,
        'maPct': maPct,
        'entryRsiMax': entryRsiMax,
        'addOnDropPct': addOnDropPct,
        'maxAdds': maxAdds,
        'takeProfitPct': takeProfitPct,
        'stopLossPct': stopLossPct,
        'exitYieldBelow': exitYieldBelow,
        'totalCapital': totalCapital,
        'trancheAmount': trancheAmount,
        'maxPositionPct': maxPositionPct,
        'feeDiscount': feeDiscount,
        'reinvestDividend': reinvestDividend,
        'frequency': frequency,
      };

  factory TradeStrategy.fromJson(Map<String, dynamic> j) => TradeStrategy(
        id: j['id'] as String,
        name: j['name'] as String? ?? '未命名策略',
        note: j['note'] as String? ?? '',
        entryYieldMin: (j['entryYieldMin'] as num?)?.toDouble(),
        entryPerRatio: (j['entryPerRatio'] as num?)?.toDouble(),
        maMode: j['maMode'] as String? ?? 'any',
        maPct: (j['maPct'] as num?)?.toDouble() ?? 0,
        entryRsiMax: (j['entryRsiMax'] as num?)?.toDouble(),
        addOnDropPct: (j['addOnDropPct'] as num?)?.toDouble() ?? 0,
        maxAdds: (j['maxAdds'] as num?)?.toInt() ?? 0,
        takeProfitPct: (j['takeProfitPct'] as num?)?.toDouble(),
        stopLossPct: (j['stopLossPct'] as num?)?.toDouble(),
        exitYieldBelow: (j['exitYieldBelow'] as num?)?.toDouble(),
        totalCapital: (j['totalCapital'] as num?)?.toDouble() ?? 500000,
        trancheAmount: (j['trancheAmount'] as num?)?.toDouble() ?? 50000,
        maxPositionPct: (j['maxPositionPct'] as num?)?.toDouble() ?? 100,
        feeDiscount: (j['feeDiscount'] as num?)?.toDouble() ?? 0.6,
        reinvestDividend: j['reinvestDividend'] as bool? ?? false,
        frequency: j['frequency'] as String? ?? 'weekly',
      );

  String get frequencyText {
    switch (frequency) {
      case 'daily':
        return '每日檢查';
      case 'monthly':
        return '每月檢查';
      default:
        return '每週檢查';
    }
  }

  /// 人話版條件摘要（給 UI 與報告用）
  List<String> get conditionLines {
    final out = <String>[];
    if (entryYieldMin != null) out.add('殖利率 ≥ ${entryYieldMin!.toStringAsFixed(1)}%');
    if (entryPerRatio != null) {
      out.add('本益比 ≤ 自身 5 年中位數 × ${entryPerRatio!.toStringAsFixed(2)}');
    }
    if (maMode == 'below') {
      out.add(maPct > 0
          ? '股價低於季線 ${maPct.toStringAsFixed(0)}% 以上才進場'
          : '股價跌破季線才進場');
    } else if (maMode == 'above') {
      out.add(maPct > 0
          ? '股價高於季線 ${maPct.toStringAsFixed(0)}% 以上才進場'
          : '股價站上季線才進場');
    }
    if (entryRsiMax != null) out.add('RSI ≤ ${entryRsiMax!.toStringAsFixed(0)}');
    if (out.isEmpty) out.add('不設進場條件（每次檢查都投入）');
    return out;
  }

  List<String> get exitLines {
    final out = <String>[];
    if (takeProfitPct != null) out.add('停利：報酬 ≥ +${takeProfitPct!.toStringAsFixed(0)}% 出場');
    if (stopLossPct != null) out.add('停損：報酬 ≤ -${stopLossPct!.toStringAsFixed(0)}% 出場');
    if (exitYieldBelow != null) {
      out.add('殖利率跌破 ${exitYieldBelow!.toStringAsFixed(1)}% 出場');
    }
    if (addOnDropPct > 0 && maxAdds > 0) {
      out.add('加碼：每再跌 ${addOnDropPct.toStringAsFixed(0)}% 加一份，最多 $maxAdds 次');
    }
    if (out.isEmpty) out.add('不設出場條件（買進後持有到期末）');
    return out;
  }
}

/// 內建交易策略模板（個人自用版預設 3 套）
class TradeStrategyPresets {
  static List<TradeStrategy> build() => <TradeStrategy>[
        const TradeStrategy(
          id: 'preset_value',
          name: '高息價值型',
          note: '殖利率有到門檻、評價不貴時才進場；漲多了分批停利，跌深了加碼。'
              '門檻預設較寬，可依標的自行調整。',
          entryYieldMin: 2.5,
          entryPerRatio: 1.05,
          maMode: 'any',
          takeProfitPct: 25,
          stopLossPct: 15,
          addOnDropPct: 8,
          maxAdds: 3,
          totalCapital: 600000,
          trancheAmount: 60000,
          maxPositionPct: 60,
          frequency: 'weekly',
          reinvestDividend: false,
        ),
        const TradeStrategy(
          id: 'preset_ma',
          name: '季線分批型',
          note: '只在跌破季線時才開始買，越跌越分批；回到成本上方一定幅度就停利。',
          maMode: 'below',
          maPct: 5,
          entryRsiMax: 45,
          takeProfitPct: 20,
          stopLossPct: 12,
          addOnDropPct: 7,
          maxAdds: 3,
          totalCapital: 600000,
          trancheAmount: 50000,
          maxPositionPct: 80,
          frequency: 'weekly',
        ),
        const TradeStrategy(
          id: 'preset_momentum',
          name: '動能突破型',
          note: '站上季線且不過熱時進場，嚴格停損；適合想抓波段但不想盯盤的人。',
          maMode: 'above',
          maPct: 0,
          entryRsiMax: 70,
          takeProfitPct: 30,
          stopLossPct: 10,
          addOnDropPct: 0,
          maxAdds: 0,
          totalCapital: 500000,
          trancheAmount: 50000,
          maxPositionPct: 100,
          frequency: 'daily',
        ),
      ];
}
