/// SilverStock v2 — 估值分位與價位反推
///
/// 核心方法論：**不用預測，用「歷史倍數分位 × 已公布基本面」反推價位**。
///   - 倍數（PE / PBR / 殖利率）取自過去 N 年的實際成交分位 → 是統計事實
///   - 基本面（EPS TTM / 每股淨值 / 現金股利）取自公司已公布的財報 → 是事實
/// 兩者相乘得到的價位，可被任何人用同一份資料複算出來，因此是「客觀」的。
///
/// 本模組不做任何趨勢外推、不給單一目標價，只給「分位對應的價位區間」。
library silverstock_v2.valuation;

import 'data.dart';
import 'stats.dart';

class ValuationProfile {
  final double? currentPer;
  final double? currentPbr;
  final double? currentYield;
  final double? perP10, perP25, perP50, perP75, perP90;
  final double? pbrP10, pbrP25, pbrP50, pbrP75, pbrP90;
  final double? yieldP10, yieldP25, yieldP50, yieldP75, yieldP90;
  final int sampleDays;
  final String windowLabel;

  const ValuationProfile({
    required this.currentPer,
    required this.currentPbr,
    required this.currentYield,
    required this.perP10,
    required this.perP25,
    required this.perP50,
    required this.perP75,
    required this.perP90,
    required this.pbrP10,
    required this.pbrP25,
    required this.pbrP50,
    required this.pbrP75,
    required this.pbrP90,
    required this.yieldP10,
    required this.yieldP25,
    required this.yieldP50,
    required this.yieldP75,
    required this.yieldP90,
    required this.sampleDays,
    required this.windowLabel,
  });

  /// 當前 PE 在歷史分布中的百分位（0–100）。無法計算時回 null。
  double? get perPercentile {
    if (currentPer == null || perP10 == null) return null;
    final p = perP50;
    if (p == null || p <= 0) return null;
    // 以分位點做分段線性內插，比「輸出的原始序列再排一次」省記憶體且可解釋
    final anchors = <double?>[perP10, perP25, perP50, perP75, perP90];
    final pcts = <double>[10, 25, 50, 75, 90];
    return _interpPercentile(currentPer!, anchors, pcts);
  }

  double? get yieldPercentile {
    if (currentYield == null) return null;
    final anchors = <double?>[yieldP10, yieldP25, yieldP50, yieldP75, yieldP90];
    final pcts = <double>[10, 25, 50, 75, 90];
    return _interpPercentile(currentYield!, anchors, pcts);
  }

  /// 注意：殖利率與價位反向，百分位越高代表「越便宜」。
  static double? _interpPercentile(
      double value, List<double?> anchors, List<double> pcts) {
    final pts = <List<double>>[];
    for (var i = 0; i < anchors.length; i++) {
      if (anchors[i] != null) pts.add([anchors[i]!, pcts[i]]);
    }
    if (pts.length < 2) return null;
    pts.sort((a, b) => a[0].compareTo(b[0]));
    if (value <= pts.first[0]) return pts.first[1];
    if (value >= pts.last[0]) return pts.last[1];
    for (var i = 1; i < pts.length; i++) {
      if (value <= pts[i][0]) {
        final x0 = pts[i - 1][0], y0 = pts[i - 1][1];
        final x1 = pts[i][0], y1 = pts[i][1];
        if (x1 == x0) return y0;
        return y0 + (y1 - y0) * (value - x0) / (x1 - x0);
      }
    }
    return null;
  }
}

/// 一個價位，附帶計算依據（可複算）
class PriceLevel {
  final String label; // 例：「PE 25 分位」
  final double? price; // 元
  final String basis; // 例：「EPS(TTM) 58.4 × 25.3 倍」
  final String? caveat; // 此法在此標的上的限制

  const PriceLevel(this.label, this.price, this.basis, {this.caveat});
}

