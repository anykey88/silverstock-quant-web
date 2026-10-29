// ============================================================================
// 本機存檔（localStorage）
// ----------------------------------------------------------------------------
// 【合規約束】參賽版不做雲端帳號系統，報告只存在使用者自己的瀏覽器裡，
// 不會上傳任何個人資料；清除瀏覽器資料即消失。
// ============================================================================

import 'dart:convert';
import 'dart:html' as html; // ignore: avoid_web_libraries_in_flutter

import '../models/models.dart';

class SavedReport {
  final String id;
  final String stockId;
  final String stockName;
  final String strategyId;
  final String strategyName;
  final String period;
  final String createdAt;
  final double irr;
  final double maxDrawdown;
  final double winRate;
  final double totalInvested;
  final double finalValue;
  final String narrative;
  final List<List<String>> risks;

  SavedReport({
    required this.id,
    required this.stockId,
    required this.stockName,
    required this.strategyId,
    required this.strategyName,
    required this.period,
    required this.createdAt,
    required this.irr,
    required this.maxDrawdown,
    required this.winRate,
    required this.totalInvested,
    required this.finalValue,
    required this.narrative,
    required this.risks,
  });

  Map<String, dynamic> toJson() => <String, dynamic>{
        'id': id,
        'stockId': stockId,
        'stockName': stockName,
        'strategyId': strategyId,
        'strategyName': strategyName,
        'period': period,
        'createdAt': createdAt,
        'irr': irr,
        'mdd': maxDrawdown,
        'win': winRate,
        'invested': totalInvested,
        'final': finalValue,
        'narrative': narrative,
        'risks': risks,
      };

  factory SavedReport.fromJson(Map<String, dynamic> j) => SavedReport(
        id: j['id'] as String,
        stockId: j['stockId'] as String? ?? '',
        stockName: j['stockName'] as String? ?? '',
        strategyId: j['strategyId'] as String? ?? '',
        strategyName: j['strategyName'] as String? ?? '',
        period: j['period'] as String? ?? '',
        createdAt: j['createdAt'] as String? ?? '',
        irr: (j['irr'] as num?)?.toDouble() ?? 0,
        maxDrawdown: (j['mdd'] as num?)?.toDouble() ?? 0,
        winRate: (j['win'] as num?)?.toDouble() ?? 0,
        totalInvested: (j['invested'] as num?)?.toDouble() ?? 0,
        finalValue: (j['final'] as num?)?.toDouble() ?? 0,
        narrative: j['narrative'] as String? ?? '',
        risks: (j['risks'] as List?)
                ?.map((e) => (e as List).map((x) => x.toString()).toList())
                .toList() ??
            <List<String>>[],
      );

  factory SavedReport.fromBundle(ReportBundle b) => SavedReport(
        id: b.id,
        stockId: b.stockId,
        stockName: b.stockName,
        strategyId: b.strategyId,
        strategyName: b.strategyName,
        period: '${b.startDate} ～ ${b.endDate}',
        createdAt: b.createdAt,
        irr: b.primary?.irr ?? 0,
        maxDrawdown: b.primary?.maxDrawdown ?? 0,
        winRate: b.primary?.winRate ?? 0,
        totalInvested: b.primary?.totalInvested ?? 0,
        finalValue: b.primary?.finalValue ?? 0,
        narrative: b.narrative,
        risks: (b.fundamental?.risks ?? [])
            .map((r) => <String>[r.level, r.title, r.detail])
            .toList(),
      );
}

class ReportStore {
  static const String _key = 'ssq_reports_v1';
  static const int _maxItems = 20;

  static List<SavedReport> list() {
    try {
      final raw = html.window.localStorage[_key];
      if (raw == null || raw.isEmpty) return <SavedReport>[];
      final arr = jsonDecode(raw) as List;
      return arr
          .map((e) => SavedReport.fromJson((e as Map).cast<String, dynamic>()))
          .toList();
    } catch (_) {
      return <SavedReport>[];
    }
  }

  static void save(SavedReport r) {
    final items = list();
    items.removeWhere((e) => e.id == r.id);
    items.insert(0, r);
    while (items.length > _maxItems) {
      items.removeLast();
    }
    html.window.localStorage[_key] =
        jsonEncode(items.map((e) => e.toJson()).toList());
  }

  static void remove(String id) {
    final items = list()..removeWhere((e) => e.id == id);
    html.window.localStorage[_key] =
        jsonEncode(items.map((e) => e.toJson()).toList());
  }

  static void clear() {
    html.window.localStorage.remove(_key);
  }
}

/// 適老化偏好設定（字體大小、高對比、使用模式）也存本機
class PrefsStore {
  static const String _kScale = 'ssq_font_scale';
  static const String _kContrast = 'ssq_high_contrast';
  static const String _kMode = 'ssq_app_mode';
  static const String _kAckPersonal = 'ssq_personal_ack';

  static int loadScaleIndex() {
    final v = int.tryParse(html.window.localStorage[_kScale] ?? '');
    return (v ?? 1).clamp(0, 2);
  }

  static void saveScaleIndex(int v) =>
      html.window.localStorage[_kScale] = v.toString();

  static bool loadHighContrast() =>
      html.window.localStorage[_kContrast] == '1';

  static void saveHighContrast(bool v) =>
      html.window.localStorage[_kContrast] = v ? '1' : '0';

  /// 0 = 個人自用版（預設），1 = 比賽合規版
  static int loadAppMode() =>
      (int.tryParse(html.window.localStorage[_kMode] ?? '') ?? 0).clamp(0, 1);

  static void saveAppMode(int index) =>
      html.window.localStorage[_kMode] = index.toString();

  static bool personalDisclaimerAcked() =>
      html.window.localStorage[_kAckPersonal] == '1';

  static void ackPersonalDisclaimer() =>
      html.window.localStorage[_kAckPersonal] = '1';
}
