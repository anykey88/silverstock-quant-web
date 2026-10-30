// ============================================================================
// SilverStock · 模式控制（單一模式）
// ----------------------------------------------------------------------------
// v2.2 起只有一個版本：實戰版。
// v2.2 起雙模式已移除——所有功能永久開啟，不再有第二種版本可以切換。
//
// 保留 AppModeController 這個型別是為了不讓既有頁面的 AnimatedBuilder
// 與 setMode 呼叫整批失效；它現在是恆真、無副作用的。
// ============================================================================

import 'package:flutter/foundation.dart';

enum AppMode { personal, competition }

class AppModeController extends ChangeNotifier {
  AppModeController._();

  static final AppModeController instance = AppModeController._();

  /// 恆為 true：功能全開。
  bool get isPersonal => true;

  /// 恆為 false：雙模式已不存在，任何殘留判斷都會走不到。
  bool get isCompetition => false;

  String get label => '實戰版';

  /// 空實作：避免殘留呼叫端編譯失敗。
  void setMode(AppMode m) {}

  void toggle() {}
}
