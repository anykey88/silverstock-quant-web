// 此頁大量使用動態主題色（cInk 等 getter），const 化收益有限
// ignore_for_file: prefer_const_constructors
// 學習路徑 + 版本記錄
import 'package:flutter/material.dart';

import '../data/market_repository.dart';
import '../ui/market_page.dart';
import '../ui/paper_page.dart';
import '../ui/screener_page.dart';
import '../ui/strategy_page.dart';
import '../ui/widgets.dart';

class LearnPage extends StatefulWidget {
  const LearnPage({Key? key}) : super(key: key);

  @override
  State<LearnPage> createState() => _LearnPageState();
}

class _LearnPageState extends State<LearnPage> with SingleTickerProviderStateMixin {
  late final TabController _tab = TabController(length: 2, vsync: this);

  @override
  void dispose() {
    _tab.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            const PersonalRiskBar(),
            Padding(
              padding: const EdgeInsets.fromLTRB(6, 6, 14, 0),
              child: Row(
                children: [
                  IconButton(
                    iconSize: 30,
                    onPressed: () => Navigator.of(context).maybePop(),
                    icon: const Icon(Icons.arrow_back_rounded),
                  ),
                  Expanded(
                    child: TabBar(
                      controller: _tab,
                      labelColor: cPrimary,
                      unselectedLabelColor: cInkSoft,
                      indicatorColor: cPrimary,
                      labelStyle: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w800),
                      tabs: const [
                        Tab(text: '學習路徑'),
                        Tab(text: '版本記錄'),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: TabBarView(
                controller: _tab,
                children: [
                  _learnTab(),
                  _changelogTab(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _learnTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 40),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 880),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              NoticeBar(
                icon: Icons.school_rounded,
                text: '8 堂課，每堂 3 分鐘。不用先懂財報，只要照著做一遍：'
                    '讀觀念 → 用工具驗證 → 開模擬單走一次。',
              ),
              const SizedBox(height: 12),
              for (var i = 0; i < _lessons.length; i++)
                _lessonCard(i + 1, _lessons[i]),
              const SizedBox(height: 8),
              const InlineDisclaimer(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _lessonCard(int no, _Lesson l) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: cSurface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: cLine, width: isHighContrast ? 2 : 1.2),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
          childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
          leading: Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: cPrimary.withOpacity(0.10),
              borderRadius: BorderRadius.circular(9),
            ),
            child: Center(
              child: Text('$no',
                  style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w900,
                      color: cPrimary)),
            ),
          ),
          title: Text(l.title,
              style: TextStyle(
                  fontSize: 16.5, fontWeight: FontWeight.w800, color: cInk)),
          subtitle: Text(l.oneLine,
              style: TextStyle(fontSize: 12.5, color: cInkSoft, height: 1.5)),
          children: [
            for (final p in l.points)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('・', style: TextStyle(fontSize: 14, color: cPrimary)),
                    Expanded(
                      child: Text(p,
                          style: TextStyle(
                              fontSize: 14, height: 1.65, color: cInk)),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 6),
            Align(
              alignment: Alignment.centerLeft,
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final a in l.actions)
                    OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size(0, 44),
                        padding: const EdgeInsets.symmetric(horizontal: 14),
                        textStyle: const TextStyle(
                            fontSize: 14, fontWeight: FontWeight.w700),
                      ),
                      onPressed: () => _go(a.target),
                      icon: Icon(a.icon, size: 18),
                      label: Text(a.label),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _go(String target) {
    Widget? page;
    switch (target) {
      case 'market':
        page = const MarketPage();
        break;
      case 'screener':
        page = const ScreenerPage();
        break;
      case 'strategy':
        page = const StrategyListPage();
        break;
      case 'paper':
        page = const PaperPage();
        break;
    }
    if (page != null) {
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => page!));
    }
  }

  Widget _changelogTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 40),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 880),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (final v in _versions) _versionCard(v),
              const SizedBox(height: 8),
              Text('資料快照：${MarketRepository.instance.capturedAt}'
                  '・${MarketRepository.instance.all.length} 档标的・加權指數 TAIEX',
                  style: TextStyle(fontSize: 12.5, color: cInkSoft)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _versionCard(_Version v) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: cSurface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
            color: v.current ? cPrimary : cLine,
            width: v.current ? 2 : 1.2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text('v${v.version}',
                  style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w900,
                      color: v.current ? cPrimary : cInk)),
              const SizedBox(width: 8),
              if (v.current)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: cPrimary,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Text('目前版本',
                      style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: Colors.white)),
                ),
              const Spacer(),
              Text(v.date,
                  style: TextStyle(fontSize: 12.5, color: cInkSoft)),
            ],
          ),
          const SizedBox(height: 4),
          Text(v.title,
              style: TextStyle(
                  fontSize: 14.5, fontWeight: FontWeight.w700, color: cInk)),
          const SizedBox(height: 8),
          for (final item in v.items)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('・', style: TextStyle(fontSize: 13, color: cInkSoft)),
                  Expanded(
                    child: Text(item,
                        style: TextStyle(
                            fontSize: 13.5, height: 1.55, color: cInkSoft)),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _Action {
  final String label;
  final IconData icon;
  final String target;
  const _Action(this.label, this.icon, this.target);
}

class _Lesson {
  final String title;
  final String oneLine;
  final List<String> points;
  final List<_Action> actions;
  const _Lesson(this.title, this.oneLine, this.points, this.actions);
}

const List<_Lesson> _lessons = <_Lesson>[
  _Lesson(
    '先想清楚：你要現金流，還是價差？',
    '同一個動作，目的不同，做法完全不同。',
    [
      '存股（現金流）：在意每年配多少、配得穩不穩，股價波動當背景雜訊。',
      '價差（波段）：在意進出價位與停損，配息只是順便。',
      '兩者混在一起最容易出事：想存股卻忍不住停損，想波段卻抱住不停損。',
      '先寫下來：這筆錢三年內會不會用到？會用到就不該放進波動大的標的。',
    ],
    [_Action('看市場溫度', Icons.thermostat_rounded, 'market')],
  ),
  _Lesson(
    '殖利率：高不代表好，可能只是股價跌出來的',
    '殖利率＝現金股利 ÷ 股價，分母跌，數字就漂亮。',
    [
      '看「連續配息幾年」比看單一年度高多少重要。',
      '配息突然大幅縮水，通常是盈餘先出問題（參考工具裡的配息紀錄與 EPS）。',
      '殖利率 8%、10% 的標的，先問：為什麼市場願意用這麼低的價格賣？',
      '用篩選器把「殖利率 ≥ 5% + 連續配息 ≥ 4 年」一起設，才不會只挑到便宜貨。',
    ],
    [_Action('打開選股篩選', Icons.filter_alt_rounded, 'screener')],
  ),
  _Lesson(
    '本益比：跟自己比，不要跟別人比',
    '同一檔股票，現在 20 倍是貴還是便宜？要看它自己過去幾年。',
    [
      '工具用的是「本益比 ÷ 自身 5 年中位數」，位階 80% 表示比過去多數時間貴。',
      '不同產業的本益比不能直接比（電信 25 倍和半導體 25 倍意義不同）。',
      '本益比是「股價 ÷ 盈餘」，盈餘若是一次性暴衝，本益比會假性變低。',
      '看位階之外，也要看 EPS 是成長還是衰退。',
    ],
    [_Action('看個股位階', Icons.insights_rounded, 'screener')],
  ),
  _Lesson(
    '除權息：除息當天股價下跌，不是賠錢',
    '配出去的錢從股價扣掉，你的總資產沒變。',
    [
      '除息參考價＝前一日收盤 − 配息金額，看起來跌，其實是左手換右手。',
      '真正影響報酬的是「有沒有填息」：填回去才是真的拿到。',
      '二代健保補充保費、股利所得稅會吃掉一部分，大額存股要算進去。',
      '工具裡的回測把股利當現金入帳，你可以選「股息再投入」看複利差異。',
    ],
    [_Action('看事件時間軸', Icons.timeline_rounded, 'screener')],
  ),
  _Lesson(
    '最大回撤：先問自己抱不抱得住',
    '報酬決定你想不想買，回撤決定你抱不抱得住。',
    [
      '最大回撤＝從高點掉到低點的最大幅度。掉 40% 要漲 67% 才回本。',
      '看到「年化 15%」很心動時，先看它的回撤是 15% 還是 45%。',
      '回測 5 年的回撤，通常低估了真正的風險（因為樣本裡可能沒遇到大空頭）。',
      '把回撤當成「入場費」：願意付，才進場。',
    ],
    [_Action('看市場溫度', Icons.thermostat_rounded, 'market')],
  ),
  _Lesson(
    '定期定額 vs 分批布局：兩種節奏的歷史差異',
    '沒有哪個一定好，差別在你能不能執行。',
    [
      '定期定額：不管價格，時間到就買。優點是不用判斷，缺點是高檔也買。',
      '分批布局：跌深才加碼。優點是成本低，缺點是可能一直等不到而錯過。',
      '工具裡兩套策略都內建，同一段歷史跑一次，看結果差多少。',
      '重點不是選哪個，是「先選一個，然後做滿 3 年」。',
    ],
    [_Action('比較策略', Icons.tune_rounded, 'strategy')],
  ),
  _Lesson(
    '停利停損：規則要在進場前寫好',
    '進場後才想的規則，通常會被情緒改寫。',
    [
      '停損是「承認判斷錯」的成本，不是失敗。',
      '停利可以用「報酬 %」或「殖利率跌破」兩種，前者抓價差、後者顧存股本質。',
      '同一組參數在不同標的表現差很多，所以要用同一套規則跑過 5 檔再定案。',
      '回測時看「勝率」不如看「獲利因子」與「最大單筆虧損」。',
    ],
    [_Action('調整策略參數', Icons.tune_rounded, 'strategy')],
  ),
  _Lesson(
    '建立自己的模式：從一檔、一個策略、一筆模擬單開始',
    '不要一次學完所有東西，先跑完一次完整循環。',
    [
      '第 1 步：用篩選器挑 1 檔你看得懂的（產業你聽過、產品你用過）。',
      '第 2 步：用 5 年資料回測，看它在最壞的時候長什麼樣。',
      '第 3 步：到模擬盤用虛擬資金買一次，體驗「抱單」的感覺。',
      '第 4 步：三個月後回頭看：當初為什麼買？理由還成立嗎？',
      '把它寫下來，就是你的第一個投資模式。',
    ],
    [
      _Action('開始選股', Icons.filter_alt_rounded, 'screener'),
      _Action('開模擬單', Icons.shopping_cart_rounded, 'paper'),
    ],
  ),
];

class _Version {
  final String version;
  final String date;
  final String title;
  final List<String> items;
  final bool current;
  const _Version(this.version, this.date, this.title, this.items,
      {this.current = false});
}

const List<_Version> _versions = <_Version>[
  _Version(
    '2.0.0',
    '2026/10/29',
    '名稱搜尋 + 自選股 + 每日精選',
    [
      '新增「名稱搜尋」：輸入名稱的任何片段就找到代號（台積／積電／鴻海都行），全台股 3171 檔',
      '新增「簡繁互通」：內建 390 字繁簡對照，大陸用簡體打「台积电」也搜得到「台積電」',
      '新增「我的自選股」：選中即自動加入，可管理、刪除、複製成文字清單，存在本機',
      '新增「每日精選」：每個交易日收盤後掃描候選池，產出買進觀察前 10 與減碼觀察名單',
      '每一檔附「估值合理區」（本益比分位或殖利率反推）、觸發條件、失效條件',
      '新增「未列入原因」：沒進名單的標的逐條說明為什麼（財務不過、估值過高、營收衰退）',
      '價格區間算法重做：原本用 20~40 百分位反推，對成長股會算出永遠等不到的價位，改以「合理」而非「便宜」為基準',
      '新增 v2 分析引擎：本益比／殖利率／股價淨值比歷史分位、財務品質十餘項檢核、營收動能階段判斷、歷史條件機率',
      '新增 GitHub Actions 每日自動掃描（台北時間 14:30），可選微信推送',
    ],
    current: true,
  ),
  _Version(
    '1.2.0',
    '2026/10/25',
    '市場觀察 + 個股檔案 + 模擬盤 + 學習路徑',
    [
      '新增「市場觀察」：加權指數位階、量能、20 日波動、市場廣度、五檔產業溫度',
      '新增「歷史條件機率」：指數在年線上下時，之後 20/60 日的報酬分布（只描述過去，不預測）',
      '新增「個股檔案」：價格＋成交量＋季線走勢圖、52 週高低、事件時間軸（除息／財報／高低點）',
      '新增「模擬交易盤」：虛擬 100 萬，模擬買賣、持倉損益、逐筆紀錄，含手續費與證交稅',
      '新增「學習路徑」：8 堂課，每堂都連到對應工具直接驗證',
      '新增「版本記錄」頁（就是這一頁）',
      '資料升級：33 檔標的加入每日成交量、加權指數 TAIEX 全期資料',
      '修正：0050 分割（2025-06-18 一分四）歷史價量同步還原，避免假的 -75% 斷崖',
    ],
  ),
  _Version(
    '1.1.0',
    '2026/10/25',
    '雙模式 + 選股 + 交易策略',
    [
      '新增「個人自用版 / 比賽合規版」一鍵切換：自用版解鎖選股與交易策略，比賽版保留固定免責與風控攔截',
      '新增「選股篩選與評分」：殖利率／評價／配息／成長／風險五維打分，附逐條理由',
      '新增「交易策略編輯器」：進場、加碼、停利停損、資金管理、成本假設可自訂',
      '新增「完整交易回測」：含手續費、證交稅、除息、期末持倉，輸出勝率、獲利因子、逐筆明細',
      '新增「無交易引導」：條件太嚴時提示原因並可一鍵放寬重跑',
      '標的池從 6 檔擴到 33 檔（半導體／電子／電信／金融／傳產／ETF）',
    ],
  ),
  _Version(
    '1.0.0',
    '2026/10/24',
    '首版：存股歷史回測',
    [
      '5 個 Agent 依序協作：基本面 → 技術指標 → 量化回測 → 適老化翻譯 → 合規風控',
      '3 套存股模板：高殖利率定投／均線分批／低本益比檢視',
      '大字適老化介面、字體三檔、高對比模式、國語／台語語音朗讀',
      '固定免責聲明、圖表水印、本機存檔',
    ],
  ),
];
