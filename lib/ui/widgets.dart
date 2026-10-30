// 共用 UI 元件（大字、大按鈕、高對比）
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../agents/agents.dart';
import '../core/app_settings.dart';
import '../core/constants.dart';
import '../core/formatters.dart';
import '../models/models.dart';
import 'theme.dart';

bool get isHighContrast => AppSettings.instance.highContrast;
Color get cInk => isHighContrast ? AppColors.hcInk : AppColors.ink;
Color get cInkSoft => isHighContrast ? AppColors.hcInkSoft : AppColors.inkSoft;
Color get cSurface => isHighContrast ? AppColors.hcSurface : AppColors.surface;
Color get cLine => isHighContrast ? AppColors.hcLine : AppColors.line;
Color get cPrimary => isHighContrast ? AppColors.hcPrimary : AppColors.primary;

/// v2.2：警語橫幅已移除，保留空殼。
/// v2.2：警語橫幅已移除。保留空殼是為了不讓 11 個頁面的引用整批失效。
class DisclaimerBanner extends StatelessWidget {
  const DisclaimerBanner({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}

/// 區塊卡片
class SectionCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final Widget child;
  final Widget? trailing;
  final Color? accent;
  final String? subtitle;

  const SectionCard({
    Key? key,
    required this.title,
    required this.icon,
    required this.child,
    this.trailing,
    this.accent,
    this.subtitle,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final a = accent ?? cPrimary;
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: cSurface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: cLine, width: isHighContrast ? 2 : 1.2),
      ),
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 24, color: a),
              const SizedBox(width: 8),
              Expanded(
                child: Text(title,
                    style: TextStyle(
                        fontSize: 19, fontWeight: FontWeight.w800, color: cInk)),
              ),
              if (trailing != null) trailing!,
            ],
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 4),
            Text(subtitle!,
                style: TextStyle(fontSize: 14, color: cInkSoft, height: 1.5)),
          ],
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

/// 指標磚
class MetricTile extends StatelessWidget {
  final String label;
  final String value;
  final String? note;
  final Color color;
  final bool big;

  const MetricTile({
    Key? key,
    required this.label,
    required this.value,
    this.note,
    this.color = AppColors.primary,
    this.big = false,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      decoration: BoxDecoration(
        color: isHighContrast ? Colors.black : color.withOpacity(0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
            color: isHighContrast ? color : color.withOpacity(0.25), width: 1.4),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label,
              style: TextStyle(
                  fontSize: 14, color: cInkSoft, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(value,
                style: TextStyle(
                    fontSize: big ? 30 : 24,
                    fontWeight: FontWeight.w900,
                    color: color,
                    height: 1.1)),
          ),
          if (note != null) ...[
            const SizedBox(height: 2),
            Text(note!, style: TextStyle(fontSize: 12.5, color: cInkSoft)),
          ],
        ],
      ),
    );
  }
}

/// 大按鈕（符合 44pt 以上觸控規範，實際高度 60）
class ActionButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback? onPressed;
  final bool primary;
  final Color? color;
  final String? sub;

  const ActionButton({
    Key? key,
    required this.label,
    required this.icon,
    required this.onPressed,
    this.primary = true,
    this.color,
    this.sub,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final child = Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 26),
            const SizedBox(width: 10),
            Flexible(
              child: Text(label,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      fontSize: 20, fontWeight: FontWeight.w800, height: 1.2)),
            ),
          ],
        ),
        if (sub != null)
          Padding(
            padding: const EdgeInsets.only(top: 3),
            child: Text(sub!,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 12.5, height: 1.3)),
          ),
      ],
    );

    final base = ButtonStyle(
      minimumSize: MaterialStateProperty.all(const Size.fromHeight(62)),
      padding: MaterialStateProperty.all(
          const EdgeInsets.symmetric(horizontal: 16, vertical: 10)),
    );

    if (primary) {
      return ElevatedButton(
        style: base.merge(ButtonStyle(
          backgroundColor: MaterialStateProperty.all(color ?? cPrimary),
        )),
        onPressed: onPressed,
        child: child,
      );
    }
    return OutlinedButton(
      style: base.merge(ButtonStyle(
        foregroundColor: MaterialStateProperty.all(color ?? cPrimary),
        side: MaterialStateProperty.all(
            BorderSide(color: color ?? cPrimary, width: 2)),
      )),
      onPressed: onPressed,
      child: child,
    );
  }
}

