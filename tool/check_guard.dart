// 合規自檢：確認風控 Agent 與語意解析的行為（不進入網頁產物）
// ignore_for_file: avoid_print, avoid_relative_lib_imports
import '../lib/agents/agents.dart';
import '../lib/core/constants.dart';

void main() {
  final samples = <String>[
    '用高殖利率策略回測台積電過去5年',
    '幫我預測台積電目標價',
    '中華電均線策略回測三年',
    '0056 高股息 5 年',
  ];
  for (final s in samples) {
    final r = QueryParser.parse(s);
    print('查詢「$s」 → 股票=${r.stockId} 策略=${r.strategyId} 年=${r.years} 攔截=${r.riskIntent} ${r.riskReason}');
  }

  const normal = '這是一份歷史回測報告，均線分批布局策略，每月固定投入，評估策略歷史表現。';
  final c = ComplianceAgent.check(normal);
  print('一般文本：攔截=${c.blocked} 改寫=${c.rewrittenTerms} 末尾含免責=${c.text.endsWith(kDisclaimer)}');

  const risky = '建議買進，目標價 3000 元，保證必漲。';
  final c2 = ComplianceAgent.check(risky);
  print('高風險文本：攔截=${c2.blocked} 告警=${c2.alerts}');
}
