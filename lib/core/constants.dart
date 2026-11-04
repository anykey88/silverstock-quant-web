// ============================================================================
// SilverStock · 全局常量
// ----------------------------------------------------------------------------
// v2.2：移除舊版聲明文案、圖表水印與用詞改寫表。
// 這是自用實戰工具，不做對外發佈，介面不再插入任何警語橫幅。
// ============================================================================

/// 版本号。顯示於首頁右上角。
const String kAppVersion = 'v2.6.0';

/// 資料來源標註。
const String kDataSourceNote =
    '資料來源：FinMind 公開歷史資料 API。行情為收盤後資料，非即時報價。';

// ============================================================================
// 輸出用词表
// ============================================================================
class ComplianceLexicon {
  /// 高風險話術：僅用於內部輸出守門，不再對使用者展示。
  static const List<String> hardBlock = <String>[
    '目標價', '目标价', '明牌', '保證', '保证', '必漲', '必涨', '飆股', '飙股',
    '財富自由', '财富自由', '翻倍', '穩賺', '稳赚', '包賺', '包赚', '內線', '内线',
    '漲停', '涨停', '預測股價', '预测股价', '帶進帶出', '带进带出', '老師帶', '老师带',
  ];

  /// v2.2：改寫表已清空。介面直接使用「買進／賣出／加碼」等交易詞，
  /// 不再改寫成「投入／報酬」這類繞口的替代詞。
  static const Map<String, String> softRewrite = <String, String>{};

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
  '電信',
  '金融',
  '水泥',
  '鋼鐵',
  '塑化',
  '食品',
  '汽車',
  'ETF',
  '天然氣',
  '紡織',
  '電機',
  '航運',
  '營造',
  '不動產',
  '生技醫療',
  '化工',
  '百貨零售',
  '機械',
  '自行車',
  '建材',
  '觀光飯店',
  '餐飲',
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