/// 大型選項膠囊
class ChoicePill extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback? onTap;
  final String? sub;

  const ChoicePill({
    Key? key,
    required this.label,
    required this.selected,
    this.onTap,
    this.sub,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final bg = selected ? cPrimary : (isHighContrast ? Colors.black : Colors.white);
    var fg = selected
        ? (isHighContrast ? Colors.black : Colors.white)
        : cInk;
    if (onTap == null) fg = fg.withOpacity(0.45);
    return Semantics(
      button: true,
      selected: selected,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          constraints: const BoxConstraints(minHeight: 48),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: selected ? cPrimary : cLine, width: 2),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(label,
                  style: TextStyle(
                      fontSize: 17, fontWeight: FontWeight.w700, color: fg)),
              if (sub != null)
                Text(sub!,
                    style: TextStyle(
                        fontSize: 13,
                        color: selected ? fg.withOpacity(0.85) : cInkSoft)),
            ],
          ),
        ),
      ),
    );
  }
}

/// Agent 執行流程（5 個 Agent 的即時狀態）
class AgentStepper extends StatelessWidget {
  final List<AgentStep> steps;
  const AgentStepper({Key? key, required this.steps}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (var i = 0; i < steps.length; i++)
          Padding(
            padding: EdgeInsets.only(bottom: i == steps.length - 1 ? 0 : 10),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _statusIcon(steps[i].state, i + 1),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${steps[i].name}${i == steps.length - 1 ? '（必呼叫·後置校驗）' : ''}',
                          style: TextStyle(
                              fontSize: 16.5,
                              fontWeight: FontWeight.w800,
                              color: steps[i].state == AgentState.idle
                                  ? cInkSoft
                                  : cInk)),
                      Text(
                        steps[i].detail.isEmpty ? steps[i].role : steps[i].detail,
                        style: TextStyle(
                            fontSize: 13.5,
                            height: 1.45,
                            color: steps[i].state == AgentState.blocked
                                ? AppColors.danger
                                : cInkSoft),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  Widget _statusIcon(AgentState st, int idx) {
    switch (st) {
      case AgentState.done:
        return Container(
          width: 30,
          height: 30,
          decoration: const BoxDecoration(
              color: AppColors.safe, shape: BoxShape.circle),
          child: const Icon(Icons.check, size: 19, color: Colors.white),
        );
      case AgentState.running:
        return const SizedBox(
          width: 30,
          height: 30,
          child: Padding(
            padding: EdgeInsets.all(3),
            child: CircularProgressIndicator(strokeWidth: 3),
          ),
        );
      case AgentState.blocked:
        return Container(
          width: 30,
          height: 30,
          decoration:
              const BoxDecoration(color: AppColors.danger, shape: BoxShape.circle),
          child: const Icon(Icons.close, size: 19, color: Colors.white),
        );
      case AgentState.idle:
        return Container(
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: cLine, width: 2),
          ),
          child: Center(
            child: Text('$idx',
                style: TextStyle(
                    fontSize: 13, fontWeight: FontWeight.w700, color: cInkSoft)),
          ),
        );
    }
  }
}

/// 回測曲線圖（自繪，含強制水印）
class EquityChart extends StatelessWidget {
  final List<NavPoint> primary;
  final Map<String, List<NavPoint>>? overlays;
  final double height;

  const EquityChart({
    Key? key,
    required this.primary,
    this.overlays,
    this.height = 250,
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
        painter: _ChartPainter(
          primary: primary,
          overlays: overlays ?? <String, List<NavPoint>>{},
          ink: cInk,
          soft: cInkSoft,
          grid: isHighContrast ? const Color(0xFF444444) : const Color(0xFFE3DCCE),
        ),
      ),
    );
  }
}

class _ChartPainter extends CustomPainter {
  final List<NavPoint> primary;
  final Map<String, List<NavPoint>> overlays;
  final Color ink;
  final Color soft;
  final Color grid;

  static const List<Color> seriesColors = <Color>[
    Color(0xFFC62828),
    Color(0xFF1565C0),
    Color(0xFF2E7D32),
  ];

