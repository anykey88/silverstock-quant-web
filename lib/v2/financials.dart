/// SilverStock v2 — 財務品質（規則式，每條可追溯）
///
/// 不用「綜合評分黑箱」，改成逐條列出：指標值 → 門檻 → 判定 → 理由。
/// 任何一條都可以被使用者拿財報原文對照驗證，這是「客觀」的最低要求。
library silverstock_v2.financials;

import 'data.dart';
import 'stats.dart';

enum Verdict { good, neutral, bad, unknown }

class CheckItem {
  final String name;
  final String? value; // 已格式化的顯示值
  final String threshold; // 門檻描述
  final Verdict verdict;
  final String reason; // 為什麼這條重要（用台股實務語言）

  const CheckItem(this.name, this.value, this.threshold, this.verdict, this.reason);
}

class FinancialQuality {
  final List<CheckItem> items;
  final int goodCount;
  final int badCount;
  final int scoredCount;
  final double? roe;
  final double? grossMargin;
  final double? operatingMargin;
  final double? netMargin;
  final double? debtRatio;
  final double? currentRatio;
  final double? freeCashFlow;
  final double? payoutRatio;
  final double? arDays;
  final double? inventoryDays;

  const FinancialQuality({
    required this.items,
    required this.goodCount,
    required this.badCount,
    required this.scoredCount,
    this.roe,
    this.grossMargin,
    this.operatingMargin,
    this.netMargin,
    this.debtRatio,
    this.currentRatio,
    this.freeCashFlow,
    this.payoutRatio,
    this.arDays,
    this.inventoryDays,
  });

  /// 0–100。只計算有資料的項目，缺資料不倒扣（避免「資料少＝分數低」的偏誤）。
  int? get score {
    if (scoredCount == 0) return null;
    return ((goodCount * 100.0) / scoredCount).round();
  }

  String get grade {
    final s = score;
    if (s == null) return '資料不足';
    if (s >= 75) return '體質穩健';
    if (s >= 55) return '尚可，需留意個別項目';
    if (s >= 35) return '偏弱，先查明原因';
    return '明顯轉差，不建議只看殖利率';
  }
}

