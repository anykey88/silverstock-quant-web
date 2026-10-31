// 此頁大量使用動態主題色（cInk 等 getter），const 化收益有限
// ignore_for_file: prefer_const_constructors
// 個股檔案頁：走勢 + 量能 + 事件時間軸（個人自用版）
import 'package:flutter/material.dart';

import '../core/constants.dart';
import '../core/formatters.dart';
import '../data/market_repository.dart';
import '../models/models.dart';
import '../models/trade_strategy.dart';
import '../services/live_quote.dart';
import '../services/margin_store.dart';
import '../services/strategy_store.dart';
import '../v2/margin.dart';
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

  // 風險預算試算器的三個輸入。預設值故意設得保守，
  // 讓使用者第一次打開看到的結論是「不該借」——再自己去調。
  double _ownCapital = 500000;
  double _toleratePct = 15;
  double _worstDropPct = 35;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    await MarketRepository.instance.ensureLoaded();
    await MarginStore.instance.ensureLoaded();
    await LiveStore.instance.ensureLoaded();
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
                              _marginCard(s),
                              _riskBudgetCard(s),
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
    // 有當日即時報價就用它，沒有就退回快照收盤價——絕不假裝是即時的
    final live = LiveStore.instance.isToday
        ? LiveStore.instance.quote(s.id)
        : null;
    final px = live?.price ?? s.closes[n - 1];
    final chg = live != null && live.hasPrev
        ? live.changePct
        : (n > 1 && s.closes[n - 2] > 0
            ? (s.closes[n - 1] / s.closes[n - 2] - 1) * 100
            : 0.0);
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
              Text(px.toStringAsFixed(2),
                  style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w900,
                      color: cInk)),
              Text(signedPct(chg, digits: 2),
                  style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: chg >= 0 ? AppColors.up : AppColors.down)),
              Text(
                  live == null
                      ? '收盤 ${s.lastDateText}'
                      : '即時 ${live.time.isEmpty ? LiveStore.instance.asOf : live.time}',
                  style: TextStyle(
                      fontSize: 11.5,
                      color: live == null ? cInkSoft : cPrimary)),
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

  // -------------------------------------------------------------------------
  // 籌碼面：融資融券
  // -------------------------------------------------------------------------
  Widget _marginCard(StockSeries s) {
    final m = MarginStore.instance
        .profile(s.id, avgVolume20: s.avgVolume(20).toDouble());
    if (!m.hasData) {
      return SectionCard(
        title: '融資融券',
        icon: Icons.account_balance_rounded,
        child: Text(
          '這檔沒有融資融券資料（ETF、興櫃或非信用交易標的都可能是這樣）。',
          style: TextStyle(fontSize: 14, height: 1.6, color: cInkSoft),
        ),
      );
    }

    // 追繳價要用「你現在買得到的價」算，不是快照收盤價
    final live = LiveStore.instance.isToday
        ? LiveStore.instance.quote(s.id)
        : null;
    final close = live?.price ?? s.closes.last;
    final callPx = m.callPrice(close);
    final liqPx = m.liquidationPrice(close);

    return SectionCard(
      title: '融資融券（籌碼面）',
      icon: Icons.account_balance_rounded,
      subtitle: '資料日 ${m.lastDate}　'
          '融資成數 ${(100 - m.ownRatio * 100).toStringAsFixed(0)}%',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          LayoutBuilder(builder: (ctx, c) {
            final cols = c.maxWidth > 620 ? 4 : 2;
            final w = (c.maxWidth - (cols - 1) * 10) / cols;
            return Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '融資餘額',
                      value: '${money(m.marginBal.toDouble())} 張',
                      note: m.chg20 == null
                          ? '借錢買進、還沒賣的張數'
                          : '20 日 ${signedPct(m.chg20!)}',
                      color: (m.chg20 ?? 0) > 0 ? AppColors.up : AppColors.down,
                    )),
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '融資／20日均量',
                      value: m.turnoverDays == null
                          ? '—'
                          : '${m.turnoverDays!.toStringAsFixed(1)} 天',
                      note: '套牢籌碼有多厚',
                      color: (m.turnoverDays ?? 0) >= 10
                          ? AppColors.up
                          : AppColors.primary,
                    )),
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '券資比',
                      value: m.shortToMargin == null
                          ? '—'
                          : pct(m.shortToMargin!, digits: 1),
                      note: '融券 ÷ 融資',
                      color: AppColors.primary,
                    )),
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '融券餘額',
                      value: '${money(m.shortBal.toDouble())} 張',
                      note: '放空、還沒回補的張數',
                      color: AppColors.primary,
                    )),
              ],
            );
          }),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.gold.withOpacity(0.08),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.gold.withOpacity(0.35)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('用融資買在 ${close.toStringAsFixed(1)} 元，會被追繳的位置',
                    style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        color: cInk)),
                const SizedBox(height: 6),
                Text(
                  '追繳價 ${callPx.toStringAsFixed(1)} 元（跌 ${m.callDropPct.toStringAsFixed(0)}%）\n'
                  '斷頭價 ${liqPx.toStringAsFixed(1)} 元（跌 ${(m.callDropPct * 110 / 130).toStringAsFixed(0)}%）',
                  style: TextStyle(
                      fontSize: 15, height: 1.7, color: cInk),
                ),
                const SizedBox(height: 6),
                Text(
                  '算法：券商以整戶維持率 130% 為追繳線，'
                  '融資金額＝成本 × 成數，所以追繳價＝成本 × 成數 × 1.3。'
                  '成數 60% 就是跌 22%、成數 50% 就是跌 35%——'
                  '這就是「融資跌兩成斷頭」這句話的由來。',
                  style: TextStyle(fontSize: 12.5, height: 1.6, color: cInkSoft),
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),
          for (final n in m.notes)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(top: 7, right: 6),
                    child: Icon(Icons.circle, size: 6, color: cPrimary),
                  ),
                  Expanded(
                    child: Text(n,
                        style: TextStyle(
                            fontSize: 14, height: 1.65, color: cInk)),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  // -------------------------------------------------------------------------
  // 風險預算試算器：能承受多少虧損 → 最多能借多少錢
  // -------------------------------------------------------------------------
  Widget _riskBudgetCard(StockSeries s) {
    final m = MarginStore.instance.profile(s.id);
    final ratio = m.hasData ? (1 - m.ownRatio) : 0.60;
    final advice = RiskBudget.evaluate(
      ownCapital: _ownCapital,
      toleratePct: _toleratePct,
      worstDropPct: _worstDropPct,
      financeRatio: ratio,
    );

    return SectionCard(
      title: '風險承受能力 → 可融資上限',
      icon: Icons.shield_moon_rounded,
      subtitle: '先算你能虧多少，再決定能借多少。順序反過來，就是悲劇的開始。',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _budgetSlider(
            label: '自有資金',
            value: _ownCapital,
            min: 100000,
            max: 5000000,
            step: 100000,
            display: '${(_ownCapital / 10000).toStringAsFixed(0)} 萬',
            onChanged: (v) => setState(() => _ownCapital = v),
          ),
          _budgetSlider(
            label: '能承受的總虧損（占自有資金）',
            value: _toleratePct,
            min: 5,
            max: 50,
            step: 5,
            display: '${_toleratePct.toStringAsFixed(0)}%　'
                '≈ ${((_ownCapital * _toleratePct / 100) / 10000).toStringAsFixed(1)} 萬',
            onChanged: (v) => setState(() => _toleratePct = v),
          ),
          _budgetSlider(
            label: '預估這檔最大跌幅',
            value: _worstDropPct,
            min: 10,
            max: 70,
            step: 5,
            display: '${_worstDropPct.toStringAsFixed(0)}%',
            onChanged: (v) => setState(() => _worstDropPct = v),
          ),
          Padding(
            padding: const EdgeInsets.only(top: 2, bottom: 10),
            child: Text(
              '第三個數字不要憑感覺填。台股個股在空頭年跌 40～60% 很常見，'
              '電子股更兇。填太小，算出來的額度會樂觀到害你。',
              style: TextStyle(fontSize: 12.5, height: 1.6, color: cInkSoft),
            ),
          ),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: advice.marginAllowed
                  ? cPrimary.withOpacity(0.07)
                  : AppColors.down.withOpacity(0.08),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: advice.marginAllowed
                    ? cPrimary.withOpacity(0.30)
                    : AppColors.down.withOpacity(0.35),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  advice.marginAllowed
                      ? '可融資上限 ${(advice.maxLoan / 10000).toStringAsFixed(1)} 萬'
                      : '不建議融資',
                  style: TextStyle(
                      fontSize: 19,
                      fontWeight: FontWeight.w900,
                      color: advice.marginAllowed
                          ? cPrimary
                          : AppColors.down),
                ),
                const SizedBox(height: 6),
                Text(advice.verdict,
                    style: TextStyle(
                        fontSize: 14.5, height: 1.65, color: cInk)),
                const SizedBox(height: 10),
                Divider(height: 1, color: cLine),
                const SizedBox(height: 8),
                for (final step in advice.steps)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 5),
                    child: Text('· $step',
                        style: TextStyle(
                            fontSize: 13, height: 1.6, color: cInkSoft)),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _budgetSlider({
    required String label,
    required double value,
    required double min,
    required double max,
    required double step,
    required String display,
    required ValueChanged<double> onChanged,
  }) {
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
            Text(display,
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
            label: display,
            onChanged: onChanged,
          ),
        ),
      ],
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
