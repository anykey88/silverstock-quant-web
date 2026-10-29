// 交易回測結果頁（個人自用版）
import 'package:flutter/material.dart';

import '../core/constants.dart';
import '../core/formatters.dart';
import '../data/market_repository.dart';
import '../engine/trade_engine.dart';
import '../models/trade_strategy.dart';
import '../services/strategy_store.dart';
import '../ui/strategy_editor_page.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';

class TradeResultPage extends StatefulWidget {
  final String stockId;
  final TradeStrategy strategy;
  final int years;
  const TradeResultPage({
    Key? key,
    required this.stockId,
    required this.strategy,
    this.years = 5,
  }) : super(key: key);

  @override
  State<TradeResultPage> createState() => _TradeResultPageState();
}

class _TradeResultPageState extends State<TradeResultPage> {
  TradeResult? _result;
  bool _ready = false;
  late TradeStrategy _strategy = widget.strategy;

  @override
  void initState() {
    super.initState();
    _run();
  }

  Future<void> _run() async {
    setState(() => _ready = false);
    await MarketRepository.instance.ensureLoaded();
    final s = MarketRepository.instance.series(widget.stockId);
    if (s == null) {
      setState(() => _ready = true);
      return;
    }
    final end = DateTime(s.dates.last ~/ 10000, (s.dates.last ~/ 100) % 100, s.dates.last % 100);
    var start = DateTime(end.year - widget.years, end.month, end.day);
    final ds = DateTime(s.dates.first ~/ 10000, (s.dates.first ~/ 100) % 100, s.dates.first % 100);
    if (start.isBefore(ds)) start = ds;
    final r = TradeEngine.run(s, _strategy, start, end,
        isEtf: s.industry == 'ETF');
    if (!mounted) return;
    setState(() {
      _result = r;
      _ready = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final r = _result;
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            const PersonalRiskBar(),
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
                        if (!_ready)
                          const Padding(
                            padding: EdgeInsets.only(top: 60),
                            child: Center(child: CircularProgressIndicator()),
                          ),
                        if (_ready && r == null) _emptyCard(),
                        if (r != null) ..._sections(r),
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
    final s = MarketRepository.instance.series(widget.stockId);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          IconButton(
            iconSize: 30,
            onPressed: () => Navigator.of(context).maybePop(),
            icon: const Icon(Icons.arrow_back_rounded),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  s == null ? '交易回測' : '${s.name}（${s.id}）交易回測',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                      fontSize: 20, fontWeight: FontWeight.w900, color: cInk),
                ),
                Text('策略：${_strategy.name}・近 ${widget.years} 年',
                    style: TextStyle(fontSize: 13.5, color: cInkSoft)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _emptyCard() => SectionCard(
        title: '無法回測',
        icon: Icons.error_outline_rounded,
        accent: AppColors.danger,
        child: Text('這檔標的的資料不足，或區間太短（至少要 60 個交易日）。',
            style: TextStyle(fontSize: 15, color: cInk)),
      );

  List<Widget> _sections(TradeResult r) {
    final positive = r.totalReturnPct >= 0;
    return [
      if (r.tradeCount == 0 && !r.holding) _noTradeCard(r),
      SectionCard(
        title: '回測結果總覽',
        icon: Icons.account_balance_wallet_rounded,
        subtitle: '本金 ${money(r.totalCapital)} 元・期末 ${money(r.finalEquity)} 元'
            '（含現金 ${money(r.cash)}）',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            LayoutBuilder(builder: (ctx, c) {
              final perRow = c.maxWidth > 620 ? 4 : 2;
              final w = (c.maxWidth - (perRow - 1) * 10) / perRow;
              return Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '總報酬率',
                      value: signedPct(r.totalReturnPct),
                      note: '損益 ${money(r.netProfit)} 元',
                      color: positive ? AppColors.up : AppColors.down,
                      big: true,
                    ),
                  ),
                  SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '年化（CAGR）',
                      value: pct(r.cagr),
                      note: '以本金計算',
                      color: positive ? AppColors.up : AppColors.down,
                    ),
                  ),
                  SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '最大回撤',
                      value: pct(r.maxDrawdown),
                      note: '權益曲線最大回落',
                      color: AppColors.primary,
                    ),
                  ),
                  SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '勝率',
                      value: '${(r.winRate * 100).toStringAsFixed(0)}%',
                      note: '${r.winCount} 勝 / ${r.lossCount} 敗',
                      color: AppColors.gold,
                    ),
                  ),
                ],
              );
            }),
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
                  Text('交易 ${r.tradeCount} 次・平均持有 ${r.avgHoldDays.toStringAsFixed(0)} 天'
                      '・平均報酬 ${signedPct(r.avgPnlPct)}',
                      style: TextStyle(
                          fontSize: 14.5,
                          fontWeight: FontWeight.w700,
                          color: cInk)),
                  const SizedBox(height: 4),
                  Text('最佳 ${signedPct(r.bestTrade)}・最差 ${signedPct(r.worstTrade)}'
                      '・獲利因子 ${r.profitFactor >= 99 ? '∞' : r.profitFactor.toStringAsFixed(2)}',
                      style: TextStyle(fontSize: 13.5, color: cInkSoft)),
                  const SizedBox(height: 4),
                  Text('成本：手續費 ${money(r.feeTotal)} 元、證交稅 ${money(r.taxTotal)} 元、'
                      '現金股利 ${money(r.dividendTotal)} 元',
                      style: TextStyle(fontSize: 13, color: cInkSoft)),
                  if (r.tradeCount > 0 && r.tradeCount < 5) ...[
                    const SizedBox(height: 6),
                    Text('※ 樣本只有 ${r.tradeCount} 筆交易，勝率與平均報酬的參考性有限。',
                        style: const TextStyle(
                            fontSize: 12.5,
                            height: 1.5,
                            color: AppColors.gold,
                            fontWeight: FontWeight.w700)),
                  ],
                  if (r.holding) ...[
                    const SizedBox(height: 6),
                    Text(
                      '期末仍持有 ${r.shares.toStringAsFixed(0)} 股，平均成本 '
                      '${r.avgCost.toStringAsFixed(2)} 元（未平倉，已按期末收盤計入市值）',
                      style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: AppColors.gold),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
      SectionCard(
        title: '權益曲線',
        icon: Icons.show_chart_rounded,
        subtitle: '以本金為基準的累積報酬率；水印固定顯示。',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            EquityChart(primary: r.equity, height: 260),
            const SizedBox(height: 8),
            Text('策略條件：${_strategy.conditionLines.join('、')}',
                style: TextStyle(fontSize: 13, height: 1.6, color: cInkSoft)),
            Text('出場規則：${_strategy.exitLines.join('；')}',
                style: TextStyle(fontSize: 13, height: 1.6, color: cInkSoft)),
            const SizedBox(height: 6),
            Row(
              children: [
                TextButton.icon(
                  onPressed: _editStrategy,
                  icon: const Icon(Icons.tune_rounded),
                  label: const Text('調整參數'),
                ),
                TextButton.icon(
                  onPressed: _switchStrategy,
                  icon: const Icon(Icons.swap_horiz_rounded),
                  label: const Text('換策略'),
                ),
              ],
            ),
          ],
        ),
      ),
      _tradesCard(r),
      SectionCard(
        title: '執行紀錄（最近動作）',
        icon: Icons.receipt_long_rounded,
        subtitle: '每一筆進出都記下來，方便核對回測邏輯。',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (r.logs.isEmpty)
              Text('這段期間沒有觸發任何交易條件。',
                  style: TextStyle(fontSize: 14, color: cInkSoft))
            else
              for (final l in r.logs.take(12))
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text('・$l',
                      style: TextStyle(fontSize: 13.5, height: 1.5, color: cInkSoft)),
                ),
          ],
        ),
      ),
      const SizedBox(height: 4),
      const InlineDisclaimer(),
      const SizedBox(height: 12),
      Text(kDataSourceNote,
          style: TextStyle(fontSize: 12.5, height: 1.6, color: cInkSoft)),
    ];
  }

  Widget _noTradeCard(TradeResult r) {
    return SectionCard(
      title: '這段期間沒有觸發交易',
      icon: Icons.info_outline_rounded,
      accent: AppColors.gold,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '條件太嚴，${_strategy.name} 在 ${r.stockName} 近 ${widget.years} 年一次都沒進場。'
            '常見原因：殖利率門檻高於這檔的實際配息水準，或本益比條件一直沒達到。',
            style: TextStyle(fontSize: 14.5, height: 1.6, color: cInk),
          ),
          const SizedBox(height: 8),
          const NoticeBar(
            icon: Icons.lightbulb_outline_rounded,
            text: '建議：把殖利率門檻降到 2%（或改成不看殖利率），'
                '或改用「季線分批型」這種不看股利的策略。',
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: ActionButton(
                  label: '放寬條件重跑',
                  icon: Icons.auto_fix_high_rounded,
                  onPressed: () async {
                    final loosened = _strategy.copyWith(
                      entryYieldMin: _strategy.entryYieldMin != null
                          ? (_strategy.entryYieldMin! - 0.5).clamp(0, 9)
                          : null,
                      entryPerRatio: _strategy.entryPerRatio != null
                          ? (_strategy.entryPerRatio! + 0.1).clamp(0.5, 1.5)
                          : null,
                      maMode: 'any',
                    );
                    setState(() => _strategy = loosened);
                    await _run();
                  },
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ActionButton(
                  label: '換一個策略',
                  icon: Icons.swap_horiz_rounded,
                  primary: false,
                  onPressed: _switchStrategy,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _editStrategy() async {
    final r = await Navigator.of(context).push<TradeStrategy>(
      MaterialPageRoute(builder: (_) => StrategyEditorPage(origin: _strategy)),
    );
    if (r == null || !mounted) return;
    setState(() => _strategy = r);
    await _run();
  }

  Future<void> _switchStrategy() async {
    final list = StrategyStore.all();
    final picked = await showModalBottomSheet<TradeStrategy>(
      context: context,
      builder: (ctx) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          padding: const EdgeInsets.symmetric(vertical: 12),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
              // ignore: prefer_const_constructors
              child: Text('換一組交易策略',
                  style: TextStyle(
                      fontSize: 16, fontWeight: FontWeight.w800, color: cInk)),
            ),
            for (final st in list)
              ListTile(
                title: Text(st.name,
                    style: TextStyle(
                        fontSize: 15.5,
                        fontWeight: FontWeight.w700,
                        color: cInk)),
                subtitle: Text(st.note,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                onTap: () => Navigator.of(ctx).pop(st),
              ),
          ],
        ),
      ),
    );
    if (picked == null || !mounted) return;
    setState(() => _strategy = picked);
    await _run();
  }

  Widget _tradesCard(TradeResult r) {
    return SectionCard(
      title: '交易明細（${r.records.length} 筆）',
      icon: Icons.list_alt_rounded,
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: EdgeInsets.zero,
          initiallyExpanded: r.records.length <= 8,
          title: Text('展開 / 收起',
              style: TextStyle(
                  fontSize: 15, fontWeight: FontWeight.w700, color: cInk)),
          children: [
            for (var i = 0; i < r.records.length; i++)
              Container(
                padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
                decoration: BoxDecoration(
                  border: Border(bottom: BorderSide(color: cLine, width: 0.8)),
                ),
                child: Row(
                  children: [
                    Expanded(
                      flex: 3,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${i + 1}. ${r.records[i].entryDate} → ${r.records[i].exitDate}',
                              style: TextStyle(
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.w700,
                                  color: cInk)),
                          Text('${r.records[i].reason}・持有 ${r.records[i].holdDays} 天',
                              style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                        ],
                      ),
                    ),
                    Expanded(
                      flex: 2,
                      child: Text(
                        '${signedPct(r.records[i].pnlPct)}（${r.records[i].pnl >= 0 ? '+' : ''}${money(r.records[i].pnl)}）',
                        textAlign: TextAlign.right,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: r.records[i].pnl >= 0
                              ? AppColors.up
                              : AppColors.down,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
