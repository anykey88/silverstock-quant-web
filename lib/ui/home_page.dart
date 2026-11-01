// 首頁：適老化大字介面（iPad mini 8.3 吋 Safari 優先適配）
// ignore_for_file: avoid_web_libraries_in_flutter
import 'dart:html' as html;
import 'dart:js_util' as jsu;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show Clipboard, ClipboardData;

import '../core/app_mode.dart';
import '../core/app_settings.dart';
import '../core/constants.dart';
import '../core/formatters.dart';
import '../data/market_repository.dart';
import '../models/trade_strategy.dart';
import '../services/report_store.dart';
import '../services/speech_service.dart';
import '../services/remote_stock_service.dart';
import '../services/stock_index.dart';
import '../services/watchlist.dart';
import '../services/strategy_store.dart';
import '../agents/agents.dart';
import 'accounts_page.dart';
import 'daily_picks_page.dart';
import 'holdings_page.dart';
import 'learn_page.dart';
import 'market_page.dart';
import 'paper_page.dart';
import 'recommendations_page.dart';
import 'result_page.dart';
import 'screener_page.dart';
import 'stock_profile_page.dart';
import 'strategy_editor_page.dart';
import 'strategy_page.dart';
import 'theme.dart';
import 'trade_result_page.dart';
import 'widgets.dart';

