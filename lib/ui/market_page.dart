// 此頁大量使用動態主題色（cInk 等 getter），const 化收益有限
// ignore_for_file: prefer_const_constructors
// 市場觀察頁（個人自用版）：大盤溫度 + 產業溫度 + 歷史條件機率
import 'package:flutter/material.dart';

import '../core/constants.dart';
import '../core/formatters.dart';
import '../data/market_repository.dart';
import '../engine/market_analyzer.dart';
import '../engine/screener.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';

class MarketPage extends StatefulWidget {
  const MarketPage({Key? key}) : super(key: key);

  @override
  State<MarketPage> createState() => _MarketPageState();
}

class _MarketPageState extends State<MarketPage> {
  bool _loading = true;
  MarketPulse? _pulse;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    await MarketRepository.instance.ensureLoaded();
    final repo = MarketRepository.instance;
    final idx = repo.index;
    MarketPulse? p;
    if (idx != null) {
      final scored = Screener.scoreAll(repo.all);
      p = MarketAnalyzer.analyze(
        idx,
        repo.all,
        scored.map((e) => ScreenedLite(e.series.id, e.score)).toList(),
      );
    }
    if (!mounted) return;
    setState(() {
      _pulse = p;
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
                          constraints: const BoxConstraints(maxWidth: 900),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              _topBar(),
                              if (_pulse == null)
                                SectionCard(
                                  title: '大盤資料不足',
                                  icon: Icons.error_outline_rounded,
                                  child: Text('目前快照沒有加權指數資料。',
                                      style: TextStyle(fontSize: 14, color: cInk)),
                                )
                              else ...[
                                _indexCard(_pulse!),
                                _tempCard(_pulse!),
                                _breadthCard(_pulse!),
                                _statsCard(_pulse!),
                                _industryCard(_pulse!),
                              ],
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
                  Text('市場觀察',
                      style: TextStyle(
                          fontSize: 21,
                          fontWeight: FontWeight.w900,
                          color: cInk)),
                  Text('只看現在的狀態與過去的分布，不預測漲跌',
                      style: TextStyle(fontSize: 13, color: cInkSoft)),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _indexCard(MarketPulse p) {
    final up = p.chg1d >= 0;
    return SectionCard(
      title: '加權指數（TAIEX）',
      icon: Icons.public_rounded,
      subtitle: '資料截至快照日，非即時行情。',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(money(p.close, digits: 2),
                  style: TextStyle(
                      fontSize: 34,
                      fontWeight: FontWeight.w900,
                      color: cInk,
                      height: 1.1)),
              const SizedBox(width: 10),
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(signedPct(p.chg1d, digits: 2),
                    style: TextStyle(
                        fontSize: 19,
                        fontWeight: FontWeight.w800,
                        color: up ? AppColors.up : AppColors.down)),
              ),
            ],
          ),
          const SizedBox(height: 10),
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
                      label: '距季線（60日）',
                      value: signedPct(p.distMa60),
                      color: p.distMa60 >= 0 ? AppColors.up : AppColors.down,
                    )),
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '距年線（240日）',
                      value: signedPct(p.distMa240),
                      color: p.distMa240 >= 0 ? AppColors.up : AppColors.down,
                    )),
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '量能（今／20日均）',
                      value: '${p.volRatio20.toStringAsFixed(2)} 倍',
                      note: p.volRatio20 >= 1.3 ? '明显放大' : '量能平稳',
                      color: AppColors.primary,
                    )),
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '20 日年化波動',
                      value: pct(p.vol20Pct),
                      color: AppColors.gold,
                    )),
              ],
            );
          }),
        ],
      ),
    );
  }

  Widget _tempCard(MarketPulse p) {
    final color = p.tempScore >= 75
        ? AppColors.up
        : (p.tempScore >= 58
            ? const Color(0xFFB26B00)
            : (p.tempScore >= 42
                ? AppColors.primary
                : AppColors.down));
    return SectionCard(
      title: '市場溫度',
      icon: Icons.thermostat_rounded,
      subtitle: '由「位階 40 + 廣度 25 + 量能 15 + 波動 20」組成，只描述狀態。',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 96,
                height: 96,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isHighContrast ? Colors.black : color.withOpacity(0.10),
                  border: Border.all(color: color, width: 3),
                ),
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(p.tempScore.toStringAsFixed(0),
                          style: TextStyle(
                              fontSize: 30,
                              fontWeight: FontWeight.w900,
                              color: color,
                              height: 1)),
                      Text('/100',
                          style: TextStyle(fontSize: 11, color: cInkSoft)),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(p.state,
                        style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w900,
                            color: color)),
                    const SizedBox(height: 4),
                    Text(p.stateNote,
                        style: TextStyle(
                            fontSize: 13.5, height: 1.6, color: cInk)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          const NoticeBar(
            icon: Icons.info_outline_rounded,
            color: AppColors.gold,
            text: '溫度高低 ≠ 未來漲跌。它只是把「現在相對過去的位階、市場廣度、量能、波動」量化，'
                '幫你決定要用幾成的資金、多嚴的紀律。',
          ),
        ],
      ),
    );
  }

  Widget _breadthCard(MarketPulse p) {
    final total = p.upCount + p.downCount;
    return SectionCard(
      title: '市場廣度（樣本 $total 檔）',
      icon: Icons.stacked_line_chart_rounded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: Row(
              children: [
                Expanded(
                  flex: p.upCount.clamp(1, 999),
                  child: Container(height: 16, color: AppColors.up),
                ),
                Expanded(
                  flex: p.downCount.clamp(1, 999),
                  child: Container(height: 16, color: AppColors.down),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Text('上漲 ${p.upCount} 檔',
                  style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: AppColors.up)),
              const Spacer(),
              Text('下跌 ${p.downCount} 檔',
                  style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: AppColors.down)),
            ],
          ),
          const SizedBox(height: 6),
          Text('上涨家数占比 ${p.breadth.toStringAsFixed(0)}%：'
              '${p.breadth >= 70 ? '普遍走扬' : (p.breadth <= 30 ? '普遍走弱' : '涨跌互见')}',
              style: TextStyle(fontSize: 13, color: cInkSoft)),
        ],
      ),
    );
  }

  Widget _statsCard(MarketPulse p) {
    return SectionCard(
      title: '歷史條件機率（不是預測）',
      icon: Icons.history_toggle_off_rounded,
      subtitle: '統計過去 5 年：處在同樣條件時，之後 20／60 個交易日的報酬分布。',
      child: Column(
        children: [
          for (final s in p.stats)
            Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isHighContrast ? Colors.black : const Color(0xFFF7F3EA),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: cLine),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(s.label,
                            style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w800,
                                color: cInk)),
                      ),
                      Text('${s.samples} 個交易日',
                          style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: _statCell('20 日中位數', signedPct(s.median20),
                            '正報酬 ${s.win20.toStringAsFixed(0)}%'),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _statCell('60 日中位數', signedPct(s.median60),
                            '正報酬 ${s.win60.toStringAsFixed(0)}%'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          Text('讀法：中位數是「一半的情況比它好、一半比它差」；正報酬比例越高，'
              '代表歷史上處在這條件時，之後上漲的次數越多。但樣本只有 5 年，'
              '且過去不代表未來。',
              style: TextStyle(fontSize: 12.5, height: 1.6, color: cInkSoft)),
        ],
      ),
    );
  }

  Widget _statCell(String label, String value, String note) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: isHighContrast ? Colors.black : Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: cLine),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(fontSize: 12, color: cInkSoft)),
          Text(value,
              style: TextStyle(
                  fontSize: 18, fontWeight: FontWeight.w900, color: cInk)),
          Text(note, style: TextStyle(fontSize: 11.5, color: cInkSoft)),
        ],
      ),
    );
  }

  Widget _industryCard(MarketPulse p) {
    return SectionCard(
      title: '產業溫度（近 20 日平均報酬排序）',
      icon: Icons.category_rounded,
      subtitle: '數字是同產業樣本股的平均值，不是指數。',
      child: Column(
        children: [
          for (final ind in p.industries)
            Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: cLine),
              ),
              child: Row(
                children: [
                  SizedBox(
                    width: 84,
                    child: Text(ind.name,
                        style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            color: cInk)),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text('20 日 ${signedPct(ind.chg20)}',
                                style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w700,
                                    color: ind.chg20 >= 0
                                        ? AppColors.up
                                        : AppColors.down)),
                            const SizedBox(width: 10),
                            Text('60 日 ${signedPct(ind.chg60)}',
                                style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w700,
                                    color: ind.chg60 >= 0
                                        ? AppColors.up
                                        : AppColors.down)),
                          ],
                        ),
                        Text('${ind.count} 檔・殖利率均 ${ind.avgYield.toStringAsFixed(1)}%'
                            '・評分均 ${ind.avgScore.toStringAsFixed(0)}',
                            style:
                                TextStyle(fontSize: 11.5, color: cInkSoft)),
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
}
