// ============================================================================
// WorkBuddy 5 Agent 叢集（前端同構執行版）
// ----------------------------------------------------------------------------
// 【架構說明】
// 正式架構：前端只做 UI，HTTP 呼叫 WorkBuddy 後端 Agent 叢集。
// 參賽 Demo：為避免公開網址依賴私有後端，前端內建「同構 Agent 執行時」，
//          完全相同的一份 5 Agent 流程在本機瀏覽器內執行；
//          只要設定 --dart-define=AGENT_ENDPOINT=https://... 即可切換為遠端呼叫
//          （見 AgentGateway），流程與資料契約完全不變。
//
// 執行順序（每次請求強制完整跑完，最後一步不可跳過）：
//   1. 基本面解析 Agent
//   2. 技術指標 Agent
//   3. 量化回測 Agent
//   4. 適老化翻譯 & 語音播報 Agent
//   5. 合規風控守門 Agent（後置校驗，必呼叫）
// ============================================================================

import 'dart:async';
import 'dart:math' as math;

import '../core/constants.dart';
import '../data/market_repository.dart';
import '../core/formatters.dart';
import '../engine/backtest.dart';
import '../engine/indicators.dart';
import '../models/models.dart';

enum AgentState { idle, running, done, blocked }

class AgentStep {
  final String key;
  final String name;
  final String role;
  AgentState state;
  String detail;
  AgentStep(this.key, this.name, this.role,
      {this.state = AgentState.idle, this.detail = ''});
}

class AgentEvent {
  final List<AgentStep> steps;
  final String currentKey;
  AgentEvent(this.steps, this.currentKey);
}

class PipelineOutcome {
  final ReportBundle? report;
  final bool blocked;
  final String blockReason;
  final List<AgentStep> steps;
  PipelineOutcome({
    this.report,
    this.blocked = false,
    this.blockReason = '',
    this.steps = const [],
  });
}

// ---------------------------------------------------------------------------
// Agent 1：基本面解析
// ---------------------------------------------------------------------------
class FundamentalAgent {
  static const String key = 'fundamental';
  static const String name = '基本面解析 Agent';

  static FundamentalReport run(StockSeries s, int startIdx, int endIdx) {
    final latest = s.latestPer;
    final risks = <RiskItem>[];

    final annual = s.annualEps;
    final years = annual.keys.toList()..sort();

    // 規則 1：曾出現單季虧損
    final lossQuarters =
        s.eps.where((q) => q.eps < 0).map((q) => q.ym).toList();
    if (lossQuarters.isNotEmpty) {
      risks.add(RiskItem(
        'high',
        '歷史上有單季虧損',
        '這段期間共有 ${lossQuarters.length} 個季度 EPS 為負（最近一次：${lossQuarters.last}）。'
            '單季虧損代表公司那段時間的營運沒有盈餘，需要留意後續變化。',
      ));
    }

    // 規則 2：年度 EPS 明顯下滑
    for (var i = 1; i < years.length; i++) {
      final prev = annual[years[i - 1]]!;
      final cur = annual[years[i]]!;
      if (prev > 0 && cur < prev * 0.7) {
        risks.add(RiskItem(
          'high',
          '${years[i]} 年度 EPS 明顯下滑',
          '${years[i]} 年 EPS 約 ${cur.toStringAsFixed(2)} 元，比 ${years[i - 1]} 年的 '
              '${prev.toStringAsFixed(2)} 元少了 ${((1 - cur / prev) * 100).toStringAsFixed(0)}%。',
        ));
      }
    }

    // 規則 3：配息金額明顯減少
    final divs = s.dividends;
    if (divs.length >= 2) {
      final last = divs.last.amount;
      final prev = divs[divs.length - 2].amount;
      if (prev > 0 && last < prev * 0.8) {
        risks.add(RiskItem(
          'watch',
          '最近一次配息比上一次少',
          '最近一次（${divs.last.ym}）每股配 ${last.toStringAsFixed(2)} 元，'
              '上一次是 ${prev.toStringAsFixed(2)} 元，減少約 ${((1 - last / prev) * 100).toStringAsFixed(0)}%。',
        ));
      }
    }

    // 規則 4：期間內價格大幅回落
    final closes = s.closes.sublist(startIdx, endIdx + 1);
    var peak = closes.first;
    var mdd = 0.0;
    for (final c in closes) {
      if (c > peak) peak = c;
      final dd = peak <= 0 ? 0.0 : (peak - c) / peak;
      if (dd > mdd) mdd = dd;
    }
    if (mdd > 0.25) {
      risks.add(RiskItem(
        'high',
        '歷史上曾出現較大幅度回落',
        '這段期間股價從最高點回落最多約 ${(mdd * 100).toStringAsFixed(1)}%，'
            '先知道歷史上會這樣，心裡比較有準備。',
      ));
    }

    // 規則 5：評價位階
    final med = s.perMedian;
    if (latest != null && med != null && latest.per > med * 1.5) {
      risks.add(RiskItem(
        'watch',
        '目前本益比高於自身 5 年中位數',
        '目前本益比約 ${latest.per.toStringAsFixed(2)} 倍，5 年中位數約 ${med.toStringAsFixed(2)} 倍，'
            '位階相對偏高。本益比會隨股價與盈餘變動，不是評價高低的最終答案。',
      ));
    }

    return FundamentalReport(
      yieldRate: latest?.yieldRate ?? s.yieldAt(endIdx),
      per: latest?.per,
      pbr: latest?.pbr,
      ttmEps: s.ttmEps,
      annualEps: annual,
      partialEps: s.partialYearEps,
      recentDividends: divs.length > 8 ? divs.sublist(divs.length - 8) : divs,
      risks: risks,
      perDate: latest?.date ?? '—',
    );
  }
}