class FinancialEngine {
  static FinancialQuality build(StockDataset d) {
    final items = <CheckItem>[];

    final q = d.quarters;
    final bs = d.balanceSheets.isEmpty ? null : d.balanceSheets.last;
    final last4 = q.length >= 4 ? q.sublist(q.length - 4) : q;
    final prev4 = q.length >= 8
        ? q.sublist(q.length - 8, q.length - 4)
        : <Quarter>[];

    // --- 獲利能力 -----------------------------------------------------------
    final gm = last4.isEmpty ? null : _avg(last4.map((x) => x.grossMargin));
    final om = last4.isEmpty ? null : _avg(last4.map((x) => x.operatingMargin));
    final nm = last4.isEmpty ? null : _avg(last4.map((x) => x.netMargin));

    if (gm != null) {
      items.add(CheckItem(
        '毛利率（近 4 季平均）',
        '${gm.toStringAsFixed(1)}%',
        '≥ 25% 較佳；< 15% 偏薄',
        gm >= 25 ? Verdict.good : (gm >= 15 ? Verdict.neutral : Verdict.bad),
        '毛利率代表產品定價能力。台股代工組裝類天生偏低，要跟同業比，不要跟軟體股比。',
      ));
    }

    if (om != null) {
      items.add(CheckItem(
        '營業利益率（近 4 季平均）',
        '${om.toStringAsFixed(1)}%',
        '≥ 10% 較佳；< 3% 偏薄',
        om >= 10 ? Verdict.good : (om >= 3 ? Verdict.neutral : Verdict.bad),
        '本業賺不賺錢看這個，比稅後淨利乾淨——稅後常被業外處分利益或匯兌美化。',
      ));
    }

    // --- 毛利率趨勢 ---------------------------------------------------------
    if (prev4.isNotEmpty && gm != null) {
      final prevGm = _avg(prev4.map((x) => x.grossMargin));
      if (prevGm != null) {
        final diff = gm - prevGm;
        items.add(CheckItem(
          '毛利率趨勢（近 4 季 vs 前 4 季）',
          '${diff >= 0 ? '+' : ''}${diff.toStringAsFixed(1)} 個百分點',
          '持平或上升',
          diff >= 0.5
              ? Verdict.good
              : (diff > -0.5 ? Verdict.neutral : Verdict.bad),
          '毛利率連續下滑通常是報價壓力或產品組合變差，比單季獲利衰退更早出現。',
        ));
      }
    }

    // --- ROE ---------------------------------------------------------------
    final niTtm = _sum(last4.map((x) => x.netIncome));
    final equity = bs?.equity;
    double? roe;
    if (niTtm != null && equity != null && equity > 0) {
      roe = niTtm / equity * 100;
      items.add(CheckItem(
        'ROE（近 4 季淨利 ÷ 股東權益）',
        '${roe.toStringAsFixed(1)}%',
        '≥ 12% 較佳；< 6% 偏弱',
        roe >= 12 ? Verdict.good : (roe >= 6 ? Verdict.neutral : Verdict.bad),
        '股東每投入 100 元，公司一年幫你賺多少。長期 ROE 高且穩，是複利的來源。',
      ));
    }

    // --- 財務結構 -----------------------------------------------------------
    final debt = bs?.debtRatio;
    if (debt != null) {
      items.add(CheckItem(
        '負債比',
        '${debt.toStringAsFixed(1)}%',
        '< 50% 穩健；> 65% 偏高',
        debt < 50 ? Verdict.good : (debt <= 65 ? Verdict.neutral : Verdict.bad),
        '負債比高的公司遇到升息或景氣反轉，利息會先吃掉獲利。金融股天生負債比高，此條不適用。',
      ));
    }

    final cr = bs?.currentRatio;
    if (cr != null) {
      items.add(CheckItem(
        '流動比',
        cr.toStringAsFixed(2),
        '≥ 1.5 較安全；< 1.0 有短期償債壓力',
        cr >= 1.5 ? Verdict.good : (cr >= 1.0 ? Verdict.neutral : Verdict.bad),
        '一年內要還的錢，手上流動資產夠不夠還。',
      ));
    }

    // --- 現金流 -------------------------------------------------------------
    final cf = d.cashFlows;
    final last4cf = cf.length >= 4 ? cf.sublist(cf.length - 4) : cf;
    final fcf = _sum(last4cf.map((x) => x.freeCashFlow));
    if (fcf != null) {
      items.add(CheckItem(
        '自由現金流（近 4 季）',
        _money(fcf),
        '為正較佳',
        fcf > 0 ? Verdict.good : Verdict.bad,
        '本業賺的錢扣掉蓋廠買設備後，還剩多少能發股利。長期為負卻又高配息，通常靠借錢或賣資產。',
      ));
    }

    // --- 配息可持續性 -------------------------------------------------------
    final eps = d.epsTtm;
    final div = d.annualCashDividend;
    double? payout;
    if (eps != null && eps > 0 && div > 0) {
      payout = div / eps * 100;
      items.add(CheckItem(
        '股息發放率',
        '${payout.toStringAsFixed(0)}%',
        '40–80% 較可持續；> 100% 需查原因',
        payout <= 90 && payout >= 30
            ? Verdict.good
            : (payout <= 110 ? Verdict.neutral : Verdict.bad),
        '賺 100 元配 60 元，剩 40 元留著擴產，這是健康的。配超過賺的，長期一定是吃老本。',
      ));
    }

    // --- 營運效率 -----------------------------------------------------------
    final arDays = _turnoverDays(d, receivables: true);
    if (arDays != null) {
      items.add(CheckItem(
        '應收帳款週轉天數',
        '${arDays.toStringAsFixed(0)} 天',
        '與同業比較，且未明顯拉長',
        arDays <= 90 ? Verdict.good : (arDays <= 150 ? Verdict.neutral : Verdict.bad),
        '貨賣出去了但錢還沒收到。天數突然拉長，可能是客戶付不出來或塞貨給通路。',
      ));
    }

    final invDays = _turnoverDays(d, receivables: false);
    if (invDays != null) {
      items.add(CheckItem(
        '存貨週轉天數',
        '${invDays.toStringAsFixed(0)} 天',
        '與同業比較，且未明顯拉長',
        invDays <= 90 ? Verdict.good : (invDays <= 150 ? Verdict.neutral : Verdict.bad),
        '貨堆在倉庫多久才賣掉。電子業存貨天數上升，常是景氣反轉的第一個訊號。',
      ));
    }

    final scored = items.where((i) => i.verdict != Verdict.unknown).toList();
    return FinancialQuality(
      items: items,
      goodCount: scored.where((i) => i.verdict == Verdict.good).length,
      badCount: scored.where((i) => i.verdict == Verdict.bad).length,
      scoredCount: scored.length,
      roe: roe,
      grossMargin: gm,
      operatingMargin: om,
      netMargin: nm,
      debtRatio: debt,
      currentRatio: cr,
      freeCashFlow: fcf,
      payoutRatio: payout,
      arDays: arDays,
      inventoryDays: invDays,
    );
  }

  // --- 內部 ---------------------------------------------------------------

  static double? _avg(Iterable<double?> xs) {
    final v = xs.whereType<double>().toList();
    if (v.isEmpty) return null;
    return v.reduce((a, b) => a + b) / v.length;
  }

  static double? _sum(Iterable<double?> xs) {
    final v = xs.whereType<double>().toList();
    if (v.isEmpty) return null;
    return v.reduce((a, b) => a + b);
  }

  /// 週轉天數：以最近一季的期末餘額 ÷ 該季營收（或成本）× 91 天。
  static double? _turnoverDays(StockDataset d, {required bool receivables}) {
    if (d.balanceSheets.isEmpty || d.quarters.isEmpty) return null;
    final bs = d.balanceSheets.last;
    final q = d.quarters.last;
    if (receivables) {
      final ar = bs.receivables;
      if (ar == null || ar <= 0 || q.revenue <= 0) return null;
      return ar / q.revenue * 91;
    } else {
      final inv = bs.inventories;
      final cogs = q.cogs;
      if (inv == null || inv <= 0 || cogs == null || cogs <= 0) return null;
      return inv / cogs * 91;
    }
  }

  static String _money(double v) {
    final abs = v.abs();
    final sign = v < 0 ? '-' : '';
    if (abs >= 1e12) return '$sign${(abs / 1e12).toStringAsFixed(2)} 兆';
    if (abs >= 1e8) return '$sign${(abs / 1e8).toStringAsFixed(1)} 億';
    if (abs >= 1e4) return '$sign${(abs / 1e4).toStringAsFixed(0)} 萬';
    return '$sign${abs.toStringAsFixed(0)}';
  }
}
