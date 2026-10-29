// ============================================================================
// SilverStock-Quant-Web · 全局常量与合规词库
// ----------------------------------------------------------------------------
// 【参赛合规约束 · 必须保留】
// 1. 本文件中的免责声明文本为活动要求文本，任何页面必须原样展示，不可关闭、不可删减。
// 2. 本工具只做「公开历史数据整理 + 历史策略回测」，不构成投资建议、不预测股价、
//    无任何实盘下单功能。
// 3. 禁用词库用于合规风控守门 Agent 的后置扫描，禁止删除。
// ============================================================================

/// 全局固定免责声明（繁体中文逐字对照版，内容与活动要求文本完全一致，未增删任何字）。
const String kDisclaimer =
    '⚠️免責聲明：本工具僅整理台股公開歷史資料，執行策略歷史回測，僅作為學習復盤使用，'
    '不構成任何投資建議，歷史回測結果不等於未來收益，證券投資存在風險，'
    '請自行承擔全部投資風險，本工具無任何實盤交易下單功能。';

/// 简体原文备份（供代码审计比对用，页面不展示）。
const String kDisclaimerHans =
    '⚠️免责声明：本工具仅整理台股公开历史数据，执行策略历史回测，仅作为学习复盘使用，'
    '不构成任何投资建议，历史回测结果不等于未来收益，证券投资存在风险，'
    '请自行承担全部投资风险，本工具无任何实盘交易下单功能。';

/// 图表水印文字（回测曲线图强制叠加，不可关闭）。
const String kChartWatermark = '歷史回測不等於未來收益';

/// 版本与数据来源标注。
const String kAppVersion = 'v1.0.0 · 1024 造物挑戰參賽版';
const String kDataSourceNote =
    '資料來源：FinMind 公開歷史資料 API（免費非商用授權，僅限本次參賽 Demo 使用）。'
    '商業化需採購 FinMind 商業授權，禁止將免費 API 直接用於售賣。';

// ============================================================================
// 合规词库
// ============================================================================
class ComplianceLexicon {
  /// 高风险话术：命中即整份输出拦截，直接返回告警，不生成报告。
  static const List<String> hardBlock = <String>[
    '目標價', '目标价', '明牌', '保證', '保证', '必漲', '必涨', '飆股', '飙股',
    '財富自由', '财富自由', '翻倍', '穩賺', '稳赚', '包賺', '包赚', '內線', '内线',
    '漲停', '涨停', '預測股價', '预测股价', '帶進帶出', '带进带出', '老師帶', '老师带',
  ];

  /// 荐股类词汇：出现则自动改写为中性描述词，并记入风控日志。
  static const Map<String, String> softRewrite = <String, String>{
    '賺錢': '累積資產',
    '赚钱': '累积资产',
    '獲利': '報酬',
    '获利': '报酬',
    '把握行情': '觀察歷史走勢',
    '提高回報': '檢視歷史報酬',
    '提高回报': '检视历史报酬',
    '買入': '投入',
    '买入': '投入',
    '布局': '分批投入',
    '看好': '歷史表現較強',
    '進場': '開始投入',
    '进场': '开始投入',
    '加碼': '增加投入',
    '加码': '增加投入',
    '抄底': '低於長期均線時投入',
    '建議買': '可自行評估',
    '建议买': '可自行评估',
    '放空': '反向操作',
    '當沖': '短線交易',
    '当冲': '短线交易',
  };

  /// 白名单：策略模板的固定名称（活动设计文档指定名称），不视为荐股话术。
  static const List<String> templateWhitelist = <String>[
    '均線分批布局策略',
    '均线分批布局策略',
  ];

  /// 扫描文本，返回命中的禁用词。
  static List<String> scan(String text) {
    String probe = text;
    for (final w in templateWhitelist) {
      probe = probe.replaceAll(w, '〔策略名稱〕');
    }
    final hits = <String>[];
    for (final w in hardBlock) {
      if (probe.contains(w)) hits.add(w);
    }
    for (final w in softRewrite.keys) {
      if (probe.contains(w)) hits.add(w);
    }
    return hits;
  }

  /// 自动改写中性描述词。
  /// 注意：策略模板的固定名称（白名单）必须先保护起来，否则「均線分批布局策略」
  /// 会被改写成「均線分批分批投入策略」，反而破坏模板名称。
  static String rewrite(String text) {
    var out = text;
    final holders = <String, String>{};
    for (var i = 0; i < templateWhitelist.length; i++) {
      final w = templateWhitelist[i];
      if (out.contains(w)) {
        final ph = '\u0001WL$i\u0001';
        out = out.replaceAll(w, ph);
        holders[ph] = w;
      }
    }
    softRewrite.forEach((k, v) {
      out = out.replaceAll(k, v);
    });
    holders.forEach((ph, w) {
      out = out.replaceAll(ph, w);
    });
    return out;
  }

  static bool isHardBlock(String text) {
    String probe = text;
    for (final w in templateWhitelist) {
      probe = probe.replaceAll(w, '〔策略名稱〕');
    }
    return hardBlock.any(probe.contains);
  }
}