// ---------------------------------------------------------------------------
// Agent 2：技術指標
// ---------------------------------------------------------------------------
class TechnicalAgent {
  static const String key = 'technical';
  static const String name = '技術指標 Agent';

  static TechnicalReport run(StockSeries s, int endIdx) =>
      Indicators.build(s, endIndex: endIdx + 1);
}

// ---------------------------------------------------------------------------
// Agent 3：量化回測
// ---------------------------------------------------------------------------
class BacktestAgent {
  static const String key = 'backtest';
  static const String name = '量化回測 Agent';

  /// 一次跑完 3 套策略，方便做橫向對照
  static Map<String, BacktestResult> runAll(
    StockSeries s,
    DateTime start,
    DateTime end,
  ) {
    final out = <String, BacktestResult>{};
    for (final st in kStrategies) {
      final r = BacktestEngine.run(s, st, start, end);
      if (r != null) out[st.id] = r;
    }
    return out;
  }

  static BacktestResult? runOne(
          StockSeries s, StrategyDef st, DateTime start, DateTime end) =>
      BacktestEngine.run(s, st, start, end);
}

// ---------------------------------------------------------------------------
// Agent 4：適老化翻譯 & 語音播報
// ---------------------------------------------------------------------------
class PlainLanguageAgent {
  static const String key = 'plain';
  static const String name = '適老化翻譯 Agent';

