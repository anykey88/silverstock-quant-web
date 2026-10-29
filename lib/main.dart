// ============================================================================
// SilverStock-Quant-Web
// 面向台胞銀髮存股族的台股多 Agent 量化研究網頁工具
// WorkBuddy「1024 造物挑戰」參賽作品
// ----------------------------------------------------------------------------
// 【重要合規聲明】
// 1. 本工具僅整理台股公開歷史資料並執行歷史策略回測，僅作為學習復盤使用。
// 2. 不提供投資建議、不預測股價、無任何實盤交易下單功能。
// 3. 資料來源為 FinMind 公開免費非商用 API（建置期快照），僅限本次參賽 Demo；
//    商業化必須採購 FinMind 商業授權，禁止把免費 API 直接用於售賣。
// 4. 每一頁最上方固定展示完整免責聲明，不可關閉。
// ============================================================================

import 'package:flutter/material.dart';

import 'core/app_settings.dart';
import 'ui/home_page.dart';
import 'ui/theme.dart';

void main() {
  runApp(const SilverStockApp());
}

class SilverStockApp extends StatelessWidget {
  const SilverStockApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: AppSettings.instance,
      builder: (context, _) {
        final hc = AppSettings.instance.highContrast;
        final scale = AppSettings.instance.textScale;
        return MaterialApp(
          title: 'SilverStock-Quant-Web',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.build(hc),
          // 適老化：以 MediaQuery 全域放大字體，標準 / 大號 / 特大號
          builder: (context, child) {
            final media = MediaQuery.of(context);
            return MediaQuery(
              data: media.copyWith(textScaleFactor: scale),
              child: child ?? const SizedBox.shrink(),
            );
          },
          home: const HomePage(),
        );
      },
    );
  }
}
