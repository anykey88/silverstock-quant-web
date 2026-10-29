// ============================================================================
// 線上股票檔案服務（任意台股代號 → 即時建立檔案）
// ----------------------------------------------------------------------------
// 用途：內建快照只有 33 檔，這裡讓使用者輸入任意台股代號，前端直接向
//       FinMind 公開 API 抓取歷史資料，組出 StockSeries 並快取在本機。
//
// 【授權約束】使用的是 FinMind 免費非商用 API；個人使用可以，
//   若要對外提供服務或商業化，必須採購 FinMind 商業授權。
//
// 【限制（UI 要如實告知）】
//   1. 一檔股票需要 4 次 API 請求（價格 / 本益比 / 股利 / 財報）
//   2. 免費額度約每小時 300 次 → 約可建立 70 檔，不建議連續大量抓取
//   3. 需要網路；離線時只能用已快取的檔案
//   4. 抓到的資料存本機 localStorage，最多保留 20 檔（超過淘汰最舊的）
// ============================================================================

import 'dart:async';
import 'dart:convert';
import 'dart:html' as html; // ignore: avoid_web_libraries_in_flutter
import 'dart:math' as math;

import '../models/models.dart';

class RemoteStockException implements Exception {
  final String message;
  final bool notFound;
  RemoteStockException(this.message, {this.notFound = false});
  @override
  String toString() => message;
}

class RemoteStockService {
  static const String _cacheKey = 'ssq_remote_stocks_v1';
  static const String _infoKey = 'ssq_stock_info_v2';
  static const int _maxCache = 20;

  static const String _base = 'https://api.finmindtrade.com/api/v4/data';

  /// 代號 → "名稱|產業"
  static Map<String, String>? _infoCache;