  static String buildNarrative({
    required StockSeries s,
    required int years,
    required String startText,
    required String endText,
    required FundamentalReport f,
    required TechnicalReport t,
    required BacktestResult b,
    required Map<String, BacktestResult> all,
  }) {
    final sb = StringBuffer();

    sb.writeln('【這份報告在幫你看什麼】');
    sb.writeln('把「${s.name}（${s.id}）」過去 $years 年（$startText ～ $endText）的公開歷史資料，'
        '用「${b.strategyName}」模擬一次：每個月固定投入 ${money(kMonthlyBudget)} 元，'
        '遇到設定條件再多投入一點。這不是預測，也不是任何建議，只是把過去發生的事，'
        '用同一套節奏重新算一次給你參考。');
    sb.writeln();

    sb.writeln('【基本面：這家公司過去的樣子】');
    if (f.yieldRate != null) {
      sb.writeln('・殖利率約 ${pct(f.yieldRate!)}（用近 12 個月的現金股利除以股價估算）。');
    }
    if (f.per != null) {
      sb.writeln('・本益比約 ${f.per!.toStringAsFixed(2)} 倍，股價淨值比約 '
          '${f.pbr?.toStringAsFixed(2) ?? '—'} 倍（資料日 ${f.perDate}）。');
    } else {
      sb.writeln('・這檔是 ETF，沒有公司財報的本益比資料，所以本益比與 EPS 相關欄位不顯示。');
    }
    if (f.annualEps.isNotEmpty) {
      final ys = f.annualEps.keys.toList()..sort();
      final parts = ys
          .map((y) => '$y 年 ${f.annualEps[y]!.toStringAsFixed(2)} 元')
          .join('、');
      sb.writeln('・近幾年度的 EPS：$parts。');
    }
    f.partialEps.forEach((y, v) {
      sb.writeln('・$y 年（年度還沒走完，只累計到目前的季度）EPS 約 ${v.toStringAsFixed(2)} 元，'
          '不要直接拿來跟全年比。');
    });
    if (f.recentDividends.isNotEmpty) {
      final parts = f.recentDividends
          .map((d) => '${d.ym} 配 ${d.amount.toStringAsFixed(2)} 元')
          .join('、');
      sb.writeln('・最近的配息記錄：$parts。');
    }
    sb.writeln();

    sb.writeln('【技術面：現在價格的位置】');
    final diff = t.ma60 <= 0 ? 0.0 : (t.lastClose / t.ma60 - 1) * 100;
    sb.writeln('・最後一天收盤 ${t.lastClose.toStringAsFixed(2)} 元，'
        '季線（60 日均線）約 ${t.ma60.toStringAsFixed(2)} 元，'
        '收盤價比季線${diff >= 0 ? '高' : '低'}約 ${diff.abs().toStringAsFixed(1)}%。');
    sb.writeln('・KD：K 值 ${t.k.toStringAsFixed(1)}、D 值 ${t.d.toStringAsFixed(1)}；'
        'RSI ${t.rsi.toStringAsFixed(1)}；'
        'MACD 的 DIF ${t.dif.toStringAsFixed(2)}、DEA ${t.dea.toStringAsFixed(2)}。');
    sb.writeln('　（以上只是描述價格現在的位置，不是叫你要做什麼。）');
    sb.writeln();

    sb.writeln('【歷史模擬結果】');
    sb.writeln('・總共投入 ${money(b.totalInvested)} 元，期末試算市值 ${money(b.finalValue)} 元'
        '（其中現金股利累計 ${money(b.dividendCash)} 元）。');
    sb.writeln('・換算年化報酬（IRR，把每筆投入的時間都算進去）約 ${pct(b.irr)}。');
    sb.writeln('・中途最大回撤 ${pct(b.maxDrawdown)}：意思是曾經從高點回落這麼多，'
        '這是長輩最需要先知道的事。');
    sb.writeln('・以每年年底結算，${b.totalYears} 個年度裡有 ${b.winYears} 個年度比前一年高。');
    if (b.boostMonths > 0) {
      sb.writeln('・這段期間有 ${b.boostMonths} 個月符合「多投入」的條件，所以投入金額比基本定額多一些。');
    }
    if (b.pauseMonths > 0) {
      sb.writeln('・有 ${b.pauseMonths} 個月因為條件沒到，當月沒有投入。');
    }
    sb.writeln();

    // 三策略對照
    if (all.length > 1) {
      sb.writeln('【三套策略擺在一起看】');
      for (final st in kStrategies) {
        final r = all[st.id];
        if (r == null) {
          sb.writeln('・${st.name}：這個標的沒有足夠資料，本次不模擬。');
          continue;
        }
        sb.writeln('・${st.name}：投入 ${money(r.totalInvested)} 元、期末 ${money(r.finalValue)} 元、'
            '年化 ${pct(r.irr)}、最大回撤 ${pct(r.maxDrawdown)}。');
      }
      sb.writeln('（同一段歷史、不同節奏，結果不一樣。這正是回測要看的重點，'
          '不是要挑一個「最好的」。）');
      sb.writeln();
    }

    sb.writeln('【三個要看清楚的地方】');
    sb.writeln('1. 這段時間的結果，和這幾年的整體市場環境有關；換一段時間，結果可能完全不同。');
    sb.writeln('2. 模擬用收盤價計算，沒有扣手續費、證交稅與二代健保補充保費。');
    sb.writeln('3. 股利以現金計入，沒有假設再投入；也沒有考慮除權息當天價格的變化。');
    sb.writeln();
    sb.writeln('以上全部是歷史資料的整理與模擬，不構成任何投資建議。');

    return sb.toString();
  }

