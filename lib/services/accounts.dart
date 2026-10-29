// ============================================================================
// 多帳戶管理（Multi-Account）
// ----------------------------------------------------------------------------
// 為什麼要做：投資從來不是一個人的事。父母的退休金、配偶的存股、自己的波段
// 部位、還有一個專門拿來「試錯」的練習帳戶——它們的目標、風險承受度、持有
// 期間完全不同，混在同一個帳戶裡看，只會得到一個誰都不適用的平均數。
//
// 設計原則：
//   1. 帳戶數量不限，名稱自訂（爸爸、媽媽、老婆、練習一號…都可以）
//   2. 兩種帳戶語義：
//        real  — 真實帳戶記帳。只記錄「你實際做了什麼」，不預測、不建議下單
//        paper — 模擬練習。用虛擬資金驗證策略，虧光也不心痛
//   3. 各自獨立的本金、現金、流水、持倉，互不污染
//   4. 全部存本機 localStorage，不上傳。家人持股屬於敏感資訊
//   5. 可單獨匯出某一本，也可一次匯出全部（CSV，Excel 可直接開）
//
// 與舊版的關係：v2.0 只有一個寫死的模擬盤（ssq_paper_v1）。載入時若偵測到
// 舊資料，會自動包成一個名為「練習帳戶」的 paper 帳戶，資料不丟。
// ============================================================================

import 'dart:convert';
import 'dart:html' as html; // ignore: avoid_web_libraries_in_flutter

import 'paper_account.dart';

/// 帳戶語義。
/// real 是真錢、真紀錄；paper 是虛擬練習。UI 用不同顏色區分，避免混淆。
enum AccountKind { real, paper }

extension AccountKindLabel on AccountKind {
  String get label => this == AccountKind.real ? '真實帳戶' : '模擬練習';
  String get shortLabel => this == AccountKind.real ? '真實' : '練習';
}

class InvestAccount {
  final String id;
  String name;
  AccountKind kind;
  String broker; // 券商或平台，可留空
  String note;
  final String createdAt;
  double initialCapital;
  double cash;
  double realizedPnl;
  List<PaperTrade> trades;
  Map<String, PaperPosition> positions;

  InvestAccount({
    required this.id,
    required this.name,
    required this.kind,
    this.broker = '',
    this.note = '',
    required this.createdAt,
    required this.initialCapital,
    required this.cash,
    required this.realizedPnl,
    required this.trades,
    required this.positions,
  });

  factory InvestAccount.fresh({
    required String name,
    AccountKind kind = AccountKind.paper,
    double capital = 1000000,
    String broker = '',
    String note = '',
  }) {
    final now = DateTime.now();
    return InvestAccount(
      id: 'acc_${now.microsecondsSinceEpoch}',
      name: name.trim().isEmpty ? '未命名帳戶' : name.trim(),
      kind: kind,
      broker: broker.trim(),
      note: note.trim(),
      createdAt: _stamp(now),
      initialCapital: capital,
      cash: capital,
      realizedPnl: 0,
      trades: <PaperTrade>[],
      positions: <String, PaperPosition>{},
    );
  }

  static String _stamp(DateTime t) =>
      '${t.year}-${_two(t.month)}-${_two(t.day)} ${_two(t.hour)}:${_two(t.minute)}';

  static String _two(int v) => v < 10 ? '0$v' : '$v';

  /// 顯示用標題，例如「爸爸（元大）」
  String get title => broker.isEmpty ? name : '$name（$broker）';

  /// 持倉市值。priceOf 由呼叫端提供，取不到價時退回成本價並記為 stale。
  double marketValue(double Function(String stockId) priceOf, {bool Function(String)? known}) {
    double sum = 0;
    positions.forEach((sid, p) {
      final px = priceOf(sid);
      final use = px > 0 ? px : p.avgCost;
      sum += use * p.shares;
    });
    return sum;
  }

  /// 總權益 = 現金 + 持倉市值
  double equity(double Function(String stockId) priceOf) =>
      cash + marketValue(priceOf);

  /// 未實現損益（不含手續費與稅，因為還沒賣）
  double unrealized(double Function(String stockId) priceOf) {
    double sum = 0;
    positions.forEach((sid, p) {
      final px = priceOf(sid);
      if (px <= 0) return;
      sum += (px - p.avgCost) * p.shares;
    });
    return sum;
  }