class HomePage extends StatefulWidget {
  const HomePage({Key? key}) : super(key: key);

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  bool _ready = false;
  String _stockId = '2330';
  int _years = 5;
  String _strategyId = 'yield_dca';
  final TextEditingController _codeCtrl = TextEditingController();
  final TextEditingController _queryCtrl = TextEditingController();
  List<SavedReport> _saved = <SavedReport>[];
  bool _autoRun = false;
  // 個人自用版專屬
  String _runType = 'stock'; // stock = 存股累積回測 / trade = 交易策略回測
  String _tradeStrategyId = 'preset_value';
  String? _deepView; // screener / strategies / trade
  bool _fetchingStock = false;
  List<WatchItem> _watchItems = <WatchItem>[];

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    await MarketRepository.instance.ensureLoaded();
    // 名稱索引（3171 檔）與自選股清單一起備好，之後搜尋零延遲
    await StockIndex.instance.ensureLoaded();
    if (!mounted) return;
    _applyDeepLink();
    setState(() {
      _ready = true;
      _saved = ReportStore.list();
      _watchItems = WatchList.all;
      // 第一次使用：把內建 33 檔全部放進自選，避免空清單讓人不知道從哪開始。
      // 先放常用那幾檔，其餘依序補上。
      if (_watchItems.isEmpty) {
        for (final id in kQuickPickIds) {
          final s0 = MarketRepository.instance.series(id);
          if (s0 != null) WatchList.addLast(id, s0.name, industry: s0.industry);
        }
        for (final s0 in MarketRepository.instance.all) {
          WatchList.addLast(s0.id, s0.name, industry: s0.industry);
        }
        _watchItems = WatchList.all;
      }
    });
    // 深連結可直接開啟某一份回測結果（方便分享與評審快速體驗）
    if (_autoRun) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _run();
      });
    }
    if (_deepView != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _openDeepView(_deepView!);
      });
    }
  }

  /// 支援網址參數：
  /// ?stock=2330&strategy=yield_dca&years=5&run=1&scale=1&contrast=0
  void _applyDeepLink() {
    try {
      // Flutter Web 預設使用 hash 路由，且啟動時會改寫網址；
      // 因此優先讀取 index.html 在啟動前保存下來的原始查詢字串。
      var q = Uri.base.queryParameters;
      String? boot;
      try {
        boot = jsu
            .getProperty<Object?>(html.window, '__SSQ_BOOT_QUERY__')
            ?.toString();
      } catch (_) {}
      final raw = (boot != null && boot.contains('?')) ? boot : Uri.base.toString();
      final qi = raw.indexOf('?');
      if (qi >= 0) {
        q = Uri.parse(raw.substring(qi).replaceAll('#', '')).queryParameters;
      }
      final stock = q['stock'];
      if (stock != null && MarketRepository.instance.series(stock) != null) {
        _stockId = stock;
      }
      final strategy = q['strategy'];
      if (strategy != null && kStrategies.any((e) => e.id == strategy)) {
        _strategyId = strategy;
      }
      final y = int.tryParse(q['years'] ?? '');
      if (y != null) _years = y.clamp(1, 6);
      final sc = int.tryParse(q['scale'] ?? '');
      if (sc != null) AppSettings.instance.setFontIndex(sc);
      final c = q['contrast'];
      if (c != null) AppSettings.instance.setHighContrast(c == '1');
      _autoRun = q['run'] == '1';
      _deepView = q['view'];
      final ts = q['tstrategy'];
      if (ts != null && StrategyStore.byId(ts) != null) _tradeStrategyId = ts;
    } catch (_) {}
  }

  @override
  void dispose() {
    _codeCtrl.dispose();
    _queryCtrl.dispose();
    super.dispose();
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg),
      duration: const Duration(seconds: 3),
    ));
  }

  Future<void> _applyQuery(String text) async {
    final r = QueryParser.parse(text);
    if (r.riskIntent) {
      await _showBlocked(r.riskReason);
      return;
    }
    var changed = false;
    if (r.stockId != null && MarketRepository.instance.series(r.stockId!) != null) {
      _stockId = r.stockId!;
      changed = true;
    }
    if (r.strategyId != null) {
      _strategyId = r.strategyId!;
      changed = true;
    }
    if (r.years != null) {
      _years = r.years!;
      changed = true;
    }
    setState(() {});
    if (changed) {
      _snack('已為您套用：${_stockName(_stockId)}・$_years 年・${strategyById(_strategyId).name}');
    } else {
      _snack('沒有聽清楚股票或策略，請直接點選下面的按鈕，或用文字輸入。');
    }
  }

  String _stockName(String id) {
    final s = MarketRepository.instance.series(id);
    return s == null ? id : '${s.name}（$id）';
  }

  void _openDeepView(String view) {
    switch (view) {
      case 'screener':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const ScreenerPage()),
        );
        break;
      case 'strategies':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const StrategyListPage()),
        );
        break;
      case 'market':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const MarketPage()),
        );
        break;
      case 'paper':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => PaperPage(presetStockId: _stockId)),
        );
        break;
      case 'learn':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const LearnPage()),
        );
        break;
      case 'daily':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const DailyPicksPage()),
        );
        break;
      case 'accounts':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const AccountsPage()),
        );
        break;
      case 'holdings':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const HoldingsPage()),
        );
        break;
      case 'recommendations':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const RecommendationsPage()),
        );
        break;
      case 'stock':
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => StockProfilePage(stockId: _stockId)),
        );
        break;
      case 'trade':
        final all = StrategyStore.all();
        final st = StrategyStore.byId(_tradeStrategyId) ??
            (all.isNotEmpty ? all.first : TradeStrategyPresets.build().first);
        Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => TradeResultPage(
            stockId: _stockId,
            strategy: st,
            years: _years,
          ),
        ));
        break;
    }
  }

  Future<void> _showBlocked(String reason) async {
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(
          children: const [
            Icon(Icons.gpp_bad_rounded, color: AppColors.danger, size: 28),
            SizedBox(width: 8),
            Expanded(
              child: Text('這個組合沒有通過檢查',
                  style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
            ),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(reason, style: const TextStyle(fontSize: 16, height: 1.6)),
              const SizedBox(height: 14),
              const InlineDisclaimer(),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
  }

  Future<void> _startVoice() async {
    if (!SpeechInputService.supported) {
      _snack('此瀏覽器不支援語音輸入，請改用下方文字輸入。');
      return;
    }
    final text = await showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (_) => const _VoiceDialog(),
    );
    if (text != null && text.trim().isNotEmpty) {
      await _applyQuery(text);
    }
  }

  void _run() {
    final series = MarketRepository.instance.series(_stockId);
    if (series == null) {
      _snack('請從上方清單選擇標的，或直接輸入代號。');
      return;
    }
    // 個人自用版：可切到「交易策略回測」（含停利停損、手續費、證交稅）
    if (AppModeController.instance.isPersonal && _runType == 'trade') {
      final st = StrategyStore.byId(_tradeStrategyId) ??
          (StrategyStore.all().isNotEmpty
              ? StrategyStore.all().first
              : TradeStrategyPresets.build().first);
      Navigator.of(context).push(MaterialPageRoute<bool>(
        builder: (_) => TradeResultPage(
          stockId: _stockId,
          strategy: st,
          years: _years,
        ),
      ));
      return;
    }
    Navigator.of(context)
        .push(MaterialPageRoute<bool>(
          builder: (_) => ResultPage(
            stockId: _stockId,
            strategyId: _strategyId,
            years: _years,
          ),
        ))
        .then((_) {
      if (mounted) setState(() => _saved = ReportStore.list());
    });
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: AppModeController.instance,
      builder: (context, _) => _buildScaffold(context),
    );
  }

  Widget _buildScaffold(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            Expanded(
              child: !_ready
                  ? const Center(child: CircularProgressIndicator())
                  : SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(14, 14, 14, 40),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 880),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              _header(),
                              const SizedBox(height: 6),
                              if (AppModeController.instance.isPersonal)
                                _toolsCard(),
                              _pickStockCard(),
                              _conditionCard(),
                              _settingsCard(),
                              _historyCard(),
                              _glossaryCard(),
                              _footer(),
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

  Widget _header() {
    final personal = AppModeController.instance.isPersonal;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: cPrimary,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(Icons.savings_rounded,
                    color: isHighContrast ? Colors.black : Colors.white, size: 28),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      alignment: Alignment.centerLeft,
                      child: Text('SilverStock-Quant-Web',
                          maxLines: 1,
                          style: TextStyle(
                              fontSize: 25,
                              fontWeight: FontWeight.w900,
                              color: cInk,
                              height: 1.15)),
                    ),
                    Text('台股實戰工作站',
                        style: TextStyle(fontSize: 15, color: cInkSoft)),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              // 版本號固定於右上角
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                  color: isHighContrast
                      ? Colors.black
                      : cPrimary.withOpacity(0.10),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: cPrimary.withOpacity(0.28)),
                ),
                child: Text(kAppVersion,
                    style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.3,
                        color: isHighContrast ? AppColors.hcPrimary : cPrimary)),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              const _Tag('繁體中文'),
              const _Tag('大字適老化'),
              const _Tag('iPad mini 優先'),
              const _Tag('選股＋交易回測'),
              const _Tag('本機儲存'),
            ],
          ),
          const SizedBox(height: 12),
          const NoticeBar(
            icon: Icons.trending_up_rounded,
            text: '每天：① 看「每日精選」的買進／減碼名單 → ② 用「市場觀察」確認大盤溫度 → '
                '③ 進「投資帳戶」看組合風險。個股買賣點用「回測設定」跑策略驗證進出場條件。',
          ),
        ],
      ),
    );
  }

  /// 個人自用版工具入口
  Widget _toolsCard() {
    final strategyCount = StrategyStore.count();
    return SectionCard(
      title: '交易工具',
      icon: Icons.workspace_premium_rounded,
      subtitle: '選股、價位、時機、部位——四個環節各自有工具。',
      child: Column(
        children: [
          ActionButton(
            label: '每日精選（買進／減碼觀察）',
            sub: '每天收盤後掃描候選池・附估值合理區與觸發條件',
            icon: Icons.auto_awesome_rounded,
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const DailyPicksPage()),
            ),
          ),
          const SizedBox(height: 10),
          ActionButton(
            label: '市場觀察',
            sub: '大盤溫度・產業溫度・歷史條件機率',
            icon: Icons.public_rounded,
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const MarketPage()),
            ),
          ),
          const SizedBox(height: 10),
          ActionButton(
            label: '選股篩選與建議',
            sub: '${MarketRepository.instance.all.length} 檔標的・殖利率／評價／配息／成長／風險打分',
            icon: Icons.filter_alt_rounded,
            primary: false,
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const ScreenerPage()),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: ActionButton(
                  label: '我的交易策略',
                  sub: '$strategyCount 組',
                  icon: Icons.tune_rounded,
                  primary: false,
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const StrategyListPage()),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ActionButton(
                  label: '投資帳戶',
                  sub: '多本帳・記帳與練習',
                  icon: Icons.account_balance_wallet_rounded,
                  primary: false,
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const AccountsPage()),
                  ),
                ),
              ),
            ],
          ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: ActionButton(
                      label: '學習路徑',
                      sub: '8 堂課・做中學',
                      icon: Icons.school_rounded,
                      primary: false,
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const LearnPage()),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: ActionButton(
                      label: '新增策略',
                      icon: Icons.add_rounded,
                      primary: false,
                      onPressed: () async {
                        final r = await Navigator.of(context).push<TradeStrategy>(
                          MaterialPageRoute(
                              builder: (_) => const StrategyEditorPage(origin: null)),
                        );
                        if (r != null) setState(() {});
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: ActionButton(
                      label: '我的持股',
                      sub: '股數＋買進價・看損益佔比',
                      icon: Icons.pie_chart_rounded,
                      primary: false,
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const HoldingsPage()),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: ActionButton(
                      label: '建議記錄',
                      sub: '助手精選池＋我的觀察',
                      icon: Icons.lightbulb_outline_rounded,
                      primary: false,
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(
                            builder: (_) => const RecommendationsPage()),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      }

  Widget _pickStockCard() {
    final series = MarketRepository.instance.series(_stockId);
    final watch = _watchItems;
    final total = StockIndex.instance.count;
    return SectionCard(
      title: '① 選一檔想看的股票',
      icon: Icons.search_rounded,
      trailing: TextButton.icon(
        onPressed: _pickFromAll,
        icon: const Icon(Icons.list_rounded, size: 20),
        label: Text(total > 0 ? '全部 $total 檔' : '全部標的'),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.star_rounded, size: 18, color: AppColors.gold),
              const SizedBox(width: 6),
              Text('我的自選股 ${watch.length}',
                  style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      color: cInk)),
              const Spacer(),
              if (watch.isNotEmpty)
                TextButton(
                  onPressed: _manageWatchlist,
                  child: const Text('管理', style: TextStyle(fontSize: 13.5)),
                ),
            ],
          ),
          if (watch.isEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4, bottom: 2),
              child: Text(
                '自選股是空的。用下面的搜尋框輸入名稱或代號，選中後會自動加進來。',
                style: TextStyle(fontSize: 13.5, height: 1.6, color: cInkSoft),
              ),
            ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              for (final w in watch.take(18))
                ChoicePill(
                  label: w.name,
                  sub: w.id,
                  selected: _stockId == w.id,
                  onTap: () => _selectWatch(w),
                ),
              if (watch.length > 18)
                ActionChip(
                  label: Text('還有 ${watch.length - 18} 檔'),
                  onPressed: _manageWatchlist,
                ),
            ],
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _codeCtrl,
            keyboardType: TextInputType.text,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
            decoration: InputDecoration(
              labelText: '輸入股票代號或名稱',
              hintText: '例如 2330、台積、鴻海',
              helperText: StockIndex.instance.isLoaded
                  ? '全市場 ${StockIndex.instance.count} 檔・可只打名稱的一部分・支援簡體'
                  : '可只打名稱的一部分，例如「台積」',
              prefixIcon: const Icon(Icons.search_rounded),
            ),
            onSubmitted: (v) => _resolveStock(v),
          ),
          if (_fetchingStock)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Row(
                children: [
                  const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2.4),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text('正在向 FinMind 抓取歷史資料（約 10–20 秒，需要 4 次請求）…',
                        style: TextStyle(fontSize: 13, color: cInkSoft)),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 10),
          Text(
            series == null
                ? '目前選擇：—'
                : '目前選擇：${series.name}（${series.id}）・${series.industry}'
                    '・資料 ${series.firstDateText} ～ ${series.lastDateText}',
            style: TextStyle(fontSize: 14.5, color: cInkSoft, height: 1.5),
          ),
          if (series != null) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                TextButton.icon(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => StockProfilePage(stockId: series.id),
                    ),
                  ),
                  icon: const Icon(Icons.candlestick_chart_rounded, size: 20),
                  label: const Text('看個股檔案（走勢／量能／事件）'),
                ),
                if (AppModeController.instance.isPersonal)
                  TextButton.icon(
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(
                          builder: (_) => PaperPage(presetStockId: series.id)),
                    ),
                    icon: const Icon(Icons.shopping_cart_outlined, size: 20),
                    label: const Text('模擬下單'),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  /// 統一入口：可以輸入代號，也可以輸入名稱的任何片段。
  ///
  /// 判斷順序刻意這樣排：
  ///   1. 已經載入過的代號 → 直接選，零延遲
  ///   2. 長得像代號（4–6 位數字，可帶英文字尾）→ 走線上建檔
  ///   3. 其餘一律當名稱搜（支援簡體輸入）
  /// 這樣「2330」不會被當成名稱去搜，「台積」也不會被誤判成代號。
  Future<void> _resolveStock(String raw) async {
    final text = raw.trim();
    if (text.isEmpty) return;
    final upper = text.toUpperCase();

    final local = MarketRepository.instance.series(upper);
    if (local != null) {
      setState(() => _stockId = upper);
      _codeCtrl.clear();
      _noteWatched(upper, local.name, local.industry);
      _snack('已選擇 ${local.name}（${local.id}）'
          '${MarketRepository.instance.isBuiltIn(upper) ? '' : '・線上建立'}');
      return;
    }

    if (RegExp(r'^[0-9]{4,6}[A-Z]?$').hasMatch(upper)) {
      await _confirmAndBuild(upper, null);
      return;
    }

    // 當名稱搜
    await StockIndex.instance.ensureLoaded();
    final hits = StockIndex.instance.search(text, limit: 30);
    if (!mounted) return;
    if (hits.isEmpty) {
      _snack('找不到「$text」。可輸入 4 位數代號（例如 2330），或名稱的一部分（例如 台積、鴻海）。');
      return;
    }
    if (hits.length == 1) {
      await _selectBrief(hits.first);
      return;
    }
    final picked = await _showPicker(hits, text);
    if (picked != null && mounted) await _selectBrief(picked);
  }

  Future<void> _selectBrief(StockBrief b) async {
    if (MarketRepository.instance.series(b.id) != null) {
      setState(() => _stockId = b.id);
      _codeCtrl.clear();
      _noteWatched(b.id, b.name, b.industry);
      _snack('已選擇 ${b.name}（${b.id}）');
      return;
    }
    await _confirmAndBuild(b.id, b.name);
  }

  /// 選中即存入自選股（已存在就不重複）
  void _noteWatched(String id, String name, String industry) {
    if (WatchList.add(id, name, industry: industry)) {
      setState(() => _watchItems = WatchList.all);
    }
  }

  Future<void> _selectWatch(WatchItem w) async {
    if (MarketRepository.instance.series(w.id) != null) {
      setState(() => _stockId = w.id);
      return;
    }
    await _confirmAndBuild(w.id, w.name);
  }

  Future<void> _manageWatchlist() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheet) {
          final items = WatchList.all;
          return SafeArea(
            child: SizedBox(
              height: MediaQuery.of(ctx).size.height * 0.8,
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 8, 8),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('我的自選股',
                                  style: TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.w900,
                                      color: cInk)),
                              const SizedBox(height: 2),
                              Text('共 ${items.length} 檔・存在這台裝置',
                                  style: TextStyle(
                                      fontSize: 13, color: cInkSoft)),
                            ],
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.copy_rounded),
                          tooltip: '複製清單',
                          onPressed: () async {
                            await Clipboard.setData(
                                ClipboardData(text: WatchList.exportText()));
                            _snack('已複製 ${items.length} 檔清單到剪貼簿');
                          },
                        ),
                        IconButton(
                          icon: const Icon(Icons.close_rounded),
                          onPressed: () => Navigator.of(ctx).pop(),
                        ),
                      ],
                    ),
                  ),
                  const Divider(height: 1),
                  Expanded(
                    child: items.isEmpty
                        ? Center(
                            child: Text('還沒有自選股',
                                style:
                                    TextStyle(fontSize: 15, color: cInkSoft)),
                          )
                        : ListView.separated(
                            itemCount: items.length,
                            separatorBuilder: (_, __) =>
                                Divider(height: 1, color: cLine),
                            itemBuilder: (_, i) {
                              final w = items[i];
                              final loaded =
                                  MarketRepository.instance.series(w.id) != null;
                              return ListTile(
                                leading: CircleAvatar(
                                  backgroundColor: AppColors.gold,
                                  child: Text('${i + 1}',
                                      style: const TextStyle(
                                          fontSize: 13,
                                          fontWeight: FontWeight.w800,
                                          color: Colors.white)),
                                ),
                                title: Text('${w.name}（${w.id}）',
                                    style: TextStyle(
                                        fontSize: 16,
                                        fontWeight: FontWeight.w700,
                                        color: cInk)),
                                subtitle: Text(
                                    '${w.industry}${loaded ? '・已建立檔案' : '・尚未建立檔案'}',
                                    style: TextStyle(
                                        fontSize: 12.5, color: cInkSoft)),
                                trailing: IconButton(
                                  icon: const Icon(Icons.delete_outline_rounded),
                                  color: AppColors.danger,
                                  onPressed: () {
                                    WatchList.remove(w.id);
                                    setSheet(() {});
                                    setState(() => _watchItems = WatchList.all);
                                  },
                                ),
                                onTap: () {
                                  Navigator.of(ctx).pop();
                                  _selectWatch(w);
                                },
                              );
                            },
                          ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
    if (mounted) setState(() => _watchItems = WatchList.all);
  }

  /// 詢問並建立線上檔案（原本 _resolveStock 的後半段，抽出來共用）
  Future<void> _confirmAndBuild(String id, String? knownName) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(knownName == null ? '建立 $id 的檔案？' : '建立 $knownName（$id）的檔案？'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text('這個代號不在內建 33 檔內。可以現在向 FinMind 抓取歷史資料，'
                '建立一份完整檔案（約 10–20 秒，需要網路）。',
                style: TextStyle(fontSize: 14.5, height: 1.6)),
            SizedBox(height: 10),
            Text('· 資料會存在這台裝置，下次開啟不用重抓\n'
                '· 最多保留 20 檔線上檔案\n'
                '· 免費 API 有次數限制，請勿連續大量抓取',
                style: TextStyle(fontSize: 12.5, height: 1.6, color: Color(0xFF6B6250))),
          ],
        ),
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
    if (ok != true || !mounted) return;

    setState(() => _fetchingStock = true);
    try {
      final s = await RemoteStockService.fetch(id);
      MarketRepository.instance.register(s);
      if (!mounted) return;
      setState(() {
        _stockId = id;
        _fetchingStock = false;
      });
      _codeCtrl.clear();
      _snack('已建立 ${s.name}（${s.id}）檔案：${s.firstDateText} ～ ${s.lastDateText}');
    } on RemoteStockException catch (e) {
      if (!mounted) return;
      setState(() => _fetchingStock = false);
      _snack(e.message);
    } catch (e) {
      if (!mounted) return;
      setState(() => _fetchingStock = false);
      _snack('建立失敗：$e');
    }
  }

  /// 名稱搜尋的候選清單（全市場 3000+ 檔，不是只有內建 33 檔）
  Future<StockBrief?> _showPicker(List<StockBrief> initial, String keyword) {
    var q = keyword;
    var list = initial;
    return showModalBottomSheet<StockBrief>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheet) {
          return SafeArea(
            child: Padding(
              padding:
                  EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
              child: SizedBox(
                height: MediaQuery.of(ctx).size.height * 0.78,
                child: Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 6),
                      child: TextField(
                        controller: TextEditingController(text: keyword),
                        onChanged: (v) {
                          q = v.trim();
                          setSheet(() => list = StockIndex.instance.search(q));
                        },
                        style: const TextStyle(fontSize: 18),
                        decoration: InputDecoration(
                          hintText: '輸入代號或名稱，例如 2330 / 台積 / 台积电',
                          prefixIcon: const Icon(Icons.search_rounded),
                          helperText:
                              '全市場 ${StockIndex.instance.count} 檔・支援簡體輸入',
                        ),
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Row(
                        children: [
                          Text('${list.length} 筆結果',
                              style: TextStyle(
                                  fontSize: 13, color: cInkSoft)),
                          const Spacer(),
                          Text('點一下選取',
                              style: TextStyle(
                                  fontSize: 13, color: cInkSoft)),
                        ],
                      ),
                    ),
                    const SizedBox(height: 4),
                    Expanded(
                      child: list.isEmpty
                          ? Center(
                              child: Padding(
                                padding: const EdgeInsets.all(24),
                                child: Text(
                                  '找不到「$q」。\n試試代號（2330）或名稱的另一段字。',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                      fontSize: 15, height: 1.7, color: cInkSoft),
                                ),
                              ),
                            )
                          : ListView.separated(
                              itemCount: list.length,
                              separatorBuilder: (_, __) =>
                                  Divider(height: 1, color: cLine),
                              itemBuilder: (_, i) {
                                final b = list[i];
                                final loaded =
                                    MarketRepository.instance.series(b.id) != null;
                                return ListTile(
                                  title: Text('${b.name}（${b.id}）',
                                      style: TextStyle(
                                          fontSize: 16.5,
                                          fontWeight: FontWeight.w700,
                                          color: cInk)),
                                  subtitle: Text(
                                      '${b.industry}・${b.marketLabel}'
                                      '${loaded ? '・已建立' : ''}',
                                      style: TextStyle(
                                          fontSize: 12.5, color: cInkSoft)),
                                  trailing: Icon(
                                      loaded
                                          ? Icons.check_circle_rounded
                                          : Icons.chevron_right_rounded,
                                      color: loaded ? AppColors.safe : cInkSoft),
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
        },
      ),
    );
  }

  /// 「從全部標的挑」：一開始列出已載入的標的，一打字就切換成全市場搜尋
  Future<void> _pickFromAll() async {
    await StockIndex.instance.ensureLoaded();
    final initial = MarketRepository.instance.all
        .map((x) => StockIndex.instance.byId(x.id))
        .whereType<StockBrief>()
        .toList();
    final picked = await _showPicker(initial, '');
    if (picked != null && mounted) await _selectBrief(picked);
  }

  Widget _conditionCard() {
    final personal = AppModeController.instance.isPersonal;
    final st = strategyById(_strategyId);
    final tradeMode = personal && _runType == 'trade';
    final strategies = StrategyStore.all();
    final currentTrade = strategies.firstWhere(
      (e) => e.id == _tradeStrategyId,
      orElse: () => strategies.isNotEmpty
          ? strategies.first
          : TradeStrategyPresets.build().first,
    );

    return SectionCard(
      title: '② 回測設定',
      icon: Icons.tune_rounded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ---- 回測類型（僅個人版）----
          if (personal) ...[
            Text('回測類型',
                style: TextStyle(
                    fontSize: 15, fontWeight: FontWeight.w700, color: cInkSoft)),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: ChoicePill(
                    label: '存股累積',
                    sub: '只買不賣・看長期',
                    selected: _runType == 'stock',
                    onTap: () => setState(() => _runType = 'stock'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ChoicePill(
                    label: '交易策略',
                    sub: '含停利停損・完整買賣',
                    selected: _runType == 'trade',
                    onTap: () => setState(() => _runType = 'trade'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
          ],
          Text('回測期間（年）',
              style: TextStyle(
                  fontSize: 15, fontWeight: FontWeight.w700, color: cInkSoft)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              for (final y in <int>[2, 3, 5])
                ChoicePill(
                  label: '$y 年',
                  selected: _years == y,
                  onTap: () => setState(() => _years = y),
                ),
            ],
          ),
          const SizedBox(height: 16),
          if (!tradeMode) ...[
            Text('存股節奏（3 套預設模板）',
                style: TextStyle(
                    fontSize: 15, fontWeight: FontWeight.w700, color: cInkSoft)),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: _strategyId,
              isExpanded: true,
              iconSize: 28,
              style: TextStyle(
                  fontSize: 18, fontWeight: FontWeight.w700, color: cInk),
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.timeline_rounded),
              ),
              items: [
                for (final s in kStrategies)
                  DropdownMenuItem<String>(
                    value: s.id,
                    child: Text(s.name, overflow: TextOverflow.ellipsis),
                  ),
              ],
              onChanged: (v) {
                if (v != null) setState(() => _strategyId = v);
              },
            ),
            const SizedBox(height: 10),
            NoticeBar(text: '${st.name}：${st.rule}', icon: Icons.menu_book_rounded),
          ] else ...[
            Text('交易策略（可自行調整參數）',
                style: TextStyle(
                    fontSize: 15, fontWeight: FontWeight.w700, color: cInkSoft)),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: currentTrade.id,
              isExpanded: true,
              iconSize: 28,
              style: TextStyle(
                  fontSize: 17, fontWeight: FontWeight.w700, color: cInk),
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.rule_rounded),
              ),
              items: [
                for (final s in strategies)
                  DropdownMenuItem<String>(
                    value: s.id,
                    child: Text(s.name, overflow: TextOverflow.ellipsis),
                  ),
              ],
              onChanged: (v) {
                if (v != null) setState(() => _tradeStrategyId = v);
              },
            ),
            const SizedBox(height: 10),
            NoticeBar(
              icon: Icons.rule_rounded,
              text: '${currentTrade.conditionLines.join('、')}\n'
                  '${currentTrade.exitLines.join('；')}\n'
                  '本金 ${money(currentTrade.totalCapital)}・每次投入 ${money(currentTrade.trancheAmount)}',
            ),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const StrategyListPage()),
                  );
                  setState(() {});
                },
                icon: const Icon(Icons.tune_rounded),
                label: const Text('管理／新增策略'),
              ),
            ),
          ],
          const SizedBox(height: 16),
          Text('也可以直接說一句（語音或文字）',
              style: TextStyle(
                  fontSize: 15, fontWeight: FontWeight.w700, color: cInkSoft)),
          const SizedBox(height: 8),
          TextField(
            controller: _queryCtrl,
            style: const TextStyle(fontSize: 17, height: 1.5),
            decoration: const InputDecoration(
              hintText: '例如：用高殖利率策略回測台積電過去 5 年',
              prefixIcon: Icon(Icons.chat_bubble_outline_rounded),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: ActionButton(
                  label: '語音輸入',
                  icon: Icons.mic_rounded,
                  primary: false,
                  onPressed: _startVoice,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ActionButton(
                  label: '解析這句話',
                  icon: Icons.auto_fix_high_rounded,
                  primary: false,
                  onPressed: () {
                    final t = _queryCtrl.text;
                    if (t.trim().isEmpty) {
                      _snack('請先輸入或說一句話。');
                    } else {
                      _applyQuery(t);
                    }
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          ActionButton(
            label: tradeMode ? '執行交易回測' : '執行回測',
            sub: tradeMode
                ? '含手續費、證交稅、停利停損，結果為歷史模擬'
                : '只用公開歷史資料模擬，不會下單、不會預測',
            icon: Icons.play_circle_fill_rounded,
            onPressed: _run,
          ),
        ],
      ),
    );
  }

  Widget _settingsCard() {
    final st = AppSettings.instance;
    return SectionCard(
      title: '③ 適老化設定',
      icon: Icons.accessibility_new_rounded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              for (var i = 0; i < AppSettings.labels.length; i++)
                ChoicePill(
                  label: AppSettings.labels[i],
                  selected: st.fontIndex == i,
                  onTap: () => st.setFontIndex(i),
                ),
            ],
          ),
          const SizedBox(height: 6),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: st.highContrast,
            onChanged: st.setHighContrast,
            title: Text('高對比模式',
                style: TextStyle(
                    fontSize: 17, fontWeight: FontWeight.w700, color: cInk)),
            subtitle: Text('黑底黃字，適合光線不足或視力較弱時使用',
                style: TextStyle(fontSize: 13.5, color: cInkSoft)),
          ),
        ],
      ),
    );
  }

  Widget _historyCard() {
    return SectionCard(
      title: '我的學習紀錄（存在這台裝置）',
      icon: Icons.history_rounded,
      subtitle: '報告只存在瀏覽器本機，不會上傳，也不需要在雲端註冊帳號。',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_saved.isEmpty)
            Text('還沒有存檔。回測完成後按「存到本機」，就會出現在這裡。',
                style: TextStyle(fontSize: 15, color: cInkSoft, height: 1.6))
          else
            for (final r in _saved.take(5))
              Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: isHighContrast ? Colors.black : const Color(0xFFF6F1E7),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: cLine),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${r.stockName}（${r.stockId}）・${r.strategyName}',
                              style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w700,
                                  color: cInk)),
                          Text('${r.period}　年化 ${pct(r.irr)}　回撤 ${pct(r.maxDrawdown)}',
                              style:
                                  TextStyle(fontSize: 13.5, color: cInkSoft)),
                        ],
                      ),
                    ),
                    IconButton(
                      tooltip: '刪除這筆',
                      icon: const Icon(Icons.delete_outline_rounded),
                      onPressed: () {
                        ReportStore.remove(r.id);
                        setState(() => _saved = ReportStore.list());
                      },
                    ),
                  ],
                ),
              ),
          if (_saved.isNotEmpty)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: () {
                  ReportStore.clear();
                  setState(() => _saved = <SavedReport>[]);
                },
                icon: const Icon(Icons.delete_sweep_rounded),
                label: const Text('清除全部'),
              ),
            ),
        ],
      ),
    );
  }

  Widget _glossaryCard() {
    return SectionCard(
      title: '名詞小辭典（看不懂就點開）',
      icon: Icons.translate_rounded,
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: Column(
          children: [
            for (final e in kGlossary.entries)
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                childrenPadding: const EdgeInsets.only(bottom: 8),
                title: Text(e.key,
                    style: TextStyle(
                        fontSize: 16.5,
                        fontWeight: FontWeight.w700,
                        color: cInk)),
                children: [
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Text(e.value,
                        style: TextStyle(
                            fontSize: 15, height: 1.65, color: cInkSoft)),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget _footer() {
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(kDataSourceNote,
              style: TextStyle(fontSize: 12.5, height: 1.6, color: cInkSoft)),
          const SizedBox(height: 6),
          Text('資料快照日期：${MarketRepository.instance.capturedAt}',
              style: TextStyle(fontSize: 12.5, color: cInkSoft)),
        ],
      ),
    );
  }
}

class _Tag extends StatelessWidget {
  final String text;
  const _Tag(this.text);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: isHighContrast ? Colors.black : cPrimary.withOpacity(0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: cPrimary.withOpacity(0.35)),
      ),
      child: Text(text,
          style: TextStyle(
              fontSize: 12.5, fontWeight: FontWeight.w700, color: cPrimary)),
    );
  }
}

