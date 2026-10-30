// ============================================================================
// 帳戶匯出（CSV）與瀏覽器下載
// ----------------------------------------------------------------------------
// 為什麼是 CSV 而不是 PDF：
//   · 家人之間要「核對」——CSV 可以丟進 Excel 自己加減、加註解、做樞紐
//   · PDF 好看但不能算，對記帳沒用
//   · 匯出檔含個人持股，只在本機產生、直接下載，不經過任何伺服器
//
// 編碼：UTF-8 帶 BOM。沒有 BOM 的檔案，Excel 開起來中文會變亂碼——這是
// 很多人匯出台股資料後「怎麼全是問號」的真正原因。
// ============================================================================

import 'dart:convert';
import 'dart:html' as html; // ignore: avoid_web_libraries_in_flutter

import 'accounts.dart';

class AccountExport {
  /// 單一帳戶 → CSV 文字
  static String one(InvestAccount a, double Function(String) priceOf) {
    final b = StringBuffer();
    b.writeln('# SilverStock 帳戶匯出');
    b.writeln('帳戶,${_q(a.name)}');
    b.writeln('類型,${a.kind.label}');
    if (a.broker.isNotEmpty) b.writeln('券商,${_q(a.broker)}');
    if (a.note.isNotEmpty) b.writeln('備註,${_q(a.note)}');
    b.writeln('建立時間,${a.createdAt}');
    b.writeln('本金,${_n(a.initialCapital)}');
    b.writeln('現金,${_n(a.cash)}');
    b.writeln('持倉市值,${_n(a.marketValue(priceOf))}');
    b.writeln('總權益,${_n(a.equity(priceOf))}');
    b.writeln('已實現損益,${_n(a.realizedPnl)}');
    b.writeln('未實現損益,${_n(a.unrealized(priceOf))}');
    b.writeln('總報酬率,${a.returnPct(priceOf).toStringAsFixed(2)}%');
    b.writeln('匯出時間,${_now()}');
    b.writeln('說明,個人記帳紀錄；數字以本機紀錄與最新收盤價估算');
    b.writeln();

    b.writeln('[持倉]');
    b.writeln('股票代號,股票名稱,股數,平均成本,現價,市值,未實現損益,報酬率%');
    final list = a.positions.values.toList()
      ..sort((x, y) => (y.avgCost * y.shares).compareTo(x.avgCost * x.shares));
    for (final p in list) {
      final px = priceOf(p.stockId);
      final last = px > 0 ? px : p.avgCost;
      final mv = last * p.shares;
      final pnl = (last - p.avgCost) * p.shares;
      final pct = p.avgCost > 0 ? (last - p.avgCost) / p.avgCost * 100 : 0.0;
      b.writeln('${p.stockId},${_q(p.stockName)},${p.shares},'
          '${_n(p.avgCost)},${_n(last)},${_n(mv)},${_n(pnl)},${pct.toStringAsFixed(2)}');
    }
    if (list.isEmpty) b.writeln('（目前無持倉）');
    b.writeln();

    b.writeln('[交易紀錄]');
    b.writeln('時間,方向,股票代號,股票名稱,單價,股數,手續費,交易稅,成交金額,已實現損益');
    for (final t in a.trades) {
      final gross = t.price * t.shares;
      b.writeln('${t.time},${t.side == 'buy' ? '買進' : '賣出'},${t.stockId},'
          '${_q(t.stockName)},${_n(t.price)},${t.shares},'
          '${_n(t.fee)},${_n(t.tax)},${_n(gross)},${_n(t.realized)}');
    }
    if (a.trades.isEmpty) b.writeln('（目前無交易紀錄）');
    return b.toString();
  }

  /// 全部帳戶 → 一份 CSV：先總覽，再逐本明細
  static String all(AccountBook book, double Function(String) priceOf) {
    final b = StringBuffer();
    b.writeln('# SilverStock 全部帳戶匯出');
    b.writeln('帳戶數,${book.accounts.length}');
    b.writeln('合計本金,${_n(book.totalCapital)}');
    b.writeln('合計權益,${_n(book.totalEquity(priceOf))}');
    final cap = book.totalCapital;
    final eq = book.totalEquity(priceOf);
    b.writeln('合計報酬率,${cap > 0 ? ((eq - cap) / cap * 100).toStringAsFixed(2) : '0.00'}%');
    b.writeln('匯出時間,${_now()}');
    b.writeln('說明,個人記帳紀錄');
    b.writeln();

    b.writeln('[帳戶總覽]');
    b.writeln('帳戶,類型,券商,本金,現金,市值,總權益,報酬率%,持倉檔數');
    for (final a in book.accounts) {
      b.writeln('${_q(a.name)},${a.kind.label},${_q(a.broker)},'
          '${_n(a.initialCapital)},${_n(a.cash)},${_n(a.marketValue(priceOf))},'
          '${_n(a.equity(priceOf))},${a.returnPct(priceOf).toStringAsFixed(2)},'
          '${a.holdingCount}');
    }
    b.writeln();

    for (final a in book.accounts) {
      b.writeln('===== ${a.name} =====');
      // 重用單帳戶格式，但去掉第一行標題避免重複
      final block = one(a, priceOf).split('\n');
      for (var i = 1; i < block.length; i++) {
        b.writeln(block[i]);
      }
      b.writeln();
    }
    return b.toString();
  }

  /// 觸發瀏覽器下載。加 BOM 讓 Excel 認得 UTF-8。
  static void download(String filename, String content) {
    final bytes = utf8.encode('\uFEFF$content');
    final blob = html.Blob(<dynamic>[bytes], 'text/csv;charset=utf-8');
    final url = html.Url.createObjectUrlFromBlob(blob);
    final a = html.AnchorElement(href: url)
      ..download = filename
      ..style.display = 'none';
    html.document.body?.children.add(a);
    a.click();
    a.remove();
    html.Url.revokeObjectUrl(url);
  }

  static String safeName(String s) {
    final cleaned = s.replaceAll(RegExp(r'[\\/:*?"<>|\s]+'), '_');
    return cleaned.isEmpty ? 'account' : cleaned;
  }

  static String _now() {
    final t = DateTime.now();
    String two(int v) => v < 10 ? '0$v' : '$v';
    return '${t.year}-${two(t.month)}-${two(t.day)} ${two(t.hour)}:${two(t.minute)}';
  }

  static String _n(double v) => v.toStringAsFixed(2);

  /// CSV 欄位跳脫：含逗號、引號、換行時用雙引號包起來
  static String _q(String s) {
    if (s.contains(',') || s.contains('"') || s.contains('\n')) {
      return '"${s.replaceAll('"', '""')}"';
    }
    return s;
  }
}
