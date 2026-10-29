// 我的交易策略（列表頁，個人自用版）
import 'package:flutter/material.dart';

import '../core/constants.dart';
import '../core/formatters.dart';
import '../data/market_repository.dart';
import '../models/trade_strategy.dart';
import '../services/strategy_store.dart';
import '../ui/strategy_editor_page.dart';
import '../ui/trade_result_page.dart';
import '../ui/widgets.dart';

class StrategyListPage extends StatefulWidget {
  const StrategyListPage({Key? key}) : super(key: key);

  @override
  State<StrategyListPage> createState() => _StrategyListPageState();
}

class _StrategyListPageState extends State<StrategyListPage> {
  List<TradeStrategy> _list = <TradeStrategy>[];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    await MarketRepository.instance.ensureLoaded();
    if (!mounted) return;
    setState(() {
      _list = StrategyStore.all();
      _loading = false;
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
                          constraints: const BoxConstraints(maxWidth: 880),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              _topBar(),
                              for (final st in _list) _strategyCard(st),
                              const SizedBox(height: 8),
                              ActionButton(
                                label: '新增策略',
                                icon: Icons.add_circle_outline_rounded,
                                primary: false,
                                onPressed: () async {
                                  final r = await Navigator.of(context).push<TradeStrategy>(
                                    MaterialPageRoute(
                                        builder: (_) =>
                                            const StrategyEditorPage(origin: null)),
                                  );
                                  if (r != null) _reload();
                                },
                              ),
                              const SizedBox(height: 14),
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

  Widget _topBar() => Padding(
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
                  Text('我的交易策略',
                      style: TextStyle(
                          fontSize: 21,
                          fontWeight: FontWeight.w900,
                          color: cInk)),
                  Text('條件可自行調整，儲存在這台裝置',
                      style: TextStyle(fontSize: 13, color: cInkSoft)),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _strategyCard(TradeStrategy st) {
    final preset = StrategyStore.isPreset(st.id);
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: cSurface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: cLine, width: isHighContrast ? 2 : 1.2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(preset ? Icons.bookmark_rounded : Icons.tune_rounded,
                  size: 20, color: cPrimary),
              const SizedBox(width: 6),
              Expanded(
                child: Text(st.name,
                    style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w900,
                        color: cInk)),
              ),
              Text(preset ? '內建' : '自訂',
                  style: TextStyle(fontSize: 12, color: cInkSoft)),
            ],
          ),
          if (st.note.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 2, bottom: 6),
              child: Text(st.note,
                  style: TextStyle(fontSize: 12.5, height: 1.5, color: cInkSoft)),
            ),
          const SizedBox(height: 6),
          for (final l in st.conditionLines)
            Padding(
              padding: const EdgeInsets.only(bottom: 2),
              child: Text('進場：$l',
                  style: TextStyle(fontSize: 13, height: 1.5, color: cInk)),
            ),
          for (final l in st.exitLines)
            Padding(
              padding: const EdgeInsets.only(bottom: 2),
              child: Text('出場：$l',
                  style: TextStyle(fontSize: 13, height: 1.5, color: cInk)),
            ),
          const SizedBox(height: 6),
          Text(
            '本金 ${money(st.totalCapital)}・每次 ${money(st.trancheAmount)}・'
            '單檔上限 ${st.maxPositionPct.toStringAsFixed(0)}%・${st.frequencyText}',
            style: TextStyle(fontSize: 12.5, color: cInkSoft),
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              if (!preset)
                IconButton(
                  tooltip: '刪除',
                  onPressed: () {
                    StrategyStore.remove(st.id);
                    _reload();
                  },
                  icon: const Icon(Icons.delete_outline_rounded),
                ),
              TextButton.icon(
                onPressed: () async {
                  final r = await Navigator.of(context).push<TradeStrategy>(
                    MaterialPageRoute(builder: (_) => StrategyEditorPage(origin: st)),
                  );
                  if (r != null) _reload();
                },
                icon: const Icon(Icons.edit_outlined),
                label: const Text('編輯'),
              ),
              const SizedBox(width: 4),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(0, 44),
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  textStyle: const TextStyle(
                      fontSize: 14, fontWeight: FontWeight.w800),
                ),
                onPressed: () => _pickStock(st),
                icon: const Icon(Icons.play_arrow_rounded, size: 20),
                label: const Text('回測'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _pickStock(TradeStrategy st) async {
    final stocks = MarketRepository.instance.all;
    String q = '';
    final picked = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheet) {
          final list = stocks
              .where((s) => q.isEmpty || s.id.contains(q) || s.name.contains(q))
              .toList();
          return SafeArea(
            child: Padding(
              padding: EdgeInsets.only(
                  bottom: MediaQuery.of(ctx).viewInsets.bottom),
              child: SizedBox(
                height: MediaQuery.of(ctx).size.height * 0.72,
                child: Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('用「${st.name}」回測哪一檔？',
                              style: TextStyle(
                                  fontSize: 17,
                                  fontWeight: FontWeight.w800,
                                  color: cInk)),
                          const SizedBox(height: 10),
                          TextField(
                            onChanged: (v) => setSheet(() => q = v.trim()),
                            decoration: const InputDecoration(
                              hintText: '輸入代號或名稱，例如 2330 / 台積電',
                              prefixIcon: Icon(Icons.search_rounded),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: ListView.separated(
                        itemCount: list.length,
                        separatorBuilder: (_, __) =>
                            Divider(height: 1, color: cLine),
                        itemBuilder: (_, i) {
                          final s = list[i];
                          return ListTile(
                            title: Text('${s.name}（${s.id}）',
                                style: TextStyle(
                                    fontSize: 15.5,
                                    fontWeight: FontWeight.w700,
                                    color: cInk)),
                            subtitle: Text(s.industry,
                                style:
                                    TextStyle(fontSize: 12.5, color: cInkSoft)),
                            trailing: const Icon(Icons.chevron_right_rounded),
                            onTap: () => Navigator.of(ctx).pop(s.id),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
    if (picked == null || !mounted) return;
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => TradeResultPage(stockId: picked, strategy: st, years: 5),
    ));
  }
}