/// 語音輸入對話框
class _VoiceDialog extends StatefulWidget {
  const _VoiceDialog({Key? key}) : super(key: key);

  @override
  State<_VoiceDialog> createState() => _VoiceDialogState();
}

class _VoiceDialogState extends State<_VoiceDialog> {
  String _text = '';
  String _status = '正在聽…請對著麥克風說一句話';
  bool _finished = false;

  @override
  void initState() {
    super.initState();
    _listen();
  }

  Future<void> _listen() async {
    final result = await SpeechInputService.listen(
      onPartial: (t) {
        if (mounted) setState(() => _text = t);
      },
      onError: (e) {
        if (!mounted) return;
        setState(() {
          _status = e == 'not-allowed'
              ? '麥克風沒有授權。請允許麥克風，或直接關閉改用文字輸入。'
              : '語音辨識中斷（$e），可以改用文字輸入。';
          _finished = true;
        });
      },
    );
    if (!mounted) return;
    setState(() {
      _finished = true;
      if (result != null && result.isNotEmpty) {
        _text = result;
        _status = '辨識完成，請確認文字';
      } else if (_text.isEmpty) {
        _status = '沒有聽到聲音，可以再試一次或改用文字輸入。';
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Row(
        children: const [
          Icon(Icons.mic_rounded, size: 28),
          SizedBox(width: 8),
          Expanded(
            child: Text('語音輸入',
                style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
          ),
        ],
      ),
      content: SizedBox(
        width: 460,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_status, style: const TextStyle(fontSize: 15, height: 1.6)),
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              constraints: const BoxConstraints(minHeight: 72),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFF6F1E7),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFD9D0BE)),
              ),
              child: Text(_text.isEmpty ? '（還沒聽到內容）' : _text,
                  style: const TextStyle(fontSize: 18, height: 1.5)),
            ),
            const SizedBox(height: 10),
            Text('例如：「用高殖利率策略回測台積電過去 5 年」',
                style: TextStyle(fontSize: 13, color: cInkSoft)),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () {
            SpeechInputService.abort();
            Navigator.of(context).pop();
          },
          child: const Text('取消'),
        ),
        TextButton(
          onPressed: _finished
              ? () => Navigator.of(context).pop(_text)
              : null,
          child: const Text('用這句話'),
        ),
      ],
    );
  }
}
