// 建議記錄（助手精選池 + 使用者本機觀察）
import 'package:flutter/material.dart';

import '../core/formatters.dart';
import '../data/market_repository.dart';
import '../services/recommendations.dart';
import '../services/remote_stock_service.dart';
import '../services/stock_index.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';
import 'stock_profile_page.dart';

class RecommendationsPage extends StatefulWidget {
  const RecommendationsPage({Key? key}) : super(key: key);

  @override
  State<RecommendationsPage> createState() => _RecommendationsPageState();
}

class _RecommendationsPageState extends State<RecommendationsPage> {
  bool _loading = true;
  RecommendationsData _data = const RecommendationsData(
      items: <RecItem>[], note: '', updatedAt: '', generatedAt: '');
  List<RecItem> _merged = <RecItem>[];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    await MarketRepository.instance.ensureLoaded();
    await StockIndex.instance.ensureLoaded();
    final data = await RecommendationsService.load();
    if (!mounted) return;
    setState(() {
      _data = data;
      _merged = RecommendationsService.withUserRecs(
          data.items, (id) => _priceOf(id));
      _loading = false;
    });
  }

  double _priceOf(String id) {
    final s = MarketRepository.instance.series(id);
    if (s != null && s.closes.isNotEmpty) return s.closes.last;
    return 0;
  }

  int get _buyCount =>
      _merged.where((e) => e.tone == 'buy' && !e.isUser).length;

  void _snack(String s) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(s), duration: const Duration(seconds: 3)),
    );
  }

  Future<void> _addMine() async {
    final r = await _showAddDialog();
    if (r == null) return;
    UserRecStore.add(UserRec(
      id: r.id,
      name: r.name,
      industry: r.industry,
      thesis: r.thesis,
      note: r.note,
      buyTarget: r.target,
    ));
    setState(() => _merged = RecommendationsService.withUserRecs(
        _data.items, (id) => _priceOf(id)));
    _snack('已加入「${r.name}」到我的觀察');
  }

  Future<void> _removeMine(UserRec u) async {
    UserRecStore.remove(u.id);
    setState(() => _merged = RecommendationsService.withUserRecs(
        _data.items, (id) => _priceOf(id)));
    _snack('已刪除觀察');
  }

  Future<_Resolved?> _resolve(String raw) async {
    final text = raw.trim();
    if (text.isEmpty) return null;
    final up = text.toUpperCase();
    final local = MarketRepository.instance.series(up);
    if (local != null) return _Resolved(local.id, local.name, local.industry);
    if (RegExp(r'^[0-9]{4,6}[A-Z]?$').hasMatch(up)) {
      if (await _confirmBuild(up, null) != true) return null;
      return _build(up, null);
    }
    await StockIndex.instance.ensureLoaded();
    final hits = StockIndex.instance.search(text, limit: 30);
    if (hits.isEmpty) {
      _snack('找不到「$text」。可輸入 4 位數代號或名稱。');
      return null;
    }
    final b = hits.length == 1 ? hits.first : await _pick(hits, text);
    if (b == null) return null;
    if (MarketRepository.instance.series(b.id) != null) {
      return _Resolved(b.id, b.name, b.industry);
    }
    if (await _confirmBuild(b.id, b.name) != true) return null;
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

  Future<_AddResult?> _showAddDialog() async {
    final idCtrl = TextEditingController();
    final nameCtrl = TextEditingController();
    final indCtrl = TextEditingController();
    final thesisCtrl = TextEditingController();
    final noteCtrl = TextEditingController();
    final targetCtrl = TextEditingController();
    var resolvedId = '';
    var err = '';

    final r = await showDialog<_AddResult>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSt) => AlertDialog(
          title: const Text('加一筆我的觀察'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: idCtrl,
                  autofocus: true,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                  decoration: const InputDecoration(
                    labelText: '股票代號或名稱',
                    hintText: '例如 2330、中華電',
                    prefixIcon: Icon(Icons.search_rounded),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Align(
                    alignment: Alignment.centerRight,
                    child: TextButton.icon(
                      onPressed: () async {
                        final res = await _resolve(idCtrl.text);
                        if (res != null && mounted) {
                          resolvedId = res.id;
                          idCtrl.text = res.id;
                          nameCtrl.text = res.name;
                          indCtrl.text = res.industry;
                          setSt(() {});
                        }
                      },
                      icon: const Icon(Icons.auto_fix_high_rounded, size: 18),
                      label: const Text('解析並帶入'),
                    ),
                  ),
                ),
                if (resolvedId.isNotEmpty)
                  Container(
                    width: double.infinity,
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF7F3EA),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: cLine),
                    ),
                    child: Text('已帶入：${nameCtrl.text}（${resolvedId}）・${indCtrl.text}',
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
                  ),
                const SizedBox(height: 8),
                TextField(
                  controller: thesisCtrl,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    labelText: '看好理由（選填）',
                    hintText: '例如：股息穩定、等回檔再加',
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: targetCtrl,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                  decoration: const InputDecoration(
                    labelText: '目標買價（選填）',
                    hintText: '低於此價標記「可建倉」',
                    prefixIcon: Icon(Icons.attach_money_rounded),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: noteCtrl,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    labelText: '備註（選填）',
                    hintText: '例如：長期存股',
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
                final target =
                    double.tryParse(targetCtrl.text.trim()) ?? 0;
                Navigator.of(ctx).pop(_AddResult(
                  id: id,
                  name: nameCtrl.text.trim(),
                  industry: indCtrl.text.trim(),
                  thesis: thesisCtrl.text.trim(),
                  note: noteCtrl.text.trim(),
                  target: target,
                ));
              },
              child: const Text('加入'),
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
                              if (_data.ok) _summaryCard(),
                              if (!_data.ok) _errorCard(),
                              const SizedBox(height: 12),
                              if (_data.note.isNotEmpty) _noteCard(),
                              const SizedBox(height: 12),
                              for (final cat in RecommendationsService.categoryOrder)
                                _categorySection(cat),
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
            IconButton(
              iconSize: 30,
              onPressed: () => Navigator.of(context).maybePop(),
              icon: const Icon(Icons.arrow_back_rounded),
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('建議記錄',
                      style: TextStyle(
                          fontSize: 21, fontWeight: FontWeight.w900, color: cInk)),
                  Text('助手精選池・你也能加本機觀察',
                      style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                ],
              ),
            ),
            IconButton(
              tooltip: '加我的觀察',
              onPressed: _addMine,
              icon: const Icon(Icons.add_circle_outline_rounded),
            ),
          ],
        ),
      );

  Widget _summaryCard() => SectionCard(
        title: '目前狀態',
        icon: Icons.lightbulb_outline_rounded,
        subtitle: '依現價 vs 助手設定的買區／減碼區自動判定',
        child: Row(
          children: [
            Expanded(
              child: _statBox('可建倉', '$_buyCount 檔',
                  _buyCount > 0 ? AppColors.safe : cInkSoft),
            ),
            Expanded(
              child: _statBox('觀察中',
                  '${_merged.where((e) => e.tone == 'watch' && !e.isUser).length} 檔', AppColors.gold),
            ),
            Expanded(
              child: _statBox('減碼觀察',
                  '${_merged.where((e) => e.tone == 'trim' && !e.isUser).length} 檔', AppColors.danger),
            ),
          ],
        ),
      );

  Widget _statBox(String label, String value, Color color) => Container(
        padding: const EdgeInsets.all(10),
        margin: const EdgeInsets.only(right: 8),
        decoration: BoxDecoration(
          color: color.withOpacity(0.10),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.35)),
        ),
        child: Column(
          children: [
            Text(value,
                style: TextStyle(
                    fontSize: 20, fontWeight: FontWeight.w900, color: color)),
            const SizedBox(height: 2),
            Text(label,
                style: TextStyle(fontSize: 12, color: cInkSoft)),
          ],
        ),
      );

  Widget _errorCard() => SectionCard(
        title: '尚無建議資料',
        icon: Icons.info_outlined,
        child: Text('目前讀取不到建議池（assets/data/recommendations.json）。'
            '請稍後重開，或確認網站已更新到 v2.5。',
            style: TextStyle(fontSize: 14, height: 1.6, color: cInkSoft)),
      );

  Widget _noteCard() => SectionCard(
        title: '關於這個池',
        icon: Icons.menu_book_rounded,
        subtitle: '精選更新：${_data.updatedAt}・行情日期：${_data.generatedAt}',
        child: Text(_data.note,
            style: TextStyle(fontSize: 13.5, height: 1.65, color: cInkSoft)),
      );

  Widget _categorySection(String cat) {
    final list = RecommendationsService.byCategory(_merged, cat);
    if (list.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: SectionCard(
        title: cat,
        icon: _catIcon(cat),
        subtitle: cat == '我的觀察'
            ? '你本機新增，不上傳、不影響精選池'
            : '助手維護',
        child: Column(
          children: [
            for (final it in list)
              _recTile(it),
          ],
        ),
      ),
    );
  }

  IconData _catIcon(String cat) {
    switch (cat) {
      case '防禦核心':
        return Icons.shield_outlined;
      case '高股息ETF':
        return Icons.account_balance_rounded;
      case '逆向收息':
        return Icons.trending_up_rounded;
      case '衛星觀察':
        return Icons.radar_outlined;
      default:
        return Icons.visibility_outlined;
    }
  }

  Widget _recTile(RecItem it) {
    final sc = _statusColor(it.tone);
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: cLine),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () {
          if (MarketRepository.instance.series(it.id) != null) {
            Navigator.of(context).push(MaterialPageRoute(
              builder: (_) => StockProfilePage(stockId: it.id),
            ));
          }
        },
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
                              fontSize: 16, fontWeight: FontWeight.w900, color: cInk)),
                      const SizedBox(height: 3),
                      Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        children: [
                          _chip(it.industry, cInkSoft),
                          _chip(it.category, AppColors.primary),
                          if (it.risk.isNotEmpty)
                            _chip('風險 $riskLabel(it.risk)', _riskColor(it.risk)),
                        ],
                      ),
                    ],
                  ),
                ),
                _statusBadge(it.status, sc),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                _kv('現價', it.close > 0 ? it.close.toStringAsFixed(2) : '—'),
                if (it.buyHigh > 0)
                  _kv('買區', '${it.buyLow.toStringAsFixed(0)}–${it.buyHigh.toStringAsFixed(0)}'),
                if (it.trimLow > 0)
                  _kv('減碼區', '${it.trimLow.toStringAsFixed(0)}–${it.trimHigh.toStringAsFixed(0)}'),
                if (it.gapPct != 0)
                  _kv('偏離', signedPct(it.gapPct)),
              ],
            ),
            if (it.thesis.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(it.thesis,
                  style: TextStyle(fontSize: 13, height: 1.6, color: cInkSoft)),
            ],
            if (it.riskNote.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text('風險：${it.riskNote}',
                  style: TextStyle(fontSize: 12, height: 1.55, color: AppColors.danger)),
            ],
            if (it.note.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text('備註：${it.note}',
                  style: TextStyle(fontSize: 12, height: 1.55, color: cInkSoft)),
            ],
            if (it.isUser) ...[
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () {
                      UserRec? u;
                      for (final x in UserRecStore.all) {
                        if (x.id == it.id) {
                          u = x;
                          break;
                        }
                      }
                      if (u != null) _removeMine(u);
                    },
                    child: Text('刪除', style: TextStyle(color: AppColors.danger)),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  String riskLabel(String r) => r;

  Widget _chip(String text, Color color) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: color.withOpacity(0.12),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: color.withOpacity(0.4)),
        ),
        child: Text(text,
            style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: color)),
      );

  Widget _statusBadge(String label, Color color) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: color.withOpacity(0.14),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: color, width: 1.4),
        ),
        child: Text(label,
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w900, color: color)),
      );

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

  Color _statusColor(String tone) {
    switch (tone) {
      case 'buy':
        return AppColors.safe;
      case 'trim':
        return AppColors.danger;
      case 'watch':
        return AppColors.gold;
      default:
        return cInkSoft;
    }
  }

  Color _riskColor(String r) {
    switch (r) {
      case '低':
        return AppColors.safe;
      case '高':
        return AppColors.danger;
      default:
        return AppColors.gold;
    }
  }
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
  final String thesis;
  final String note;
  final double target;
  const _AddResult({
    required this.id,
    required this.name,
    required this.industry,
    required this.thesis,
    required this.note,
    required this.target,
  });
}
