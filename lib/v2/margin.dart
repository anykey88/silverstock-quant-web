/// 融資融券與槓桿風險引擎
// ---------------------------------------------------------------------------
/// 這個檔案回答兩個問題，而不是一個：
///   1. 這檔股票的籌碼結構現在長什麼樣（融資餘額、券源用了多少）
///   2. 以你的風險承受能力，最多能借多少錢買它
///
/// 融資餘額上升不是「人氣旺」這麼簡單。它同時是未實現賣壓：
/// 那些人借錢買、成本被套在上面，股價回到成本區就會解套賣出。
/// 所以融資高的股票，上漲時會遇到源源不絕的解套賣單。
library silverstock_v2.margin;

/// 單日融資融券餘額
class MarginPoint {
  final String date;
  final int marginBal; // 融資今日餘額（張）
  final int shortBal; // 融券今日餘額（張）
  final int marginLimit; // 融資限額（張）
  final int shortLimit; // 融券限額（張）

  const MarginPoint({
    required this.date,
    required this.marginBal,
    required this.shortBal,
    required this.marginLimit,
    required this.shortLimit,
  });
}

/// 一檔股票的籌碼面剖面
class MarginProfile {
  final String stockId;
  final bool hasData;

  final int marginBal;
  final int shortBal;
  final int marginLimit;
  final int shortLimit;

  /// 券源使用率＝融資餘額／融資限額。
  /// 注意：這個數字幾乎永遠低於 1%——因為融資限額是「整間公司股數」的某個比例，
  /// 不是「今天可以借你多少」。它只在極端炒作股上才會衝高，當異常偵測用。
  final double? usageRate;

  /// 融資餘額換算成「幾天的成交量」。這才是實務上有用的水位指標：
  /// 3 天以內算正常，超過 10 天代表有一批借錢買的人套在上面，
  /// 他們解套的賣壓會壓著股價。
  final double? turnoverDays;

  /// 融券使用率＝融券餘額／融券限額。
  final double? shortUsageRate;

  /// 券資比＝融券餘額／融資餘額。低於 5% 代表幾乎沒人放空。
  final double? shortToMargin;

  /// 融資餘額 5 日／20 日變化（%）
  final double? chg5;
  final double? chg20;

  /// 需要的自備款比例（融資成數的補數）
  final double ownRatio;

  /// 這檔股票在目前融資成數下，從成本價起算的追繳價跌幅（%）
  final double callDropPct;

  /// 資料最後一筆的日期（不是抓取日期）
  final String lastDate;

  final List<String> notes;

  const MarginProfile({
    required this.lastDate,
    required this.stockId,
    required this.hasData,
    required this.marginBal,
    required this.shortBal,
    required this.marginLimit,
    required this.shortLimit,
    required this.usageRate,
    required this.turnoverDays,
    required this.shortUsageRate,
    required this.shortToMargin,
    required this.chg5,
    required this.chg20,
    required this.ownRatio,
    required this.callDropPct,
    required this.notes,
  });

  static const MarginProfile empty = MarginProfile(
    lastDate: '',
    stockId: '',
    hasData: false,
    marginBal: 0,
    shortBal: 0,
    marginLimit: 0,
    shortLimit: 0,
    usageRate: null,
    turnoverDays: null,
    shortUsageRate: null,
    shortToMargin: null,
    chg5: null,
    chg20: null,
    ownRatio: 0.4,
    callDropPct: 22,
    notes: <String>[],
  );

  /// 以某個成本價計算追繳價。
  ///
  /// 券商以「整戶擔保維持率 130%」為追繳線：
  ///   維持率 = 擔保品市值 / 融資金額
  ///   融資金額 = 成本價 × 融資成數
  ///   → 追繳價 = 成本價 × 融資成數 × 1.30
  /// 上市股成數 60% → 追繳價 = 成本 × 0.78，也就是跌 22% 就會被通知。
  double callPrice(double costPrice) => costPrice * (1 - callDropPct / 100);

  /// 斷頭價：維持率掉到 110% 左右，券商會直接處分。
  double liquidationPrice(double costPrice) =>
      costPrice * (1 - callDropPct / 100) * 110 / 130;
}