  _ChartPainter({
    required this.primary,
    required this.overlays,
    required this.ink,
    required this.soft,
    required this.grid,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (primary.length < 2) return;
    const padL = 48.0, padR = 10.0, padT = 14.0, padB = 26.0;
    final w = size.width - padL - padR;
    final h = size.height - padT - padB;
    if (w <= 10 || h <= 10) return;

    final all = <double>[
      ...primary.map((e) => e.cumReturn),
      for (final l in overlays.values) ...l.map((e) => e.cumReturn),
      0
    ];
    var minV = all.reduce(math.min);
    var maxV = all.reduce(math.max);
    if (maxV - minV < 10) {
      final mid = (maxV + minV) / 2;
      minV = mid - 5;
      maxV = mid + 5;
    }

    // 把刻度對齊到「好看」的級距（1 / 2 / 5 的倍數），避免出現 -80% 這種怪數字
    final step = _niceStep((maxV - minV) / 4);
    minV = (minV / step).floorToDouble() * step;
    maxV = (maxV / step).ceilToDouble() * step;
    if (maxV - minV < step) maxV = minV + step;

    double yOf(double v) => padT + h - (v - minV) / (maxV - minV) * h;
    double xOf(int i, int n) => padL + (n <= 1 ? 0 : i / (n - 1) * w);

    // 網格與 Y 軸
    final gridPaint = Paint()
      ..color = grid
      ..strokeWidth = 1;
    for (var v = minV; v <= maxV + step / 2; v += step) {
      final y = yOf(v);
      canvas.drawLine(Offset(padL, y), Offset(padL + w, y), gridPaint);
      _drawText(canvas, '${v.toStringAsFixed(0)}%', Offset(4, y - 8),
          TextStyle(fontSize: 11.5, color: soft));
    }

    // 零軸
    if (minV < 0 && maxV > 0) {
      final zero = Paint()
        ..color = soft.withOpacity(0.55)
        ..strokeWidth = 1.4;
      canvas.drawLine(Offset(padL, yOf(0)), Offset(padL + w, yOf(0)), zero);
    }

    // 只有單一曲線時才填色；有對照線時改用三條線，差異才看得出來
    if (overlays.isEmpty) {
      _drawLine(canvas, primary, xOf, yOf, seriesColors[0], width: 0.001, fill: true);
    }

    var ci = 1;
    overlays.forEach((k, v) {
      if (v.length >= 2) {
        _drawLine(canvas, v, xOf, yOf, seriesColors[ci % seriesColors.length],
            width: 2.0, fill: false);
        ci++;
      }
    });

    _drawLine(canvas, primary, xOf, yOf, seriesColors[0], width: 3.0, fill: false);


    // 水印（右下角固定標籤，確保任何螢幕尺寸都讀得到）
    final tag = TextPainter(
      text: const TextSpan(
        text: ' 歷史回測不等於未來收益 ',
        style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: Colors.white),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    final tagRect = Rect.fromLTWH(padL + w - tag.width, padT + h - tag.height - 2,
        tag.width, tag.height);
    canvas.drawRRect(
        RRect.fromRectAndRadius(tagRect.inflate(2), const Radius.circular(4)),
        Paint()..color = const Color(0xFFB3261E).withOpacity(0.88));
    tag.paint(canvas, tagRect.topLeft);

    // X 軸標籤
    final n = primary.length;
    final ticks = n <= 4 ? n : 4;
    for (var t = 0; t < ticks; t++) {
      final idx = ticks == 1 ? 0 : (n - 1) * t ~/ (ticks - 1);
      final label = primary[idx].label;
      final tp = TextPainter(
        text: TextSpan(text: label, style: TextStyle(fontSize: 11, color: soft)),
        textDirection: TextDirection.ltr,
      )..layout();
      var x = xOf(idx, n) - tp.width / 2;
      x = x.clamp(padL, padL + w - tp.width);
      tp.paint(canvas, Offset(x, size.height - padB + 6));
    }
  }

  void _drawLine(Canvas canvas, List<NavPoint> pts, double Function(int, int) xOf,
      double Function(double) yOf, Color color,
      {required double width, required bool fill}) {
    final path = Path();
    for (var i = 0; i < pts.length; i++) {
      final x = xOf(i, pts.length);
      final y = yOf(pts[i].cumReturn);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    if (fill) {
      final area = Path.from(path)
        ..lineTo(xOf(pts.length - 1, pts.length), yOf(0.0).clamp(0.0, 9999.0).toDouble())
        ..lineTo(xOf(0, pts.length), yOf(0.0).clamp(0.0, 9999.0).toDouble())
        ..close();
      canvas.drawPath(
        area,
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: <Color>[color.withOpacity(0.22), color.withOpacity(0.02)],
          ).createShader(const Rect.fromLTWH(0, 0, 400, 400)),
      );
    }
    canvas.drawPath(
      path,
      Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = width
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round,
    );
  }

  static double _niceStep(double raw) {
    if (raw <= 0 || raw.isNaN || raw.isInfinite) return 10;
    final exp = math.pow(10, (math.log(raw) / math.ln10).floor()).toDouble();
    final f = raw / exp;
    final nf = f <= 1 ? 1.0 : (f <= 2 ? 2.0 : (f <= 5 ? 5.0 : 10.0));
    return nf * exp;
  }

  void _drawText(Canvas canvas, String s, Offset o, TextStyle st) {
    final tp = TextPainter(
        text: TextSpan(text: s, style: st), textDirection: TextDirection.ltr)
      ..layout();
    tp.paint(canvas, o);
  }

  @override
  bool shouldRepaint(covariant _ChartPainter old) =>
      old.primary != primary || old.overlays != overlays;
}

/// 策略對照圖例
class ChartLegend extends StatelessWidget {
  final List<String> names;
  const ChartLegend({Key? key, required this.names}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 14,
      runSpacing: 6,
      children: [
        for (var i = 0; i < names.length; i++)
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 16,
                height: 4,
                color: _ChartPainter.seriesColors[i % 3],
              ),
              const SizedBox(width: 6),
              Text(names[i], style: TextStyle(fontSize: 13, color: cInkSoft)),
            ],
          ),
      ],
    );
  }
}

