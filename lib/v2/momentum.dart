/// SilverStock v2 — 營收動能
///
/// 台股獨有的高頻公開資料：**月營收於次月 10 日前公告**，比季報早 1.5～3 個月。
/// 這是台股相對其他市場最大的資訊優勢，也是本模組存在的理由。
///
/// 判定一律用「同比（YoY）」為主，因為台股電子業季節性極強（Q1 淡、Q4 旺），
/// 月增率（MoM）單看幾乎沒有意義，只作輔助。
library silverstock_v2.momentum;

import 'data.dart';
import 'stats.dart';

enum MomentumStage {
  accelerating, // 加速擴張
  steady, // 穩定成長
  plateau, // 高檔持平
  decelerating, // 減速
  contracting, // 收縮
  unknown, // 資料不足
}

class MomentumReport {
  final double? latestYoY;
  final double? latestMoM;
  final double? threeMonthYoY; // 近 3 月平均 YoY（平滑單月雜訊）
  final double? ytdYoY; // 今年累計 vs 去年同期
  final int positiveStreak; // 連續 YoY 為正的月數
  final double? shortVsLong; // 3MA ÷ 12MA
  final double? epsYoY; // 近 4 季 EPS vs 前 4 季
  final MomentumStage stage;
  final List<String> evidence; // 判定依據，逐條列出
  final String? lastMonth; // 最新月份標籤

  const MomentumReport({
    required this.latestYoY,
    required this.latestMoM,
    required this.threeMonthYoY,
    required this.ytdYoY,
    required this.positiveStreak,
    required this.shortVsLong,
    required this.epsYoY,
    required this.stage,
    required this.evidence,
    required this.lastMonth,
  });

  String get stageLabel {
    switch (stage) {
      case MomentumStage.accelerating:
        return '加速擴張';
      case MomentumStage.steady:
        return '穩定成長';
      case MomentumStage.plateau:
        return '高檔持平';
      case MomentumStage.decelerating:
        return '動能減速';
      case MomentumStage.contracting:
        return '營收收縮';
      case MomentumStage.unknown:
        return '資料不足';
    }
  }
}

