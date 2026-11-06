// 每日精選頁（個人自用版）
//
// 兩個名單：
//   買進觀察 — 財務過關、估值在相對低檔、動能不再惡化
//   減碼觀察 — 估值在歷史高檔、動能轉弱、或股利開始衰退
//
// 每一檔都給三樣東西：價格區間、觸發條件、失效條件。
// 原則：**區間不是目標價，觸發條件不是預測**。它們只是把「什麼情況才算數」寫清楚。
import 'package:flutter/material.dart';

import '../core/formatters.dart';
import '../services/daily_picks.dart';
import '../services/stock_index.dart';
import '../services/watchlist.dart';
import '../ui/stock_detail_page.dart';
import '../ui/stock_profile_page.dart';
import '../ui/widgets.dart';
import 'theme.dart';

/// 價格顯示：整數不帶小數，有零頭才顯示一位
String fmtPrice(double v) {
  if (v <= 0) return '—';
  return v >= 100 ? v.toStringAsFixed(0) : v.toStringAsFixed(1);
}

class DailyPicksPage extends StatefulWidget {
  const DailyPicksPage({Key? key}) : super(key: key);

  @override
  State<DailyPicksPage> createState() => _DailyPicksPageState();
}

class _DailyPicksPageState extends State<DailyPicksPage> {
  bool _loading = true;
  DailyPicks? _picks;
  int _tab = 0; // 0 = 買進觀察, 1 = 減碼觀察
  String? _expanded;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final p = await DailyPicks.load();
    await StockIndex.instance.ensureLoaded();
    if (!mounted) return;
    setState(() {
      _picks = p;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final p = _picks;
    return Scaffold(
      appBar: AppBar(
        title: const Text('每日精選'),
        automaticallyImplyLeading: !isRootRoute(context),
        leading: isRootRoute(context)
            ? null
            : IconButton(
                icon: const Icon(Icons.arrow_back_rounded),
                onPressed: () => Navigator.of(context).maybePop(),
              ),
      ),
      body: SafeArea(
        bottom: false,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : p == null || p.isEmpty
                ? _emptyState()
                : ListView(
                    padding: const EdgeInsets.fromLTRB(14, 12, 14, 24),
                    children: [
                      _headerCard(p),
                      const SizedBox(height: 12),
                      _tabBar(p),
                      const SizedBox(height: 12),
                      ..._buildList(p),
                      const SizedBox(height: 8),
                      if (_tab == 0) _excludedCard(p),
                      _methodCard(p),
                    ],
                  ),
      ),
    );
  }

  Widget _emptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.inbox_rounded, size: 56, color: cInkSoft),
            const SizedBox(height: 16),
            Text('尚未產生每日名單',
                style: TextStyle(
                    fontSize: 19, fontWeight: FontWeight.w800, color: cInk)),
            const SizedBox(height: 10),
            Text(
              '名單由每日收盤後的掃描程式產生。\n'
              '第一次使用或資料尚未更新時，這裡會是空的。',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 15, height: 1.7, color: cInkSoft),
            ),
            const SizedBox(height: 20),
            Text(
              '在還沒有名單之前，可以用首頁的代號／名稱搜尋，\n'
              '直接查任何一檔股票的檔案。',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, height: 1.7, color: cInkSoft),
            ),
          ],
        ),
      ),
    );
  }

  Widget _headerCard(DailyPicks p) {
    final gen = p.generatedAt.length >= 16
        ? p.generatedAt.replaceFirst('T', ' ').substring(0, 16)
        : p.generatedAt;
    return Container(
      decoration: BoxDecoration(
        color: cSurface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: cLine, width: isHighContrast ? 2 : 1.2),
      ),
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.event_available_rounded, size: 22, color: cPrimary),
              const SizedBox(width: 8),
              Text('交易日 ${p.tradeDate}',
                  style: TextStyle(
                      fontSize: 17, fontWeight: FontWeight.w800, color: cInk)),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '掃描 ${p.universe} 檔候選池，${p.analyzed} 檔通過流動性與財務門檻\n'
            '產生時間 $gen',
            style: TextStyle(fontSize: 13.5, height: 1.6, color: cInkSoft),
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(
              color: isHighContrast ? const Color(0xFF241E00) : AppColors.warnBg,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              '分數＝財務品質 30%＋估值位階 30%＋殖利率 20%＋營收動能 20%。\n'
              '排序在前代表「目前條件最整齊」，不代表明天會漲；條件變了就該重看。',
              style: TextStyle(
                fontSize: 13.5,
                height: 1.6,
                color: isHighContrast ? AppColors.hcInk : const Color(0xFF3A2A00),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _tabBar(DailyPicks p) {
    Widget btn(int idx, String label, int count, Color accent) {
      final on = _tab == idx;
      return Expanded(
        child: GestureDetector(
          onTap: () => setState(() {
            _tab = idx;
            _expanded = null;
          }),
          child: Container(
            height: 56,
            decoration: BoxDecoration(
              color: on ? accent : cSurface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                  color: on ? accent : cLine,
                  width: isHighContrast ? 2 : 1.2),
            ),
            alignment: Alignment.center,
            child: Text(
              '$label $count',
              style: TextStyle(
                fontSize: 16.5,
                fontWeight: FontWeight.w800,
                color: on ? Colors.white : cInk,
              ),
            ),
          ),
        ),
      );
    }

    return Row(
      children: [
        btn(0, '買進觀察', p.buy.length,
            isHighContrast ? AppColors.hcPrimary : AppColors.primary),
        const SizedBox(width: 10),
        btn(1, '減碼觀察', p.trim.length,
            isHighContrast ? AppColors.hcPrimary : AppColors.danger),
      ],
    );
  }

  List<Widget> _buildList(DailyPicks p) {
    final list = _tab == 0 ? p.buy : p.trim;
    if (list.isEmpty) {
      return [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: cSurface,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: cLine),
          ),
          child: Text(
            _tab == 0
                ? '這次掃描沒有標的同時通過四道門檻。\n'
                    '這通常代表整體市場估值偏高，或營收動能普遍轉弱——'
                    '「找不到」本身也是有用的訊息。'
                : '這次掃描沒有標的達到減碼警戒分數（門檻 15 分）。\n'
                    '沒有警示不代表沒有風險，只代表目前沒有觸發設定條件——'
                    '這通常發生在多數標的估值仍在合理區、營收動能也還沒轉弱的時候。',
            style: TextStyle(fontSize: 15, height: 1.7, color: cInkSoft),
          ),
        ),
      ];
    }
    return [
      for (var i = 0; i < list.length; i++)
        _pickCard(list[i], i + 1, isTrim: _tab == 1),
    ];
  }

  Widget _pickCard(PickItem it, int rank, {required bool isTrim}) {
    final expanded = _expanded == '${isTrim ? 't' : 'b'}${it.id}';
    final accent = isTrim
        ? (isHighContrast ? AppColors.hcPrimary : AppColors.danger)
        : (isHighContrast ? AppColors.hcPrimary : AppColors.primary);
    final score = isTrim ? it.trimScore : it.buyScore;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: cSurface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: cLine, width: isHighContrast ? 2 : 1.2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: () => setState(
                () => _expanded = expanded ? null : '${isTrim ? 't' : 'b'}${it.id}'),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 30,
                        height: 30,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: accent,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text('$rank',
                            style: const TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w900,
                                color: Colors.white)),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('${it.name}  ${it.id}',
                                style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.w900,
                                    color: cInk)),
                            const SizedBox(height: 2),
                            Text('${it.industry}・${it.stage}',
                                style: TextStyle(
                                    fontSize: 12.5, color: cInkSoft)),
                          ],
                        ),
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(fmtPrice(it.close),
                              style: TextStyle(
                                  fontSize: 19,
                                  fontWeight: FontWeight.w900,
                                  color: cInk)),
                          const SizedBox(height: 2),
                          Text('${score.toStringAsFixed(0)} 分',
                              style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w800,
                                  color: accent)),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  // 價格區間：全頁最重要的資訊，用最大字級
                  Container(
                    width: double.infinity,
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: BoxDecoration(
                      color: isHighContrast
                          ? const Color(0xFF1A1A1A)
                          : const Color(0xFFF4F1EA),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: cLine),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(isTrim ? '減碼區間' : '估值合理區',
                                style: TextStyle(
                                    fontSize: 12.5,
                                    fontWeight: FontWeight.w700,
                                    color: cInkSoft)),
                            if (!isTrim && it.volatileEps) ...[
                              const SizedBox(width: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: isHighContrast
                                      ? const Color(0xFF2A2400)
                                      : const Color(0xFFFFF1CC),
                                  borderRadius: BorderRadius.circular(5),
                                ),
                                child: const Text('盈餘波動大・參考用',
                                    style: TextStyle(
                                        fontSize: 10.5,
                                        fontWeight: FontWeight.w800,
                                        color: Color(0xFF7A5A00))),
                              ),
                            ],
                          ],
                        ),
                        const SizedBox(height: 3),
                        Text(
                          '${fmtPrice(isTrim ? it.trimLow : it.buyLow)}'
                          ' ～  '
                          '${fmtPrice(isTrim ? it.trimHigh : it.buyHigh)}',
                          style: TextStyle(
                              fontSize: 23,
                              fontWeight: FontWeight.w900,
                              color: accent,
                              letterSpacing: 0.5),
                        ),
                        if (!isTrim) ...[
                          const SizedBox(height: 4),
                          Text(
                            _zoneText(it),
                            style: TextStyle(
                                fontSize: 13,
                                height: 1.5,
                                color: it.buyZoneState == 0
                                    ? AppColors.safe
                                    : cInkSoft,
                                fontWeight: it.buyZoneState == 0
                                    ? FontWeight.w800
                                    : FontWeight.w500),
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: [
                      (it.per == null || it.per! <= 0)
                          ? Tooltip(
                              message: kNoDataTip,
                              child: _chip('本益比 ${fmtPe(it.per)}'),
                            )
                          : _chip('本益比 ${fmtPe(it.per)}'),
                      _chip('分位 ${it.perPct == null ? '—' : '${it.perPct!.toStringAsFixed(0)}%'}',
                          strong: !isTrim && (it.perPct ?? 100) <= 40),
                      (it.yieldPct == null || it.yieldPct! <= 0)
                          ? Tooltip(
                              message: kNoDataTip,
                              child: _chip('殖利率 ${fmtYield(it.yieldPct)}',
                                  strong: !isTrim && (it.yieldPct ?? 0) >= 4),
                            )
                          : _chip('殖利率 ${fmtYield(it.yieldPct)}',
                              strong: !isTrim && (it.yieldPct ?? 0) >= 4),
                      _chip('財檢 ${it.finScore ?? '—'}',
                          strong: (it.finScore ?? 0) >= 70),
                      _chip(
                          '營收 ${it.revYoY == null ? '—' : '${it.revYoY! >= 0 ? '+' : ''}${it.revYoY!.toStringAsFixed(0)}%'}',
                          strong: (it.revYoY ?? -99) > 0),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Icon(expanded ? Icons.expand_less : Icons.expand_more,
                          size: 20, color: cInkSoft),
                      const SizedBox(width: 4),
                      Text(expanded ? '收起理由與條件' : '看理由與觸發條件',
                          style: TextStyle(fontSize: 13.5, color: cInkSoft)),
                    ],
                  ),
                ],
              ),
            ),
          ),
          if (expanded) _detail(it, isTrim: isTrim, accent: accent),
        ],
      ),
    );
  }

  String _zoneText(PickItem it) {
    if (it.volatileEps) {
      // EPS 波動劇烈時，「低於合理區」不代表便宜。
      // 那個區間的分母（EPS）本身在跳動，說「便宜 27%」是誤導。
      return '近四季盈餘波動大，這個區間只能當參考座標，'
          '不能用來判斷「便宜」或「貴」';
    }
    switch (it.buyZoneState) {
      case 0:
        return '現價已在估值合理區內 — 但仍要等觸發條件成立';
      case 1:
        return '現價低於合理區下緣 ${(-(it.gapToBuyZone ?? 0)).toStringAsFixed(1)}%'
            '，需確認不是基本面轉壞才往下掉';
      default:
        return '現價高於合理區上緣 ${(it.gapToBuyZone ?? 0).toStringAsFixed(1)}%，'
            '按歷史估值看還在偏貴的位置';
    }
  }

  Widget _chip(String text, {bool strong = false}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: strong
            ? (isHighContrast ? const Color(0xFF2A2400) : const Color(0xFFE8F5EC))
            : (isHighContrast ? const Color(0xFF1A1A1A) : const Color(0xFFF4F1EA)),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
            color: strong ? AppColors.safe : cLine,
            width: isHighContrast ? 1.6 : 1),
      ),
      child: Text(text,
          style: TextStyle(
              fontSize: 12.5,
              fontWeight: strong ? FontWeight.w800 : FontWeight.w600,
              color: strong ? AppColors.safe : cInkSoft)),
    );
  }

  Widget _detail(PickItem it, {required bool isTrim, required Color accent}) {
    final reasons = isTrim ? it.trimReasons : it.buyReasons;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Divider(height: 20),
          _block('評分依據', reasons, accent, Icons.check_circle_outline_rounded),
          if (!isTrim) ...[
            const SizedBox(height: 12),
            _block('通過的門檻', it.gates, AppColors.safe,
                Icons.verified_outlined),
          ],
          const SizedBox(height: 12),
          _block('要等到這些才算數', it.triggers, accent,
              Icons.rule_rounded),
          const SizedBox(height: 12),
          _block('這份判讀的邊界', it.caveats, cInkSoft,
              Icons.info_outline_rounded),
          if (it.basis.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text('區間推算依據：${it.basis}',
                style: TextStyle(
                    fontSize: 13, height: 1.6, color: cInkSoft)),
          ],
          if (it.ma60 != null) ...[
            const SizedBox(height: 10),
            Text(
              '季線 ${fmtPrice(it.ma60!)}　52 週高 ${fmtPrice(it.high52 ?? 0)}　'
              '低 ${fmtPrice(it.low52 ?? 0)}　日均額 ${it.turnover.toStringAsFixed(1)} 億',
              style: TextStyle(fontSize: 12.5, height: 1.6, color: cInkSoft),
            ),
          ],
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                flex: 3,
                child: SizedBox(
                  height: 50,
                  child: OutlinedButton.icon(
                    onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => StockProfilePage(stockId: it.id),
                    )),
                    icon: const Icon(Icons.insights_rounded, size: 20),
                    label: const Text('個股檔案'),
                    style: OutlinedButton.styleFrom(
                      primary: accent,
                      side: BorderSide(color: accent, width: 1.6),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10)),
                      textStyle: const TextStyle(
                          fontSize: 15.5, fontWeight: FontWeight.w800),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                flex: 2,
                child: SizedBox(
                  height: 50,
                  child: OutlinedButton.icon(
                    onPressed: () {
                      final added = WatchList.add(it.id, it.name,
                          industry: it.industry);
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                        content: Text(added
                            ? '已加入自選股：${it.name}（${it.id}）'
                            : '${it.name} 已在自選股中'),
                        duration: const Duration(seconds: 2),
                      ));
                      setState(() {});
                    },
                    icon: Icon(
                        WatchList.contains(it.id)
                            ? Icons.star_rounded
                            : Icons.star_border_rounded,
                        size: 20),
                    label: Text(WatchList.contains(it.id) ? '已自選' : '加自選'),
                    style: OutlinedButton.styleFrom(
                      primary: AppColors.gold,
                      side: const BorderSide(color: AppColors.gold, width: 1.6),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10)),
                      textStyle: const TextStyle(
                          fontSize: 14.5, fontWeight: FontWeight.w800),
                    ),
                  ),
                ),
              ),
            ],
          ),
          // V2.7：個股詳情頁入口（走勢／股利／填息／殖利率區間／EPS）
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => StockDetailPage(stockId: it.id),
              )),
              icon: const Icon(Icons.candlestick_chart_rounded, size: 17),
              label: const Text('查看個股詳情'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _block(String title, List<String> items, Color accent, IconData icon) {
    if (items.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 17, color: accent),
            const SizedBox(width: 6),
            Text(title,
                style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                    color: cInk)),
          ],
        ),
        const SizedBox(height: 6),
        for (final s in items)
          Padding(
            padding: const EdgeInsets.only(bottom: 5),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.only(top: 7, right: 7),
                  child: Container(
                    width: 4,
                    height: 4,
                    decoration: BoxDecoration(
                        color: accent, shape: BoxShape.circle),
                  ),
                ),
                Expanded(
                  child: Text(s,
                      style: TextStyle(
                          fontSize: 14.5, height: 1.65, color: cInkSoft)),
                ),
              ],
            ),
          ),
      ],
    );
  }

  /// 被門檻擋掉的標的。這塊常常比名單本身更有用：
  /// 使用者最常問的是「為什麼我那檔沒在裡面」，這裡直接給答案。
  Widget _excludedCard(DailyPicks p) {
    if (p.excluded.isEmpty) return const SizedBox.shrink();
    final open = _expanded == 'ex';
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: cSurface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: cLine, width: isHighContrast ? 2 : 1.2),
      ),
      child: Column(
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: () => setState(() => _expanded = open ? null : 'ex'),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
              child: Row(
                children: [
                  Icon(Icons.filter_alt_off_rounded, size: 19, color: cInkSoft),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text('這次沒列入買進名單的 ${p.excluded.length} 檔',
                        style: TextStyle(
                            fontSize: 14.5,
                            fontWeight: FontWeight.w800,
                            color: cInk)),
                  ),
                  Icon(open ? Icons.expand_less : Icons.expand_more,
                      size: 20, color: cInkSoft),
                ],
              ),
            ),
          ),
          if (open)
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
              child: Column(
                children: [
                  for (final e in p.excluded)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          SizedBox(
                            width: 106,
                            child: Text('${e.name} ${e.id}',
                                style: TextStyle(
                                    fontSize: 13.5,
                                    fontWeight: FontWeight.w700,
                                    color: cInk)),
                          ),
                          Expanded(
                            child: Text(e.reason,
                                style: TextStyle(
                                    fontSize: 13, height: 1.5, color: cInkSoft)),
                          ),
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

  Widget _methodCard(DailyPicks p) {
    return Container(
      margin: const EdgeInsets.only(top: 4),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
      decoration: BoxDecoration(
        color: isHighContrast ? const Color(0xFF1A1A1A) : const Color(0xFFF4F1EA),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: cLine),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('評分怎麼算的',
              style: TextStyle(
                  fontSize: 14.5,
                  fontWeight: FontWeight.w900,
                  color: cInk)),
          const SizedBox(height: 8),
          if (p.method['buy'] != null)
            Text('買進觀察：${p.method['buy']}',
                style: TextStyle(fontSize: 13, height: 1.65, color: cInkSoft)),
          if (p.method['trim'] != null) ...[
            const SizedBox(height: 6),
            Text('減碼觀察：${p.method['trim']}',
                style: TextStyle(fontSize: 13, height: 1.65, color: cInkSoft)),
          ],
          const SizedBox(height: 10),
          Text(
            '規則寫在程式裡、可以重跑驗證，沒有隱藏參數。'
            '名單只用公開財務與價量資料，未含法人預估、訂單能見度與經營層訪談。',
            style: TextStyle(fontSize: 12.5, height: 1.65, color: cInkSoft),
          ),
        ],
      ),
    );
  }
}