  static String _ymd(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  static Future<dynamic> _get(Map<String, String> q, {int timeoutSec = 25}) async {
    final uri = Uri.parse('$_base?${q.entries.map((e) => '${e.key}=${Uri.encodeComponent(e.value)}').join('&')}');
    try {
      final req = await html.HttpRequest.request(
        uri.toString(),
        method: 'GET',
        requestHeaders: {'Accept': 'application/json'},
      ).timeout(Duration(seconds: timeoutSec));
      final body = req.responseText;
      if (body == null) throw RemoteStockException('伺服器沒有回應，請稍後再試');
      final json = jsonDecode(body) as Map<String, dynamic>;
      if (json['status'] != 200) {
        throw RemoteStockException('FinMind 回應：${json['msg'] ?? '未知錯誤'}');
      }
      return json['data'];
    } on TimeoutException {
      throw RemoteStockException('連線逾時，請確認網路後再試');
    } on RemoteStockException {
      rethrow;
    } catch (e) {
      throw RemoteStockException('網路請求失敗：$e');
    }
  }

  /// 股票名稱與產業（全表快取 7 天）
  static Future<String> _nameAndIndustry(String id) async {
    if (_infoCache == null) {
      final raw = html.window.localStorage[_infoKey];
      if (raw != null && raw.isNotEmpty) {
        try {
          final j = jsonDecode(raw) as Map<String, dynamic>;
          final ts = (j['ts'] as num).toInt();
          if (DateTime.now().millisecondsSinceEpoch - ts < 7 * 86400 * 1000) {
            _infoCache = (j['map'] as Map).map((k, v) => MapEntry(k.toString(), v.toString()));
          }
        } catch (_) {}
      }
    }
    if (_infoCache == null) {
      final data = await _get({'dataset': 'TaiwanStockInfo'}, timeoutSec: 40);
      final map = <String, String>{};
      for (final row in (data as List)) {
        final m = (row as Map).cast<String, dynamic>();
        final sid = (m['stock_id'] ?? '').toString();
        final name = (m['stock_name'] ?? '').toString();
        final ind = (m['industry_category'] ?? '').toString();
        if (sid.isNotEmpty) map[sid] = '$name|${ind.isEmpty ? '未分類' : ind}';
      }
      _infoCache = map;
      html.window.localStorage[_infoKey] = jsonEncode({
        'ts': DateTime.now().millisecondsSinceEpoch,
        'map': map,
      });
    }
    return _infoCache![id] ?? '未分類|未分類';
  }

  /// 建立一檔股票的完整檔案
  static Future<StockSeries> fetch(String rawId, {int years = 5}) async {
    final id = rawId.trim().toUpperCase();
    if (!RegExp(r'^[0-9]{4,6}$').hasMatch(id)) {
      throw RemoteStockException('請輸入 4 位數台股代號（例如 2603）', notFound: true);
    }

    final end = DateTime.now();
    final start = DateTime(end.year - years, end.month, end.day);
    final startStr = _ymd(start);
    final endStr = _ymd(end);

    // 先確認這檔存在（用價格資料判斷）
    final price = await _get({
      'dataset': 'TaiwanStockPrice',
      'data_id': id,
      'start_date': startStr,
      'end_date': endStr,
    });
    if ((price as List).isEmpty) {
      throw RemoteStockException('查不到 $id 的歷史價格，請確認代號是否正確', notFound: true);
    }

    // 其餘三項並行抓（任一失敗不影響主檔建立）
    final results = await Future.wait<dynamic>([
      _get({
        'dataset': 'TaiwanStockPER',
        'data_id': id,
        'start_date': startStr,
        'end_date': endStr,
      }).catchError((_) => <dynamic>[]),
      _get({
        'dataset': 'TaiwanStockDividend',
        'data_id': id,
        'start_date': '${end.year - years - 1}-01-01',
        'end_date': endStr,
      }).catchError((_) => <dynamic>[]),
      _get({
        'dataset': 'TaiwanStockFinancialStatements',
        'data_id': id,
        'start_date': '${end.year - years - 1}-01-01',
        'end_date': endStr,
      }).catchError((_) => <dynamic>[]),
      _nameAndIndustry(id).catchError((_) => '未分類|未分類'),
    ]);

    final perRows = results[0] as List;
    final divRows = results[1] as List;
    final finRows = results[2] as List;
    final nameInfo = (results[3] as String).split('|');
    final name = nameInfo.isNotEmpty ? nameInfo[0] : id;
    final industry = nameInfo.length > 1 ? nameInfo[1] : '未分類';

    // ---- 價格 ----
    final dates = <int>[];
    final closes = <double>[];
    final volumes = <int>[];
    for (final row in price) {
      final m = (row as Map).cast<String, dynamic>();
      try {
        dates.add(int.parse((m['date'] as String).replaceAll('-', '')));
        closes.add((m['close'] as num).toDouble());
        volumes.add(((m['Trading_Volume'] as num?)?.toDouble() ?? 0).round() ~/ 1000);
      } catch (_) {}
    }

    // ---- 本益比 / 殖利率 / 股價淨值比（每月第一筆）----
    final perSeries = <List<dynamic>>[];
    final seen = <String>{};
    for (final row in perRows) {
      final m = (row as Map).cast<String, dynamic>();
      final d = (m['date'] ?? '').toString();
      if (d.length < 7) continue;
      final ym = d.substring(0, 7);
      if (seen.contains(ym) || m['PER'] == null) continue;
      seen.add(ym);
      perSeries.add([
        d,
        (m['dividend_yield'] as num?)?.toDouble() ?? 0,
        (m['PER'] as num?)?.toDouble() ?? 0,
        (m['PBR'] as num?)?.toDouble() ?? 0,
      ]);
    }
    perSeries.sort((a, b) => (a[0] as String).compareTo(b[0] as String));

    // ---- 股利 ----
    final divMap = <String, double>{};
    for (final row in divRows) {
      final m = (row as Map).cast<String, dynamic>();
      final cash = ((m['CashEarningsDistribution'] as num?)?.toDouble() ?? 0) +
          ((m['CashStatutorySurplus'] as num?)?.toDouble() ?? 0);
      if (cash <= 0) continue;
      final key = (m['CashExDividendTradingDate'] ?? m['date'] ?? '').toString();
      if (key.length < 7) continue;
      final ym = key.substring(0, 7);
      divMap[ym] = (divMap[ym] ?? 0) + cash;
    }
    final dividends = divMap.entries.map((e) => <dynamic>[e.key, e.value]).toList()
      ..sort((a, b) => (a[0] as String).compareTo(b[0] as String));

    // ---- 單季 EPS ----
    final epsMap = <String, double>{};
    for (final row in finRows) {
      final m = (row as Map).cast<String, dynamic>();
      if (m['type'] != 'EPS') continue;
      final v = m['value'];
      if (v == null) continue;
      final d = (m['date'] ?? '').toString();
      if (d.length < 7) continue;
      epsMap[d.substring(0, 7)] = (v as num).toDouble();
    }
    final eps = epsMap.entries.map((e) => <dynamic>[e.key, e.value]).toList()
      ..sort((a, b) => (a[0] as String).compareTo(b[0] as String));

    // ---- 清洗：補零 + 分割回溯調整 ----
    for (var i = 0; i < closes.length; i++) {
      if (closes[i] <= 0) {
        closes[i] = i > 0 ? closes[i - 1] : (closes.firstWhere((c) => c > 0, orElse: () => 1));
      }
    }
    final splits = <String>[];
    for (var i = 1; i < closes.length; i++) {
      final r = closes[i] / closes[i - 1];
      if (r < 0.75) {
        final f = (1 / r).round();
        if (f >= 2 && f <= 10 && ((1 / r) - f).abs() / f < 0.08) {
          for (var j = 0; j < i; j++) {
            closes[j] = double.parse((closes[j] * r).toStringAsFixed(4));
            volumes[j] = volumes[j] * f;
          }
          final ym = dates[i] ~/ 100;
          for (final d in dividends) {
            if (int.parse((d[0] as String).replaceAll('-', '')) < ym) {
              d[1] = (d[1] as double) * r;
            }
          }
          splits.add('${StockSeries.fmtYmd(dates[i])} 1分$f');
        }
      }
    }

    final series = StockSeries(
      id: id,
      name: name,
      industry: industry,
      dates: dates,
      closes: closes,
      volumes: volumes,
      per: perSeries.map((e) => PerPoint.fromJson(e)).toList(),
      dividends: dividends.map((e) => DivRecord.fromJson(e)).toList(),
      eps: eps.map((e) => QuarterEps.fromJson(e)).toList(),
    );

    _cache(series);
    return series;
  }

  // ---- 快取 ----
  static void _cache(StockSeries s) {
    try {
      final list = loadCached().where((e) => e.id != s.id).toList();
      list.insert(0, s);
      while (list.length > _maxCache) {
        list.removeLast();
      }
      final payload = list.map(_toJson).toList();
      html.window.localStorage[_cacheKey] = jsonEncode(payload);
    } catch (_) {
      // 容量不足時，清掉舊快取重試一次
      try {
        html.window.localStorage.remove(_cacheKey);
        html.window.localStorage[_cacheKey] = jsonEncode([_toJson(s)]);
      } catch (_) {}
    }
  }

  static Map<String, dynamic> _toJson(StockSeries s) => <String, dynamic>{
        'id': s.id,
        'name': s.name,
        'industry': s.industry,
        'dates': s.dates,
        'closes': s.closes,
        'volumes': s.volumes,
        'perSeries': s.per
            .map((e) => <dynamic>[e.date, e.yieldRate, e.per, e.pbr])
            .toList(),
        'dividends': s.dividends.map((e) => <dynamic>[e.ym, e.amount]).toList(),
        'quarterlyEps': s.eps.map((e) => <dynamic>[e.ym, e.eps]).toList(),
      };

  static List<StockSeries> loadCached() {
    try {
      final raw = html.window.localStorage[_cacheKey];
      if (raw == null || raw.isEmpty) return <StockSeries>[];
      final arr = jsonDecode(raw) as List;
      return arr
          .map((e) => StockSeries.fromJson(
                (e as Map)['id'].toString(),
                e.cast<String, dynamic>(),
              ))
          .toList();
    } catch (_) {
      return <StockSeries>[];
    }
  }

  static void remove(String id) {
    final list = loadCached()..removeWhere((e) => e.id == id);
    html.window.localStorage[_cacheKey] =
        jsonEncode(list.map(_toJson).toList());
  }

  static int get cachedCount => loadCached().length;

  static const int maxCache = 20;

  /// 估算每檔的資料量（KB），用於提示
  static int estimateKb() => math.max(1, 0) + 30;
}
