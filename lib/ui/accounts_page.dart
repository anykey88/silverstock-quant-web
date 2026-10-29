// ============================================================================
// 投資帳戶管理（多本帳冊）
// ----------------------------------------------------------------------------
// 這一頁解決的是「記帳」而不是「下單」：
//   · 家裡有幾本帳？各自多少錢？合起來多少？
//   · 哪一本結構最脆弱？（組合風險體檢）
//   · 匯出一份給家人核對，或匯出全部做年度檢討
//
// 刻意不做的事：不串接券商、不自動抓對帳單、不同步雲端。
// 一來台股券商 API 不對個人開放，二來家人的持股不該離開這台裝置。
// ============================================================================

import 'package:flutter/material.dart';

import '../core/formatters.dart';
import '../data/market_repository.dart';
import '../services/account_export.dart';
import '../services/accounts.dart';
import '../services/daily_picks.dart';
import '../ui/paper_page.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';
import '../v2/portfolio_risk.dart';

class AccountsPage extends StatefulWidget {
  const AccountsPage({Key? key}) : super(key: key);

  @override
  State<AccountsPage> createState() => _AccountsPageState();
}

class _AccountsPageState extends State<AccountsPage> {
  bool _loading = true;
  AccountBook _book = AccountBook.empty();
  DailyPicks? _picks;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    await MarketRepository.instance.ensureLoaded();
    final picks = await DailyPicks.load();
    if (!mounted) return;
    setState(() {
      _book = AccountStore.load(force: true);
      _picks = picks;
      _loading = false;
    });
  }

  void _refresh() {
    setState(() => _book = AccountStore.load());
  }

  // ------------------------------------------------------------------ 資料
  double _priceOf(String id) {
    final s = MarketRepository.instance.series(id);
    if (s != null && s.closes.isNotEmpty) return s.closes.last;
    for (final p in _picks?.all ?? const <PickItem>[]) {
      if (p.id == id && p.close > 0) return p.close;
    }
    return 0;
  }

  StockMeta? _metaOf(String id) {
    for (final p in _picks?.all ?? const <PickItem>[]) {
      if (p.id == id) {
        return StockMeta(
          id: p.id,
          name: p.name,
          industry: p.industry,
          close: _priceOf(id) > 0 ? _priceOf(id) : p.close,
          perPctile: p.perPct ?? 50,
          yieldPct: p.yieldPct ?? 0,
          high52: p.high52 ?? 0,
          low52: p.low52 ?? 0,
          trimScore: p.trimScore,
        );
      }
    }
    final s = MarketRepository.instance.series(id);
    if (s != null) {
      return StockMeta(
        id: id,
        name: s.name,
        industry: s.industry,
        close: s.closes.isEmpty ? 0 : s.closes.last,
      );
    }
    return null;
  }

  PortfolioRisk _riskOf(InvestAccount a) {
    final pos = <String, HoldingInput>{};
    a.positions.forEach((k, v) {
      pos[k] = HoldingInput(v.shares, v.avgCost);
    });
    return PortfolioRiskEngine.build(
      positions: pos,
      cash: a.cash,
      metaOf: _metaOf,
    );
  }

  // ------------------------------------------------------------------ 操作
  Future<void> _create() async {
    final r = await _showEditor(
      title: '新增帳戶',
      name: '',
      kind: AccountKind.paper,
      capital: 1000000,
      broker: '',
      note: '',
    );
    if (r == null) return;
    AccountStore.add(
      name: r.name,
      kind: r.kind,
      capital: r.capital,
      broker: r.broker,
      note: r.note,
    );
    _refresh();
    _snack('已建立「${r.name}」');
  }

  Future<void> _edit(InvestAccount a) async {
    final r = await _showEditor(
      title: '編輯帳戶',
      name: a.name,
      kind: a.kind,
      capital: a.initialCapital,
      broker: a.broker,
      note: a.note,
      lockCapital: a.trades.isNotEmpty || a.positions.isNotEmpty,
    );
    if (r == null) return;
    AccountStore.rename(a.id, r.name, broker: r.broker, note: r.note);
    _refresh();
    _snack('已更新');
  }

  /// 選定這本帳並直接進去記帳／模擬下單
  Future<void> _open(InvestAccount a) async {
    AccountStore.select(a.id);
    _refresh();
    await Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => const PaperPage()),
    );
    if (!mounted) return;
    _refresh();
  }

  Future<void> _remove(InvestAccount a) async {
    if (_book.accounts.length <= 1) {
      _snack('至少要保留一本帳戶');
      return;
    }
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('刪除「${a.name}」？'),
        content: Text('這本帳戶的 ${a.holdingCount} 檔持倉與 ${a.trades.length} 筆紀錄會一起刪掉，無法復原。\n'
            '建議先匯出一份再刪。'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('取消')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('仍要刪除')),
        ],
      ),
    );
    if (ok != true) return;
    AccountStore.remove(a.id);
    _refresh();
    _snack('已刪除');
  }

  void _exportOne(InvestAccount a) {
    if (a.trades.isEmpty && a.positions.isEmpty) {
      _snack('「${a.name}」還沒有任何紀錄，匯出會是空表');
    }
    final csv = AccountExport.one(a, _priceOf);
    AccountExport.download(
        'SilverStock_${AccountExport.safeName(a.name)}_${_dateTag()}.csv', csv);
    _snack('已匯出「${a.name}」');
  }

  void _exportAll() {
    final csv = AccountExport.all(_book, _priceOf);
    AccountExport.download('SilverStock_帳戶總覽_${_dateTag()}.csv', csv);
    _snack('已匯出 ${_book.accounts.length} 本帳戶');
  }

  String _dateTag() {
    final t = DateTime.now();
    String two(int v) => v < 10 ? '0$v' : '$v';
    return '${t.year}${two(t.month)}${two(t.day)}';
  }

  void _snack(String s) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(s), duration: const Duration(seconds: 2)));
  }

  // ------------------------------------------------------------------ 畫面
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
                              _riskCard(),
                              const SizedBox(height: 12),
                              _listCard(),
                              const SizedBox(height: 12),
                              _howToCard(),
                              const SizedBox(height: 8),
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
                  Text('投資帳戶',
                      style: TextStyle(
                          fontSize: 21, fontWeight: FontWeight.w900, color: cInk)),
                  Text('家人的、自己的、練習的——分開記，才看得清',
                      style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                ],
              ),
            ),
            IconButton(
              tooltip: '匯出全部帳戶',
              onPressed: _exportAll,
              icon: const Icon(Icons.file_download_outlined),
            ),
            IconButton(
              tooltip: '新增帳戶',
              onPressed: _create,
              icon: const Icon(Icons.add_circle_outline_rounded),
            ),
          ],
        ),
      );

  Widget _summaryCard() {
    final eq = _book.totalEquity(_priceOf);
    final cap = _book.totalCapital;
    final pct = cap > 0 ? (eq - cap) / cap * 100 : 0.0;
    return SectionCard(
      title: '全部帳戶合計',
      icon: Icons.account_balance_wallet_rounded,
      subtitle: '${_book.accounts.length} 本帳戶・本金合計 ${money(cap)}',
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
                  label: '合計權益',
                  value: money(eq),
                  note: '現金＋持倉市值',
                  color: cInk,
                  big: true,
                )),
            SizedBox(
                width: w,
                child: MetricTile(
                  label: '合計報酬率',
                  value: signedPct(pct),
                  note: '損益 ${money(eq - cap)}',
                  color: pct > 0
                      ? AppColors.up
                      : (pct < 0 ? AppColors.down : cInkSoft),
                )),
            SizedBox(
                width: w,
                child: MetricTile(
                  label: '持倉總檔數',
                  value: '${_book.accounts.fold<int>(0, (a, x) => a + x.holdingCount)} 檔',
                  note: '跨帳戶不重複計算市值',
                  color: AppColors.primary,
                )),
          ],
        );
      }),
    );
  }

  Widget _riskCard() {
    final a = _book.active;
    if (a == null) return const SizedBox.shrink();
    final risk = _riskOf(a);
    final color = risk.score >= 70
        ? AppColors.down
        : risk.score >= 50
            ? const Color(0xFFB26A00)
            : AppColors.up;
    return SectionCard(
      title: '組合風險體檢・${a.name}',
      icon: Icons.shield_outlined,
      subtitle: '只看結構，不預測漲跌、不給買賣點',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                width: 74,
                height: 74,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: color.withOpacity(0.10),
                  border: Border.all(color: color.withOpacity(0.45), width: 2),
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text('${risk.score}',
                        style: TextStyle(
                            fontSize: 24, fontWeight: FontWeight.w900, color: color)),
                    Text('脆弱度', style: TextStyle(fontSize: 10.5, color: cInkSoft)),
                  ],
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(risk.level,
                        style: TextStyle(
                            fontSize: 17, fontWeight: FontWeight.w900, color: cInk)),
                    const SizedBox(height: 3),
                    Text('分數越高，代表這一籃股票越依賴少數幾個假設。'
                        '分數低不等於會賺錢，只代表「出錯時不會一次全錯」。',
                        style: TextStyle(fontSize: 12, color: cInkSoft, height: 1.45)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          LayoutBuilder(builder: (ctx, c) {
            final perRow = c.maxWidth > 620 ? 4 : 2;
            final w = (c.maxWidth - (perRow - 1) * 8) / perRow;
            return Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final m in risk.metrics)
                  SizedBox(
                    width: w,
                    child: Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: cInk.withOpacity(0.035),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: cInk.withOpacity(0.07)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                width: 6,
                                height: 6,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: m.tone == RiskTone.good
                                      ? AppColors.up
                                      : m.tone == RiskTone.watch
                                          ? const Color(0xFFB26A00)
                                          : AppColors.down,
                                ),
                              ),
                              const SizedBox(width: 5),
                              Expanded(
                                child: Text(m.label,
                                    style: TextStyle(
                                        fontSize: 11.5, color: cInkSoft),
                                    overflow: TextOverflow.ellipsis),
                              ),
                            ],
                          ),
                          const SizedBox(height: 3),
                          Text(m.value,
                              style: TextStyle(
                                  fontSize: 15.5,
                                  fontWeight: FontWeight.w900,
                                  color: cInk)),
                          const SizedBox(height: 2),
                          Text(m.hint,
                              style: TextStyle(
                                  fontSize: 10.5, color: cInkSoft, height: 1.35)),
                        ],
                      ),
                    ),
                  ),
              ],
            );
          }),
          if (risk.actions.isNotEmpty) ...[
            const SizedBox(height: 14),
            Text('看完這三個數字，可以做的事',
                style: TextStyle(
                    fontSize: 13, fontWeight: FontWeight.w800, color: cInk)),
            const SizedBox(height: 6),
            for (var i = 0; i < risk.actions.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${i + 1}. ',
                        style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w900,
                            color: AppColors.primary)),
                    Expanded(
                      child: Text(risk.actions[i],
                          style: TextStyle(fontSize: 13, height: 1.55, color: cInk)),
                    ),
                  ],
                ),
              ),
          ],
          if (risk.blindSpots.isNotEmpty) ...[
            const SizedBox(height: 4),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF6E5),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('以下部位資料不足，未納入計算',
                      style: TextStyle(
                          fontSize: 12, fontWeight: FontWeight.w800, color: cInk)),
                  const SizedBox(height: 4),
                  for (final s in risk.blindSpots.take(5))
                    Text('・$s',
                        style: TextStyle(fontSize: 11.5, color: cInkSoft, height: 1.5)),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _listCard() {
    return SectionCard(
      title: '帳戶清單（${_book.accounts.length}）',
      icon: Icons.folder_shared_outlined,
      subtitle: '點「使用」進入該本記帳；「匯出」可單獨給家人核對',
      child: Column(
        children: [
          for (final a in _book.accounts) _acctTile(a),
          const SizedBox(height: 4),
          OutlinedButton.icon(
            onPressed: _create,
            icon: const Icon(Icons.add_rounded, size: 18),
            label: const Text('新增一本帳戶'),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size(double.infinity, 44),
              primary: AppColors.primary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _acctTile(InvestAccount a) {
    final isReal = a.kind == AccountKind.real;
    final active = a.id == _book.active?.id;
    final eq = a.equity(_priceOf);
    final pct = a.returnPct(_priceOf);
    final base = isReal ? AppColors.primary : cInkSoft;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.fromLTRB(12, 11, 10, 8),
      decoration: BoxDecoration(
        color: active ? base.withOpacity(0.055) : Colors.transparent,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
            color: active ? base.withOpacity(0.55) : cInk.withOpacity(0.10),
            width: active ? 1.6 : 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(isReal ? Icons.account_balance_rounded : Icons.school_rounded,
                  size: 17, color: base),
              const SizedBox(width: 7),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(a.title,
                              style: TextStyle(
                                  fontSize: 15.5,
                                  fontWeight: FontWeight.w900,
                                  color: cInk),
                              overflow: TextOverflow.ellipsis),
                        ),
                        const SizedBox(width: 6),
                        if (active)
                          Container(
                            padding:
                                const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                            decoration: BoxDecoration(
                                color: base, borderRadius: BorderRadius.circular(5)),
                            child: const Text('目前',
                                style: TextStyle(
                                    fontSize: 9.5,
                                    color: Colors.white,
                                    fontWeight: FontWeight.w800)),
                          ),
                      ],
                    ),
                    Text(
                        '${a.kind.label}・持倉 ${a.holdingCount} 檔・${a.trades.length} 筆紀錄',
                        style: TextStyle(fontSize: 11.5, color: cInkSoft)),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(money(eq),
                      style: TextStyle(
                          fontSize: 15, fontWeight: FontWeight.w900, color: cInk)),
                  Text(signedPct(pct),
                      style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                          color: pct > 0
                              ? AppColors.up
                              : (pct < 0 ? AppColors.down : cInkSoft))),
                ],
              ),
            ],
          ),
          if (a.note.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(a.note,
                  style: TextStyle(fontSize: 11.5, color: cInkSoft, height: 1.4)),
            ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 2,
            children: [
              _mini(active ? '去記帳' : '使用', Icons.play_arrow_rounded, () => _open(a)),
              _mini('編輯', Icons.edit_outlined, () => _edit(a)),
              _mini('匯出', Icons.file_download_outlined, () => _exportOne(a)),
              _mini('刪除', Icons.delete_outline_rounded, () => _remove(a),
                  danger: true),
            ],
          ),
        ],
      ),
    );
  }

  Widget _mini(String label, IconData icon, VoidCallback onTap,
      {bool danger = false}) {
    final col = danger ? AppColors.down : cInkSoft;
    return TextButton.icon(
      onPressed: onTap,
      icon: Icon(icon, size: 15, color: col),
      label: Text(label, style: TextStyle(fontSize: 12, color: col)),
      style: TextButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        minimumSize: Size.zero,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
      ),
    );
  }

  Widget _howToCard() {
    return SectionCard(
      title: '怎麼用這幾本帳',
      icon: Icons.lightbulb_outline_rounded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _tip('1', '真實帳戶＝記帳，不是下單',
              '你在券商做完交易，回頭把成交價與股數記進來。系統不會、也不能幫你下單，但可以幫你算出「這筆到底賺賠多少」與「佔比有沒有失控」。'),
          _tip('2', '練習帳戶＝讓策略先死一次',
              '同一套規則先跑三個月虛擬單，再決定要不要投真錢。練習帳戶虧 30% 你不會痛，真帳戶會。'),
          _tip('3', '家人帳戶分開的理由',
              '父母的錢要的是現金流與保本，你的錢可能想拚成長。混在一起算報酬率，會得到一個誰都不滿意的數字。分開之後，每本帳的「合理期望」才說得清楚。'),
          _tip('4', '匯出格式',
              'CSV（UTF-8 含 BOM），Excel 與 Google Sheets 直接開，中文不會亂碼。單本匯出只有該本明細，全部匯出會先給一張總覽表。檔案在你電腦上產生，不經過任何伺服器。'),
        ],
      ),
    );
  }

  Widget _tip(String no, String title, String body) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 11),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 20,
            height: 20,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.12),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(no,
                style: TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w900,
                    color: AppColors.primary)),
          ),
          const SizedBox(width: 9),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: TextStyle(
                        fontSize: 13.5, fontWeight: FontWeight.w800, color: cInk)),
                const SizedBox(height: 2),
                Text(body,
                    style: TextStyle(fontSize: 12.5, height: 1.55, color: cInkSoft)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ------------------------------------------------------------------ 編輯器
  Future<_EditResult?> _showEditor({
    required String title,
    required String name,
    required AccountKind kind,
    required double capital,
    required String broker,
    required String note,
    bool lockCapital = false,
  }) {
    final nameCtrl = TextEditingController(text: name);
    final brokerCtrl = TextEditingController(text: broker);
    final noteCtrl = TextEditingController(text: note);
    final capCtrl = TextEditingController(text: capital.toStringAsFixed(0));
    var k = kind;
    var err = '';

    return showDialog<_EditResult>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSt) => AlertDialog(
          title: Text(title),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: nameCtrl,
                  autofocus: true,
                  decoration: const InputDecoration(
                    labelText: '帳戶名稱',
                    hintText: '例如：爸爸、老婆、我自己、練習一號',
                  ),
                  textInputAction: TextInputAction.next,
                ),
                const SizedBox(height: 12),
                Text('帳戶性質', style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 8,
                  children: [
                    ChoiceChip(
                      label: const Text('真實帳戶'),
                      selected: k == AccountKind.real,
                      selectedColor: AppColors.primary.withOpacity(0.16),
                      onSelected: (_) => setSt(() => k = AccountKind.real),
                    ),
                    ChoiceChip(
                      label: const Text('模擬練習'),
                      selected: k == AccountKind.paper,
                      selectedColor: AppColors.primary.withOpacity(0.16),
                      onSelected: (_) => setSt(() => k = AccountKind.paper),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                    k == AccountKind.real
                        ? '記錄你在券商實際成交的買賣，用來算真實報酬與佔比。'
                        : '虛擬資金，用來驗證策略。虧光也不影響真實資產。',
                    style: TextStyle(fontSize: 11.5, color: cInkSoft, height: 1.4)),
                const SizedBox(height: 12),
                TextField(
                  controller: capCtrl,
                  enabled: !lockCapital,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                    labelText: '本金（TWD）',
                    helperText: lockCapital ? '已有交易紀錄，本金不可修改' : null,
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: brokerCtrl,
                  decoration: const InputDecoration(
                    labelText: '券商（選填）',
                    hintText: '例如：元大、玉山、富邦',
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: noteCtrl,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    labelText: '備註（選填）',
                    hintText: '例如：媽媽的退休金，只買金融股與電信',
                  ),
                ),
                if (err.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(err,
                        style: TextStyle(fontSize: 12, color: AppColors.down)),
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
                final n = nameCtrl.text.trim();
                if (n.isEmpty) {
                  setSt(() => err = '請填帳戶名稱');
                  return;
                }
                final cap = double.tryParse(capCtrl.text.trim()) ?? capital;
                Navigator.of(ctx).pop(_EditResult(
                  name: n,
                  kind: k,
                  capital: cap < 0 ? 0 : cap,
                  broker: brokerCtrl.text,
                  note: noteCtrl.text,
                ));
              },
              child: const Text('儲存'),
            ),
          ],
        ),
      ),
    );
  }
}

class _EditResult {
  final String name;
  final AccountKind kind;
  final double capital;
  final String broker;
  final String note;
  const _EditResult({
    required this.name,
    required this.kind,
    required this.capital,
    required this.broker,
    required this.note,
  });
}
