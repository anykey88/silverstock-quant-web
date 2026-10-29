/// SilverStock v2 — 訊號整合與衝突檢查
///
/// 目的不是給答案，是**把彼此矛盾的證據擺在一起**。
/// 散戶最常犯的錯不是資料不足，是只挑支持自己想法的資料看。
/// 本模組強制把相反方向的證據列出來。
library silverstock_v2.signals;

import 'data.dart';
import 'financials.dart';
import 'levels.dart';
import 'momentum.dart';
import 'valuation.dart';

enum SignalTone { positive, caution, conflict, neutral }

class Signal {
  final String title;
  final String detail;
  final SignalTone tone;

  const Signal(this.title, this.detail, this.tone);
}

class SignalReport {
  final List<Signal> signals;
  final String positionLabel; // 九宮格定位
  final String positionDetail;
  final List<String> watchPoints;
  final List<String> invalidation; // 什麼情況下這個判讀就失效

  const SignalReport({
    required this.signals,
    required this.positionLabel,
    required this.positionDetail,
    required this.watchPoints,
    required this.invalidation,
  });
}

class SignalEngine {
  static SignalReport build({
    required StockDataset d,
    required ValuationProfile vp,
    required FinancialQuality fq,
    required MomentumReport mo,
    required LevelMap lv,
  }) {
    final signals = <Signal>[];
    final close = d.latest?.close ?? 0;
    final perPct = vp.perPercentile;
    final yldPct = vp.yieldPercentile;
    final score = fq.score;

    // --- 三維定位 -----------------------------------------------------------
    final finStrong = score != null && score >= 70;
    final finWeak = score != null && score < 45;
    final cheap = perPct != null && perPct < 30;
    final expensive = perPct != null && perPct > 70;
    final growing = mo.stage == MomentumStage.accelerating ||
        mo.stage == MomentumStage.steady;
    final shrinking = mo.stage == MomentumStage.decelerating ||
        mo.stage == MomentumStage.contracting;

    String label;
    String detail;
    if (finStrong && cheap) {
      label = '體質強 × 估值低';
      detail = '財務檢核通過率高，且本益比位於歷史低檔。這種組合在統計上出現的次數不多，'
          '下一步要確認的是「為什麼便宜」——是整體市場下跌，還是這家公司出了什麼事。';
    } else if (finStrong && expensive) {
      label = '體質強 × 估值高';
      detail = '公司本身沒問題，問題在價格。歷史上這種組合之後的報酬，主要取決於成長能不能繼續兌現，'
          '而不是取決於公司好不好。';
    } else if (finStrong) {
      label = '體質強 × 估值中間';
      detail = '財務面穩健，估值沒有明顯偏離歷史中位數。這是最常見、也最沒有戲劇性的狀態。';
    } else if (finWeak && cheap) {
      label = '體質弱 × 估值低';
      detail = '便宜，但財務檢核有多項未通過。低估值可能已反映基本面轉差，而不是市場看錯。';
    } else if (finWeak && expensive) {
      label = '體質弱 × 估值高';
      detail = '財務面已出現弱項，價格卻仍在歷史高位。這是最需要查清楚原因的組合。';
    } else if (cheap) {
      label = '體質中等 × 估值低';
      detail = '估值在歷史低檔，財務面沒有明顯問題但也沒有亮點。';
    } else if (expensive) {
      label = '體質中等 × 估值高';
      detail = '估值偏貴，財務面普通。支撐價格的理由不在財報上，需要另外找。';
    } else {
      label = '體質中等 × 估值中間';
      detail = '各項指標都在中間區間，沒有明顯的錯配，也沒有明顯的吸引力。';
    }

    // --- 衝突訊號（重點）----------------------------------------------------
    if (finStrong && expensive) {
      signals.add(Signal(
        '衝突：基本面強，但估值已在高檔',
        '財務檢核 $score 分，本益比卻位於歷史 ${perPct.toStringAsFixed(0)} 百分位。'
            '「好公司」與「好價格」在這裡是兩個不同的問題。',
        SignalTone.conflict,
      ));
    }

    if (growing && expensive) {
      signals.add(Signal(
        '衝突：成長仍在加速，但價格已提前反映',
        '近 3 月營收 YoY ${mo.threeMonthYoY?.toStringAsFixed(1) ?? '—'}%，'
            '估值卻在歷史高位。市場已把未來的成長計入價格，成長一旦減速，修正幅度會比想像大。',
        SignalTone.caution,
      ));
    }

    if (shrinking && cheap) {
      signals.add(Signal(
        '衝突：估值便宜，但營收在收縮',
        '營收動能為「${mo.stageLabel}」，估值卻在低檔。便宜可能是結果，不是機會。',
        SignalTone.conflict,
      ));
    }

    // 籌碼 vs 基本面
    if (d.institutions.length >= 20) {
      final t20 = d.institutions.sublist(d.institutions.length - 20);
      final foreignLots =
          t20.fold<double>(0, (s, x) => s + x.foreignNet) / 1000;
      if (growing && foreignLots < -5000) {
        signals.add(Signal(
          '衝突：營收成長，但外資近 20 日大幅賣超',
          '外資近 20 日賣超 ${(-foreignLots).toStringAsFixed(0)} 張，'
              '同期營收仍在成長。法人可能在調節持股比重，或看到了財報以外的東西。',
          SignalTone.conflict,
        ));
      }
      if (shrinking && foreignLots > 5000) {
        signals.add(Signal(
          '衝突：營收衰退，但外資在買',
          '外資近 20 日買超 ${foreignLots.toStringAsFixed(0)} 張，營收卻在下滑。'
              '法人買的可能是下一段循環，而不是現在的數字。',
          SignalTone.caution,
        ));
      }
      if (foreignLots.abs() > 5000) {
        signals.add(Signal(
          foreignLots > 0 ? '籌碼：外資近 20 日偏多' : '籌碼：外資近 20 日偏空',
          '外資近 20 日${foreignLots > 0 ? '買超' : '賣超'} '
              '${foreignLots.abs().toStringAsFixed(0)} 張。',
          foreignLots > 0 ? SignalTone.positive : SignalTone.caution,
        ));
      }
    }

    // 位置 vs 價值區
    if (lv.valueAreaLow != null && lv.valueAreaHigh != null && close > 0) {
      if (close > lv.valueAreaHigh!) {
        signals.add(Signal(
          '位置：股價在價值區之上',
          '現價 ${close.toStringAsFixed(0)} 元高於價值區上緣 '
              '${lv.valueAreaHigh!.toStringAsFixed(0)} 元，表示多數持有者的成本低於現價。',
          SignalTone.caution,
        ));
      } else if (close < lv.valueAreaLow!) {
        signals.add(Signal(
          '位置：股價跌破價值區',
          '現價 ${close.toStringAsFixed(0)} 元低於價值區下緣 '
              '${lv.valueAreaLow!.toStringAsFixed(0)} 元，過去一年的持有者多數處於虧損。',
          SignalTone.conflict,
        ));
      } else {
        signals.add(Signal(
          '位置：股價在價值區內',
          '現價落在 ${lv.valueAreaLow!.toStringAsFixed(0)} ～ '
              '${lv.valueAreaHigh!.toStringAsFixed(0)} 元的成交密集區間內。',
          SignalTone.neutral,
        ));
      }
    }

    // 殖利率（存股視角）
    if (yldPct != null && vp.currentYield != null) {
      if (yldPct < 20) {
        signals.add(Signal(
          '存股視角：殖利率處於歷史低檔',
          '目前殖利率 ${vp.currentYield!.toStringAsFixed(2)}%，位於歷史 ${yldPct.toStringAsFixed(0)} 百分位。'
              '以領息為目的的話，這個價位的現金流報酬是近 5 年較差的時候。',
          SignalTone.caution,
        ));
      } else if (yldPct > 80) {
        signals.add(Signal(
          '存股視角：殖利率處於歷史高檔',
          '目前殖利率 ${vp.currentYield!.toStringAsFixed(2)}%，位於歷史 ${yldPct.toStringAsFixed(0)} 百分位。'
              '需確認高殖利率是來自穩定配息，還是股價下跌造成。',
          SignalTone.positive,
        ));
      }
    }

    // --- 觀察重點 -----------------------------------------------------------
    final watch = <String>[];
    if (mo.lastMonth != null) {
      watch.add('每月 10 日前的月營收（目前最新為 ${mo.lastMonth}），是台股最領先的公開數字。');
    }
    watch.add('季度財報公布日：Q1 5/15、Q2 8/14、Q3 11/14、Q4 次年 3/31 前。');
    if (fq.payoutRatio != null && fq.payoutRatio! > 0) {
      watch.add('股息發放率 ${fq.payoutRatio!.toStringAsFixed(0)}%，'
          '下次股利政策公告時確認是否維持。');
    }
    if (lv.atrPct != null) {
      watch.add('日常波動約 ${lv.atrPct!.toStringAsFixed(1)}%（ATR），'
          '單日超過此幅度屬異常，需查原因。');
    }

    // --- 失效條件 -----------------------------------------------------------
    final invalid = <String>[];
    invalid.add('若下一季營收年增由正轉負，本判讀中的「成長」前提即不成立。');
    if (fq.roe != null) {
      invalid.add('若 ROE 連續兩季低於 ${(fq.roe! * 0.7).toStringAsFixed(0)}%，代表獲利能力明顯轉差。');
    }
    invalid.add('若出現減資、大額現金增資或經營權變動，歷史估值分位的參考性會大幅下降。');
    invalid.add('本報告使用快照資料，資料截止日之後的價格變動與事件均未納入。');

    return SignalReport(
      signals: signals,
      positionLabel: label,
      positionDetail: detail,
      watchPoints: watch,
      invalidation: invalid,
    );
  }
}