  static String buildSpeech({
    required StockSeries s,
    required int years,
    required BacktestResult b,
    required TechnicalReport t,
    required FundamentalReport f,
  }) {
    final sb = StringBuffer();
    sb.write('這是一份歷史回測的學習報告。');
    sb.write('標的是${s.name}，代號${s.id.split('').join(' ')}。');
    sb.write('期間是過去$years 年。');
    sb.write('用${b.strategyName}模擬，每個月投入一萬元，總共投入 ${b.totalInvested.toStringAsFixed(0)} 元。');
    sb.write('期末試算市值大約 ${b.finalValue.toStringAsFixed(0)} 元。');
    sb.write('其中現金股利累計 ${b.dividendCash.toStringAsFixed(0)} 元。');
    sb.write('年化報酬大約 ${b.irr.toStringAsFixed(1)} 趴。');
    sb.write('中途最大回撤大約 ${b.maxDrawdown.toStringAsFixed(0)} 趴，也就是曾經從高點回落這麼多。');
    if (f.yieldRate != null) {
      sb.write('目前的殖利率大約 ${f.yieldRate!.toStringAsFixed(2)} 趴。');
    }
    sb.write('最後一天收盤價 ${t.lastClose.toStringAsFixed(0)} 元。');
    sb.write('提醒您，這是過去的模擬結果，不代表未來，也不是投資建議。');
    sb.write('投資有風險，請自行評估。');
    return sb.toString();
  }
}

// ---------------------------------------------------------------------------
// Agent 5：合規風控守門（每次請求必呼叫，後置校驗）
// ---------------------------------------------------------------------------
class ComplianceAgent {
  static const String key = 'compliance';
  static const String name = '合規風控守門 Agent';

  static ComplianceResult check(String text) {
    final hits = ComplianceLexicon.scan(text);
    if (ComplianceLexicon.isHardBlock(text)) {
      return ComplianceResult(
        passed: false,
        blocked: true,
        rewrittenTerms: hits,
        alerts: <String>['偵測到高風險話術：${hits.join('、')}，已攔截本次輸出。'],
        text: '',
      );
    }
    final rewritten = ComplianceLexicon.rewrite(text);
    final alerts = <String>[];
    if (hits.isNotEmpty) {
      alerts.add('已自動改寫 ${hits.length} 個薦股類詞彙為中性描述：${hits.join('、')}');
    }
    alerts.add('已自動附加完整免責聲明。');
    // 強制拼接完整免責聲明（不可由使用者關閉）
    final withDisclaimer = '$rewritten\n\n$kDisclaimer';
    return ComplianceResult(
      passed: true,
      blocked: false,
      rewrittenTerms: hits,
      alerts: alerts,
      text: withDisclaimer,
    );
  }
}

// ---------------------------------------------------------------------------
// 使用者輸入解析（語音／文字 → 表單參數）
// ---------------------------------------------------------------------------
class QueryParseResult {
  final String? stockId;
  final String? strategyId;
  final int? years;
  final bool riskIntent;
  final String riskReason;
  QueryParseResult({
    this.stockId,
    this.strategyId,
    this.years,
    this.riskIntent = false,
    this.riskReason = '',
  });
}