// ============================================================================
// 策略模板定义（仅 3 套，均为「歷史模擬投入」，不含任何買賣建議）
// ============================================================================
class StrategyDef {
  final String id;
  final String name;
  final String rule; // 規則說明（大白話）
  final String logic; // 觸發條件摘要
  const StrategyDef(this.id, this.name, this.rule, this.logic);
}

const List<StrategyDef> kStrategies = <StrategyDef>[
  StrategyDef(
    'yield_dca',
    '高殖利率定投策略',
    '每個月固定投入一筆錢；當當時的殖利率比較高（4% 以上），就多投入一些，'
        '殖利率特別高（5% 以上）再多投入一些。模擬「股利便宜時多買一點」的存股習慣。',
    '每月定額投入；殖利率 ≥ 4% 投入 1.5 倍、≥ 5% 投入 2 倍',
  ),
  StrategyDef(
    'ma_batch',
    '均線分批布局策略',
    '每個月固定投入基本金額；如果股價跌到季線（60 日均線）以下，就分批多投入一些，'
        '跌得越深分批越多。模擬「越跌越分批」的長期存股節奏。',
    '每月基本 1 份；低於季線 5% 加 1 份、低於季線 10% 加 2 份',
  ),
  StrategyDef(
    'low_per',
    '低本益比檢視策略',
    '只在「本益比低於這檔股票自己近 5 年中位數」的月份才投入，本益比偏高的月份先不投入，'
        '用來檢視「等便宜一點再存」在歷史上會長成什麼樣子。',
    '每月檢視本益比：≤ 中位數 0.85 倍投 2 份、≤ 1.0 倍投 1 份、≤ 1.1 倍投 0.5 份、其餘 0 份',
  ),
];

StrategyDef strategyById(String id) =>
    kStrategies.firstWhere((s) => s.id == id, orElse: () => kStrategies.first);

// ============================================================================
// 可選標的（首頁快選 6 檔；完整 30+ 檔由資料快照提供）
// ============================================================================
class StockMeta {
  final String id;
  final String name;
  final String industry;
  const StockMeta(this.id, this.name, this.industry);
}

/// 首頁快選（長輩最常聽到的 6 檔）；完整標的池由 MarketRepository 從資料快照載入。
const List<String> kQuickPickIds = <String>['2330', '2412', '2884', '0050', '0056', '1101'];

/// 產業分類（篩選器用；實際以資料檔的 industry 為準）
const List<String> kIndustries = <String>[
  '半導體',
  '電子零組件',
  '電子製造',
  '電腦及週邊',
  '電信',
  '金融',
  '傳產',
  'ETF',
];

/// 相容舊版：只保留 6 檔基本資料的靜態表（名稱仍以資料檔為準）
const List<StockMeta> kStockUniverse = <StockMeta>[
  StockMeta('2330', '台積電', '半導體'),
  StockMeta('2412', '中華電', '電信'),
  StockMeta('2884', '玉山金', '金融'),
  StockMeta('0050', '元大台灣50', 'ETF'),
  StockMeta('0056', '元大高股息', 'ETF'),
  StockMeta('1101', '台泥', '傳產'),
];

const double kMonthlyBudget = 10000; // 每月模擬投入金額（新台幣），僅為回測參數

/// 名詞小辭典（適老化：把專業術語講成大白話）。
const Map<String, String> kGlossary = <String, String>{
  '殖利率': '一年配到的現金股利 ÷ 目前股價。例如股價 100 元、一年配 5 元，殖利率就是 5%。',
  '本益比': '股價 ÷ 每股盈餘（EPS）。數字越大，代表市場願意用越高的價格買公司現在的一年盈餘。',
  '股價淨值比': '股價 ÷ 每股淨值。可以想成「用幾倍的價格買公司的帳面資產」。',
  'EPS': '每股盈餘，公司一年下來的盈餘分攤到每一股是多少元。是「賺多少」的會計數字。',
  '除權息': '公司把股利或股票發給股東的那一天，股價會先把配出去的金額扣掉，所以當天股價看起來會下跌，不是真的跌。',
  '季線（60日均線）': '最近 60 個交易日的平均收盤價，長輩常說的「季線」。用它來看現在價格是偏高還是偏低。',
  'KD': '看最近 9 天收盤價落在這段區間的高檔還是低檔，數值 0～100。',
  'RSI': '強弱指標，看最近漲的力量和跌的力量哪個大，數值 0～100。',
  'MACD': '用兩條不同速度的平均線差距，來看趨勢的方向和力道。',
  '最大回撤': '這段期間裡，資產從最高點掉到最低點的最大幅度。數字越大，代表中途心裡越難受。',
  '年化報酬': '把整段期間的結果換算成「一年大約幾 %」。這是把每筆投入的時間都算進去的內部報酬率（IRR）。',
  '勝率（年度）': '以每年年底結算，淨值比前一年高的年度占多少比例。',
};
