// ============================================================================
// 模式控制：個人自用版 / 比賽合規版
// ----------------------------------------------------------------------------
// 背景：同一份程式要同時滿足兩種使用情境。
//   個人版（personal）  ：以「自己用」為主，解除比賽期的合規限制，
//                        開啟選股篩選、選股建議、自訂交易條件與完整交易回測。
//   比賽版（competition）：只保留歷史回測學習功能，強制固定免責聲明、
//                        禁用薦股詞彙、不提供選股建議與交易策略。
//
// 設計原則：
//   1. 模式只影響「功能可見性與文案口徑」，不影響底層計算，避免兩套邏輯分叉。
//   2. 個人版仍保留風險提示（可收起、不佔版面），只是不再強制攔截。
//   3. 模式選擇存在本機 localStorage，預設為「個人版」。
// ============================================================================

import 'package:flutter/foundation.dart';

import '../services/report_store.dart';

enum AppMode { personal, competition }

class AppModeController extends ChangeNotifier {
  AppModeController._() {
    final i = PrefsStore.loadAppMode();
    _mode = i == 1 ? AppMode.competition : AppMode.personal;
  }

  static final AppModeController instance = AppModeController._();

  late AppMode _mode;

  AppMode get mode => _mode;
  bool get isPersonal => _mode == AppMode.personal;
  bool get isCompetition => _mode == AppMode.competition;

  String get label => isPersonal ? '個人自用版' : '比賽合規版';

  void setMode(AppMode m) {
    if (_mode == m) return;
    _mode = m;
    PrefsStore.saveAppMode(m.index);
    notifyListeners();
  }

  void toggle() => setMode(isPersonal ? AppMode.competition : AppMode.personal);
}