  double get totalCost =>
      positions.values.fold<double>(0.0, (a, p) => a + p.avgCost * p.shares);

  /// 總報酬率（%）。以本金為分母，含已實現 + 未實現。
  double returnPct(double Function(String stockId) priceOf) {
    if (initialCapital <= 0) return 0;
    final eq = equity(priceOf);
    return (eq - initialCapital) / initialCapital * 100;
  }

  /// 持倉檔數
  int get holdingCount => positions.length;

  /// 現金比重（0~100）。給風險體檢看「子彈還剩多少」。
  double cashRatio(double Function(String stockId) priceOf) {
    final eq = equity(priceOf);
    if (eq <= 0) return 0;
    return cash / eq * 100;
  }

  Map<String, dynamic> toJson() => <String, dynamic>{
        'id': id,
        'name': name,
        'kind': kind.name,
        'broker': broker,
        'note': note,
        'createdAt': createdAt,
        'initialCapital': initialCapital,
        'cash': cash,
        'realizedPnl': realizedPnl,
        'trades': trades.map((e) => e.toJson()).toList(),
        'positions': positions.map((k, v) => MapEntry(k, v.toJson())),
      };

  factory InvestAccount.fromJson(Map<String, dynamic> j) => InvestAccount(
        id: j['id'] as String? ?? 'acc_legacy',
        name: j['name'] as String? ?? '未命名帳戶',
        kind: (j['kind'] as String?) == 'real' ? AccountKind.real : AccountKind.paper,
        broker: j['broker'] as String? ?? '',
        note: j['note'] as String? ?? '',
        createdAt: j['createdAt'] as String? ?? '',
        initialCapital: (j['initialCapital'] as num?)?.toDouble() ?? 0,
        cash: (j['cash'] as num?)?.toDouble() ?? 0,
        realizedPnl: (j['realizedPnl'] as num?)?.toDouble() ?? 0,
        trades: (j['trades'] as List?)
                ?.map((e) => PaperTrade.fromJson((e as Map).cast<String, dynamic>()))
                .toList() ??
            <PaperTrade>[],
        positions: (j['positions'] as Map?)?.map((k, v) => MapEntry(
                k.toString(),
                PaperPosition.fromJson((v as Map).cast<String, dynamic>()))) ??
            <String, PaperPosition>{},
      );
}

/// 整本帳冊：多個帳戶 + 目前選中的那一本。
class AccountBook {
  int version;
  String activeId;
  List<InvestAccount> accounts;

  AccountBook({this.version = 2, required this.activeId, required this.accounts});

  InvestAccount? get active {
    if (accounts.isEmpty) return null;
    for (final a in accounts) {
      if (a.id == activeId) return a;
    }
    return accounts.first;
  }

  InvestAccount? byId(String id) {
    for (final a in accounts) {
      if (a.id == id) return a;
    }
    return null;
  }

  /// 全部帳戶合計權益（新手最常問：我們家到底有多少錢在股市裡）
  double totalEquity(double Function(String stockId) priceOf) =>
      accounts.fold<double>(0.0, (a, ac) => a + ac.equity(priceOf));

  double get totalCapital =>
      accounts.fold<double>(0.0, (a, ac) => a + ac.initialCapital);

  Map<String, dynamic> toJson() => <String, dynamic>{
        'version': version,
        'activeId': activeId,
        'accounts': accounts.map((e) => e.toJson()).toList(),
      };

  factory AccountBook.fromJson(Map<String, dynamic> j) => AccountBook(
        version: (j['version'] as num?)?.toInt() ?? 2,
        activeId: j['activeId'] as String? ?? '',
        accounts: (j['accounts'] as List?)
                ?.map((e) => InvestAccount.fromJson((e as Map).cast<String, dynamic>()))
                .toList() ??
            <InvestAccount>[],
      );

  factory AccountBook.empty() {
    final a = InvestAccount.fresh(name: '我的練習帳', kind: AccountKind.paper);
    return AccountBook(activeId: a.id, accounts: <InvestAccount>[a]);
  }
}

class AccountStore {
  static const String _key = 'ssq_accounts_v2';
  static const String _legacyKey = 'ssq_paper_v1';

  static AccountBook? _cache;

