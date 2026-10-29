/// SilverStock v2 — 每日掃描引擎
///
/// 目的：每天收盤後，對「候選池」內的每一檔跑一次客觀評分，
/// 產出兩份名單：**買進觀察前十** 與 **減碼觀察前十**，
/// 每一檔都附上價格區間與觸發條件。
///
/// 刻意設計成三件事：
///   1. 有硬門檻（gate）——流動性不足、財務不過關的直接剔除，不讓它們混進排名
///   2. 評分規則寫死在程式裡，可被任何人重跑驗證，不是調出來的
///   3. 名單是「觀察」不是「建議」——每一檔都必須帶失效條件
///
/// 用法：
///   dart run tool/v2_scan.dart --limit 5                 # 試跑 5 檔
///   dart run tool/v2_scan.dart --out assets/data/daily_picks.json
///   FINMIND_TOKEN=xxx dart run tool/v2_scan.dart         # 用註冊額度（600/小時）
library silverstock_v2.scan;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:silverstock_quant_web/v2/data.dart';
import 'package:silverstock_quant_web/v2/financials.dart';
import 'package:silverstock_quant_web/v2/momentum.dart';
import 'package:silverstock_quant_web/v2/parse.dart';
import 'package:silverstock_quant_web/v2/valuation.dart';

const _api = 'https://api.finmindtrade.com/api/v4/data';

/// 每日必抓（會變）：價、估值、營收、股利。
const _dailyDatasets = <String, int>{
  'TaiwanStockPrice': 2, // 2 年日線：算均線、52 週高低、流動性
  'TaiwanStockPER': 3, // 3 年估值分位
  'TaiwanStockMonthRevenue': 3, // 3 年月營收：YoY、連續正成長
  'TaiwanStockDividend': 3, // 3 年股利：殖利率、衰退判斷
};

/// 財報只按季更新（一年四次），抓一次放 30 天。
///
/// 為什麼要拆開：三張財報是「財務品質分」的唯一來源，少了它，
/// 買進評分會憑空少掉 30 分，硬門檻（財務檢核 ≥ 50）也會失效——
/// 名單會變成只看估值、不看體質。但每天重抓 3 個資料集 × 130 檔
/// 是 390 次請求，超過免費額度的兩倍，所以按季快取。
const _fundDatasets = <String>[
  'TaiwanStockFinancialStatements',
  'TaiwanStockBalanceSheet',
  'TaiwanStockCashFlowsStatement',
];
const _fundTtlDays = 30;

/// 候選池：上市櫃中流動性與市值足以支撐「每日掃描」的標的。
///
/// 為什麼不是全市場：FinMind 免費額度逐檔計費（每檔 4 次請求），
/// 2000 檔要 8000 次請求，一小時額度只有 600。這裡用一份約 130 檔的池子，
/// 每天跑得完，且覆蓋台股市值絕大部分。使用者自選股由前端本機另外計算。
const candidatePool = <String>[
  // --- 半導體 ---
  '2330', '2317', '2454', '2308', '2379', '3034', '3711', '2408', '2344',
  '6415', '3661', '3035', '3105', '8299', '3443', '5274', '3529', '8081',
  '2382', '2356', '2357', '2324', '3231', '2353', '4938', '2354',
  // --- 電子零組件 / 光電 ---
  '2303', '2409', '3481', '6176', '3008', '2392', '2313', '2360', '3044',
  '2327', '2492', '2377', '3017', '3324', '3532',
  // --- 電腦及週邊 ---
  '2352', '2355', '2362', '2385', '2376', '2395', '3706', '6669', '2382',
  // --- 網通 / 資訊服務 ---
  '2345', '3596', '5388', '6285', '2480', '3029', '6214',
  // --- 金融保險 ---
  '2881', '2882', '2883', '2884', '2885', '2886', '2887', '2888', '2889',
  '2890', '2891', '2892', '5871', '5876', '2801', '2834', '2809',
  // --- 傳產：塑膠、紡織、水泥、鋼鐵 ---
  '1301', '1303', '1326', '6505', '1101', '1102', '1402', '1409', '1605',
  '2002', '2015', '2027', '2023',
  // --- 食品、零售、生活 ---
  '1216', '1210', '1227', '2912', '5903', '5904', '2915', '2207', '2201',
  // --- 航運 ---
  '2603', '2609', '2615', '2610', '2606',
  // --- 生技醫療 ---
  '4137', '1795', '4736', '6446', '6472', '4128',
  // --- 電機機械 / 重電 ---
  '1503', '1504', '1513', '1519', '2049', '1590',
  // --- 其他電子 / 通路 ---
  '2317', '2354', '3036', '3702', '2464', '6281',
  // --- ETF（僅作對照，不進個股排名）---
  '0050', '0056', '00878', '006208',
];

