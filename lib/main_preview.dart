// 临时预览入口（不提交）
import 'package:flutter/material.dart';

import 'core/app_settings.dart';
import 'ui/family_lists_page.dart';
import 'ui/theme.dart';

void main() {
  runApp(const PreviewApp());
}

class PreviewApp extends StatelessWidget {
  const PreviewApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: AppSettings.instance,
      builder: (context, _) {
        final hc = AppSettings.instance.highContrast;
        final scale = AppSettings.instance.textScale;
        return MaterialApp(
          title: 'preview',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.build(hc),
          builder: (context, child) {
            final media = MediaQuery.of(context);
            return MediaQuery(
              data: media.copyWith(textScaleFactor: scale),
              child: child ?? const SizedBox.shrink(),
            );
          },
          home: const FamilyListsPage(),
        );
      },
    );
  }
}