  static AccountBook load({bool force = false}) {
    if (_cache != null && !force) return _cache!;
    final book = _read();
    _cache = book;
    return book;
  }

  static AccountBook _read() {
    try {
      final raw = html.window.localStorage[_key];
      if (raw != null && raw.isNotEmpty) {
        final book = AccountBook.fromJson((jsonDecode(raw) as Map).cast<String, dynamic>());
        if (book.accounts.isNotEmpty) {
          // activeId 失效時修正，避免畫面空白
          if (book.byId(book.activeId) == null) book.activeId = book.accounts.first.id;
          return book;
        }
      }
    } catch (_) {
      // 壞掉就往下走，嘗試遷移或重建
    }
    return _migrateLegacy() ?? AccountBook.empty();
  }

  /// v2.0 舊模擬盤 → v2.1 練習帳戶。有資料才搬，沒資料回 null。
  static AccountBook? _migrateLegacy() {
    try {
      final raw = html.window.localStorage[_legacyKey];
      if (raw == null || raw.isEmpty) return null;
      final j = (jsonDecode(raw) as Map).cast<String, dynamic>();
      final trades = (j['trades'] as List?) ?? const [];
      final positions = (j['positions'] as Map?) ?? const {};
      if (trades.isEmpty && positions.isEmpty) return null;
      final cap = (j['initialCapital'] as num?)?.toDouble() ?? 1000000;
      final legacy = InvestAccount.fromJson(<String, dynamic>{
        'id': 'acc_legacy_paper',
        'name': '練習帳（v2.0 舊資料）',
        'kind': 'paper',
        'broker': '',
        'note': '由 v2.0 單一模擬盤自動搬移，流水與持倉完整保留。',
        'createdAt': '',
        'initialCapital': cap,
        'cash': j['cash'],
        'realizedPnl': j['realizedPnl'],
        'trades': trades,
        'positions': positions,
      });
      final book = AccountBook(activeId: legacy.id, accounts: <InvestAccount>[legacy]);
      save(book);
      return book;
    } catch (_) {
      return null;
    }
  }

  static void save(AccountBook book) {
    _cache = book;
    try {
      html.window.localStorage[_key] = jsonEncode(book.toJson());
    } catch (_) {
      // localStorage 滿了就放棄寫入，不讓整個頁面掛掉
    }
  }

  /// 存回目前快取的帳冊。改完帳戶欄位後呼叫這一行即可。
  static void persist() {
    final b = _cache;
    if (b != null) save(b);
  }

  static InvestAccount add({
    required String name,
    AccountKind kind = AccountKind.paper,
    double capital = 1000000,
    String broker = '',
    String note = '',
  }) {
    final book = load();
    final acc = InvestAccount.fresh(
        name: name, kind: kind, capital: capital, broker: broker, note: note);
    book.accounts.add(acc);
    book.activeId = acc.id;
    save(book);
    return acc;
  }

  static void select(String id) {
    final book = load();
    if (book.byId(id) == null) return;
    book.activeId = id;
    save(book);
  }

  static bool rename(String id, String name, {String? broker, String? note}) {
    final book = load();
    final acc = book.byId(id);
    if (acc == null) return false;
    final n = name.trim();
    if (n.isEmpty) return false;
    acc.name = n;
    if (broker != null) acc.broker = broker.trim();
    if (note != null) acc.note = note.trim();
    save(book);
    return true;
  }

  /// 刪除帳戶。至少保留一本，避免出現「沒有任何帳戶」的空白狀態。
  static bool remove(String id) {
    final book = load();
    if (book.accounts.length <= 1) return false;
    book.accounts.removeWhere((a) => a.id == id);
    if (book.activeId == id && book.accounts.isNotEmpty) {
      book.activeId = book.accounts.first.id;
    }
    save(book);
    return true;
  }

  /// 清空某本帳戶的流水與持倉，保留帳戶本身（重新開始練習用）
  static void reset(String id, {double? capital}) {
    final book = load();
    final acc = book.byId(id);
    if (acc == null) return;
    final cap = capital ?? acc.initialCapital;
    acc.initialCapital = cap;
    acc.cash = cap;
    acc.realizedPnl = 0;
    acc.trades.clear();
    acc.positions.clear();
    save(book);
  }
}