/// ETF 不進個股排名（成分股邏輯與個股不同，財務指標不適用）
const _etfLike = {'0050', '0056', '00878', '006208', '0051', '00713'};

// ---------------------------------------------------------------------------
// 抓取
// ---------------------------------------------------------------------------

class Fetcher {
  final HttpClient _client = HttpClient()
    ..connectionTimeout = const Duration(seconds: 20);
  final String? token;
  final int delayMs;
  int calls = 0;

  Fetcher({this.token, this.delayMs = 6200});

  Future<List<dynamic>> get(String dataset, String sid, String startDate,
      {int retries = 3}) async {
    final q = {
      'dataset': dataset,
      'data_id': sid,
      'start_date': startDate,
      if (token != null) 'token': token!,
    };
    final uri = Uri.parse(_api).replace(queryParameters: q);

    for (var attempt = 0; attempt < retries; attempt++) {
      try {
        final req = await _client.getUrl(uri);
        req.headers.set('User-Agent', 'SilverStock/2.0');
        final res = await req.close();
        final body = await res.transform(utf8.decoder).join();
        calls++;
        final payload = jsonDecode(body) as Map<String, dynamic>;
        if (payload['status'] != 200) {
          throw Exception('${payload['msg']}');
        }
        await Future<void>.delayed(Duration(milliseconds: delayMs));
        return payload['data'] as List<dynamic>? ?? const [];
      } catch (e) {
        if (attempt == retries - 1) {
          stderr.writeln('  ! $dataset $sid 失敗: $e');
          await Future<void>.delayed(Duration(milliseconds: delayMs));
          return const [];
        }
        await Future<void>.delayed(Duration(seconds: 3 * (attempt + 1)));
      }
    }
    return const [];
  }

  void close() => _client.close(force: true);
}

String _dateBack(int years) {
  final now = DateTime.now();
  final d = DateTime(now.year - years, now.month, now.day);
  return d.toIso8601String().substring(0, 10);
}

// ---------------------------------------------------------------------------
// 評分
// ---------------------------------------------------------------------------

class Pick {
  final String id;
  final String name;
  final String industry;
  final double close;
  final double? per;
  final double? yieldPct;
  final double? perPct; // 本益比歷史百分位
  final double? yieldPctile; // 殖利率歷史百分位
  final int? finScore;
  final double? revYoY;
  final int revStreak;
  final String stage;
  final double? ma60;
  final double? high52;
  final double? low52;
  final double turnoverAvg; // 60 日均額（億元）
  final double buyLow;
  final double buyHigh;
  final double trimLow;
  final double trimHigh;
  final double buyScore;
  final double trimScore;
  final List<String> buyReasons;
  final List<String> trimReasons;
  final List<String> triggers; // 觸發條件（未成立就不動作）
  final List<String> gates; // 通過了哪些門檻
  final List<String> caveats; // 失效條件
  final String basis; // 價格區間的推算依據

