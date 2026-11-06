// 繪圖用色多為動態主題色
// ignore_for_file: prefer_const_constructors
// 個股日 K 走勢圖（蠟燭＋成交量＋季線）
//
// 說明：內建快照（snapshot.json）只提供「收盤價＋成交量」，沒有逐筆開高低；
// 因此蠟燭的開盤價由前一交易日收盤還原，最高／最低取開收兩者極值。
// 這是資料限制下的近似呈現（已在圖下方標註），真實 OHLC 需 FinMind 日線資料集。
import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'widgets.dart';

class CandleVolumeChart extends StatelessWidget {
  final List<int> dates;
  final List<double> closes;
  final List<int> volumes;
  final int days;
  final double height;

  const CandleVolumeChart({
    Key? key,
    required this.dates,
    required this.closes,
    required this.volumes,
    this.days = 500,
    this.height = 320,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        color: isHighContrast ? Colors.black : const Color(0xFFFCFAF5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: cLine, width: 1.4),
      ),
      padding: const EdgeInsets.all(6),
      child: CustomPaint(
        size: Size.infinite,
        painter: _CVC(
          dates: dates,
          closes: closes,
          volumes: volumes,
          days: days,
          ink: cInk,
          soft: cInkSoft,
          grid:
              isHighContrast ? const Color(0xFF444444) : const Color(0xFFE3DCCE),
        ),
      ),
    );
  }
}

class _CVC extends CustomPainter {
  final List<int> dates;
  final List<double> closes;
  final List<int> volumes;
  final int days;
  final Color ink;
  final Color soft;
  final Color grid;

  _CVC({
    required this.dates,
    required this.closes,
    required this.volumes,
    required this.days,
    required this.ink,
    required this.soft,
    required this.grid,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (closes.length < 2) return;
    final from = math.max(0, closes.length - days);
    final n = closes.length - from;
    if (n < 2) return;

    const padL = 46.0, padR = 8.0, padT = 12.0, padB = 22.0;
    final w = size.width - padL - padR;
    final totalH = size.height - padT - padB;
    final priceH = totalH * 0.72;
    final volH = totalH * 0.22;
    final gap = totalH * 0.06;
    if (w <= 10 || priceH <= 10) return;

    final pt = closes.sublist(from);
    var lo = pt.reduce(math.min);
    var hi = pt.reduce(math.max);
    if (hi - lo < 0.01) hi = lo + 1;
    final pad = (hi - lo) * 0.08;
    lo -= pad;
    hi += pad;

    double xOf(int i) => padL + i / (n - 1) * w;
    double yOf(double v) => padT + priceH - (v - lo) / (hi - lo) * priceH;

    // 網格
    final gp = Paint()..color = grid..strokeWidth = 1;
    for (var g = 0; g <= 3; g++) {
      final v = lo + (hi - lo) * g / 3;
      final y = yOf(v);
      canvas.drawLine(Offset(padL, y), Offset(padL + w, y), gp);
      _text(canvas, v.toStringAsFixed(1), Offset(3, y - 7),
          TextStyle(fontSize: 10.5, color: soft));
    }

    // 成交量
    final baseY = padT + priceH + gap + volH;
    if (volumes.isNotEmpty) {
      final volSlice = volumes.sublist(from);
      final maxVol = volSlice.reduce(math.max).toDouble();
      final bw = math.max(1.0, w / n * 0.62);
      for (var i = 0; i < n; i++) {
        final v = volSlice[i].toDouble();
        final h = maxVol <= 0 ? 0.0 : v / maxVol * volH;
        final rising = i == 0 || pt[i] >= pt[i - 1];
        canvas.drawRect(
          Rect.fromLTWH(xOf(i) - bw / 2, baseY - h, bw, h),
          Paint()
            ..color = (rising ? const Color(0xFFC62828) : const Color(0xFF1B7F3B))
                .withOpacity(0.42),
        );
      }
    }

    // 季線
    final ma = <double>[];
    for (var i = 0; i < closes.length; i++) {
      final s = math.max(0, i - 59);
      final slice = closes.sublist(s, i + 1);
      ma.add(slice.reduce((a, b) => a + b) / slice.length);
    }
    final maPts = ma.sublist(from);

    // 蠟燭（開盤由前一日收盤還原）
    final candleW = math.max(1.5, w / n * 0.6);
    for (var i = 0; i < n; i++) {
      final open = i == 0 ? pt[i] : pt[i - 1];
      final close = pt[i];
      final high = math.max(open, close);
      final low = math.min(open, close);
      final up = close >= open;
      final col =
          up ? const Color(0xFFC62828) : const Color(0xFF1B7F3B);
      final x = xOf(i);
      // 影線
      canvas.drawLine(
        Offset(x, yOf(high)),
        Offset(x, yOf(low)),
        Paint()..color = col..strokeWidth = 1,
      );
      // 實體
      final top = yOf(math.max(open, close));
      final bot = yOf(math.min(open, close));
      canvas.drawRect(
        Rect.fromLTWH(x - candleW / 2, top, candleW, math.max(1.0, bot - top)),
        Paint()..color = col,
      );
    }

    // 季線
    final maPath = Path();
    for (var i = 0; i < n; i++) {
      final x = xOf(i);
      final y = yOf(maPts[i]);
      if (i == 0) {
        maPath.moveTo(x, y);
      } else {
        maPath.lineTo(x, y);
      }
    }
    canvas.drawPath(
      maPath,
      Paint()
        ..color = const Color(0xFF9A6B00)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.4,
    );

    // X 軸
    for (var t = 0; t < 4; t++) {
      final i = (n - 1) * t ~/ 3;
      final d = dates[from + i];
      final label = '${d ~/ 10000}/${(d ~/ 100) % 100}';
      final tp = TextPainter(
        text: TextSpan(text: label, style: TextStyle(fontSize: 10.5, color: soft)),
        textDirection: TextDirection.ltr,
      )..layout();
      var x = xOf(i) - tp.width / 2;
      x = x.clamp(padL, padL + w - tp.width);
      tp.paint(canvas, Offset(x, size.height - padB + 4));
    }

    // 圖例
    _text(canvas, '日 K', Offset(padL + 4, padT + 2),
        const TextStyle(fontSize: 10.5, color: Color(0xFFC62828), fontWeight: FontWeight.w700));
    _text(canvas, '季線', Offset(padL + 40, padT + 2),
        const TextStyle(fontSize: 10.5, color: Color(0xFF9A6B00), fontWeight: FontWeight.w700));
  }

  void _text(Canvas canvas, String s, Offset o, TextStyle st) {
    final tp = TextPainter(
        text: TextSpan(text: s, style: st), textDirection: TextDirection.ltr)
      ..layout();
    tp.paint(canvas, o);
  }

  @override
  bool shouldRepaint(covariant _CVC old) =>
      old.closes != closes ||
      old.volumes != volumes ||
      old.dates != dates ||
      old.days != days;
}
