// 此頁大量使用動態主題色（cInk 等 getter），const 化收益有限
// ignore_for_file: prefer_const_constructors
// 個股檔案頁：走勢 + 量能 + 事件時間軸（個人自用版）
import 'package:flutter/material.dart';

import '../core/constants.dart';
import '../core/formatters.dart';
import '../data/market_repository.dart';
import '../models/models.dart';
import '../models/trade_strategy.dart';
import '../services/strategy_store.dart';
import '../ui/price_chart.dart';
import '../ui/result_page.dart';
import '../ui/theme.dart';
import '../ui/trade_result_page.dart';
import '../ui/widgets.dart';

class StockProfilePage extends StatefulWidget {
  final String stockId;
  const StockProfilePage({Key? key, required this.stockId}) : super(key: key);

  @override
  State<StockProfilePage> createState() => _StockProfilePageState();
}

class _StockProfilePageState extends State<StockProfilePage> {
  bool _loading = true;
  int _days = 250;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    await MarketRepository.instance.ensureLoaded();
    if (!mounted) return;
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final s = MarketRepository.instance.series(widget.stockId);
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            const PersonalRiskBar(),
            Expanded(
              child: _loading || s == null
                  ? const Center(child: CircularProgressIndicator())
                  : SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(14, 12, 14, 40),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 900),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              _topBar(s),
                              _priceCard(s),
                              _keyCard(s),
                              _eventsCard(s),
                              _actions(s),
                              const SizedBox(height: 8),
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

