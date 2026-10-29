// 適老化主題：大字、高對比、夠大的點擊區域（iPad mini Safari 優先）
import 'package:flutter/material.dart';

class AppColors {
  // 一般模式：暖白底，降低眩光
  static const Color bg = Color(0xFFFBF7EF);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color primary = Color(0xFF124E8C);
  static const Color primaryDark = Color(0xFF0B3560);
  static const Color ink = Color(0xFF15181D);
  static const Color inkSoft = Color(0xFF4A5563);
  static const Color line = Color(0xFFDDD5C7);
  static const Color warnBg = Color(0xFFFFF1CC);
  static const Color warnLine = Color(0xFFB3261E);
  static const Color danger = Color(0xFFB3261E);
  static const Color dangerBg = Color(0xFFFDECEA);
  static const Color safe = Color(0xFF1B6B3A);
  static const Color safeBg = Color(0xFFE8F5EC);
  // 台股慣例：紅漲綠跌
  static const Color up = Color(0xFFC62828);
  static const Color down = Color(0xFF1B7F3B);
  static const Color gold = Color(0xFF9A6B00);

  // 高對比模式：黑底黃字
  static const Color hcBg = Color(0xFF000000);
  static const Color hcSurface = Color(0xFF121212);
  static const Color hcPrimary = Color(0xFFFFD400);
  static const Color hcInk = Color(0xFFFFFFFF);
  static const Color hcInkSoft = Color(0xFFE6E6E6);
  static const Color hcLine = Color(0xFFFFD400);
}

class AppTheme {
  static ThemeData build(bool highContrast) {
    final bg = highContrast ? AppColors.hcBg : AppColors.bg;
    final surface = highContrast ? AppColors.hcSurface : AppColors.surface;
    final ink = highContrast ? AppColors.hcInk : AppColors.ink;
    final inkSoft = highContrast ? AppColors.hcInkSoft : AppColors.inkSoft;
    final primary = highContrast ? AppColors.hcPrimary : AppColors.primary;
    final onPrimary = highContrast ? Colors.black : Colors.white;
    final line = highContrast ? AppColors.hcLine : AppColors.line;

    final base = ThemeData(
      useMaterial3: false,
      brightness: highContrast ? Brightness.dark : Brightness.light,
      scaffoldBackgroundColor: bg,
      colorScheme: ColorScheme.fromSwatch().copyWith(
        primary: primary,
        secondary: highContrast ? AppColors.hcPrimary : AppColors.gold,
        brightness: highContrast ? Brightness.dark : Brightness.light,
      ),
      canvasColor: bg,
      cardColor: surface,
      dividerColor: line,
    );

    return base.copyWith(
      textTheme: base.textTheme
          .apply(bodyColor: ink, displayColor: ink)
          .copyWith(
            bodyLarge: TextStyle(fontSize: 18, height: 1.7, color: ink),
            bodyMedium: TextStyle(fontSize: 16.5, height: 1.7, color: ink),
            bodySmall: TextStyle(fontSize: 14.5, height: 1.6, color: inkSoft),
            titleLarge: TextStyle(
                fontSize: 23, fontWeight: FontWeight.w800, color: ink, height: 1.35),
            titleMedium: TextStyle(
                fontSize: 19, fontWeight: FontWeight.w700, color: ink, height: 1.4),
          ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ButtonStyle(
          backgroundColor: MaterialStateProperty.all(primary),
          foregroundColor: MaterialStateProperty.all(onPrimary),
          minimumSize: MaterialStateProperty.all(const Size.fromHeight(60)),
          elevation: MaterialStateProperty.all(0),
          textStyle: MaterialStateProperty.all(
              const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
          shape: MaterialStateProperty.all(RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
              side: BorderSide(
                  color: highContrast ? primary : Colors.transparent, width: 2))),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: ButtonStyle(
          foregroundColor: MaterialStateProperty.all(
              highContrast ? AppColors.hcPrimary : AppColors.primary),
          minimumSize: MaterialStateProperty.all(const Size.fromHeight(58)),
          side: MaterialStateProperty.all(BorderSide(color: primary, width: 2)),
          textStyle: MaterialStateProperty.all(
              const TextStyle(fontSize: 19, fontWeight: FontWeight.w700)),
          shape: MaterialStateProperty.all(
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: ButtonStyle(
          foregroundColor: MaterialStateProperty.all(
              highContrast ? AppColors.hcPrimary : AppColors.primary),
          textStyle: MaterialStateProperty.all(
              const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface,
        contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
        hintStyle: TextStyle(fontSize: 17, color: inkSoft),
        labelStyle: TextStyle(fontSize: 16, color: inkSoft, fontWeight: FontWeight.w600),
        floatingLabelStyle: TextStyle(fontSize: 16, color: primary, fontWeight: FontWeight.w700),
        border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: line, width: 2)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: line, width: 2)),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: primary, width: 3)),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: highContrast ? AppColors.hcPrimary : AppColors.primaryDark,
        contentTextStyle: TextStyle(
            fontSize: 17,
            color: highContrast ? Colors.black : Colors.white,
            fontWeight: FontWeight.w600),
        behavior: SnackBarBehavior.floating,
      ),
      dialogTheme: DialogTheme(
        backgroundColor: surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
      bottomSheetTheme: BottomSheetThemeData(backgroundColor: surface),
      iconTheme: IconThemeData(color: ink, size: 26),
    );
  }
}
