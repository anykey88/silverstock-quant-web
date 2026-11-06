// 個股詳情頁（V2.7 新增）
// 由觀察清單／我的持股點進來：走勢＋量能＋現金股利＋填息＋殖利率區間＋EPS／配息率。
// 離線優先：有歷史快照的標的給完整資料；不在快照內的標的只顯示清單基本資料並標註待補。
import 'package:flutter/material.dart';

import '../core/constants.dart';
import '../core/formatters.dart';
import '../services/stock_detail.dart';
import '../ui/candle_chart.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';

class StockDetailPage extends StatefulWidget {
  final String stockId;
  const StockDetailPage({Key? key, required this.stockId}) : super(key: key);

  @override
  State<StockDetailPage> createState() => _StockDetailPageState();
}

class _StockDetailPageState extends State<StockDetailPage> {
  bool _loading = true;
  StockDetail? _d;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final d = await StockDetailService.load(widget.stockId);
    if (!mounted) return;
    setState(() {
      _d = d;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            const PersonalRiskBar(),
            Expanded(
              child: _loading || d == null
                  ? const Center(child: CircularProgressIndicator())
                  : SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(14, 6, 14, 40),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 900),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              _topBar(d),
                              _basicCard(d),
                              if (d.hasSeries) ...[
                                const SizedBox(height: 12),
                                _chartCard(d),
                                const SizedBox(height: 12),
                                _dividendCard(d),
                                const SizedBox(height: 12),
                                _yieldCard(d),
                                const SizedBox(height: 12),
                                _epsCard(d),
                              ] else
                                _noSeriesNotice(d),
                              const SizedBox(height: 12),
                              _revenueCard(),
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

  Widget _topBar(StockDetail d) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          children: [
            if (!isRootRoute(context))
              IconButton(
                iconSize: 30,
                onPressed: () => Navigator.of(context).maybePop(),
                icon: const Icon(Icons.arrow_back_rounded),
              ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${d.name}（${d.id}）',
                      style: TextStyle(
                          fontSize: 21, fontWeight: FontWeight.w900, color: cInk)),
                  Text(
                      d.industry.isEmpty
                          ? (d.group.isEmpty ? '個股詳情' : d.group)
                          : '${d.industry}${d.group.isEmpty ? '' : '・${d.group}'}',
                      style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                ],
              ),
            ),
            if (d.close > 0)
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(d.close.toStringAsFixed(2),
                      style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w900,
                          color: cInk)),
                  Text('收盤（清單）',
                      style: TextStyle(fontSize: 11.5, color: cInkSoft)),
                ],
              ),
          ],
        ),
      );

  Widget _basicCard(StockDetail d) => SectionCard(
        title: '基本指標',
        icon: Icons.pin_invoke_rounded,
        subtitle: d.source == 'snapshot' ? '資料來源：歷史快照' : '資料來源：家族清單（尚無歷史快照）',
        child: LayoutBuilder(builder: (ctx, c) {
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
                  value: fmtYield(d.yieldPct),
                  color: AppColors.gold,
                  tooltip: (d.yieldPct == null || d.yieldPct! <= 0) ? kNoDataTip : null,
                ),
              ),
              SizedBox(
                width: w,
                child: MetricTile(
                  label: '本益比',
                  value: fmtPe(d.pe),
                  color: AppColors.primary,
                  tooltip: (d.pe == null || d.pe! <= 0) ? kNoDataTip : null,
                ),
              ),
              SizedBox(
                width: w,
                child: MetricTile(
                  label: '股淨比',
                  value: fmtPb(d.pb),
                  color: AppColors.primary,
                  tooltip: (d.pb == null || d.pb! <= 0) ? kPbNaTip : null,
                ),
              ),
            ],
          );
        }),
      );

  Widget _chartCard(StockDetail d) => SectionCard(
        title: '日 K 走勢與成交量（示意）',
        icon: Icons.candlestick_chart_rounded,
        subtitle: '示意：開盤價為前一日收盤還原，非真實 OHLC｜紅漲綠跌・褐色線為 60 日季線・近 2 年',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CandleVolumeChart(
              dates: d.dates,
              closes: d.closes,
              volumes: d.volumes,
              days: 500,
              height: 320,
            ),
            const SizedBox(height: 8),
            Text('蠟燭開盤價由前一日收盤還原（內建快照僅提供收盤價＋成交量，非真實開高低）。'
                '真實 OHLC 日 K 需 FinMind 日線資料集。',
                style: TextStyle(fontSize: 12, color: cInkSoft, height: 1.5)),
          ],
        ),
      );

  Widget _dividendCard(StockDetail d) {
    final rows = d.dividends;
    if (rows.isEmpty) {
      return SectionCard(
        title: '現金股利與填息',
        icon: Icons.payments_rounded,
        subtitle: '這檔在快照中沒有現金股利紀錄（可能是 ETF 或不配息标的）。',
        child: Text('暫無現金股利資料。',
            style: TextStyle(fontSize: 14, color: cInkSoft)),
      );
    }
    // 最新的放最上面
    final ordered = List<DivRow>.from(rows.reversed);
    return SectionCard(
      title: '現金股利與填息',
      icon: Icons.payments_rounded,
      subtitle: '每股現金股利・除息月・填息天數（股價回到除息前水位所需交易日）',
      child: Column(
        children: [
          for (final r in ordered) _divRow(r),
        ],
      ),
    );
  }

  Widget _divRow(DivRow r) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          children: [
            SizedBox(
              width: 86,
              child: Text('${r.year} 年',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: cInk)),
            ),
            Expanded(
              child: Text('每股 ${r.cash.toStringAsFixed(2)} 元',
                  style: TextStyle(fontSize: 14, color: cInk)),
            ),
            SizedBox(
              width: 96,
              child: Text(
                r.fillDays == null ? '填息觀察中' : '${r.fillDays} 天填息',
                style: TextStyle(
                  fontSize: 13.5,
                  fontWeight: FontWeight.w700,
                  color: r.fillDays == null ? AppColors.gold : AppColors.safe,
                ),
              ),
            ),
          ],
        ),
      );

  Widget _yieldCard(StockDetail d) {
    final y = d.yieldRange;
    if (y == null) {
      return SectionCard(
        title: '殖利率區間',
        icon: Icons.show_chart_rounded,
        child: Text('快照中缺少足夠的殖利率序列，無法計算區間。',
            style: TextStyle(fontSize: 14, color: cInkSoft)),
      );
    }
    return SectionCard(
      title: '殖利率區間',
      icon: Icons.show_chart_rounded,
      subtitle: '取快照中本益比序列的殖利率資料（歷史區間，非預測）',
      child: LayoutBuilder(builder: (ctx, c) {
        final w = (c.maxWidth - 20) / 3;
        return Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            SizedBox(
              width: w,
              child: MetricTile(label: '最低', value: pct(y.min, digits: 2), color: AppColors.gold),
            ),
            SizedBox(
              width: w,
              child: MetricTile(label: '最高', value: pct(y.max, digits: 2), color: AppColors.gold),
            ),
            SizedBox(
              width: w,
              child: MetricTile(label: '平均', value: pct(y.avg, digits: 2), color: AppColors.gold),
            ),
          ],
        );
      }),
    );
  }

  Widget _epsCard(StockDetail d) {
    final rows = d.epsYears;
    final payout = d.payoutRatio;
    final last = rows.isNotEmpty ? rows.last : null;
    return SectionCard(
      title: 'EPS 與配息率',
      icon: Icons.bar_chart_rounded,
      subtitle: '年度 EPS（四個季度都公布才算完整年度）・最新完整年度配息率',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          LayoutBuilder(builder: (ctx, c) {
            final perRow = c.maxWidth > 620 ? 2 : 1;
            final w = (c.maxWidth - (perRow - 1) * 10) / perRow;
            return Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                SizedBox(
                  width: w,
                  child: MetricTile(
                    label: '最新年度 EPS',
                    value: last == null ? '—' : last.eps.toStringAsFixed(2),
                    note: last == null ? '無完整年度' : '${last.year} 年',
                    color: AppColors.primary,
                  ),
                ),
                SizedBox(
                  width: w,
                  child: MetricTile(
                    label: '配息率',
                    value: payout == null ? '—' : pct(payout, digits: 1),
                    note: payout == null ? '資料不足' : '現金股利 ÷ 年度 EPS',
                    color: AppColors.safe,
                  ),
                ),
              ],
            );
          }),
          if (rows.length > 1) ...[
            const SizedBox(height: 12),
            const Divider(height: 1),
            const SizedBox(height: 8),
            Text('近 ${rows.length} 個完整年度 EPS',
                style: TextStyle(fontSize: 13, color: cInkSoft)),
            const SizedBox(height: 6),
            for (final e in rows.reversed.take(8))
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Row(
                  children: [
                    SizedBox(
                      width: 86,
                      child: Text('${e.year} 年',
                          style: TextStyle(fontSize: 14, color: cInk)),
                    ),
                    Text(e.eps.toStringAsFixed(2),
                        style: TextStyle(
                            fontSize: 14.5,
                            fontWeight: FontWeight.w700,
                            color: cInk)),
                  ],
                ),
              ),
          ],
        ],
      ),
    );
  }

  Widget _noSeriesNotice(StockDetail d) => const SizedBox.shrink();

  Widget _revenueCard() => SectionCard(
        title: '月營收年增率（YoY）',
        icon: Icons.trending_up_rounded,
        subtitle: '資料待補',
        child: NoticeBar(
          icon: Icons.hourglass_empty_rounded,
          color: AppColors.gold,
          text: '月營收年增率需要 FinMind「TaiwanStockMonthRevenue」資料集，'
              '目前內建快照未納入。V2.7 後續將透過週度 CI 抓取補齊，'
              '屆時本區塊會顯示近 3 年各月 YoY。',
        ),
      );
}
