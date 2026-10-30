// 分析回測結果頁：基本面 / 技術指標 / 回測曲線 / 大白話報告 / 語音播報
import 'package:flutter/material.dart';

import '../agents/agents.dart';
import '../core/constants.dart';
import '../core/formatters.dart';
import '../data/market_repository.dart';
import '../models/models.dart';
import '../services/report_store.dart';
import '../services/speech_service.dart';
import 'theme.dart';
import 'widgets.dart';

class ResultPage extends StatefulWidget {
  final String stockId;
  final String strategyId;
  final int years;
  const ResultPage({
    Key? key,
    required this.stockId,
    required this.strategyId,
    required this.years,
  }) : super(key: key);

  @override
  State<ResultPage> createState() => _ResultPageState();
}

class _ResultPageState extends State<ResultPage> {
  final SpeechService _speech = SpeechService();
  final AgentOrchestrator _orch = AgentOrchestrator();

  List<AgentStep> _steps = AgentOrchestrator.freshSteps();
  bool _running = true;
  ReportBundle? _report;
  bool _blocked = false;
  String _blockReason = '';
  bool _saved = false;
  late String _selectedStrategyId = widget.strategyId;

  @override
  void initState() {
    super.initState();
    _speech.addListener(() {
      if (mounted) setState(() {});
    });
    _run();
  }

  @override
  void dispose() {
    _speech.stop();
    _speech.dispose();
    super.dispose();
  }

  Future<void> _run() async {
    await MarketRepository.instance.ensureLoaded();
    final series = MarketRepository.instance.series(widget.stockId);
    if (series == null) {
      setState(() {
        _running = false;
        _blocked = true;
        _blockReason = '找不到這檔標的的歷史資料。';
      });
      return;
    }
    final end = _parse(series.dates.last);
    var start = DateTime(end.year - widget.years, end.month, end.day);
    final dataStart = _parse(series.dates.first);
    if (start.isBefore(dataStart)) start = dataStart;

    final out = await _orch.run(
      series: series,
      strategy: strategyById(widget.strategyId),
      years: widget.years,
      start: start,
      end: end,
      onEvent: (e) {
        if (mounted) setState(() => _steps = e.steps);
      },
    );
    if (!mounted) return;
    setState(() {
      _running = false;
      _blocked = out.blocked;
      _blockReason = out.blockReason;
      _report = out.report;
    });
  }

