// 繪圖用色多為動態主題色
// ignore_for_file: prefer_const_constructors
// 個股走勢圖（價格 + 均線 + 成交量）
import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'widgets.dart';

class PriceVolumeChart extends StatelessWidget {
  final List<int> dates;
  final List<double> closes;
  final List<int> volumes;
  final int days;
  final double height;

  const PriceVolumeChart({
    Key? key,
    required this.dates,
    required this.closes,
    required this.volumes,
    this.days = 250,
    this.height = 300,
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
        painter: _PVC(
          dates: dates,
          closes: closes,
          volumes: volumes,
          days: days,
          ink: cInk,
          soft: cInkSoft,
          grid: isHighContrast ? const Color(0xFF444444) : const Color(0xFFE3DCCE),
        ),
      ),
    );
  }
}

class _PVC extends CustomPainter {
  final List<int> dates;
  final List<double> closes;
  final List<int> volumes;
  final int days;
  final Color ink;
  final Color soft;
  final Color grid;

  _PVC({
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

    final pts = closes.sublist(from);
    var lo = pts.reduce(math.min);
    var hi = pts.reduce(math.max);
    if (hi - lo < 0.01) {
      hi = lo + 1;
    }
    final pad = (hi - lo) * 0.08;
    lo -= pad;
    hi += pad;

    double xOf(int i) => padL + i / (n - 1) * w;
    double yOf(double v) => padT + priceH - (v - lo) / (hi - lo) * priceH;

    // 網格
    final gp = Paint()
      ..color = grid
      ..strokeWidth = 1;
    for (var g = 0; g <= 3; g++) {
      final v = lo + (hi - lo) * g / 3;
      final y = yOf(v);
      canvas.drawLine(Offset(padL, y), Offset(padL + w, y), gp);
      _text(canvas, v.toStringAsFixed(1), Offset(3, y - 7),
          TextStyle(fontSize: 10.5, color: soft));
    }

    // 成交量
    if (volumes.isNotEmpty) {
      final volSlice = volumes.sublist(from);
      final maxVol = volSlice.reduce(math.max).toDouble();
      final baseY = padT + priceH + gap + volH;
      final bw = math.max(1.0, w / n * 0.62);
      for (var i = 0; i < n; i++) {
        final v = volSlice[i].toDouble();
        final h = maxVol <= 0 ? 0.0 : v / maxVol * volH;
        final rising = i == 0 || pts[i] >= pts[i - 1];
        canvas.drawRect(
          Rect.fromLTWH(xOf(i) - bw / 2, baseY - h, bw, h),
          Paint()
            ..color = (rising ? const Color(0xFFC62828) : const Color(0xFF1B7F3B))
                .withOpacity(0.42),
        );
      }
      // 量能區不另加文字，避免與 X 軸標籤重疊（下方 caption 已說明）
    }

    // 季線
    final ma = <double>[];
    for (var i = 0; i < closes.length; i++) {
      final s = math.max(0, i - 59);
      final slice = closes.sublist(s, i + 1);
      ma.add(slice.reduce((a, b) => a + b) / slice.length);
    }
    final maPts = ma.sublist(from);

    // 價格線 + 面積
    final path = Path();
    for (var i = 0; i < n; i++) {
      final x = xOf(i);
      final y = yOf(pts[i]);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    final area = Path.from(path)
      ..lineTo(xOf(n - 1), padT + priceH)
      ..lineTo(xOf(0), padT + priceH)
      ..close();
    canvas.drawPath(
      area,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[Color(0x332E7DBB), Color(0x052E7DBB)],
        ).createShader(Rect.fromLTWH(padL, padT, w, priceH)),
    );
    canvas.drawPath(
      path,
      Paint()
        ..color = const Color(0xFF1565C0)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.2
        ..strokeJoin = StrokeJoin.round,
    );

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
        text: TextSpan(
            text: label, style: TextStyle(fontSize: 10.5, color: soft)),
        textDirection: TextDirection.ltr,
      )..layout();
      var x = xOf(i) - tp.width / 2;
      x = x.clamp(padL, padL + w - tp.width);
      tp.paint(canvas, Offset(x, size.height - padB + 4));
    }

    // 圖例
    _text(canvas, '收盤價', Offset(padL + 4, padT + 2),
        const TextStyle(fontSize: 10.5, color: Color(0xFF1565C0), fontWeight: FontWeight.w700));
    _text(canvas, '季線', Offset(padL + 52, padT + 2),
        const TextStyle(fontSize: 10.5, color: Color(0xFF9A6B00), fontWeight: FontWeight.w700));
  }

  void _text(Canvas canvas, String s, Offset o, TextStyle st) {
    final tp = TextPainter(
        text: TextSpan(text: s, style: st), textDirection: TextDirection.ltr)
      ..layout();
    tp.paint(canvas, o);
  }

  @override
  bool shouldRepaint(covariant _PVC old) =>
      old.closes != closes || old.volumes != volumes || old.days != days;
}