/// 小提示條
class NoticeBar extends StatelessWidget {
  final String text;
  final Color color;
  final IconData icon;
  const NoticeBar({
    Key? key,
    required this.text,
    this.color = AppColors.primary,
    this.icon = Icons.info_outline,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: isHighContrast ? Colors.black : color.withOpacity(0.07),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withOpacity(0.45), width: 1.2),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Text(text,
                style: TextStyle(fontSize: 14, height: 1.55, color: cInk)),
          ),
        ],
      ),
    );
  }
}

/// v2.2：報告內嵌區塊已移除。
class InlineDisclaimer extends StatelessWidget {
  const InlineDisclaimer({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}

String pctOrDash(double? v, {int digits = 2}) => v == null ? '—' : pct(v, digits: digits);
String numOrDash(double? v, {int digits = 2}) =>
    v == null ? '—' : v.toStringAsFixed(digits);

/// v2.2：風險提示條已移除，保留空殼。
/// v2.2：風險提示條已移除。保留空殼，避免各頁面引用報錯。
class PersonalRiskBar extends StatelessWidget {
  const PersonalRiskBar({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}

/// 分數徽章（0-100）
class ScoreBadge extends StatelessWidget {
  final double score;
  final String label;
  final double size;
  const ScoreBadge({
    Key? key,
    required this.score,
    required this.label,
    this.size = 62,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final color = score >= 80
        ? const Color(0xFFB3261E)
        : (score >= 65
            ? const Color(0xFFB26B00)
            : (score >= 50 ? AppColors.primary : const Color(0xFF6B7280)));
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isHighContrast ? Colors.black : color.withOpacity(0.10),
            border: Border.all(color: color, width: 2.5),
          ),
          child: Center(
            child: Text(score.toStringAsFixed(0),
                style: TextStyle(
                    fontSize: size * 0.38,
                    fontWeight: FontWeight.w900,
                    color: color)),
          ),
        ),
        const SizedBox(height: 4),
        Text(label,
            style: TextStyle(
                fontSize: 11.5, fontWeight: FontWeight.w700, color: color)),
      ],
    );
  }
}
