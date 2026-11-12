// V2.8 資料時效判斷：只比較資料自帶時間，不讀 DateTime.now()。
// 由 tool/v3/step2_freshness.py 產出，判斷邏輯與資料常數分開，方便單獨重跑對照。
import 'data_freshness_data.dart';

enum FreshnessState { intraday, todayClose, historical }

class DataFreshness {
  final String label;
  final String quoteAsOf;
  final String capturedAt;
  final FreshnessState state;
  final String basis;

  const DataFreshness({
    required this.label,
    required this.quoteAsOf,
    required this.capturedAt,
    required this.state,
    required this.basis,
  });

  static DateTime _parse(String s) => DateTime.parse(s);

  /// 落後天數＝抓檔日減行情日，兩個都是資料自己寫的，不是現在幾點。
  int get lagDays =>
      _parse(capturedAt).difference(_parse(quoteAsOf)).inDays;

  bool get isStale => lagDays > FreshnessConst.staleThresholdDays;

  String get stateLabel {
    switch (state) {
      case FreshnessState.intraday:
        return '盤中報價';
      case FreshnessState.todayClose:
        return '今日收盤';
      case FreshnessState.historical:
        return '歷史資料';
    }
  }

  static FreshnessState _stateOf(String key) {
    switch (key) {
      case 'intraday':
        return FreshnessState.intraday;
      case 'todayClose':
        return FreshnessState.todayClose;
      default:
        return FreshnessState.historical;
    }
  }

  static List<DataFreshness> get all {
    final out = <DataFreshness>[];
    for (final m in FreshnessConst.sources) {
      out.add(DataFreshness(
        label: m['label'] ?? '',
        quoteAsOf: m['quoteAsOf'] ?? '',
        capturedAt: m['capturedAt'] ?? '',
        state: _stateOf(m['state'] ?? 'historical'),
        basis: m['basis'] ?? '',
      ));
    }
    return out;
  }
}