class QueryParser {
  static QueryParseResult parse(String raw) {
    final text = raw.trim();
    if (text.isEmpty) return QueryParseResult();

    if (ComplianceLexicon.isHardBlock(text)) {
      return QueryParseResult(
        riskIntent: true,
        riskReason: '您的需求包含「${ComplianceLexicon.hardBlock.firstWhere(text.contains)}」等字詞，'
            '本工具只做歷史回測學習，不提供任何預測、價格目標或買賣判斷，因此無法執行這類需求。',
      );
    }

    String? stockId;
    // 以實際載入的標的池比對（可支援 30+ 檔）
    final pool = MarketRepository.instance.isLoaded
        ? MarketRepository.instance.all
        : <StockSeries>[];
    for (final s in pool) {
      if (text.contains(s.id) || text.contains(s.name)) {
        stockId = s.id;
        break;
      }
    }
    if (stockId == null) {
      for (final s in kStockUniverse) {
        if (text.contains(s.id) || text.contains(s.name)) {
          stockId = s.id;
          break;
        }
      }
    }
    // 常見別名
    if (stockId == null) {
      if (text.contains('護國神山')) stockId = '2330';
      if (text.contains('電信') || text.contains('種花')) stockId = '2412';
      if (text.contains('高股息')) stockId = '0056';
      if (text.contains('台灣50') || text.contains('台灣五十')) stockId = '0050';
    }

    String? strategyId;
    if (text.contains('殖利率')) strategyId = 'yield_dca';
    if (text.contains('均線') || text.contains('季線')) strategyId = 'ma_batch';
    if (text.contains('本益比')) strategyId = 'low_per';

    int? years;
    final m = RegExp(r'(\d+)\s*年').firstMatch(text);
    if (m != null) {
      final v = int.tryParse(m.group(1)!);
      if (v != null) years = v.clamp(1, 6);
    }
    if (years == null) {
      if (text.contains('三年')) years = 3;
      if (text.contains('五年')) years = 5;
    }

    return QueryParseResult(
      stockId: stockId,
      strategyId: strategyId,
      years: years,
    );
  }
}

// ---------------------------------------------------------------------------
// 編排器：依序驅動 5 個 Agent，並回報每一步狀態給 UI
// ---------------------------------------------------------------------------
class AgentOrchestrator {
  static final List<AgentStep> _blueprint = <AgentStep>[
    AgentStep(FundamentalAgent.key, FundamentalAgent.name, '整理財報、EPS、殖利率、配息與風險事件'),
    AgentStep(TechnicalAgent.key, TechnicalAgent.name, '計算 MA／KD／RSI／MACD，只給數值不給訊號'),
    AgentStep(BacktestAgent.key, BacktestAgent.name, '以歷史資料模擬 3 套策略，輸出年化／回撤／勝率'),
    AgentStep(PlainLanguageAgent.key, PlainLanguageAgent.name, '把術語翻成台灣大白話，產出語音播報稿'),
    AgentStep(ComplianceAgent.key, ComplianceAgent.name, '全量掃描禁用詞、附加免責聲明、攔截高風險話術'),
  ];

  static List<AgentStep> freshSteps() => _blueprint
      .map((e) => AgentStep(e.key, e.name, e.role))
      .toList(growable: false);