class MarginEngine {
  /// 上市股 60%、上櫃股 50%。資料源沒有上市別，預設用 60%（比較寬鬆，
  /// 等於低估風險），由上層依個股性質覆寫。
  static MarginProfile build(
    String stockId,
    List<MarginPoint> rows, {
    double financeRatio = 0.60,
    double avgVolume20 = 0,
  }) {
    if (rows.isEmpty) return MarginProfile.empty;

    final sorted = List<MarginPoint>.from(rows)
      ..sort((a, b) => a.date.compareTo(b.date));
    final last = sorted.last;

    final usage = last.marginLimit > 0
        ? last.marginBal / last.marginLimit * 100
        : null;
    final shortUsage = last.shortLimit > 0
        ? last.shortBal / last.shortLimit * 100
        : null;
    final s2m = last.marginBal > 0
        ? last.shortBal / last.marginBal * 100
        : null;
    final tdays =
        avgVolume20 > 0 ? last.marginBal / avgVolume20 : null;

    double? pctChange(int back) {
      final i = sorted.length - 1 - back;
      if (i < 0) return null;
      final base = sorted[i].marginBal;
      if (base <= 0) return null;
      return (last.marginBal - base) / base * 100;
    }

    final notes = <String>[];

    // 套牢籌碼的厚度：融資餘額相當於幾天的成交量
    if (tdays != null) {
      if (tdays >= 15) {
        notes.add('融資餘額相當於 ${tdays.toStringAsFixed(0)} 個交易日的成交量，'
            '非常厚。這批人成本都在附近，反彈到他們的成本區就會遇到解套賣壓。');
      } else if (tdays >= 6) {
        notes.add('融資餘額相當於 ${tdays.toStringAsFixed(1)} 個交易日的成交量，'
            '偏多但還沒到極端。');
      } else if (tdays < 2) {
        notes.add('融資餘額只相當於 ${tdays.toStringAsFixed(1)} 個交易日的成交量，'
            '籌碼相對乾淨，沒有大量借錢買的套牢盤。');
      }
    }

    // 券源使用率：正常標的幾乎都是 0.x%，只有異常炒作時才需要提醒
    if (usage != null && usage >= 20) {
      notes.add('融資限額已用掉 ${usage.toStringAsFixed(0)}%，'
          '這種水位通常出現在股價被連續炒高之後，要注意流動性反轉。');
    }

    // 券資比
    if (s2m != null) {
      if (s2m < 3) {
        notes.add('券資比 ${s2m.toStringAsFixed(1)}%，幾乎沒人放空。'
            '一片樂觀時，通常也是沒人幫你踩剎車的時候。');
      } else if (s2m > 25) {
        notes.add('券資比 ${s2m.toStringAsFixed(1)}%，空單不少。'
            '這些人未來要回補，是潛在買盤，但也代表有一批人看法跟你相反。');
      }
    }

    // 餘額變化
    final c20 = pctChange(20);
    if (c20 != null) {
      if (c20 >= 15) {
        notes.add('近 20 個交易日融資餘額增加 ${c20.toStringAsFixed(0)}%，'
            '散戶在加槓桿進場——這批籌碼的成本就在附近，回檔時容易鬆動。');
      } else if (c20 <= -15) {
        notes.add('近 20 個交易日融資餘額減少 ${c20.abs().toStringAsFixed(0)}%，'
            '有人在認賠出場，賣壓正在消化。');
      }
    }

    if (notes.isEmpty) {
      notes.add('融資融券水位沒有異常，籌碼面沒有額外訊號。');
    }

    return MarginProfile(
      lastDate: last.date,
      stockId: stockId,
      hasData: true,
      marginBal: last.marginBal,
      shortBal: last.shortBal,
      marginLimit: last.marginLimit,
      shortLimit: last.shortLimit,
      usageRate: usage,
      turnoverDays: tdays,
      shortUsageRate: shortUsage,
      shortToMargin: s2m,
      chg5: pctChange(5),
      chg20: c20,
      ownRatio: 1 - financeRatio,
      callDropPct: (financeRatio * 1.30 * 100 - 100) < 0
          ? -(financeRatio * 1.30 * 100 - 100)
          : 0,
      notes: notes,
    );
  }
}

// ---------------------------------------------------------------------------
// 風險承受能力 → 可融資上限
// ---------------------------------------------------------------------------

/// 槓桿建議結果
class LeverageAdvice {
  /// 光是自有資金，就已經超過你能承受的虧損 → 不該融資
  final bool marginAllowed;

  /// 最大可持有的總市值（自有＋融資）
  final double maxMarketValue;

  /// 建議融資上限（0 代表不該借）
  final double maxLoan;

