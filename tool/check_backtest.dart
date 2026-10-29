// 建置期自檢腳本：印出三套策略的回測指標，確認計算正確（不進入網頁產物）
// 用法：dart run tool/check_backtest.dart
// ignore_for_file: avoid_print, avoid_relative_lib_imports
import 'dart:convert';
import 'dart:io';

import '../lib/core/constants.dart';
import '../lib/engine/backtest.dart';
import '../lib/models/models.dart';

void main() {
  final raw = File('assets/data/snapshot.json').readAsStringSync();
  final root = jsonDecode(raw) as Map<String, dynamic>;
  final stocks = (root['stocks'] as Map).cast<String, dynamic>();

  for (final entry in stocks.entries) {
    final s = StockSeries.fromJson(entry.key, (entry.value as Map).cast<String, dynamic>());
    final end = _dt(s.dates.last);
    final start = _dt(s.dates.first);
    print('==== ${s.id} ${s.name} ${s.firstDateText}~${s.lastDateText}');
    for (final st in kStrategies) {
      final r = BacktestEngine.run(s, st, start, end);
      if (r == null) {
        print('  ${st.name}: (無資料)');
        continue;
      }
      final navMin = r.nav.map((e) => e.cumReturn).reduce((a, b) => a < b ? a : b);
      final navMax = r.nav.map((e) => e.cumReturn).reduce((a, b) => a > b ? a : b);
      print('  ${st.name}: 投入 ${r.totalInvested.toStringAsFixed(0)} 期末 ${r.finalValue.toStringAsFixed(0)} '
          'IRR ${r.irr.toStringAsFixed(1)}% MDD ${r.maxDrawdown.toStringAsFixed(1)}% '
          '勝率 ${(r.winRate * 100).toStringAsFixed(0)}% 曲線 ${navMin.toStringAsFixed(0)}%~${navMax.toStringAsFixed(0)}% '
          '加碼月 ${r.boostMonths} 空月 ${r.pauseMonths} 均價 ${r.avgCost.toStringAsFixed(1)}');
    }
  }
}

DateTime _dt(int ymd) => DateTime(ymd ~/ 10000, (ymd ~/ 100) % 100, ymd % 100);
