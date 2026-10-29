// ============================================================================
// 模擬交易盤（Paper Trading）
// ----------------------------------------------------------------------------
// 目的：用虛擬資金練習「下單 → 持有 → 出場」的完整流程，建立肌肉記憶。
// 規則（刻意簡化，避免誤導）：
//   · 成交價 = 目前資料的最新收盤價（不是即時價，也不是未成交掛單）
//   · 手續費 0.1425% × 6 折（最低 20 元）；賣出另加證交稅 0.3%（ETF 0.1%）
//   · 只能整股買賣，不做融資、放空、零股
//   · 全部存在本機 localStorage，不上傳
//   · 這是練習用的虛擬帳戶，與真實券商帳戶完全無關
// ============================================================================

import 'dart:convert';
import 'dart:html' as html; // ignore: avoid_web_libraries_in_flutter

class PaperTrade {
  final String id;
  final String stockId;
  final String stockName;
  final String side; // buy / sell
  final double price;
  final int shares;
  final double fee;
  final double tax;
  final String time;
  final double realized; // 賣出時的已實現損益（買入為 0）

  PaperTrade({
    required this.id,
    required this.stockId,
    required this.stockName,
    required this.side,
    required this.price,
    required this.shares,
    required this.fee,
    required this.tax,
    required this.time,
    this.realized = 0,
  });

  double get gross => price * shares;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'id': id,
        'stockId': stockId,
        'stockName': stockName,
        'side': side,
        'price': price,
        'shares': shares,
        'fee': fee,
        'tax': tax,
        'time': time,
        'realized': realized,
      };

  factory PaperTrade.fromJson(Map<String, dynamic> j) => PaperTrade(
        id: j['id'] as String,
        stockId: j['stockId'] as String,
        stockName: j['stockName'] as String,
        side: j['side'] as String,
        price: (j['price'] as num).toDouble(),
        shares: (j['shares'] as num).toInt(),
        fee: (j['fee'] as num?)?.toDouble() ?? 0,
        tax: (j['tax'] as num?)?.toDouble() ?? 0,
        time: j['time'] as String? ?? '',
        realized: (j['realized'] as num?)?.toDouble() ?? 0,
      );
}

class PaperPosition {
  final String stockId;
  final String stockName;
  int shares;
  double avgCost; // 含手續費的每股成本

  PaperPosition(this.stockId, this.stockName, this.shares, this.avgCost);

  Map<String, dynamic> toJson() => <String, dynamic>{
        'stockId': stockId,
        'stockName': stockName,
        'shares': shares,
        'avgCost': avgCost,
      };

  factory PaperPosition.fromJson(Map<String, dynamic> j) => PaperPosition(
        j['stockId'] as String,
        j['stockName'] as String,
        (j['shares'] as num).toInt(),
        (j['avgCost'] as num).toDouble(),
      );
}

/// 交易成本規則（集中一處，方便調整）
class TradeCost {
  static const double feeRate = 0.001425;
  static const double feeDiscount = 0.6;
  static const double minFee = 20;

  static double buyFee(double amount) =>
      (amount * feeRate * feeDiscount).clamp(minFee, double.infinity).toDouble();

  static double sellFee(double amount) =>
      (amount * feeRate * feeDiscount).clamp(minFee, double.infinity).toDouble();

  static double tax(double amount, {bool isEtf = false}) =>
      amount * (isEtf ? 0.001 : 0.003);
}