class MomentumEngine {
  static MomentumReport build(StockDataset d) {
    final revs = d.monthRevenues;
    final evidence = <String>[];

    double? latestYoY;
    double? latestMoM;
    double? threeMonthYoY;
    double? ytdYoY;
    var streak = 0;
    double? shortVsLong;
    String? lastMonth;

    if (revs.length >= 13) {
      final last = revs.last;
      lastMonth = last.label;

      // 同比：找去年同月
      MonthRevenue? sameMonthLastYear;
      for (final r in revs) {
        if (r.year == last.year - 1 && r.month == last.month) {
          sameMonthLastYear = r;
          break;
        }
      }
      if (sameMonthLastYear != null && sameMonthLastYear.revenue > 0) {
        latestYoY =
            (last.revenue - sameMonthLastYear.revenue) / sameMonthLastYear.revenue * 100;
      }

      // 月增
      if (revs.length >= 2) {
        final prev = revs[revs.length - 2];
        if (prev.revenue > 0) {
          latestMoM = (last.revenue - prev.revenue) / prev.revenue * 100;
        }
      }

      // 近 3 月平均 YoY
      final yoy3 = <double>[];
      for (var i = revs.length - 3; i < revs.length; i++) {
        if (i < 0) continue;
        final cur = revs[i];
        for (final r in revs) {
          if (r.year == cur.year - 1 && r.month == cur.month && r.revenue > 0) {
            yoy3.add((cur.revenue - r.revenue) / r.revenue * 100);
            break;
          }
        }
      }
      threeMonthYoY = Stats.mean(yoy3);

      // 今年累計 YoY
      final thisYear = last.year;
      final curYtd = revs
          .where((r) => r.year == thisYear && r.month <= last.month)
          .fold<double>(0, (s, r) => s + r.revenue);
      final prevYtd = revs
          .where((r) => r.year == thisYear - 1 && r.month <= last.month)
          .fold<double>(0, (s, r) => s + r.revenue);
      if (prevYtd > 0 && curYtd > 0) {
        ytdYoY = (curYtd - prevYtd) / prevYtd * 100;
      }

      // 連續正成長月數（往回數）
      for (var i = revs.length - 1; i >= 0; i--) {
        final cur = revs[i];
        MonthRevenue? base;
        for (final r in revs) {
          if (r.year == cur.year - 1 && r.month == cur.month) {
            base = r;
            break;
          }
        }
        if (base == null || base.revenue <= 0) break;
        if (cur.revenue > base.revenue) {
          streak++;
        } else {
          break;
        }
      }

      // 3MA ÷ 12MA
      if (revs.length >= 12) {
        final ma3 = Stats.mean(
            revs.sublist(revs.length - 3).map((r) => r.revenue).toList());
        final ma12 = Stats.mean(
            revs.sublist(revs.length - 12).map((r) => r.revenue).toList());
        if (ma3 != null && ma12 != null && ma12 > 0) {
          shortVsLong = ma3 / ma12;
        }
      }
    }

    // EPS 同比
    double? epsYoY;
    final q = d.quarters.where((x) => x.eps != null).toList();
    if (q.length >= 8) {
      final cur = q.sublist(q.length - 4).fold<double>(0, (s, x) => s + x.eps!);
      final prev = q
          .sublist(q.length - 8, q.length - 4)
          .fold<double>(0, (s, x) => s + x.eps!);
      if (prev.abs() > 0.01) {
        epsYoY = (cur - prev) / prev.abs() * 100;
      }
    }

    // --- 判定 ---------------------------------------------------------------
    var stage = MomentumStage.unknown;
    final yoy = threeMonthYoY ?? latestYoY;
    if (yoy != null) {
      if (yoy >= 15 && (shortVsLong ?? 1) > 1.0) {
        stage = MomentumStage.accelerating;
        evidence.add('近 3 月營收 YoY ${yoy.toStringAsFixed(1)}%，且 3MA 高於 12MA，屬加速。');
      } else if (yoy >= 3) {
        stage = MomentumStage.steady;
        evidence.add('近 3 月營收 YoY ${yoy.toStringAsFixed(1)}%，維持正成長。');
      } else if (yoy > -3) {
        stage = MomentumStage.plateau;
        evidence.add('近 3 月營收 YoY ${yoy.toStringAsFixed(1)}%，大致持平。');
      } else if (yoy > -15) {
        stage = MomentumStage.decelerating;
        evidence.add('近 3 月營收 YoY ${yoy.toStringAsFixed(1)}%，已轉為負成長。');
      } else {
        stage = MomentumStage.contracting;
        evidence.add('近 3 月營收 YoY ${yoy.toStringAsFixed(1)}%，明顯收縮。');
      }

      if (streak >= 3) {
        evidence.add('已連續 $streak 個月營收年增為正。');
      } else if (streak == 0) {
        evidence.add('最近一個月營收年增為負或無同期可比資料，成長動能中斷。');
      }

      if (shortVsLong != null) {
        evidence.add(shortVsLong > 1.02
            ? '近 3 月營收均值高於 12 月均值 ${((shortVsLong - 1) * 100).toStringAsFixed(1)}%，短期優於長期。'
            : (shortVsLong < 0.98
                ? '近 3 月營收均值低於 12 月均值 ${((1 - shortVsLong) * 100).toStringAsFixed(1)}%，短期弱於長期。'
                : '短期與長期營收趨勢接近，無明顯轉折。'));
      }
    } else {
      evidence.add('月營收資料不足 13 個月，無法計算同比。');
    }

    if (epsYoY != null) {
      evidence.add('近 4 季 EPS 合計較前 4 季 ${epsYoY >= 0 ? '成長' : '衰退'} '
          '${epsYoY.abs().toStringAsFixed(1)}%。');
    }

    return MomentumReport(
      latestYoY: latestYoY,
      latestMoM: latestMoM,
      threeMonthYoY: threeMonthYoY,
      ytdYoY: ytdYoY,
      positiveStreak: streak,
      shortVsLong: shortVsLong,
      epsYoY: epsYoY,
      stage: stage,
      evidence: evidence,
      lastMonth: lastMonth,
    );
  }
}