class ValuationEngine {
  /// 建立估值分位檔。預設取近 5 年日資料。
  static ValuationProfile profile(StockDataset d, {int years = 5}) {
    final cutoff = _cutoff(d, years);
    final vp = d.valuations.where((v) => v.date.compareTo(cutoff) >= 0).toList();

    final pers = vp.map((v) => v.per).whereType<double>().where((x) => x > 0).toList();
    final pbrs = vp.map((v) => v.pbr).whereType<double>().where((x) => x > 0).toList();
    final yields = vp
        .map((v) => v.yieldPct)
        .whereType<double>()
        .where((x) => x > 0)
        .toList();

    final last = d.valuations.isEmpty ? null : d.valuations.last;

    return ValuationProfile(
      currentPer: last?.per,
      currentPbr: last?.pbr,
      currentYield: last?.yieldPct,
      perP10: Stats.percentile(pers, 0.10),
      perP25: Stats.percentile(pers, 0.25),
      perP50: Stats.percentile(pers, 0.50),
      perP75: Stats.percentile(pers, 0.75),
      perP90: Stats.percentile(pers, 0.90),
      pbrP10: Stats.percentile(pbrs, 0.10),
      pbrP25: Stats.percentile(pbrs, 0.25),
      pbrP50: Stats.percentile(pbrs, 0.50),
      pbrP75: Stats.percentile(pbrs, 0.75),
      pbrP90: Stats.percentile(pbrs, 0.90),
      yieldP10: Stats.percentile(yields, 0.10),
      yieldP25: Stats.percentile(yields, 0.25),
      yieldP50: Stats.percentile(yields, 0.50),
      yieldP75: Stats.percentile(yields, 0.75),
      yieldP90: Stats.percentile(yields, 0.90),
      sampleDays: vp.length,
      windowLabel: '近 $years 年',
    );
  }

  /// 用 PE 分位 × EPS(TTM) 反推價位
  static List<PriceLevel> peLevels(StockDataset d, ValuationProfile p) {
    final eps = d.epsTtm;
    if (eps == null || eps <= 0) {
      return [
        PriceLevel('本益比法不適用', null, 'EPS(TTM) 為負或缺失，PE 無意義',
            caveat: '虧損或無 EPS 資料時，只能用股價淨值比或殖利率評估'),
      ];
    }
    final warn = _cycleCaveat(d);
    final out = <PriceLevel>[];
    void add(String label, double? m) {
      if (m == null || m <= 0) return;
      out.add(PriceLevel(
        label,
        eps * m,
        'EPS(TTM) ${eps.toStringAsFixed(2)} × ${m.toStringAsFixed(1)} 倍',
        caveat: warn,
      ));
    }

    add('PE 10 分位（歷史最便宜 10%）', p.perP10);
    add('PE 25 分位', p.perP25);
    add('PE 50 分位（中位數）', p.perP50);
    add('PE 75 分位', p.perP75);
    add('PE 90 分位（歷史最貴 10%）', p.perP90);
    return out;
  }

  /// 用「目標殖利率」反推價位（存股族最直觀）
  static List<PriceLevel> yieldLevels(StockDataset d) {
    final div = d.annualCashDividend;
    if (div <= 0) {
      return [
        PriceLevel('殖利率法不適用', null, '近一年無現金股利紀錄',
            caveat: '不配息或不穩定配息的公司，殖利率反推沒有參考價值'),
      ];
    }
    // 現價殖利率過低時，此法反推的價位會離市價極遠，必須明示不可作為主要依據
    final cur = d.valuations.isEmpty ? null : d.valuations.last.yieldPct;
    final curClose = d.latest?.close;
    String? base = _dividendCaveat(d);
    if (cur != null && cur > 0 && cur < 2.0 && curClose != null) {
      final implied = div / (cur / 100);
      base =
          '目前殖利率僅 ${cur.toStringAsFixed(2)}%，市場是以成長而非配息定價；'
          '殖利率法反推價位（3% 對應 ${(div / 0.03).toStringAsFixed(0)} 元）與市價 '
          '${curClose.toStringAsFixed(0)} 元差距過大，不宜作為主要估價依據';
      if (implied > 0 && implied < curClose * 0.5) {
        // 已包含在上述描述中
      }
    }
    final out = <PriceLevel>[];
    for (final target in [3.0, 4.0, 5.0, 6.0, 7.0, 8.0]) {
      out.add(PriceLevel(
        '殖利率 ${target.toStringAsFixed(0)}%',
        div / (target / 100),
        '年現金股利 ${div.toStringAsFixed(2)} 元 ÷ ${target.toStringAsFixed(0)}%',
        caveat: base,
      ));
    }
    return out;
  }