  Widget _topBar(StockSeries s) {
    final n = s.closes.length;
    final chg = n > 1 && s.closes[n - 2] > 0
        ? (s.closes[n - 1] / s.closes[n - 2] - 1) * 100
        : 0.0;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
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
                Text('${s.name}（${s.id}）',
                    style: TextStyle(
                        fontSize: 21,
                        fontWeight: FontWeight.w900,
                        color: cInk)),
                Text('${s.industry}・資料 ${s.firstDateText} ～ ${s.lastDateText}',
                    style: TextStyle(fontSize: 12.5, color: cInkSoft)),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(s.closes[n - 1].toStringAsFixed(2),
                  style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w900,
                      color: cInk)),
              Text(signedPct(chg, digits: 2),
                  style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: chg >= 0 ? AppColors.up : AppColors.down)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _priceCard(StockSeries s) {
    return SectionCard(
      title: '走勢與成交量',
      icon: Icons.candlestick_chart_rounded,
      trailing: Row(
        children: [
          ChoicePill(
            label: '1 年',
            selected: _days == 250,
            onTap: () => setState(() => _days = 250),
          ),
          const SizedBox(width: 6),
          ChoicePill(
            label: '3 年',
            selected: _days == 750,
            onTap: () => setState(() => _days = 750),
          ),
          const SizedBox(width: 6),
          ChoicePill(
            label: '全部',
            selected: _days == 1200,
            onTap: () => setState(() => _days = 1200),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PriceVolumeChart(
            dates: s.dates,
            closes: s.closes,
            volumes: s.volumes,
            days: _days,
            height: 300,
          ),
          const SizedBox(height: 8),
          Text('紅柱＝當日收盤上漲、綠柱＝下跌（台股慣例）；褐色線為 60 日季線。',
              style: TextStyle(fontSize: 12, color: cInkSoft)),
        ],
      ),
    );
  }

  Widget _keyCard(StockSeries s) {
    final n = s.closes.length;
    final from = n > 252 ? n - 252 : 0;
    final win = s.closes.sublist(from);
    final hi = win.reduce((a, b) => a > b ? a : b);
    final lo = win.reduce((a, b) => a < b ? a : b);
    final close = s.closes[n - 1];
    final ma60 = s.closes
            .sublist(n > 60 ? n - 60 : 0)
            .reduce((a, b) => a + b) /
        (n > 60 ? 60 : n);
    final dist = ma60 > 0 ? (close / ma60 - 1) * 100 : 0.0;
    final y = s.yieldAt(n - 1);
    final per = s.latestPer?.per;

    return SectionCard(
      title: '關鍵數據',
      icon: Icons.insights_rounded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          LayoutBuilder(builder: (ctx, c) {
            final perRow = c.maxWidth > 620 ? 3 : 2;
            final w = (c.maxWidth - (perRow - 1) * 10) / perRow;
            return Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '殖利率',
                      value: pct(y, digits: 2),
                      note: '近 12 個月現金股利 ÷ 股價',
                      color: AppColors.gold,
                    )),
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '本益比',
                      value: per == null ? '—' : per.toStringAsFixed(1),
                      note: per == null ? 'ETF 無此資料' : '資料日 ${s.latestPer!.date}',
                      color: AppColors.primary,
                    )),
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '距季線',
                      value: signedPct(dist),
                      note: '季線 ${ma60.toStringAsFixed(1)} 元',
                      color: dist >= 0 ? AppColors.up : AppColors.down,
                    )),
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '52 週高／低',
                      value: '${hi.toStringAsFixed(0)}／${lo.toStringAsFixed(0)}',
                      note: '現在位於區間 ${((close - lo) / (hi - lo) * 100).clamp(0, 100).toStringAsFixed(0)}%',
                      color: AppColors.primary,
                    )),
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '20 日均量',
                      value: '${money(s.avgVolume(20))} 張',
                      note: '流動性參考',
                      color: AppColors.primary,
                    )),
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '連續配息',
                      value: '${_divStreak(s)} 年',
                      note: '資料範圍內',
                      color: AppColors.gold,
                    )),
              ],
            );
          }),
        ],
      ),
    );
  }

  int _divStreak(StockSeries s) {
    final years =
        s.dividends.map((d) => int.parse(d.ym.substring(0, 4))).toSet().toList()
          ..sort();
    if (years.isEmpty) return 0;
    var streak = 0;
    var y = years.last;
    final set = years.toSet();
    while (set.contains(y)) {
      streak++;
      y--;
    }
    return streak;
  }

  Widget _eventsCard(StockSeries s) {
    final events = <List<String>>[];
    // 除息
    for (final d in s.dividends.reversed.take(6)) {
      events.add(<String>[
        d.ym,
        '除息',
        '每股配 ${d.amount.toStringAsFixed(2)} 元',
      ]);
    }
    // 財報（單季 EPS）
    for (final q in s.eps.reversed.take(4)) {
      events.add(<String>[
        q.ym,
        '單季 EPS',
        '${q.eps.toStringAsFixed(2)} 元',
      ]);
    }
    // 52 週高低點
    final n = s.closes.length;
    final from = n > 252 ? n - 252 : 0;
    var hiI = from, loI = from;
    for (var i = from; i < n; i++) {
      if (s.closes[i] > s.closes[hiI]) hiI = i;
      if (s.closes[i] < s.closes[loI]) loI = i;
    }
    events.add(<String>[
      StockSeries.fmtYmd(s.dates[hiI]),
      '近一年最高',
      '收盤 ${s.closes[hiI].toStringAsFixed(2)} 元',
    ]);
    events.add(<String>[
      StockSeries.fmtYmd(s.dates[loI]),
      '近一年最低',
      '收盤 ${s.closes[loI].toStringAsFixed(2)} 元',
    ]);
    events.sort((a, b) => b[0].compareTo(a[0]));

    return SectionCard(
      title: '事件時間軸',
      icon: Icons.timeline_rounded,
      subtitle: '除息、財報、年度高低點都標在同一個時間軸上，方便對照股價反應。',
      child: Column(
        children: [
          for (final e in events.take(12))
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 86,
                    child: Text(e[0],
                        style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                  ),
                  Container(
                    margin: const EdgeInsets.only(top: 6, right: 8),
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: e[1].contains('配') || e[1].contains('除息')
                          ? AppColors.gold
                          : (e[1].contains('最高')
                              ? AppColors.up
                              : (e[1].contains('最低')
                                  ? AppColors.down
                                  : AppColors.primary)),
                      shape: BoxShape.circle,
                    ),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(e[1],
                            style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w700,
                                color: cInk)),
                        Text(e[2],
                            style:
                                TextStyle(fontSize: 12.5, color: cInkSoft)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _actions(StockSeries s) {
    return SectionCard(
      title: '接下來可以做',
      icon: Icons.play_circle_outline_rounded,
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: ActionButton(
                  label: '存股回測',
                  icon: Icons.savings_rounded,
                  primary: false,
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => ResultPage(
                      stockId: s.id,
                      strategyId: 'yield_dca',
                      years: 5,
                    ),
                  )),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ActionButton(
                  label: '交易回測',
                  icon: Icons.query_stats_rounded,
                  primary: false,
                  onPressed: _openTrade,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          NoticeBar(
            icon: Icons.lightbulb_outline_rounded,
            color: AppColors.gold,
            text: '想練手感又不想冒真錢？回首頁開「模擬交易盤」，用虛擬資金照這個價位買賣，'
                '把「看到訊號→下單→抱單→出場」走完一次。',
          ),
        ],
      ),
    );
  }

  Future<void> _openTrade() async {
    final list = StrategyStore.all();
    final picked = await showModalBottomSheet<TradeStrategy>(
      context: context,
      builder: (ctx) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          padding: const EdgeInsets.symmetric(vertical: 12),
          children: [
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
    await Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => TradeResultPage(
        stockId: widget.stockId,
        strategy: picked,
        years: 5,
      ),
    ));
  }
}