  /// 等效槓桿倍數（總市值 / 自有資金）
  final double leverage;

  /// 一句話結論
  final String verdict;

  /// 推導步驟，讓使用者自己檢查這個數字怎麼來的
  final List<String> steps;

  const LeverageAdvice({
    required this.marginAllowed,
    required this.maxMarketValue,
    required this.maxLoan,
    required this.leverage,
    required this.verdict,
    required this.steps,
  });
}

class RiskBudget {
  /// 用「能承受的虧損」反推「可以持有多少部位」。
  ///
  /// 公式很簡單，但方向跟多數人想的相反：
  ///   可承受虧損金額 = 自有資金 × 承受比例
  ///   最大部位市值   = 可承受虧損金額 / 預估最大跌幅
  ///   可融資額       = 最大部位市值 − 自有資金
  ///
  /// 重點：**分母是預估跌幅**。跌幅估得越大，能買的越少。
  /// 如果你覺得「這檔不會跌那麼多」而把跌幅調小，那只是在自我催眠——
  /// 這個計算器的價值就在於逼你把那個數字寫出來。
  static LeverageAdvice evaluate({
    required double ownCapital,
    required double toleratePct, // 能承受的總虧損占自有資金比例（%）
    required double worstDropPct, // 預估最大跌幅（%），用歷史回撤代入
    required double financeRatio, // 融資成數 0.6 / 0.5
  }) {
    final steps = <String>[];
    final tolerableLoss = ownCapital * toleratePct / 100;
    steps.add('可承受虧損：${_money(ownCapital)} × ${toleratePct.toStringAsFixed(0)}% '
        '= ${_money(tolerableLoss)}');

    final drop = worstDropPct <= 0 ? 1 : worstDropPct;
    final maxMv = tolerableLoss / (drop / 100);
    steps.add('若這檔最多跌 ${drop.toStringAsFixed(0)}%，'
        '要讓虧損不超過上限，部位市值最多 ${_money(maxMv)}');
    steps.add('算法：${_money(tolerableLoss)} ÷ ${(drop / 100).toStringAsFixed(2)} '
        '= ${_money(maxMv)}');

    if (maxMv <= ownCapital) {
      steps.add('這個市值比你手上的 ${_money(ownCapital)} 還小——'
          '代表光是自有資金全押，就已經超過你能承受的虧損。');
      return LeverageAdvice(
        marginAllowed: false,
        maxMarketValue: maxMv,
        maxLoan: 0,
        leverage: 1,
        verdict: '不該融資。這檔的波動對你的資金規模來說太大，'
            '先降低部位或換波動小一點的標的。',
        steps: steps,
      );
    }

    final loan = maxMv - ownCapital;
    final byRatio = ownCapital * financeRatio / (1 - financeRatio);
    final cap = loan < byRatio ? loan : byRatio;
    final lev = (ownCapital + cap) / ownCapital;

    steps.add('可融資上限（風險預算）＝ ${_money(maxMv)} − ${_money(ownCapital)} '
        '= ${_money(loan)}');
    steps.add('但券商依成數 ${(financeRatio * 100).toStringAsFixed(0)}% 最多只借你 '
        '${_money(byRatio)}，兩者取小 → ${_money(cap)}');
    steps.add('等效槓桿 ${lev.toStringAsFixed(2)} 倍。'
        '股價每跌 10%，你的自有資金會虧 ${(lev * 10).toStringAsFixed(1)}%。');

    String verdict;
    if (cap <= 0) {
      verdict = '不建議融資。';
    } else if (lev >= 1.6) {
      verdict = '可以借，但這已經是 1.6 倍以上的槓桿。'
          '先問自己：連續三根跌停睡得著嗎？睡不著就別借。';
    } else if (lev >= 1.3) {
      verdict = '適度槓桿。借 ${_money(cap)} 以內，'
          '且只用在波動小、配息穩的標的上。';
    } else {
      verdict = '小幅槓桿。上限 ${_money(cap)}，'
          '真正的限制是你的風險預算，不是券商的額度。';
    }

    return LeverageAdvice(
      marginAllowed: true,
      maxMarketValue: maxMv,
      maxLoan: cap,
      leverage: lev,
      verdict: verdict,
      steps: steps,
    );
  }

  static String _money(double v) {
    if (v.abs() >= 10000) {
      return '${(v / 10000).toStringAsFixed(1)} 萬';
    }
    return v.toStringAsFixed(0);
  }
}
