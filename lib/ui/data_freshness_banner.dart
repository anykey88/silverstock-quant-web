// V2.8 首頁資料時效橫幅：雙時間、三態標籤、時效總覽，淺底大字。
// 由 tool/v3/step2_freshness.py 產出。完全靜態，不顯示會跳動的裝置時鐘。
import 'package:flutter/material.dart';

import '../core/data_freshness.dart';
import '../core/data_freshness_data.dart';

class DataFreshnessBanner extends StatelessWidget {
  const DataFreshnessBanner({Key? key}) : super(key: key);

  Color _color(FreshnessState s) {
    switch (s) {
      case FreshnessState.intraday:
        return const Color(0xFFA8641C);
      case FreshnessState.todayClose:
        return const Color(0xFF2E7D5B);
      case FreshnessState.historical:
        return const Color(0xFF1F6F8B);
    }
  }

  Widget _timeCell(String label, String value) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFFF4F8F9),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontSize: 17, color: Color(0xFF5B6B78))),
            const SizedBox(height: 4),
            Text(value, style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w700)),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final items = DataFreshness.all;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: const Color(0xFFE3E0D5)),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('這筆資料是舊的還是新的？',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700)),
          const SizedBox(height: 12),
          Row(
            children: [
              _timeCell('行情時間（價格是哪一天）', FreshnessConst.quoteAsOf),
              const SizedBox(width: 12),
              _timeCell('資料更新（哪天去抓的）', FreshnessConst.capturedAt),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final it in items)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: _color(it.state).withOpacity(0.10),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text('${it.label}・${it.stateLabel}・落後 ${it.lagDays} 天',
                      style: TextStyle(fontSize: 17, color: _color(it.state),
                          fontWeight: FontWeight.w700)),
                ),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            '全部 ${FreshnessConst.nStocks} 檔裡，有 ${FreshnessConst.nStale} 檔落後超過 '
            '${FreshnessConst.staleThresholdDays} 天（${FreshnessConst.staleRatioPct}%），'
            '最多落後 ${FreshnessConst.maxLagDays} 天。',
            style: TextStyle(fontSize: 19),
          ),
          const SizedBox(height: 6),
          const Text(
            '資料標籤寫到 ${FreshnessConst.metaClaimedEnd}，但大盤軸實際只到 '
            '${FreshnessConst.indexActualLastDate}；回測用的是後者。'
            '${FreshnessConst.nStocks} 檔中 ${FreshnessConst.nStocksAtClaimedEnd} 檔到標籤那天。',
            style: TextStyle(fontSize: 17, color: Color(0xFFB03A2E)),
          ),
          const SizedBox(height: 6),
          const Text('兩個時間都是固定值；畫面不顯示現在幾點，避免誤會成即時價格。',
              style: TextStyle(fontSize: 17, color: Color(0xFF5B6B78))),
        ],
      ),
    );
  }
}