  /// 用 PBR 分位 × 每股淨值反推（適合虧損股、資產股、金融股）
  static List<PriceLevel> pbrLevels(StockDataset d, ValuationProfile p) {
    final bs = d.balanceSheets.isEmpty ? null : d.balanceSheets.last;
    final equity = bs?.equity;
    if (equity == null || equity <= 0) {
      return const [PriceLevel('股價淨值比法不適用', null, '缺少股東權益資料')];
    }
    // 需要股數：用市值 / 股價反推，或直接由 EPS 與淨利推得
    // 這裡以「近 4 季淨利合計 ÷ EPS(TTM)」估股數，避免另抓資料集
    final eps = d.epsTtm;
    final ni = _netIncomeTtm(d);
    double? shares;
    if (eps != null && eps > 0 && ni != null && ni > 0) {
      shares = ni / eps;
    }
    if (shares == null || shares <= 0) {
      return const [PriceLevel('股價淨值比法不適用', null, '無法推算流通股數')];
    }
    final bvps = equity / shares; // 每股淨值
    final out = <PriceLevel>[];
    void add(String label, double? m) {
      if (m == null || m <= 0) return;
      out.add(PriceLevel(
        label,
        bvps * m,
        '每股淨值 ${bvps.toStringAsFixed(2)} × ${m.toStringAsFixed(2)} 倍',
      ));
    }

    add('PBR 10 分位', p.pbrP10);
    add('PBR 25 分位', p.pbrP25);
    add('PBR 50 分位', p.pbrP50);
    add('PBR 75 分位', p.pbrP75);
    return out;
  }

  // --- 內部 ---------------------------------------------------------------

  static String _cutoff(StockDataset d, int years) {
    if (d.bars.isEmpty) return '0000-00-00';
    final last = DateTime.tryParse(d.bars.last.date) ?? DateTime(2026);
    final c = DateTime(last.year - years, last.month, last.day);
    return c.toIso8601String().substring(0, 10);
  }

  static double? _netIncomeTtm(StockDataset d) {
    final valid = d.quarters.where((q) => q.netIncome != null).toList();
    if (valid.isEmpty) return null;
    final take = valid.length >= 4 ? valid.sublist(valid.length - 4) : valid;
    if (take.length < 4) return null;
    return take.fold<double>(0, (s, q) => s + q.netIncome!);
  }

  /// 景氣循環警示：若 TTM EPS 處於近 5 年季度 EPS 的高分位，PE 反推會系統性偏高。
  static String? _cycleCaveat(StockDataset d) {
    final epsList = d.quarters.map((q) => q.eps).whereType<double>().toList();
    if (epsList.length < 8) return null;
    final p80 = Stats.percentile(epsList, 0.80);
    final ttm = d.epsTtm;
    if (p80 == null || ttm == null) return null;
    // 以「單季 EPS 的 4 倍」與 TTM 比較，避免單位不同
    if (ttm >= p80 * 4 * 1.05) {
      return '目前 EPS 處於近 5 年高分位，景氣循環股在高點用 PE 反推會偏高';
    }
    return null;
  }

  static String? _dividendCaveat(StockDataset d) {
    final recent = d.dividends.length >= 4
        ? d.dividends.sublist(d.dividends.length - 4)
        : d.dividends;
    if (recent.isEmpty) return null;
    final amounts = recent.map((x) => x.cash).toList();
    final mn = amounts.reduce((a, b) => a < b ? a : b);
    final mx = amounts.reduce((a, b) => a > b ? a : b);
    if (mn <= 0) return '近年曾有不配息紀錄，年化股利可能高估';
    if (mx / mn > 1.5) {
      return '近年配息波動達 ${((mx / mn - 1) * 100).toStringAsFixed(0)}%，殖利率反推的穩定度較低';
    }
    return null;
  }
}
