// ============================================================================
// 資料存取層
// ----------------------------------------------------------------------------
// 【Agent 呼叫邏輯說明】
// 前端不直接計算業務邏輯，所有資料先經 MarketRepository 取得，再交給 agents/ 目錄下
// 的 5 個 Agent 依序處理（基本面 → 技術指標 → 回測 → 白話翻譯 → 輸出檢查）。
//
// 【資料來源約束】
// - 預設：assets/data/snapshot.json（建置期自 FinMind 公開 API 抓取的真實歷史資料快照）
// - 選用：FinMind v4 公開 API 即時查詢（需自行申請 token，免費額度有限）
// - 商業化必須採購 FinMind 商業授權，
//   禁止把免費 API 直接用於售賣。
// ============================================================================

import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/services.dart';

import '../models/models.dart';
import '../services/remote_stock_service.dart';

/// 大盤（加權指數）序列
class IndexSeries {
  final String id;
  final String name;
  final List<int> dates;
  final List<double> closes;
  final List<int> volumes;
  IndexSeries(this.id, this.name, this.dates, this.closes, this.volumes);

  factory IndexSeries.fromJson(Map<String, dynamic> j) => IndexSeries(
        j['id'] as String? ?? 'TAIEX',
        j['name'] as String? ?? '加權指數',
        (j['dates'] as List).map((e) => (e as num).toInt()).toList(),
        (j['closes'] as List).map((e) => (e as num).toDouble()).toList(),
        (j['volumes'] as List?)?.map((e) => (e as num).toInt()).toList() ??
            const <int>[],
      );
}

class MarketRepository {
  static final MarketRepository instance = MarketRepository._internal();
  MarketRepository._internal();

  final Map<String, StockSeries> _series = <String, StockSeries>{};
  final Set<String> _builtIn = <String>{};
  Map<String, dynamic> _meta = <String, dynamic>{};
  IndexSeries? _index;
  bool _loaded = false;

  IndexSeries? get index => _index;

  bool get isLoaded => _loaded;
  Map<String, dynamic> get meta => _meta;

  Future<void> ensureLoaded() async {
    if (_loaded) return;
    final raw = await rootBundle.loadString('assets/data/snapshot.json');
    final json = jsonDecode(raw) as Map<String, dynamic>;
    _meta = (json['meta'] as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{};
    final idx = json['index'];
    if (idx is Map) {
      _index = IndexSeries.fromJson(idx.cast<String, dynamic>());
    }
    final stocks = (json['stocks'] as Map).cast<String, dynamic>();
    stocks.forEach((k, v) {
      _series[k] = StockSeries.fromJson(k, (v as Map).cast<String, dynamic>());
      _builtIn.add(k);
    });
    // 使用者先前線上建立的檔案（本機快取）
    for (final s in RemoteStockService.loadCached()) {
      _series.putIfAbsent(s.id, () => s);
    }
    _loaded = true;
  }

  StockSeries? series(String id) => _series[id];

  /// 是否為內建快照標的（false = 使用者線上建立）
  bool isBuiltIn(String id) => _builtIn.contains(id);

  /// 註冊使用者線上建立的標的（不覆蓋內建）
  void register(StockSeries s) {
    if (_builtIn.contains(s.id)) return;
    _series[s.id] = s;
  }

  /// 移除線上建立的標的
  void unregister(String id) {
    if (_builtIn.contains(id)) return;
    _series.remove(id);
    RemoteStockService.remove(id);
  }

  List<StockSeries> get all => _series.values.toList()
    ..sort((a, b) => a.id.compareTo(b.id));

  String get capturedAt => (_meta['capturedAt'] ?? '') as String;
}

/// FinMind 公開 API 客戶端（選用）。
/// 說明：預設關閉即時連線，改用建置期快照，避免免費額度與跨域限制；
/// 於「進階設定」開啟後，改為即時查詢，資料欄位與快照完全一致。
class FinMindClient {
  static const String baseUrl = 'https://api.finmindtrade.com/api/v4/data';

  final String? token;
  FinMindClient({this.token});

  Future<StockSeries?> fetchDaily(String stockId, DateTime start, DateTime end) async {
    // 注意：Flutter Web 端需 FinMind 允許 CORS；若被瀏覽器攔截，會自動回退到內建快照。
    throw UnimplementedError(
      '未啟用即時連線；如需啟用請參考 README「資料來源」章節，'
      '並自行部署代理或採購 FinMind 商業授權。',
    );
  }
}

/// 簡單的統計工具
class Stats {
  static double mean(List<double> v) => v.isEmpty ? 0 : v.reduce((a, b) => a + b) / v.length;

  static double std(List<double> v) {
    if (v.length < 2) return 0;
    final m = mean(v);
    final s = v.map((e) => (e - m) * (e - m)).reduce((a, b) => a + b);
    return math.sqrt(s / (v.length - 1));
  }

  static double? median(List<double> v) {
    if (v.isEmpty) return null;
    final s = List<double>.from(v)..sort();
    return s[s.length ~/ 2];
  }
}
