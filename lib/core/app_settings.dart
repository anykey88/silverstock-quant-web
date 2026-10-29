// 適老化偏好設定（字體三檔、高對比模式）
import 'package:flutter/foundation.dart';

import '../services/report_store.dart';

class AppSettings extends ChangeNotifier {
  AppSettings._() {
    _fontIndex = PrefsStore.loadScaleIndex();
    _highContrast = PrefsStore.loadHighContrast();
  }

  static final AppSettings instance = AppSettings._();

  late int _fontIndex;
  late bool _highContrast;

  int get fontIndex => _fontIndex;
  bool get highContrast => _highContrast;

  /// 標準 / 大號 / 特大號
  static const List<double> scales = <double>[1.0, 1.18, 1.42];
  static const List<String> labels = <String>['標準', '大號', '特大號'];

  double get textScale => scales[_fontIndex];

  void setFontIndex(int v) {
    _fontIndex = v.clamp(0, 2);
    PrefsStore.saveScaleIndex(_fontIndex);
    notifyListeners();
  }

  void setHighContrast(bool v) {
    _highContrast = v;
    PrefsStore.saveHighContrast(v);
    notifyListeners();
  }
}
