// ============================================================================
// SilverStock · 台股實戰工作站
// ----------------------------------------------------------------------------
// 資料來源：FinMind 公開 API（建置期快照）。
// 商業化使用需採購 FinMind 商業授權。
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