  static DateTime _parse(int ymd) =>
      DateTime(ymd ~/ 10000, (ymd ~/ 100) % 100, ymd % 100);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            const DisclaimerBanner(),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(14, 12, 14, 40),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 900),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _topBar(),
                        if (_running) _runningCard(),
                        if (!_running && _blocked) _blockedCard(),
                        if (!_running && !_blocked && _report != null) ..._resultSections(),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _topBar() {
    final r = _report;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          IconButton(
            tooltip: '回到首頁',
            iconSize: 30,
            onPressed: () => Navigator.of(context).maybePop(),
            icon: const Icon(Icons.arrow_back_rounded),
          ),
          const SizedBox(width: 2),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  r == null ? '正在產生學習報告…' : '${r.stockName}（${r.stockId}）學習報告',
                  maxLines: 2,
                  style: TextStyle(
                      fontSize: 20, fontWeight: FontWeight.w900, color: cInk),
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  r == null
                      ? '5 個 Agent 依序處理中'
                      : '${r.strategyName}・${r.startDate} ～ ${r.endDate}',
                  style: TextStyle(fontSize: 13.5, color: cInkSoft),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _runningCard() {
    return SectionCard(
      title: 'WorkBuddy Agent 協作中',
      icon: Icons.hub_rounded,
      subtitle: '依序：基本面 → 技術指標 → 量化回測 → 白話翻譯',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AgentStepper(steps: _steps),
          const SizedBox(height: 14),
          const LinearProgressIndicator(minHeight: 6),
        ],
      ),
    );
  }

  Widget _blockedCard() {
    return SectionCard(
      title: '這個組合沒有通過檢查',
      icon: Icons.gpp_bad_rounded,
      accent: AppColors.danger,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(_blockReason,
              style: TextStyle(fontSize: 16, height: 1.6, color: cInk)),
          const SizedBox(height: 12),
          const InlineDisclaimer(),
          const SizedBox(height: 14),
          ActionButton(
            label: '回上一頁',
            icon: Icons.arrow_back_rounded,
            onPressed: () => Navigator.of(context).maybePop(),
          ),
        ],
      ),
    );
  }

  List<Widget> _resultSections() {
    final r = _report!;
    return [
      _summaryCard(r),
      _fundamentalCard(r),
      _riskCard(r),
      _technicalCard(r),
      _backtestCard(r),
      _narrativeCard(r),
      _voiceCard(r),
      _saveCard(r),
      const SizedBox(height: 4),
      const InlineDisclaimer(),
      const SizedBox(height: 14),
      Text(kDataSourceNote,
          style: TextStyle(fontSize: 12.5, height: 1.6, color: cInkSoft)),
    ];
  }

  Widget _metricsRow(List<Widget> children) {
    return LayoutBuilder(builder: (context, c) {
      final perRow = c.maxWidth > 620 ? 3 : (c.maxWidth > 300 ? 2 : 1);
      final w = (c.maxWidth - (perRow - 1) * 10) / perRow;
      return Wrap(
        spacing: 10,
        runSpacing: 10,
        children: [for (final ch in children) SizedBox(width: w, child: ch)],
      );
    });
  }

  Widget _summaryCard(ReportBundle r) {
    final b = r.primary!;
    final isUp = b.irr >= 0;
    return SectionCard(
      title: '一眼看重點',
      icon: Icons.insights_rounded,
      subtitle: '全部是過去資料的模擬結果，不是預測，也不是建議。',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _metricsRow([
            MetricTile(
              label: '歷史年化（IRR）',
              value: pct(b.irr),
              note: '把每筆投入的時間都算進去',
              color: isUp ? AppColors.up : AppColors.down,
              big: true,
            ),
            MetricTile(
              label: '最大回撤',
              value: pct(b.maxDrawdown),
              note: '中途從高點回落的最大幅度',
              color: AppColors.primary,
              big: true,
            ),
            MetricTile(
              label: '年度勝率',
              value: '${(b.winRate * 100).toStringAsFixed(0)}%',
              note: '${b.totalYears} 個年度中 ${b.winYears} 年比前一年高',
              color: AppColors.gold,
              big: true,
            ),
          ]),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: isHighContrast ? Colors.black : const Color(0xFFF6F1E7),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: cLine),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('模擬方式：每月投入 ${money(kMonthlyBudget)} 元・共 ${b.months} 個月',
                    style: TextStyle(
                        fontSize: 15, fontWeight: FontWeight.w700, color: cInk)),
                const SizedBox(height: 4),
                Text(
                  '總投入 ${money(b.totalInvested)} 元　期末試算 ${money(b.finalValue)} 元'
                  '　現金股利 ${money(b.dividendCash)} 元',
                  style: TextStyle(fontSize: 14, height: 1.6, color: cInkSoft),
                ),
                if (b.avgCost > 0)
                  Text('平均每股投入成本 ${b.avgCost.toStringAsFixed(2)} 元'
                      '　期末收盤 ${b.endPrice.toStringAsFixed(2)} 元',
                      style: TextStyle(fontSize: 14, height: 1.6, color: cInkSoft)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _fundamentalCard(ReportBundle r) {
    final f = r.fundamental;
    if (f == null) return const SizedBox.shrink();
    final years = f.annualEps.keys.toList()..sort();
    return SectionCard(
      title: '基本面摘要',
      icon: Icons.receipt_long_rounded,
      subtitle: '資料來源：FinMind 公開財報與股利資料，僅做客觀整理。',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _metricsRow([
            MetricTile(
              label: '殖利率（近 12 個月）',
              value: f.yieldRate == null ? '—' : pct(f.yieldRate!),
              note: '現金股利 ÷ 股價',
              color: AppColors.gold,
            ),
            MetricTile(
              label: '本益比',
              value: f.per == null ? '—' : f.per!.toStringAsFixed(2),
              note: f.per == null ? 'ETF 無此資料' : '資料日 ${f.perDate}',
              color: AppColors.primary,
            ),
            MetricTile(
              label: '股價淨值比',
              value: f.pbr == null ? '—' : f.pbr!.toStringAsFixed(2),
              note: f.pbr == null ? 'ETF 無此資料' : '每股淨值的倍數',
              color: AppColors.primary,
            ),
          ]),
          const SizedBox(height: 14),
          if (years.isNotEmpty) ...[
            Text('年度 EPS（每股盈餘，元）',
                style: TextStyle(
                    fontSize: 15, fontWeight: FontWeight.w800, color: cInk)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final y in years)
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                    decoration: BoxDecoration(
                      color: isHighContrast ? Colors.black : Colors.white,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: cLine),
                    ),
                    child: Text(
                      '$y 年　${f.annualEps[y]!.toStringAsFixed(2)}',
                      style: TextStyle(
                          fontSize: 14.5,
                          fontWeight: FontWeight.w700,
                          color: f.annualEps[y]! < 0 ? AppColors.danger : cInk),
                    ),
                  ),
              ],
            ),
            if (f.partialEps.isNotEmpty) ...[
              const SizedBox(height: 8),
              for (final e in f.partialEps.entries)
                Text(
                  '※ ${e.key} 年為「年度累計」（年度還沒結束，只累計到目前公布的季度）：'
                  '${e.value.toStringAsFixed(2)} 元，不能直接與全年比較。',
                  style: TextStyle(fontSize: 13, color: cInkSoft, height: 1.5),
                ),
            ],
            const SizedBox(height: 14),
          ],
          if (f.recentDividends.isNotEmpty) ...[
            Text('最近的現金配息記錄（每股，元）',
                style: TextStyle(
                    fontSize: 15, fontWeight: FontWeight.w800, color: cInk)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final d in f.recentDividends)
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                    decoration: BoxDecoration(
                      color: isHighContrast ? Colors.black : Colors.white,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: cLine),
                    ),
                    child: Text('${d.ym}　${d.amount.toStringAsFixed(2)}',
                        style: TextStyle(
                            fontSize: 14.5,
                            fontWeight: FontWeight.w700,
                            color: cInk)),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _riskCard(ReportBundle r) {
    final risks = r.fundamental?.risks ?? <RiskItem>[];
    if (risks.isEmpty) {
      return const SectionCard(
        title: '風險檢核結果',
        icon: Icons.verified_rounded,
        accent: AppColors.safe,
        child: NoticeBar(
          icon: Icons.check_circle_outline_rounded,
          color: AppColors.safe,
          text: '這次的資料規則檢查，沒有發現虧損、配息明顯減少或大幅回落等情況。',
        ),
      );
    }
    return SectionCard(
      title: '風險檢核結果（請先看這裡）',
      icon: Icons.warning_amber_rounded,
      accent: AppColors.danger,
      subtitle: '以下為系統依公開資料做的規則檢核，不是主觀評價。',
      child: Column(
        children: [
          for (final risk in risks)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isHighContrast
                    ? Colors.black
                    : (risk.level == 'high'
                        ? AppColors.dangerBg
                        : const Color(0xFFFFF6E0)),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: risk.level == 'high'
                      ? AppColors.danger.withOpacity(0.6)
                      : const Color(0xFFD8A93A),
                  width: 1.4,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        risk.level == 'high'
                            ? Icons.error_rounded
                            : Icons.info_rounded,
                        color: risk.level == 'high'
                            ? AppColors.danger
                            : const Color(0xFF9A6B00),
                        size: 22,
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(risk.title,
                            style: TextStyle(
                                fontSize: 16.5,
                                fontWeight: FontWeight.w800,
                                color: cInk)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(risk.detail,
                      style:
                          TextStyle(fontSize: 14.5, height: 1.65, color: cInk)),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _technicalCard(ReportBundle r) {
    final t = r.technical;
    if (t == null) return const SizedBox.shrink();
    final diff = t.ma60 <= 0 ? 0.0 : (t.lastClose / t.ma60 - 1) * 100;
    return SectionCard(
      title: '技術指標（只看位置，不給訊號）',
      icon: Icons.show_chart_rounded,
      subtitle: '這裡只列出 4 組長輩最常用的指標數值，不輸出任何買賣訊號。',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _metricsRow([
            MetricTile(
              label: '收盤價 vs 季線',
              value: '${diff >= 0 ? '+' : ''}${diff.toStringAsFixed(1)}%',
              note: '季線 ${t.ma60.toStringAsFixed(1)} 元',
              color: diff >= 0 ? AppColors.up : AppColors.down,
            ),
            MetricTile(
              label: 'KD（9 日）',
              value: 'K ${t.k.toStringAsFixed(0)}／D ${t.d.toStringAsFixed(0)}',
              note: '0～100，越高越接近區間高檔',
              color: AppColors.primary,
            ),
            MetricTile(
              label: 'RSI（14 日）',
              value: t.rsi.toStringAsFixed(1),
              note: '0～100，看漲跌力量比較',
              color: AppColors.primary,
            ),
          ]),
          const SizedBox(height: 10),
          _metricsRow([
            MetricTile(
              label: 'MACD 的 DIF',
              value: t.dif.toStringAsFixed(2),
              note: '兩條平均線的差距',
              color: AppColors.gold,
            ),
            MetricTile(
              label: 'MACD 的 DEA',
              value: t.dea.toStringAsFixed(2),
              note: 'DIF 的平均線',
              color: AppColors.gold,
            ),
            MetricTile(
              label: '均線 5／20／60',
              value: '${t.ma5.toStringAsFixed(0)}／${t.ma20.toStringAsFixed(0)}／'
                  '${t.ma60.toStringAsFixed(0)}',
              note: '單位：元',
              color: AppColors.primary,
            ),
          ]),
        ],
      ),
    );
  }

  Widget _backtestCard(ReportBundle r) {
    final results = r.comparison;
    final selected = results[_selectedStrategyId] ?? r.primary!;
    // 三套策略的淨值曲線在這段歷史上幾乎重疊，因此圖上只畫「目前選取」的那一套，
    // 差異交給下方的橫向對照表呈現，避免長輩誤以為只有一條線。

    return SectionCard(
      title: '歷史回測結果',
      icon: Icons.query_stats_rounded,
      subtitle: '同一段歷史、三套節奏的模擬對照。圖表上的水印固定顯示，不可關閉。',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              for (final s in kStrategies)
                ChoicePill(
                  label: results.containsKey(s.id) ? s.name : '${s.name}（無資料）',
                  selected: _selectedStrategyId == s.id,
                  onTap: results.containsKey(s.id)
                      ? () => setState(() => _selectedStrategyId = s.id)
                      : null,
                ),
            ],
          ),
          const SizedBox(height: 14),
          EquityChart(primary: selected.nav, height: 270),
          const SizedBox(height: 6),
          Row(
            children: [
              Container(width: 16, height: 4, color: const Color(0xFFC62828)),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  '曲線：${selected.strategyName} 的累積報酬率（起始為 0%）',
                  style: TextStyle(fontSize: 13, color: cInkSoft),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          _metricsRow([
            MetricTile(
              label: '歷史年化（IRR）',
              value: pct(selected.irr),
              color: selected.irr >= 0 ? AppColors.up : AppColors.down,
            ),
            MetricTile(
              label: '最大回撤',
              value: pct(selected.maxDrawdown),
              color: AppColors.primary,
            ),
            MetricTile(
              label: '年度勝率',
              value: '${(selected.winRate * 100).toStringAsFixed(0)}%',
              color: AppColors.gold,
            ),
          ]),
          const SizedBox(height: 16),
          Text('三套策略橫向對照（都用同一段歷史資料）',
              style: TextStyle(
                  fontSize: 15, fontWeight: FontWeight.w800, color: cInk)),
          const SizedBox(height: 8),
          Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: cLine),
            ),
            child: Column(
              children: [
                _tableRow(<String>['策略', '年化', '回撤', '勝率'],
                    header: true),
                for (final s in kStrategies)
                  if (results[s.id] != null)
                    _tableRow(<String>[
                      s.name,
                      pct(results[s.id]!.irr),
                      pct(results[s.id]!.maxDrawdown),
                      '${(results[s.id]!.winRate * 100).toStringAsFixed(0)}%',
                    ], highlight: s.id == _selectedStrategyId)
                  else
                    _tableRow(<String>[s.name, '—', '—', '—']),
              ],
            ),
          ),
          const SizedBox(height: 10),
          Text(
            '說明：三套策略都是「分批投入並持有」的歷史模擬，不含放空、融資或短線交易。'
            '同一段歷史用不同節奏，結果會不一樣，這正是回測要看的重點。',
            style: TextStyle(fontSize: 13.5, height: 1.6, color: cInkSoft),
          ),
        ],
      ),
    );
  }

  Widget _tableRow(List<String> cells, {bool header = false, bool highlight = false}) {
    return Container(
      color: header
          ? (isHighContrast ? const Color(0xFF1E1E1E) : const Color(0xFFF1EADB))
          : (highlight
              ? (isHighContrast
                  ? const Color(0xFF2A2410)
                  : cPrimary.withOpacity(0.06))
              : Colors.transparent),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      child: Row(
        children: [
          Expanded(
            flex: 4,
            child: Text(cells[0],
                style: TextStyle(
                    fontSize: header ? 14.5 : 14,
                    fontWeight: header ? FontWeight.w800 : FontWeight.w700,
                    color: cInk)),
          ),
          for (var i = 1; i < cells.length; i++)
            Expanded(
              flex: 2,
              child: Text(cells[i],
                  textAlign: TextAlign.right,
                  style: TextStyle(
                      fontSize: 14,
                      fontWeight: header ? FontWeight.w800 : FontWeight.w600,
                      color: header ? cInkSoft : cInk)),
            ),
        ],
      ),
    );
  }

  Widget _narrativeCard(ReportBundle r) {
    return SectionCard(
      title: '大白話報告（適老化翻譯 Agent 產出）',
      icon: Icons.record_voice_over_rounded,
      subtitle: '把上面那些數字，翻成平常講話的方式。',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SelectableText(
            r.narrative,
            style: TextStyle(fontSize: 16, height: 1.85, color: cInk),
          ),
          const SizedBox(height: 12),
          if (r.compliance != null)
            NoticeBar(
              icon: Icons.verified_user_outlined,
              color: AppColors.safe,
              text: r.compliance!.alerts.join('\n'),
            ),
        ],
      ),
    );
  }

  Widget _voiceCard(ReportBundle r) {
    return SectionCard(
      title: '用聽的（國語／台語）',
      icon: Icons.volume_up_rounded,
      subtitle: '適合一邊做家事一邊聽。台語語音需裝置本身有安裝，沒安裝會自動改用國語。',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: ActionButton(
                  label: '國語播放',
                  icon: Icons.headphones_rounded,
                  onPressed: () => _speech.speak(r.speechScript),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ActionButton(
                  label: '台語播放',
                  icon: Icons.record_voice_over_rounded,
                  primary: false,
                  onPressed: () =>
                      _speech.speak(r.speechScript, kind: 'taiwanese'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ActionButton(
            label: _speech.speaking ? '停止朗讀' : '停止',
            icon: Icons.stop_circle_outlined,
            primary: false,
            color: AppColors.danger,
            onPressed: _speech.stop,
          ),
          if (_speech.note != null) ...[
            const SizedBox(height: 10),
            NoticeBar(
              icon: Icons.info_outline_rounded,
              color: AppColors.gold,
              text: _speech.note!,
            ),
          ],
          const SizedBox(height: 10),
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            title: Text('看朗讀稿（共 ${r.speechScript.length} 字）',
                style: TextStyle(
                    fontSize: 15, fontWeight: FontWeight.w700, color: cInk)),
            children: [
              Align(
                alignment: Alignment.centerLeft,
                child: SelectableText(r.speechScript,
                    style: TextStyle(
                        fontSize: 14.5, height: 1.7, color: cInkSoft)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _saveCard(ReportBundle r) {
    return SectionCard(
      title: '存到這台裝置',
      icon: Icons.save_alt_rounded,
      subtitle: '只存在這個瀏覽器的 localStorage，不會上傳到任何伺服器。',
      child: ActionButton(
        label: _saved ? '已存到本機（可再存一次）' : '存到本機',
        icon: _saved ? Icons.check_circle_rounded : Icons.download_rounded,
        onPressed: () {
          ReportStore.save(SavedReport.fromBundle(r));
          setState(() => _saved = true);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('已存到本機。回首頁的「我的學習紀錄」就看得到。')),
          );
        },
      ),
    );
  }
}
