// 選股篩選頁（個人自用版）
import 'package:flutter/material.dart';

import '../core/constants.dart';
import '../core/formatters.dart';
import '../data/market_repository.dart';
import '../engine/screener.dart';
import '../models/trade_strategy.dart';
import '../services/strategy_store.dart';
import '../ui/result_page.dart';
import '../ui/trade_result_page.dart';
import '../ui/widgets.dart';

class ScreenerPage extends StatefulWidget {
  const ScreenerPage({Key? key}) : super(key: key);

  @override
  State<ScreenerPage> createState() => _ScreenerPageState();
}

class _ScreenerPageState extends State<ScreenerPage> {
  bool _loading = true;
  List<ScreenedStock> _all = <ScreenedStock>[];
  List<ScreenedStock> _view = <ScreenedStock>[];
  String? _expandedId;

  ScreenerFilter _f = const ScreenerFilter();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    await MarketRepository.instance.ensureLoaded();
    final scored = Screener.scoreAll(MarketRepository.instance.all,
        lookbackYears: _f.lookbackYears);
    if (!mounted) return;
    setState(() {
      _all = scored;
      _view = Screener.filter(scored, _f);
      _loading = false;
    });
  }

  void _apply(ScreenerFilter f) {
    // 窗口一改，回撤與風險分都要重算，不能只重篩
    if (f.lookbackYears != _f.lookbackYears) {
      setState(() {
        _f = f;
        _all = Screener.scoreAll(MarketRepository.instance.all,
            lookbackYears: f.lookbackYears);
        _view = Screener.filter(_all, f);
      });
      return;
    }
    setState(() {
      _f = f;
      _view = Screener.filter(_all, f);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            const PersonalRiskBar(),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(14, 12, 14, 40),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 900),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              _topBar(),
                              _filterCard(),
                              _resultHeader(),
                              for (final s in _view) _stockCard(s),
                              if (_view.isEmpty) _empty(),
                              const SizedBox(height: 10),
                              const InlineDisclaimer(),
                              const SizedBox(height: 12),
                              Text(kDataSourceNote,
                                  style: TextStyle(
                                      fontSize: 12.5,
                                      height: 1.6,
                                      color: cInkSoft)),
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
                Text('選股篩選與評分',
                    style: TextStyle(
                        fontSize: 21, fontWeight: FontWeight.w900, color: cInk)),
                Text('${_all.length} 檔標的・依殖利率、評價、配息、成長、風險打分',
                    style: TextStyle(fontSize: 13, color: cInkSoft)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _filterCard() {
    return SectionCard(
      title: '篩選條件',
      icon: Icons.filter_alt_rounded,
      trailing: TextButton(
        onPressed: () => _apply(const ScreenerFilter()),
        child: const Text('重設'),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _label('策略預設（一鍵套用，逆向收息不怕科技巨震）'),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              ChoicePill(
                label: '綜合評分',
                selected: !_f.excludeIndustries.contains('半導體') &&
                    _f.industries.isEmpty,
                onTap: () => _apply(const ScreenerFilter()),
              ),
              ChoicePill(
                label: '防禦逆向收息',
                selected: _f.excludeIndustries.contains('半導體'),
                onTap: () => _apply(ScreenerFilter.defensive),
              ),
            ],
          ),
          _label('產業（可多選，不選＝全部）'),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final ind in kIndustries)
                ChoicePill(
                  label: ind,
                  selected: _f.industries.contains(ind),
                  onTap: () {
                    final set = Set<String>.from(_f.industries);
                    if (!set.add(ind)) set.remove(ind);
                    _apply(_f.copyWith(industries: set));
                  },
                ),
            ],
          ),
          const SizedBox(height: 8),
          _label('排除產業（逆向策略：把高波動科技濾掉，點選＝不顯示）'),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final ind in kIndustries)
                ChoicePill(
                  label: ind,
                  selected: _f.excludeIndustries.contains(ind),
                  onTap: () {
                    final set = Set<String>.from(_f.excludeIndustries);
                    if (!set.add(ind)) set.remove(ind);
                    _apply(_f.copyWith(excludeIndustries: set));
                  },
                ),
            ],
          ),
          const SizedBox(height: 6),
          _label('股價範圍（資金有限時，先把買不起的濾掉）'),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final cap in const <double>[0, 50, 100, 200, 300, 500, 1000])
                ChoicePill(
                  label: cap <= 0 ? '不限' : r'$' + cap.toStringAsFixed(0),
                  selected: (_f.maxPrice ?? 0) == cap,
                  onTap: () => _apply(cap <= 0
                      ? _f.copyWith(clearMaxPrice: true)
                      : _f.copyWith(maxPrice: cap)),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Text('股價下限：',
                  style: TextStyle(
                      fontSize: 14, fontWeight: FontWeight.w700, color: cInkSoft)),
              const SizedBox(width: 4),
              for (final lo in const <double>[0, 10, 20, 50])
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoicePill(
                    label: lo <= 0 ? '不限' : r'$' + lo.toStringAsFixed(0),
                    selected: _f.minPrice == lo,
                    onTap: () => _apply(_f.copyWith(minPrice: lo)),
                  ),
                ),
            ],
          ),
          _label('統計窗口（回撤與風險分用哪一段歷史來算）'),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final yr in const <int>[1, 2, 3, 0])
                ChoicePill(
                  label: yr <= 0 ? '全部歷史' : '近 $yr 年',
                  selected: _f.lookbackYears == yr,
                  onTap: () => _apply(_f.copyWith(lookbackYears: yr)),
                ),
            ],
          ),
          Padding(
            padding: const EdgeInsets.only(top: 6, bottom: 2),
            child: Text(
              '窗口越短，越貼近現在的市場脾氣，但容易被單一事件帶偏；'
              '窗口越長，看得到完整的多空循環，但十年前的黑天鵝對今天的參考價值遞減。',
              style: TextStyle(fontSize: 12.5, height: 1.5, color: cInkSoft),
            ),
          ),
          _slider(
            label: '殖利率至少',
            value: _f.minYield,
            min: 0,
            max: 8,
            step: 0.5,
            unit: '%',
            onChange: (v) => _apply(_f.copyWith(minYield: v)),
          ),
          _slider(
            label: '本益比上限',
            value: _f.maxPer ?? 0,
            min: 0,
            max: 40,
            step: 1,
            unit: '倍（0＝不限）',
            onChange: (v) => _apply(v <= 0
                ? _f.copyWith(clearMaxPer: true)
                : _f.copyWith(maxPer: v)),
          ),
          _slider(
            label: '連續配息至少',
            value: _f.minDivYears.toDouble(),
            min: 0,
            max: 5,
            step: 1,
            unit: '年',
            onChange: (v) => _apply(_f.copyWith(minDivYears: v.round())),
          ),
          _slider(
            label: '股價距季線上限',
            value: _f.maxDistMa60 ?? 30,
            min: -20,
            max: 30,
            step: 5,
            unit: '%（30＝不限）',
            onChange: (v) => _apply(v >= 30
                ? _f.copyWith(clearDist: true)
                : _f.copyWith(maxDistMa60: v)),
          ),
          _slider(
            label: _f.lookbackYears <= 0
                ? '最大回撤上限（全部歷史）'
                : '近 ${_f.lookbackYears} 年最大回撤上限',
            value: _f.maxDrawdown1y ?? 80,
            min: 15,
            max: 80,
            step: 5,
            unit: '%（80＝不限）',
            onChange: (v) => _apply(v >= 80
                ? _f.copyWith(clearMdd: true)
                : _f.copyWith(maxDrawdown1y: v)),
          ),
          _slider(
            label: '綜合評分至少',
            value: _f.minScore,
            min: 0,
            max: 90,
            step: 5,
            unit: '分',
            onChange: (v) => _apply(_f.copyWith(minScore: v)),
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Text('排序：',
                  style: TextStyle(
                      fontSize: 14, fontWeight: FontWeight.w700, color: cInkSoft)),
              const SizedBox(width: 8),
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _f.sortBy,
                  isExpanded: true,
                  style: TextStyle(fontSize: 15, color: cInk),
                  decoration: const InputDecoration(
                    contentPadding:
                        EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'score', child: Text('綜合評分（高→低）')),
                    DropdownMenuItem(value: 'yield', child: Text('殖利率（高→低）')),
                    DropdownMenuItem(value: 'per', child: Text('本益比（低→高）')),
                    DropdownMenuItem(value: 'drawdown', child: Text('回撤（小→大）')),
                    DropdownMenuItem(value: 'eps', child: Text('EPS 成長（高→低）')),
                  ],
                  onChanged: (v) {
                    if (v != null) _apply(_f.copyWith(sortBy: v));
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _label(String t) => Padding(
        padding: const EdgeInsets.only(top: 8, bottom: 6),
        child: Text(t,
            style: TextStyle(
                fontSize: 14, fontWeight: FontWeight.w700, color: cInkSoft)),
      );

  Widget _slider({
    required String label,
    required double value,
    required double min,
    required double max,
    required double step,
    required String unit,
    required ValueChanged<double> onChange,
  }) {
    final shown = value <= min && (label.contains('上限') || label.contains('至少'))
        ? value
        : value;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(label,
                  style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: cInkSoft)),
            ),
            Text('${shown.toStringAsFixed(shown == shown.roundToDouble() ? 0 : 1)} $unit',
                style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                    color: cPrimary)),
          ],
        ),
        SliderTheme(
          data: SliderTheme.of(context).copyWith(
            trackHeight: 4,
            thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 11),
          ),
          child: Slider(
            value: value.clamp(min, max),
            min: min,
            max: max,
            divisions: ((max - min) / step).round(),
            label: shown.toStringAsFixed(0),
            onChanged: onChange,
          ),
        ),
      ],
    );
  }

  Widget _resultHeader() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8, top: 4),
      child: Row(
        children: [
          Icon(Icons.fact_check_rounded, size: 20, color: cPrimary),
          const SizedBox(width: 6),
          Expanded(
            child: Text('符合條件：${_view.length} 檔 / 全部 ${_all.length} 檔',
                style: TextStyle(
                    fontSize: 16, fontWeight: FontWeight.w800, color: cInk)),
          ),
        ],
      ),
    );
  }

  Widget _empty() => SectionCard(
        title: '沒有符合條件的標的',
        icon: Icons.search_off_rounded,
        child: Text('把條件放寬一點再試（例如殖利率門檻降到 3%、或取消回撤限制）。',
            style: TextStyle(fontSize: 14.5, height: 1.6, color: cInkSoft)),
      );

  Widget _stockCard(ScreenedStock s) {
    final expanded = _expandedId == s.series.id;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: cSurface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: cLine, width: isHighContrast ? 2 : 1.2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ScoreBadge(score: s.score, label: s.label),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${s.series.name}（${s.series.id}）',
                        style: TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w900,
                            color: cInk)),
                    Text('${s.series.industry}・收盤 ${s.close.toStringAsFixed(2)} 元',
                        style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: [
                        _kv('殖利率', pct(s.yieldRate, digits: 2)),
                        _kv('本益比', s.per == null ? '—' : s.per!.toStringAsFixed(1)),
                        _kv('配息', '${s.divStreak} 年'),
                        _kv('距季線', signedPct(s.distMa60)),
                        _kv(_f.lookbackYears <= 0
                                ? '最大回撤'
                                : '${_f.lookbackYears} 年回撤',
                            pct(s.mddWindow)),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              TextButton.icon(
                onPressed: () => setState(() => _expandedId = expanded ? null : s.series.id),
                icon: Icon(expanded
                    ? Icons.expand_less_rounded
                    : Icons.expand_more_rounded),
                label: Text(expanded ? '收起理由' : '為什麼是這個分數'),
              ),
              const Spacer(),
              TextButton.icon(
                onPressed: () => _openTrade(s),
                icon: const Icon(Icons.play_circle_outline_rounded),
                label: const Text('交易回測'),
              ),
              const SizedBox(width: 4),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(0, 44),
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  textStyle: const TextStyle(
                      fontSize: 14, fontWeight: FontWeight.w800),
                ),
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => ResultPage(
                      stockId: s.series.id,
                      strategyId: 'yield_dca',
                      years: 5,
                    ),
                  ),
                ),
                child: const Text('存股回測'),
              ),
            ],
          ),
          if (expanded) ...[
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: isHighContrast ? Colors.black : const Color(0xFFF7F3EA),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final e in s.parts.entries)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Row(
                        children: [
                          SizedBox(
                            width: 52,
                            child: Text(e.key,
                                style: TextStyle(
                                    fontSize: 12.5, color: cInkSoft)),
                          ),
                          Expanded(
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: LinearProgressIndicator(
                                value: e.value / 100,
                                minHeight: 8,
                                backgroundColor: cLine.withOpacity(0.4),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          SizedBox(
                            width: 32,
                            child: Text(e.value.toStringAsFixed(0),
                                textAlign: TextAlign.right,
                                style: TextStyle(
                                    fontSize: 12.5,
                                    fontWeight: FontWeight.w700,
                                    color: cInk)),
                          ),
                        ],
                      ),
                    ),
                  const SizedBox(height: 4),
                  for (final r in s.reasons)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 2),
                      child: Text('・$r',
                          style: TextStyle(
                              fontSize: 13, height: 1.55, color: cInk)),
                    ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _kv(String k, String v) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: isHighContrast ? Colors.black : const Color(0xFFF2EEE3),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text('$k $v',
          style: TextStyle(
              fontSize: 12.5, fontWeight: FontWeight.w700, color: cInk)),
    );
  }

  Future<void> _openTrade(ScreenedStock s) async {
    final strategies = StrategyStore.all();
    final picked = await showModalBottomSheet<TradeStrategy>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('選一組交易策略，回測 ${s.series.name}',
                  style: TextStyle(
                      fontSize: 17, fontWeight: FontWeight.w800, color: cInk)),
              const SizedBox(height: 4),
              Text('手續費與證交稅已計入；結果為歷史模擬。',
                  style: TextStyle(fontSize: 13, color: cInkSoft)),
              const SizedBox(height: 12),
              for (final st in strategies)
                Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: cLine),
                  ),
                  child: ListTile(
                    contentPadding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    title: Text(st.name,
                        style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                            color: cInk)),
                    subtitle: Text(st.note,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () => Navigator.of(ctx).pop(st),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
    if (picked == null || !mounted) return;
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => TradeResultPage(
        stockId: s.series.id,
        strategy: picked,
        years: 5,
      ),
    ));
  }
}