  Pick({
    required this.id,
    required this.name,
    required this.industry,
    required this.close,
    required this.per,
    required this.yieldPct,
    required this.perPct,
    required this.yieldPctile,
    required this.finScore,
    required this.revYoY,
    required this.revStreak,
    required this.stage,
    required this.ma60,
    required this.high52,
    required this.low52,
    required this.turnoverAvg,
    required this.buyLow,
    required this.buyHigh,
    required this.trimLow,
    required this.trimHigh,
    required this.buyScore,
    required this.trimScore,
    required this.buyReasons,
    required this.trimReasons,
    required this.triggers,
    required this.gates,
    required this.caveats,
    required this.basis,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'ind': industry,
        'close': _r(close),
        'per': _r(per),
        'yield': _r(yieldPct),
        'perPct': _r(perPct),
        'yieldPctile': _r(yieldPctile),
        'finScore': finScore,
        'revYoY': _r(revYoY),
        'revStreak': revStreak,
        'stage': stage,
        'ma60': _r(ma60),
        'high52': _r(high52),
        'low52': _r(low52),
        'turnover': _r(turnoverAvg),
        'buyLow': _r(buyLow),
        'buyHigh': _r(buyHigh),
        'trimLow': _r(trimLow),
        'trimHigh': _r(trimHigh),
        'buyScore': _r(buyScore),
        'trimScore': _r(trimScore),
        'buyReasons': buyReasons,
        'trimReasons': trimReasons,
        'triggers': triggers,
        'gates': gates,
        'caveats': caveats,
        'basis': basis,
      };
}

double? _r(double? v) => v == null ? null : (v * 100).roundToDouble() / 100;

double _clamp(double v, double lo, double hi) => v < lo ? lo : (v > hi ? hi : v);

/// 由估值分位反推價位：找本益比分位對應的價格。
/// 做法是把「分位 → 倍數」用線性內插，再乘上 EPS(TTM)。
double? _priceAtPerPercentile(ValuationProfile vp, double eps, double pct) {
  final anchors = <double?>[vp.perP10, vp.perP25, vp.perP50, vp.perP75, vp.perP90];
  const pcts = [10.0, 25.0, 50.0, 75.0, 90.0];
  for (var i = 0; i < pcts.length; i++) {
    if (anchors[i] == null) continue;
    if ((pct - pcts[i]).abs() < 0.001) return anchors[i]! * eps;
  }
  for (var i = 1; i < pcts.length; i++) {
    final a0 = anchors[i - 1], a1 = anchors[i];
    if (a0 == null || a1 == null) continue;
    if (pct >= pcts[i - 1] && pct <= pcts[i]) {
      final t = (pct - pcts[i - 1]) / (pcts[i] - pcts[i - 1]);
      return (a0 + (a1 - a0) * t) * eps;
    }
  }
  return null;
}

/// 分析結果：要嘛是一筆評分，要嘛是一句「為什麼不列名單」。
/// 後者同樣重要——使用者最有疑問的往往是「為什麼這檔沒在裡面」。
class _Analysis {
  final Pick? pick;
  final String? excluded;
  const _Analysis.ok(this.pick) : excluded = null;
  const _Analysis.skip(this.excluded) : pick = null;
}

_Analysis _analyze(String sid, StockDataset d) {
  if (d.bars.length < 120) {
    return const _Analysis.skip('上市未滿半年或資料不足 120 個交易日，任何統計結論都不可靠');
  }
  final close = d.latest!.close;
  final vp = ValuationEngine.profile(d, years: 3);
  final fq = FinancialEngine.build(d);
  final mo = MomentumEngine.build(d);

  // --- 流動性：60 日均額（億）---
  final tail = d.bars.length > 60 ? d.bars.sublist(d.bars.length - 60) : d.bars;
  final turnoverAvg =
      tail.map((b) => b.money).fold<double>(0, (a, b) => a + b) / tail.length / 1e8;

  // --- 52 週高低、季線 ---
  final yearBars = d.bars.length > 250 ? d.bars.sublist(d.bars.length - 250) : d.bars;
  final high52 = yearBars.map((b) => b.high).reduce((a, b) => a > b ? a : b);
  final low52 = yearBars.map((b) => b.low).reduce((a, b) => a < b ? a : b);
  final ma60 = tail.map((b) => b.close).fold<double>(0, (a, b) => a + b) / tail.length;

  final per = vp.currentPer;
  final yld = vp.currentYield;
  final perPct = vp.perPercentile;
  final yldPctile = vp.yieldPercentile;
  final eps = d.epsTtm;
  final div = d.annualCashDividend;

  // --- 價格區間 -------------------------------------------------------------
  // 這裡刻意不叫「買進區間」，叫「估值合理區」。
  //
  // 原因：用歷史本益比 20~40 百分位反推，對長期成長股會算出永遠等不到的價格
  // （例如獲利年年創高、股價沿著 60 倍本益比走，回推 30 百分位等於腰斬）。
  // 那種數字看起來很保守，實際上是把「不會發生」包裝成「紀律」。
  //
  // 改法：用「合理」而非「便宜」當基準。
  //   下緣 = 本益比 30 百分位 與 殖利率 5.5% 反推，取較高者（較嚴）
  //   上緣 = 本益比 55 百分位 與 殖利率 4.2% 反推，取較低者（較嚴）
  // 兩種方法都指向同一個區間，才有參考價值；分歧太大時只取本益比法並標註。
  double fairLow = 0, fairHigh = 0;
  String basis = '本益比歷史分位';
  final pe30 = (eps != null && eps > 0) ? _priceAtPerPercentile(vp, eps, 30) : null;
  final pe55 = (eps != null && eps > 0) ? _priceAtPerPercentile(vp, eps, 55) : null;
  final yLo = div > 0 ? div / 0.055 : null;
  final yHi = div > 0 ? div / 0.042 : null;

  if (pe30 != null && pe55 != null) {
    fairLow = pe30;
    fairHigh = pe55;
    if (yLo != null && yHi != null) {
      // 只在兩種方法差距 35% 以內時交叉校正，否則視為其中一種失效
      final ratio = yHi / pe55;
      if (ratio > 0.65 && ratio < 1.35) {
        fairLow = yLo > pe30 ? yLo : pe30;
        fairHigh = yHi < pe55 ? yHi : pe55;
        basis = '本益比分位 + 殖利率反推';
      }
    }
  } else if (yLo != null && yHi != null) {
    fairLow = yLo;
    fairHigh = yHi;
    basis = '殖利率反推（EPS 不適用）';
  } else {
    fairLow = ma60 * 0.94;
    fairHigh = ma60 * 1.04;
    basis = '季線 ±6%（估值資料不足）';
  }
  if (fairHigh <= fairLow) fairHigh = fairLow * 1.08;
  fairLow = _clamp(fairLow, low52 * 0.8, close * 1.4);
  fairHigh = _clamp(fairHigh, fairLow * 1.03, high52 * 1.15);

  // 減碼區間：本益比 80~92 百分位（歷史上的相對高檔）
  double trimLow = 0, trimHigh = 0;
  if (eps != null && eps > 0) {
    trimLow = _priceAtPerPercentile(vp, eps, 80) ?? 0;
    trimHigh = _priceAtPerPercentile(vp, eps, 92) ?? 0;
  }
  if (trimLow == 0) {
    trimLow = div > 0 ? div / 0.032 : high52 * 0.98;
    trimHigh = div > 0 ? div / 0.026 : high52 * 1.12;
  }
  if (trimHigh <= trimLow) trimHigh = trimLow * 1.12;
  if (trimLow < fairHigh) trimLow = fairHigh;

  // --- 買進評分 -------------------------------------------------------------
  final buyReasons = <String>[];
  final gates = <String>[];
  double score = 0;

  // 門檻 1：流動性
  if (turnoverAvg < 0.5) {
    return _Analysis.skip(
        '日均成交額僅 ${turnoverAvg.toStringAsFixed(2)} 億，低於 0.5 億門檻，進出容易滑價');
  }
  if (turnoverAvg >= 3) gates.add('日均成交額 ${turnoverAvg.toStringAsFixed(1)} 億，流動性充足');

  // 門檻 2：財務品質
  final fs = fq.score;
  if (fs != null && fs < 50) {
    return _Analysis.skip('財務檢核僅 $fs 分（門檻 50），多項指標未達標');
  }
  if (fs != null && fs >= 70) gates.add('財務檢核 $fs 分，體質通過');

  // 門檻 3：不能在營收崩跌時買
  final yoy = mo.threeMonthYoY ?? mo.latestYoY;
  if (yoy != null && yoy < -20) {
    return _Analysis.skip('近 3 月營收年減 ${(-yoy).toStringAsFixed(0)}%，超過 -20% 門檻');
  }

  // 門檻 4：不在極端高檔追價
  if (perPct != null && perPct > 85) {
    return _Analysis.skip(
        '本益比位於近 3 年 ${perPct.toStringAsFixed(0)} 百分位（門檻 85），屬絕對高檔不追價');
  }

  if (fs != null) {
    score += fs / 100 * 30;
    if (fs >= 80) {
      buyReasons.add('財務品質 $fs 分，近四季獲利與現金流結構穩健');
    }
  }
  if (perPct != null) {
    score += (100 - perPct) / 100 * 30;
    if (perPct <= 30) {
      buyReasons.add('本益比 ${per?.toStringAsFixed(1)} 倍，位於近 3 年 ${perPct.toStringAsFixed(0)} 百分位（相對低檔）');
    }
  }
  if (yld != null && yld > 0) {
    score += _clamp(yld / 6, 0, 1) * 20;
    if (yld >= 4) {
      buyReasons.add('殖利率 ${yld.toStringAsFixed(2)}%，高於台股長期平均');
    }
  }
  // 動能：連續正成長月數 + 3 月均 YoY
  final streakScore = _clamp(mo.positiveStreak / 6, 0, 1);
  final yoyScore = yoy == null ? 0.5 : _clamp((yoy + 20) / 60, 0, 1);
  score += (streakScore * 0.5 + yoyScore * 0.5) * 20;
  if (mo.positiveStreak >= 3) {
    buyReasons.add('月營收年增率已連續 ${mo.positiveStreak} 個月為正');
  } else if (mo.positiveStreak == 0) {
    buyReasons.add('營收動能尚未轉正（這是扣分項，也是必須等待的理由）');
  }
  if (yoy != null && yoy > 10) {
    buyReasons.add('近 3 月平均營收年增 ${yoy.toStringAsFixed(1)}%');
  }
  if (close < ma60 * 0.9) {
    buyReasons.add('現價低於季線 ${((1 - close / ma60) * 100).toStringAsFixed(1)}%，落入統計上的相對低區');
  }

  // --- 減碼評分 -------------------------------------------------------------
  final trimReasons = <String>[];
  double tScore = 0;

  if (perPct != null && perPct > 70) {
    tScore += _clamp((perPct - 70) / 30, 0, 1) * 30;
    trimReasons.add('本益比位於近 3 年 ${perPct.toStringAsFixed(0)} 百分位，估值已在歷史高檔');
  }
  if (mo.stage == MomentumStage.decelerating || mo.stage == MomentumStage.contracting) {
    tScore += 25;
    trimReasons.add('營收動能處於「${_stageLabel(mo.stage)}」，成長正在放緩');
  }
  if (mo.positiveStreak == 0 && (mo.latestYoY ?? 0) < 0) {
    tScore += 10;
    trimReasons.add('月營收年增率已轉負（${(mo.latestYoY ?? 0).toStringAsFixed(1)}%）');
  }
  if (fs != null && fs < 60) {
    tScore += _clamp((60 - fs) / 60, 0, 1) * 20;
    trimReasons.add('財務檢核僅 $fs 分，多項指標未達門檻');
  }
  final drawdown = (close / high52 - 1) * 100;
  if (drawdown < -20) {
    tScore += _clamp((-drawdown - 20) / 30, 0, 1) * 15;
    trimReasons.add('距 52 週高點已回落 ${(-drawdown).toStringAsFixed(1)}%，趨勢結構受損');
  }
  final divTrend = d.annualCashDividend;
  if (divTrend > 0 && d.dividends.length >= 2) {
    final prevYear = d.dividends[d.dividends.length - 2].cash;
    if (prevYear > 0 && divTrend < prevYear * 0.9) {
      tScore += 10;
      trimReasons.add('最近一年現金股利較前一年減少，配息能力在下滑');
    }
  }
  if (tScore > 0 && per != null && per > 30 && perPct != null && perPct > 80) {
    tScore += 5;
    trimReasons.add('本益比 ${per.toStringAsFixed(1)} 倍屬絕對高檔，需要極高的成長才能支撐');
  }

  // --- 觸發條件（不是建議，是「等到什麼才算數」）----------------------------
  final triggers = <String>[];
  if (mo.positiveStreak == 0) {
    triggers.add('月營收年增率轉正，且連續 2 個月維持（目前連續 ${mo.positiveStreak} 個月）');
  } else if (mo.positiveStreak < 3) {
    triggers.add('月營收年增率維持正值至連續 3 個月（目前 ${mo.positiveStreak} 個月）');
  }
  if (close > fairHigh) {
    triggers.add('股價回到估值合理區上緣 ${fairHigh.toStringAsFixed(1)} 元以下'
        '（目前高出 ${((close / fairHigh - 1) * 100).toStringAsFixed(1)}%）');
  } else if (close < fairLow) {
    triggers.add('確認股價低於合理區下緣 ${fairLow.toStringAsFixed(1)} 元的原因是市場整體下跌，'
        '而非公司基本面轉壞');
  } else {
    triggers.add('股價維持在估值合理區 ${fairLow.toStringAsFixed(1)}–${fairHigh.toStringAsFixed(1)} 元內');
  }
  if (close < ma60) {
    triggers.add('收盤站回季線 ${ma60.toStringAsFixed(1)} 元並維持 3 個交易日');
  }
  triggers.add('成交量放大至 60 日均量的 1.3 倍以上（確認而非猜測）');

  // --- 失效條件（這份判讀在什麼情況下就不成立）------------------------------
  final caveats = <String>[];
  if (eps == null || eps <= 0) {
    caveats.add('本益比區間推算不適用（EPS 為負或缺失），價格區間改以均線法估算，可信度較低');
  }
  if (vp.sampleDays < 250) {
    caveats.add('估值歷史樣本僅 ${vp.sampleDays} 天，分位數的代表性不足');
  }
  if (industryContains(d.info.industry, const ['金融', '保險'])) {
    caveats.add('金融股不適用本益比邏輯（損益受利率與提存影響大），區間請以股價淨值比為主要參考');
  }
  if (turnoverAvg < 1) {
    caveats.add('日均成交額僅 ${turnoverAvg.toStringAsFixed(1)} 億，進出容易滑價');
  }
  caveats.add('價格區間依據：$basis；若產業進入結構性變化（新技術替代、政策轉向），歷史分位會失效');
  caveats.add('本評分只用公開財務與價量資料，未含法人預估、訂單能見度與經營層訪談');

  return _Analysis.ok(Pick(
    id: sid,
    name: d.info.name,
    industry: d.info.industry,
    close: close,
    per: per,
    yieldPct: yld,
    perPct: perPct,
    yieldPctile: yldPctile,
    finScore: fs,
    revYoY: yoy,
    revStreak: mo.positiveStreak,
    stage: _stageLabel(mo.stage),
    ma60: ma60,
    high52: high52,
    low52: low52,
    turnoverAvg: turnoverAvg,
    buyLow: fairLow,
    buyHigh: fairHigh,
    trimLow: trimLow,
    trimHigh: trimHigh,
    buyScore: _clamp(score, 0, 100),
    trimScore: _clamp(tScore, 0, 100),
    buyReasons: buyReasons,
    trimReasons: trimReasons,
    triggers: triggers,
    gates: gates,
    caveats: caveats,
    basis: basis,
  ));
}

bool industryContains(String ind, List<String> keys) =>
    keys.any((k) => ind.contains(k));

String _stageLabel(MomentumStage s) {
  switch (s) {
    case MomentumStage.accelerating:
      return '加速成長';
    case MomentumStage.steady:
      return '穩定成長';
    case MomentumStage.decelerating:
      return '成長放緩';
    case MomentumStage.plateau:
      return '高檔持平';
    case MomentumStage.contracting:
      return '營收衰退';
    case MomentumStage.unknown:
      return '資料不足';
  }
}

// ---------------------------------------------------------------------------
// 主流程
// ---------------------------------------------------------------------------

Future<void> main(List<String> args) async {
  final outPath = _arg(args, '--out') ?? 'assets/data/daily_picks.json';
  final limit = int.tryParse(_arg(args, '--limit') ?? '') ?? candidatePool.length;
  final delay = int.tryParse(_arg(args, '--delay') ?? '') ?? 6200;
  final token = Platform.environment['FINMIND_TOKEN'];
  final cacheDir = Directory('tool/v2/cache');

  final pool = candidatePool.where((e) => !_etfLike.contains(e)).toSet().toList();
  final targets = pool.take(limit).toList();

  final perStock = _dailyDatasets.length + _fundDatasets.length; // 基礎資料另計 1 次
  stdout.writeln('SilverStock v2 每日掃描');
  stdout.writeln('  候選池 ${targets.length} 檔 · 每檔最多 $perStock 次請求'
      '（財報 30 天內只抓一次）');
  stdout.writeln('  額度 ${token != null ? "註冊 600/小時" : "匿名 300/小時"}，'
      '間隔 ${delay}ms');
  stdout.writeln('');

  final fetcher = Fetcher(token: token, delayMs: delay);

  // 公司名稱／產業一次抓全表（1 次請求），不要每檔各抓一次
  stdout.writeln('  抓取全市場基礎資料…');
  final infoRows = await fetcher.get('TaiwanStockInfo', '', '1970-01-01');
  final infoMap = <String, Map<String, dynamic>>{};
  for (final r in infoRows) {
    final m = (r as Map).cast<String, dynamic>();
    final sid0 = (m['stock_id'] ?? '').toString();
    if (sid0.isEmpty) continue;
    final prev = infoMap[sid0];
    if (prev == null ||
        (m['date'] ?? '').toString().compareTo((prev['date'] ?? '').toString()) > 0) {
      infoMap[sid0] = m;
    }
  }
  stdout.writeln('  基礎資料 ${infoMap.length} 檔');
  stdout.writeln('');

  final picks = <Pick>[];
  final excluded = <Map<String, String>>[];
  var i = 0;

  for (final sid in targets) {
    i++;
    final stamp = DateTime.now().toIso8601String().substring(0, 10);
    final cacheFile = File('${cacheDir.path}/${sid}_$stamp.json');

    // 財報：30 天內沿用快取。抽成函式是因為「當日行情快取存在但缺財報」
    // 這個情況會發生（例如先跑過一次不含財報的掃描），必須能補抓。
    Future<Map<String, dynamic>> loadFund() async {
      await cacheDir.create(recursive: true);
      final fundFile = File('${cacheDir.path}/fund_$sid.json');
      if (await fundFile.exists()) {
        final age = DateTime.now().difference((await fundFile.stat()).modified);
        if (age.inDays < _fundTtlDays) {
          return (jsonDecode(await fundFile.readAsString()) as Map)
              .cast<String, dynamic>();
        }
      }
      final fr = <String, dynamic>{};
      for (final dsName in _fundDatasets) {
        fr[dsName] = await fetcher.get(dsName, sid, _dateBack(2));
      }
      await fundFile.writeAsString(jsonEncode(fr));
      return fr;
    }

    StockDataset d;
    if (await cacheFile.exists()) {
      final bundle =
          jsonDecode(await cacheFile.readAsString()) as Map<String, dynamic>;
      final ds = (bundle['datasets'] as Map).cast<String, dynamic>();
      var note = '當日快取';
      if (!ds.containsKey('TaiwanStockFinancialStatements')) {
        ds.addAll(await loadFund());
        await cacheFile.writeAsString(jsonEncode(bundle));
        note = '當日快取 + 補財報';
      }
      d = parseDataset(bundle);
      stdout.writeln('[$i/${targets.length}] $sid  ($note)');
    } else {
      final ds = <String, dynamic>{};
      for (final e in _dailyDatasets.entries) {
        ds[e.key] = await fetcher.get(e.key, sid, _dateBack(e.value));
      }
      ds.addAll(await loadFund());
      final bundle = {
        'stock_id': sid,
        'fetched_at': stamp,
        'info': infoMap[sid] ?? const {},
        'datasets': ds,
      };
      await cacheFile.writeAsString(jsonEncode(bundle));
      d = parseDataset(bundle);
      stdout.writeln('[$i/${targets.length}] $sid  '
          '${d.info.name}  ${d.bars.length} 根K線');
    }

    try {
      final a = _analyze(sid, d);
      if (a.pick != null) {
        picks.add(a.pick!);
      } else {
        excluded.add({
          'id': sid,
          'name': d.info.name,
          'reason': a.excluded ?? '未通過門檻',
        });
      }
    } catch (e) {
      stderr.writeln('  ! $sid 分析失敗: $e');
      excluded.add({'id': sid, 'name': d.info.name, 'reason': '分析失敗：$e'});
    }
  }
  fetcher.close();

  // 排序：買進與減碼各自排名，同一批資料、兩套標準
  final buyTop = picks.toList()
    ..sort((a, b) => b.buyScore.compareTo(a.buyScore));
  // 減碼名單只留有實質警示的（≥15 分）。全為 0 分時寧可空著，
  // 也不要每天硬湊 10 檔——「今天沒有該減碼的」本身就是有用的結論。
  final trimTop = picks.where((p) => p.trimScore >= 15).toList()
    ..sort((a, b) => b.trimScore.compareTo(a.trimScore));

  final payload = {
    'generated_at': DateTime.now().toIso8601String(),
    'trade_date': _latestTradeDate(picks, targets),
    'universe': targets.length,
    'analyzed': picks.length,
    'requests': fetcher.calls,
    'method': {
      'buy': '財務品質 30% + 估值分位 30% + 殖利率 20% + 營收動能 20%；'
          '另有四道硬門檻：日均成交額 ≥ 0.5 億、財務檢核 ≥ 50 分、'
          '近 3 月營收年增 ≥ -20%、本益比百分位 ≤ 85',
      'trim': '估值分位 30% + 動能階段 25% + 營收轉負 10% + 財務 20% + '
          '距高點回落 15% + 股利衰退 10%；減碼名單不受買進門檻限制，'
          '全候選池一起排名',
      'range': '估值合理區 = 本益比 30 百分位（或殖利率 5.5% 反推，取較嚴）'
          '至 55 百分位（或殖利率 4.2%，取較嚴）；'
          '減碼區 = 本益比 80~92 百分位',
      'disclaimer': '本名單為量化條件篩選結果，非投資建議、非買賣推薦，'
          '不保證報酬。所有評分規則公開可重跑驗證。',
    },
    'buy': buyTop.take(10).map((p) => p.toJson()).toList(),
    'trim': trimTop.take(10).map((p) => p.toJson()).toList(),
    'excluded': excluded,
    'all': picks.map((p) => p.toJson()).toList(),
  };

  final f = File(outPath);
  await f.parent.create(recursive: true);
  await f.writeAsString(const JsonEncoder.withIndent('  ').convert(payload));

  stdout.writeln('');
  stdout.writeln('=== 買進觀察前 10 ===');
  for (final p in buyTop.take(10)) {
    stdout.writeln('${p.id} ${p.name.padRight(6)} '
        '${p.buyScore.toStringAsFixed(1).padLeft(5)} 分  '
        '合理區 ${p.buyLow.toStringAsFixed(1)}–${p.buyHigh.toStringAsFixed(1)}  '
        '現價 ${p.close.toStringAsFixed(1)}');
  }
  stdout.writeln('');
  stdout.writeln('=== 減碼觀察前 10 ===');
  for (final p in trimTop.take(10)) {
    stdout.writeln('${p.id} ${p.name.padRight(6)} '
        '${p.trimScore.toStringAsFixed(1).padLeft(5)} 分  '
        '減碼 ${p.trimLow.toStringAsFixed(1)}–${p.trimHigh.toStringAsFixed(1)}  '
        '現價 ${p.close.toStringAsFixed(1)}');
  }
  if (excluded.isNotEmpty) {
    stdout.writeln('');
    stdout.writeln('=== 未列入買進名單（${excluded.length} 檔）===');
    for (final e in excluded) {
      stdout.writeln('${e['id']} ${(e['name'] ?? '').padRight(6)} ${e['reason']}');
    }
  }
  stdout.writeln('');
  stdout.writeln('寫入 $outPath（${picks.length} 檔完成分析，'
      '${excluded.length} 檔未列入，${fetcher.calls} 次請求）');
}

String? _arg(List<String> args, String key) {
  final i = args.indexOf(key);
  if (i < 0 || i + 1 >= args.length) return null;
  return args[i + 1];
}

String _latestTradeDate(List<Pick> picks, List<String> targets) {
  // 由快取檔的日線最後一根推估；失敗就回今天
  try {
    for (final sid in targets) {
      final dir = Directory('tool/v2/cache');
      if (!dir.existsSync()) break;
      final files = dir
          .listSync()
          .whereType<File>()
          .where((f) => f.path.split('/').last.startsWith('${sid}_'))
          .toList();
      if (files.isEmpty) continue;
      final m = jsonDecode(files.first.readAsStringSync()) as Map;
      final bars = (m['datasets']?['TaiwanStockPrice'] as List?) ?? const [];
      if (bars.isNotEmpty) return bars.last['date'].toString();
    }
  } catch (_) {}
  return DateTime.now().toIso8601String().substring(0, 10);
}