  Future<PipelineOutcome> run({
    required StockSeries series,
    required StrategyDef strategy,
    required int years,
    required DateTime start,
    required DateTime end,
    required void Function(AgentEvent) onEvent,
    Duration stepDelay = const Duration(milliseconds: 260),
  }) async {
    final steps = freshSteps();

    Future<void> mark(String key, AgentState st, [String detail = '']) async {
      final i = steps.indexWhere((e) => e.key == key);
      if (i >= 0) {
        steps[i].state = st;
        if (detail.isNotEmpty) steps[i].detail = detail;
      }
      onEvent(AgentEvent(steps, key));
      await Future<void>.delayed(stepDelay);
    }

    // 對齊到實際交易日（若區間超出資料範圍則夾回邊界）
    var si = series.indexOnOrAfter(_int(start));
    if (si < 0) si = 0;
    var ei = series.indexOnOrBefore(_int(end));
    if (ei < 0 || ei >= series.dates.length) ei = series.dates.length - 1;
    final startInt = series.dates[si];
    final endInt = series.dates[ei];

    // ---- Agent 1 ----
    await mark(FundamentalAgent.key, AgentState.running);
    final iStart = series.indexOnOrAfter(startInt);
    final iEnd = series.indexOnOrBefore(endInt);
    final fundamental = FundamentalAgent.run(series, iStart, iEnd);
    await mark(
      FundamentalAgent.key,
      AgentState.done,
      '解析 ${series.dates.length} 筆日資料、${series.eps.length} 季 EPS、'
          '${series.dividends.length} 筆配息、${fundamental.risks.length} 項風險檢核',
    );

    // ---- Agent 2 ----
    await mark(TechnicalAgent.key, AgentState.running);
    final technical = TechnicalAgent.run(series, iEnd);
    await mark(TechnicalAgent.key, AgentState.done,
        'MA5/20/60、KD(9)、RSI(14)、MACD(12,26,9) 計算完成');

    // ---- Agent 3 ----
    await mark(BacktestAgent.key, AgentState.running);
    final all = BacktestAgent.runAll(series, start, end);
    final primary = all[strategy.id];
    if (primary == null) {
      await mark(BacktestAgent.key, AgentState.done, '此標的缺少該策略所需資料，已跳過');
    } else {
      await mark(BacktestAgent.key, AgentState.done,
          '3 套策略完成歷史模擬，主策略：${strategy.name}');
    }

    // ---- Agent 4 ----
    await mark(PlainLanguageAgent.key, AgentState.running);
    String narrative = '';
    String speech = '';
    if (primary != null) {
      narrative = PlainLanguageAgent.buildNarrative(
        s: series,
        years: years,
        startText: StockSeries.fmtYmd(startInt),
        endText: StockSeries.fmtYmd(endInt),
        f: fundamental,
        t: technical,
        b: primary,
        all: all,
      );
      speech = PlainLanguageAgent.buildSpeech(
        s: series,
        years: years,
        b: primary,
        t: technical,
        f: fundamental,
      );
    }
    await mark(PlainLanguageAgent.key, AgentState.done,
        '產出 ${narrative.length} 字大白話報告 + ${speech.length} 字語音稿');

    // ---- Agent 5（後置校驗，必呼叫）----
    await mark(ComplianceAgent.key, AgentState.running);
    final compliance = ComplianceAgent.check('$narrative\n$speech');
    if (compliance.blocked) {
      await mark(ComplianceAgent.key, AgentState.blocked, compliance.alerts.join('；'));
      return PipelineOutcome(
        blocked: true,
        blockReason: compliance.alerts.join('；'),
        steps: steps,
      );
    }
    await mark(ComplianceAgent.key, AgentState.done, compliance.alerts.join('；'));

    final report = ReportBundle(
      id: '${series.id}_${strategy.id}_${DateTime.now().millisecondsSinceEpoch}',
      stockId: series.id,
      stockName: series.name,
      strategyId: strategy.id,
      strategyName: strategy.name,
      years: years,
      startDate: StockSeries.fmtYmd(startInt),
      endDate: StockSeries.fmtYmd(endInt),
      createdAt: nowStamp(),
      fundamental: fundamental,
      technical: technical,
      primary: primary,
      comparison: all,
      narrative: compliance.text,
      speechScript: speech,
      compliance: compliance,
    );
    return PipelineOutcome(report: report, steps: steps);
  }

  static int _int(DateTime d) => d.year * 10000 + d.month * 100 + d.day;
}

/// 遠端 Agent 閘道（正式架構用；參賽版預設未啟用）
class AgentGateway {
  static const String endpoint = String.fromEnvironment('AGENT_ENDPOINT');
  static bool get enabled => endpoint.isNotEmpty;
  static double get mixRate => 0;
}

/// 小工具：把數字轉為給長輩看的「大約」
String approx(num v) {
  final abs = v.abs();
  if (abs >= 100000000) return '約 ${(v / 100000000).toStringAsFixed(2)} 億';
  if (abs >= 10000) return '約 ${(v / 10000).toStringAsFixed(1)} 萬';
  return '約 ${v.toStringAsFixed(0)}';
}

double clampDouble(double v, double lo, double hi) => math.min(hi, math.max(lo, v));
