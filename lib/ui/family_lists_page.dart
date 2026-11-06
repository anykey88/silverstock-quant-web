// 三份觀察清單（清單甲／清單乙／共同關注），一頁看完
import 'package:flutter/material.dart';

import '../core/formatters.dart';
import '../services/family_lists.dart';
import '../ui/stock_detail_page.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';

class FamilyListsPage extends StatefulWidget {
  const FamilyListsPage({Key? key}) : super(key: key);

  @override
  State<FamilyListsPage> createState() => _FamilyListsPageState();
}

class _FamilyListsPageState extends State<FamilyListsPage> {
  bool _loading = true;
  FamilyListsData? _data;
  int _tab = 2;
  String _cat = '全部';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final d = await FamilyListsService.load();
    if (!mounted) return;
    setState(() {
      _data = d;
      _loading = false;
    });
  }

  FamilyList? get _cur {
    final lists = _data?.lists ?? const <FamilyList>[];
    if (lists.isEmpty) return null;
    final i = _tab.clamp(0, lists.length - 1);
    return lists[i];
  }

  List<String> get _cats {
    final c = _cur;
    if (c == null) return const <String>['全部'];
    final seen = <String>[];
    for (final it in c.items) {
      final k = it.category.isEmpty ? '其他' : it.category;
      if (!seen.contains(k)) seen.add(k);
    }
    return <String>['全部', ...seen];
  }

  List<FamilyItem> get _items {
    final c = _cur;
    if (c == null) return const <FamilyItem>[];
    if (_cat == '全部') return c.items;
    return c.items
        .where((e) => (e.category.isEmpty ? '其他' : e.category) == _cat)
        .toList();
  }

  void _switchTab(int i) {
    setState(() {
      _tab = i;
      _cat = '全部';
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
                      padding: const EdgeInsets.fromLTRB(14, 6, 14, 40),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 900),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              _topBar(),
                              if (_data == null || !_data!.ok) _errorCard(),
                              if (_data != null && _data!.ok) ...[
                                _tabs(),
                                const SizedBox(height: 10),
                                if (_cur != null && _cur!.note.isNotEmpty)
                                  NoticeBar(
                                    text: _cur!.note,
                                    color: AppColors.gold,
                                    icon: Icons.push_pin_outlined,
                                  ),
                                const SizedBox(height: 10),
                                _summary(),
                                const SizedBox(height: 10),
                                _catBar(),
                                const SizedBox(height: 10),
                                _listCard(),
                              ],
                              const SizedBox(height: 12),
                              _footNote(),
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
                  Text('觀察清單',
                      style: TextStyle(
                          fontSize: 21, fontWeight: FontWeight.w900, color: cInk)),
                  Text('清單甲・清單乙・共同關注 三份清單，每日更新',
                      style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                ],
              ),
            ),
            IconButton(
              tooltip: '重新載入',
              onPressed: () {
                setState(() => _loading = true);
                _load();
              },
              icon: const Icon(Icons.refresh_rounded),
            ),
          ],
        ),
      );

  Widget _errorCard() => SectionCard(
        title: '清單讀取失敗',
        icon: Icons.error_outline_rounded,
        accent: AppColors.danger,
        child: Text('找不到 assets/data/family_lists.json，或格式有誤。'
            '請確認檔案已隨版本打包（flutter pub get 後重新建置）。',
            style: TextStyle(fontSize: 14.5, height: 1.6, color: cInkSoft)),
      );

  Widget _tabs() {
    final lists = _data!.lists;
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (var i = 0; i < lists.length; i++)
          ChoicePill(
            label: _shortName(lists[i].key, lists[i].title),
            sub: '${lists[i].items.length} 檔',
            selected: i == _tab,
            onTap: () => _switchTab(i),
          ),
      ],
    );
  }

  String _shortName(String key, String title) {
    // 標題一律以資料檔為準（清單甲／清單乙／共同關注），
    // 避免對外暴露家人身份；舊資料若仍含舊稱謂也不顯示。
    switch (key) {
      case 'mom':
        return title.contains('清單') ? title : '清單甲';
      case 'dad':
        return title.contains('清單') ? title : '清單乙';
      case 'adv':
        return title.contains('建議') ? '共同關注' : title;
      default:
        return title;
    }
  }

  Widget _summary() {
    final items = _items;
    var up = 0;
    var down = 0;
    var flat = 0;
    var ySum = 0.0;
    var yN = 0;
    for (final it in items) {
      if (it.pct > 0) {
        up++;
      } else if (it.pct < 0) {
        down++;
      } else {
        flat++;
      }
      final y = it.yieldPct;
      if (y != null && y > 0) {
        ySum += y;
        yN++;
      }
    }
    final avgY = yN > 0 ? ySum / yN : 0.0;
    return SectionCard(
      title: '${_cur?.title ?? ''}・${items.length} 檔',
      icon: Icons.list_alt_rounded,
      subtitle: _cur?.subtitle ?? '',
      child: LayoutBuilder(builder: (ctx, c) {
        final perRow = c.maxWidth > 620 ? 4 : 2;
        final w = (c.maxWidth - (perRow - 1) * 10) / perRow;
        return Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            SizedBox(
              width: w,
              child: MetricTile(
                label: '上漲',
                value: '$up 檔',
                color: AppColors.up,
                big: true,
              ),
            ),
            SizedBox(
              width: w,
              child: MetricTile(
                label: '下跌',
                value: '$down 檔',
                color: AppColors.down,
                big: true,
              ),
            ),
            SizedBox(
              width: w,
              child: MetricTile(
                label: '平盤',
                value: '$flat 檔',
                color: cInkSoft,
              ),
            ),
            SizedBox(
              width: w,
              child: MetricTile(
                label: '平均殖利率',
                value: yN > 0 ? pct(avgY, digits: 2) : '—',
                note: yN > 0 ? '$yN 檔有配息資料' : '多為 ETF 或未提供',
                color: AppColors.gold,
              ),
            ),
          ],
        );
      }),
    );
  }

  Widget _catBar() {
    final cats = _cats;
    if (cats.length <= 2) return const SizedBox.shrink();
    return SizedBox(
      height: 44,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: cats.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (_, i) {
          final k = cats[i];
          final sel = k == _cat;
          return InkWell(
            onTap: () => setState(() => _cat = k),
            borderRadius: BorderRadius.circular(20),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: sel ? cPrimary : Colors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: sel ? cPrimary : cLine, width: 1.6),
              ),
              child: Text(
                k,
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: sel ? Colors.white : cInk,
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _listCard() {
    final items = _items;
    if (items.isEmpty) {
      return SectionCard(
        title: '沒有符合的標的',
        icon: Icons.inbox_rounded,
        child: Text('換個分類看看。',
            style: TextStyle(fontSize: 14.5, color: cInkSoft)),
      );
    }
    return SectionCard(
      title: '個股（${items.length} 檔）',
      icon: Icons.table_rows_rounded,
      subtitle: items.any((e) => !e.live)
          ? '紅漲綠跌・價格為最近收盤（非盤中即時）'
          : '紅漲綠跌・殖利率／本益比／股淨比為體質參考',
      child: Column(
        children: [for (final it in items) _itemTile(it)],
      ),
    );
  }

  Widget _itemTile(FamilyItem it) {
    final col = it.pct > 0
        ? AppColors.up
        : (it.pct < 0 ? AppColors.down : AppColors.inkSoft);
    final yStr = fmtYield(it.yieldPct);
    final peStr = fmtPe(it.pe);
    final pbStr = fmtPb(it.pb);

    return InkWell(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => StockDetailPage(stockId: it.id),
      )),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: cLine),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${it.name}（${it.id}）',
                          style: TextStyle(
                              fontSize: 16.5,
                              fontWeight: FontWeight.w900,
                              color: cInk)),
                      const SizedBox(height: 2),
                      Text(
                          '${it.industry}${it.group.isEmpty ? '' : '・${it.group}'}',
                          style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                      const SizedBox(height: 4),
                      Text('點擊查看走勢・股利・填息・EPS',
                          style: TextStyle(
                              fontSize: 11.5,
                              color: cPrimary,
                              fontWeight: FontWeight.w600)),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(it.close > 0 ? it.close.toStringAsFixed(2) : '—',
                        style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w900,
                            color: cInk)),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          it.pct > 0
                              ? Icons.arrow_upward_rounded
                              : (it.pct < 0
                                  ? Icons.arrow_downward_rounded
                                  : Icons.remove_rounded),
                          size: 13,
                          color: col,
                        ),
                        Text(
                          '${it.change >= 0 ? '+' : ''}${it.change.toStringAsFixed(2)}'
                          '　${signedPct(it.pct, digits: 2)}',
                          style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w800,
                              color: col),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                _kv('殖利率', yStr,
                    tooltip: yStr.startsWith('N/A') ? kNoDataTip : null),
                _kv('本益比', peStr,
                    tooltip: peStr.startsWith('N/A') ? kNoDataTip : null),
                _kv('股淨比', pbStr,
                    tooltip: pbStr.startsWith('N/A') ? kPbNaTip : null),
                if (it.status.isNotEmpty)
                  _kv('狀態', it.status, color: _statusColor(it.status)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Color _statusColor(String s) {
    switch (s) {
      case '可建倉':
        return AppColors.safe;
      case '減碼觀察':
        return AppColors.danger;
      default:
        return AppColors.gold;
    }
  }

  Widget _kv(String k, String v, {Color? color, String? tooltip}) {
    final tile = Padding(
      padding: const EdgeInsets.only(right: 16, bottom: 2),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(k, style: TextStyle(fontSize: 11, color: cInkSoft)),
          Text(v,
              style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w800,
                  color: color ?? cInk)),
        ],
      ),
    );
    return tooltip == null ? tile : Tooltip(message: tooltip, child: tile);
  }

  Widget _footNote() {
    final d = _data;
    final text = d == null
        ? ''
        : '資料日 ${d.generatedAt}・清單版本 ${d.updatedAt}。'
            '價格來自證交所公開資訊，收盤後更新；盤中可能延遲。'
            '本頁只整理自選標的與助手觀察，不構成買賣建議。';
    if (text.isEmpty) return const SizedBox.shrink();
    return Text(text,
        style: TextStyle(fontSize: 12, height: 1.6, color: cInkSoft));
  }
}
