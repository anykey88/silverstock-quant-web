// 我的持股（輕量、獨立於多帳戶系統）
import 'package:flutter/material.dart';

import '../core/formatters.dart';
import '../data/market_repository.dart';
import '../services/account_export.dart';
import '../services/holdings.dart';
import '../services/remote_stock_service.dart';
import '../services/stock_index.dart';
import '../ui/stock_detail_page.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';

class HoldingsPage extends StatefulWidget {
  const HoldingsPage({Key? key}) : super(key: key);

  @override
  State<HoldingsPage> createState() => _HoldingsPageState();
}

class _HoldingsPageState extends State<HoldingsPage> {
  bool _loading = true;
  List<Holding> _list = <Holding>[];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    await MarketRepository.instance.ensureLoaded();
    await StockIndex.instance.ensureLoaded();
    if (!mounted) return;
    setState(() {
      _list = HoldingsStore.all;
      _loading = false;
    });
  }

  double _priceOf(String id) {
    final s = MarketRepository.instance.series(id);
    if (s != null && s.closes.isNotEmpty) return s.closes.last;
    return 0;
  }

  double get _totalCost =>
      _list.fold(0.0, (a, h) => a + h.costPrice * h.shares);

  double get _totalMv =>
      _list.fold(0.0, (a, h) => a + _priceOf(h.id) * h.shares);

  double get _totalPnl => _totalMv - _totalCost;

  double get _totalPct =>
      _totalCost > 0 ? _totalPnl / _totalCost * 100 : 0.0;

  void _snack(String s) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(s), duration: const Duration(seconds: 3)),
    );
  }

  Future<void> _add() async {
    final r = await _showAddDialog();
    if (r == null) return;
    final added = HoldingsStore.add(Holding(
      id: r.id,
      name: r.name,
      industry: r.industry,
      shares: r.shares,
      costPrice: r.cost,
      note: r.note,
    ));
    setState(() => _list = HoldingsStore.all);
    _snack(added ? '已加入「${r.name}」' : '已合併／更新「${r.name}」');
  }

  Future<void> _edit(Holding h) async {
    final r = await _showAddDialog(existing: h);
    if (r == null) return;
    HoldingsStore.update(Holding(
      id: h.id,
      name: r.name,
      industry: r.industry,
      shares: r.shares,
      costPrice: r.cost,
      note: r.note,
    ));
    setState(() => _list = HoldingsStore.all);
    _snack('已更新「${h.name}」');
  }

  Future<void> _remove(Holding h) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('刪除「${h.name}」？'),
        content: const Text('這筆持股會從清單移除，無法復原。'),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('取消')),
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text('刪除')),
        ],
      ),
    );
    if (ok != true) return;
    HoldingsStore.remove(h.id);
    setState(() => _list = HoldingsStore.all);
    _snack('已刪除');
  }

  void _export() {
    if (_list.isEmpty) {
      _snack('清單是空的，沒有可匯出的資料');
      return;
    }
    final csv = HoldingsStore.exportCsv(_priceOf);
    AccountExport.download(
        'SilverStock_我的持股_${_dateTag()}.csv', csv);
    _snack('已匯出 ${_list.length} 檔持股');
  }

  String _dateTag() {
    final t = DateTime.now();
    String two(int v) => v < 10 ? '0$v' : '$v';
    return '${t.year}${two(t.month)}${two(t.day)}';
  }

  // ---------------------------------------------------------------- 解析股票
  Future<_Resolved?> _resolve(String raw) async {
    final text = raw.trim();
    if (text.isEmpty) return null;
    final up = text.toUpperCase();
    final local = MarketRepository.instance.series(up);
    if (local != null) {
      return _Resolved(local.id, local.name, local.industry);
    }
    if (RegExp(r'^[0-9]{4,6}[A-Z]?$').hasMatch(up)) {
      final ok = await _confirmBuild(up, null);
      if (ok != true) return null;
      return _build(up, null);
    }
    await StockIndex.instance.ensureLoaded();
    final hits = StockIndex.instance.search(text, limit: 30);
    if (hits.isEmpty) {
      _snack('找不到「$text」。可輸入 4 位數代號，或名稱的一部分。');
      return null;
    }
    final b = hits.length == 1
        ? hits.first
        : await _pick(hits, text);
    if (b == null) return null;
    if (MarketRepository.instance.series(b.id) != null) {
      return _Resolved(b.id, b.name, b.industry);
    }
    final ok = await _confirmBuild(b.id, b.name);
    if (ok != true) return null;
    return _build(b.id, b.name);
  }

  Future<StockBrief?> _pick(List<StockBrief> hits, String kw) {
    return showModalBottomSheet<StockBrief>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: SizedBox(
          height: MediaQuery.of(ctx).size.height * 0.78,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 6),
                child: Text('選擇標的（${hits.length} 筆）',
                    style: const TextStyle(
                        fontSize: 18, fontWeight: FontWeight.w900)),
              ),
              Expanded(
                child: ListView.separated(
                  itemCount: hits.length,
                  separatorBuilder: (_, __) => Divider(height: 1, color: cLine),
                  itemBuilder: (_, i) {
                    final b = hits[i];
                    return ListTile(
                      title: Text('${b.name}（${b.id}）',
                          style: const TextStyle(
                              fontSize: 16, fontWeight: FontWeight.w700)),
                      subtitle: Text('${b.industry}・${b.marketLabel}',
                          style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                      onTap: () => Navigator.of(ctx).pop(b),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<bool?> _confirmBuild(String id, String? name) async {
    return showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(name == null ? '建立 $id 的檔案？' : '建立 $name（$id）？'),
        content: const Text('這個代號不在內建 111 檔內。可現在向 FinMind 抓取歷史資料'
            '建立檔案（約 10–20 秒，需要網路）。建立後才有現價與損益。',
            style: TextStyle(fontSize: 14.5, height: 1.6)),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('取消')),
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text('建立檔案')),
        ],
      ),
    );
  }

  Future<_Resolved?> _build(String id, String? name) async {
    try {
      final s = await RemoteStockService.fetch(id);
      MarketRepository.instance.register(s);
      return _Resolved(s.id, s.name, s.industry);
    } on RemoteStockException catch (e) {
      _snack(e.message);
      return null;
    } catch (e) {
      _snack('建立失敗：$e');
      return null;
    }
  }

  // ---------------------------------------------------------------- 新增對話框
  Future<_AddResult?> _showAddDialog({Holding? existing}) async {
    final idCtrl = TextEditingController(
        text: existing == null ? '' : '${existing.id}');
    final nameCtrl = TextEditingController(text: existing?.name ?? '');
    final indCtrl =
        TextEditingController(text: existing?.industry ?? '');
    final sharesCtrl = TextEditingController(
        text: existing == null ? '1000' : '${existing.shares}');
    final costCtrl = TextEditingController(
        text: existing == null
            ? ''
            : existing.costPrice.toStringAsFixed(2));
    final noteCtrl =
        TextEditingController(text: existing?.note ?? '');
    var resolvedId = existing?.id ?? '';
    var err = '';

    final r = await showDialog<_AddResult>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSt) => AlertDialog(
          title: Text(existing == null ? '加入一筆持股' : '編輯持股'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: idCtrl,
                  autofocus: existing == null,
                  keyboardType: TextInputType.text,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                  decoration: const InputDecoration(
                    labelText: '股票代號或名稱',
                    hintText: '例如 2330、中華電、台積',
                    prefixIcon: Icon(Icons.search_rounded),
                  ),
                ),
                if (existing == null)
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Align(
                      alignment: Alignment.centerRight,
                      child: TextButton.icon(
                        onPressed: () async {
                          final res =
                              await _resolve(idCtrl.text);
                          if (res != null && mounted) {
                            resolvedId = res.id;
                            idCtrl.text = res.id;
                            nameCtrl.text = res.name;
                            indCtrl.text = res.industry;
                            // 預填現價為買進價參考
                            final px = _priceOf(res.id);
                            if (px > 0 && costCtrl.text.isEmpty) {
                              costCtrl.text = px.toStringAsFixed(2);
                            }
                            setSt(() {});
                          }
                        },
                        icon: const Icon(Icons.auto_fix_high_rounded, size: 18),
                        label: const Text('解析並帶入'),
                      ),
                    ),
                  ),
                const SizedBox(height: 10),
                if (resolvedId.isNotEmpty)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF7F3EA),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: cLine),
                    ),
                    child: Text(
                        '已帶入：${nameCtrl.text}（${resolvedId}）・${indCtrl.text}',
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
                  ),
                const SizedBox(height: 12),
                TextField(
                  controller: sharesCtrl,
                  keyboardType: TextInputType.number,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                  decoration: const InputDecoration(
                    labelText: '持有股數',
                    hintText: '例如 1000、500、2000',
                    prefixIcon: Icon(Icons.tag_rounded),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: costCtrl,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                  decoration: const InputDecoration(
                    labelText: '買進價格（每股）',
                    hintText: '留空則以現價計（無損益）',
                    prefixIcon: Icon(Icons.attach_money_rounded),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: noteCtrl,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    labelText: '備註（選填）',
                    hintText: '例如：長期存股、股息再投入',
                  ),
                ),
                if (err.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(err,
                        style: TextStyle(fontSize: 12, color: AppColors.danger)),
                  ),
              ],
            ),
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: const Text('取消')),
            TextButton(
              onPressed: () {
                final id = resolvedId.isNotEmpty
                    ? resolvedId
                    : idCtrl.text.trim().toUpperCase();
                if (id.isEmpty) {
                  setSt(() => err = '請先輸入代號並解析');
                  return;
                }
                final shares = int.tryParse(sharesCtrl.text.trim()) ?? 0;
                if (shares <= 0) {
                  setSt(() => err = '股數必須大於 0');
                  return;
                }
                final cost = double.tryParse(costCtrl.text.trim()) ?? 0;
                Navigator.of(ctx).pop(_AddResult(
                  id: id,
                  name: nameCtrl.text.trim(),
                  industry: indCtrl.text.trim(),
                  shares: shares,
                  cost: cost,
                  note: noteCtrl.text.trim(),
                ));
              },
              child: const Text('儲存'),
            ),
          ],
        ),
      ),
    );
    return r;
  }

  // ---------------------------------------------------------------- 畫面
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
                              _summaryCard(),
                              const SizedBox(height: 12),
                              _listCard(),
                              const SizedBox(height: 12),
                              const InlineDisclaimer(),
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
                  Text('我的持股',
                      style: TextStyle(
                          fontSize: 21, fontWeight: FontWeight.w900, color: cInk)),
                  Text('記錄手上持有・看成本、現價、損益與佔比',
                      style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                ],
              ),
            ),
            IconButton(
              tooltip: '匯出 CSV',
              onPressed: _export,
              icon: const Icon(Icons.file_download_outlined),
            ),
            IconButton(
              tooltip: '加入持股',
              onPressed: _add,
              icon: const Icon(Icons.add_circle_outline_rounded),
            ),
          ],
        ),
      );

  Widget _summaryCard() {
    final pnl = _totalPnl;
    final col = pnl >= 0 ? AppColors.up : AppColors.down;
    return SectionCard(
      title: '持股總覽',
      icon: Icons.pie_chart_rounded,
      subtitle: '${_list.length} 檔・現價取自資料快照',
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
                label: '總市值',
                value: money(_totalMv),
                note: '現價 × 股數',
                color: cInk,
                big: true,
              ),
            ),
            SizedBox(
              width: w,
              child: MetricTile(
                label: '總成本',
                value: money(_totalCost),
                color: AppColors.primary,
              ),
            ),
            SizedBox(
              width: w,
              child: MetricTile(
                label: '總損益',
                value: money(pnl),
                note: '市值 − 成本',
                color: col,
              ),
            ),
            SizedBox(
              width: w,
              child: MetricTile(
                label: '報酬率',
                value: signedPct(_totalPct),
                color: col,
              ),
            ),
          ],
        );
      }),
    );
  }

  Widget _listCard() {
    if (_list.isEmpty) {
      return SectionCard(
        title: '持股清單',
        icon: Icons.inventory_2_rounded,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('還沒有持股。點右上角「＋」加入第一筆——輸入代號、股數、買進價格即可。',
                style: TextStyle(fontSize: 14.5, height: 1.6, color: cInkSoft)),
            const SizedBox(height: 12),
            ActionButton(
              label: '加入一筆持股',
              icon: Icons.add_rounded,
              onPressed: _add,
            ),
          ],
        ),
      );
    }
    // 依市值佔比排序（大的在前）
    final sorted = List<Holding>.from(_list)
      ..sort((a, b) => (_priceOf(b.id) * b.shares)
          .compareTo(_priceOf(a.id) * a.shares));
    return SectionCard(
      title: '持股清單（${_list.length} 檔）',
      icon: Icons.inventory_2_rounded,
      subtitle: '點「編輯」改股數／買價；點「賣出」只清掉這筆紀錄（不會真的下單）',
      child: Column(
        children: [
          for (final h in sorted) _holdingTile(h),
        ],
      ),
    );
  }

  Widget _holdingTile(Holding h) {
    final px = _priceOf(h.id);
    final mv = px * h.shares;
    final cost = h.costPrice * h.shares;
    final pnl = mv - cost;
    final pnlPct = cost > 0 ? pnl / cost * 100 : 0;
    final weight = _totalMv > 0 ? mv / _totalMv * 100 : 0;
    final pnlCol = pnl >= 0 ? AppColors.up : AppColors.down;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: cLine),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          InkWell(
            onTap: () => Navigator.of(context).push(MaterialPageRoute(
              builder: (_) => StockDetailPage(stockId: h.id),
            )),
            borderRadius: BorderRadius.circular(8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${h.name}（${h.id}）',
                              style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w900,
                                  color: cInk)),
                          Text('${h.industry}・${h.shares} 股',
                              style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                        ],
                      ),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(money(pnl),
                            style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w900,
                                color: pnlCol)),
                        Text(signedPct(pnlPct),
                            style: TextStyle(fontSize: 12, color: pnlCol)),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _kv('買進價', h.costPrice > 0 ? h.costPrice.toStringAsFixed(2) : '—'),
                    _kv('現價', px > 0 ? px.toStringAsFixed(2) : '—'),
                    _kv('市值', money(mv)),
                  ],
                ),
                const SizedBox(height: 6),
                Text('點擊查看走勢・股利・填息・EPS',
                    style: TextStyle(
                        fontSize: 11.5,
                        color: cPrimary,
                        fontWeight: FontWeight.w600)),
              ],
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              _kv('佔比', pct(weight)),
              if (h.note.isNotEmpty) Expanded(child: _kv('備註', h.note)),
              const Spacer(),
              TextButton(
                onPressed: () => _edit(h),
                child: const Text('編輯'),
              ),
              TextButton(
                onPressed: () => _remove(h),
                child: Text('刪除', style: TextStyle(color: AppColors.danger)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.only(right: 14, bottom: 2),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(k, style: TextStyle(fontSize: 11, color: cInkSoft)),
            Text(v,
                style: TextStyle(
                    fontSize: 14, fontWeight: FontWeight.w800, color: cInk)),
          ],
        ),
      );
}

class _Resolved {
  final String id;
  final String name;
  final String industry;
  const _Resolved(this.id, this.name, this.industry);
}

class _AddResult {
  final String id;
  final String name;
  final String industry;
  final int shares;
  final double cost;
  final String note;
  const _AddResult({
    required this.id,
    required this.name,
    required this.industry,
    required this.shares,
    required this.cost,
    required this.note,
  });
}
