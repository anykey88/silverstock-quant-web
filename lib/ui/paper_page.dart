// 此頁大量使用動態主題色與字串插值
// ignore_for_file: prefer_const_constructors, unnecessary_brace_in_string_interps
// 模擬交易盤：用虛擬資金走完「下單 → 持有 → 出場」的完整流程
import 'package:flutter/material.dart';

import '../core/formatters.dart';
import '../data/market_repository.dart';
import '../services/paper_account.dart';
import '../ui/theme.dart';
import '../ui/widgets.dart';

class PaperPage extends StatefulWidget {
  final String? presetStockId;
  const PaperPage({Key? key, this.presetStockId}) : super(key: key);

  @override
  State<PaperPage> createState() => _PaperPageState();
}

class _PaperPageState extends State<PaperPage> {
  bool _loading = true;
  PaperAccount _acc = PaperAccount.empty();
  String _side = 'buy';
  String? _stockId;
  final TextEditingController _sharesCtrl = TextEditingController(text: '1000');

  @override
  void initState() {
    super.initState();
    _stockId = widget.presetStockId;
    _load();
  }

  @override
  void dispose() {
    _sharesCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    await MarketRepository.instance.ensureLoaded();
    if (!mounted) return;
    setState(() {
      _acc = PaperStore.load();
      _stockId ??= MarketRepository.instance.all.isNotEmpty
          ? MarketRepository.instance.all.first.id
          : null;
      _loading = false;
    });
    _suggestShares();
  }

  void _persist() => PaperStore.save(_acc);

  /// 依本金與現價，預設一個買得起的股數（避免一開始就「現金不足」）
  void _suggestShares() {
    if (_stockId == null) return;
    final p = _priceOf(_stockId!);
    if (p <= 0) return;
    final afford = (_acc.cash / p).floor();
    final sh = afford >= 1000 ? 1000 : (afford >= 100 ? (afford ~/ 100) * 100 : afford);
    _sharesCtrl.text = '$sh';
    if (mounted) setState(() {});
  }

  double _priceOf(String id) {
    final s = MarketRepository.instance.series(id);
    if (s == null || s.closes.isEmpty) return 0;
    return s.closes.last;
  }

  double get _marketValue {
    var v = 0.0;
    _acc.positions.forEach((k, p) {
      v += _priceOf(k) * p.shares;
    });
    return v;
  }

  double get _unrealized {
    var v = 0.0;
    _acc.positions.forEach((k, p) {
      v += (_priceOf(k) - p.avgCost) * p.shares;
    });
    return v;
  }

  double get _equity => _acc.cash + _marketValue;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            const PersonalRiskBar(),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(14, 12, 14, 40),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 900),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              _topBar(),
                              _accountCard(),
                              _orderCard(),
                              _positionCard(),
                              _historyCard(),
                              const SizedBox(height: 8),
                              const InlineDisclaimer(),
                            ],
                          ),
                        ),
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _topBar() => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          children: [
            IconButton(
              iconSize: 30,
              onPressed: () => Navigator.of(context).maybePop(),
              icon: const Icon(Icons.arrow_back_rounded),
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('模擬交易盤',
                      style: TextStyle(
                          fontSize: 21,
                          fontWeight: FontWeight.w900,
                          color: cInk)),
                  Text('虛擬資金・與真實券商無關・資料存本機',
                      style: TextStyle(fontSize: 12.5, color: cInkSoft)),
                ],
              ),
            ),
            TextButton(
              onPressed: _reset,
              child: const Text('重置'),
            ),
          ],
        ),
      );

  Widget _accountCard() {
    final pnl = _equity - _acc.initialCapital;
    final pnlPct =
        _acc.initialCapital <= 0 ? 0.0 : pnl / _acc.initialCapital * 100;
    return SectionCard(
      title: '帳戶總覽',
      icon: Icons.account_balance_wallet_rounded,
      subtitle: '成交價＝資料最新收盤價；含手續費 6 折、證交稅。',
      child: Column(
        children: [
          LayoutBuilder(builder: (ctx, c) {
            final perRow = c.maxWidth > 620 ? 4 : 2;
            final w = (c.maxWidth - (perRow - 1) * 10) / perRow;
            return Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '總權益',
                      value: money(_equity),
                      note: '本金 ${money(_acc.initialCapital)}',
                      color: cInk,
                      big: true,
                    )),
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '報酬率',
                      value: signedPct(pnlPct),
                      note: '損益 ${money(pnl)}',
                      color: pnl >= 0 ? AppColors.up : AppColors.down,
                    )),
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '現金',
                      value: money(_acc.cash),
                      color: AppColors.primary,
                    )),
                SizedBox(
                    width: w,
                    child: MetricTile(
                      label: '未實現損益',
                      value: money(_unrealized),
                      note: '已實現 ${money(_acc.realizedPnl)}',
                      color: _unrealized >= 0 ? AppColors.up : AppColors.down,
                    )),
              ],
            );
          }),
        ],
      ),
    );
  }

  Widget _orderCard() {
    final stocks = MarketRepository.instance.all;
    final selected = _stockId == null
        ? null
        : MarketRepository.instance.series(_stockId!);
    final price = selected == null ? 0.0 : selected.closes.last;
    final shares = int.tryParse(_sharesCtrl.text.trim()) ?? 0;
    final gross = price * shares;
    final fee = gross <= 0
        ? 0.0
        : (_side == 'buy' ? TradeCost.buyFee(gross) : TradeCost.sellFee(gross));
    final tax = _side == 'buy'
        ? 0.0
        : TradeCost.tax(gross, isEtf: selected?.industry == 'ETF');
    final total = _side == 'buy' ? gross + fee : gross - fee - tax;

    return SectionCard(
      title: '下單（模擬）',
      icon: Icons.shopping_cart_rounded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          DropdownButtonFormField<String>(
            value: _stockId,
            isExpanded: true,
            style: TextStyle(
                fontSize: 16, fontWeight: FontWeight.w700, color: cInk),
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search_rounded),
              labelText: '標的',
            ),
            items: [
              for (final s in stocks)
                DropdownMenuItem<String>(
                  value: s.id,
                  child: Text(
                      '${s.name}（${s.id}） ${s.closes.last.toStringAsFixed(2)}',
                      overflow: TextOverflow.ellipsis),
                ),
            ],
            onChanged: (v) {
              setState(() => _stockId = v);
              _suggestShares();
            },
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: ChoicePill(
                  label: '買進',
                  selected: _side == 'buy',
                  onTap: () => setState(() => _side = 'buy'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ChoicePill(
                  label: '賣出',
                  selected: _side == 'sell',
                  onTap: () => setState(() => _side = 'sell'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _sharesCtrl,
            keyboardType: TextInputType.number,
            style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w700),
            decoration: InputDecoration(
              labelText: '股數（可輸入 100、500、1000）',
              prefixIcon: const Icon(Icons.tag_rounded),
              suffixText: price > 0
                  ? '≈ ${money(gross)} 元'
                  : null,
            ),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final amt in <int>[10000, 30000, 50000, 100000])
                ChoicePill(
                  label: '${amt ~/ 10000} 萬',
                  selected: false,
                  onTap: price <= 0
                      ? null
                      : () {
                          final sh = (amt / price / 1000).floor() * 1000;
                          setState(() =>
                              _sharesCtrl.text = sh <= 0 ? '1' : '$sh');
                        },
                ),
              ChoicePill(
                label: '全部',
                selected: false,
                onTap: () {
                  if (_side == 'sell') {
                    final p = _acc.positions[_stockId];
                    if (p != null) {
                      setState(() => _sharesCtrl.text = '${p.shares}');
                    }
                  } else if (price > 0) {
                    final sh = (_acc.cash / (price * 1.001) / 100).floor() * 100;
                    setState(() => _sharesCtrl.text = sh <= 0 ? '0' : '$sh');
                  }
                },
              ),
            ],
          ),
          const SizedBox(height: 10),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: isHighContrast ? Colors.black : const Color(0xFFF7F3EA),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: cLine),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _kv('成交價（最新收盤）', price <= 0 ? '—' : '${price.toStringAsFixed(2)} 元'),
                _kv('成交金額', '${money(gross)} 元'),
                _kv('手續費', '${money(fee)} 元'),
                if (_side == 'sell') _kv('證交稅', '${money(tax)} 元'),
                _kv(_side == 'buy' ? '需要現金' : '可收回',
                    '${money(total)} 元'),
              ],
            ),
          ),
          const SizedBox(height: 10),
          ActionButton(
            label: _side == 'buy' ? '確認買進' : '確認賣出',
            icon: _side == 'buy'
                ? Icons.trending_up_rounded
                : Icons.trending_down_rounded,
            onPressed: shares > 0 ? () => _submit(shares, price, fee, tax) : null,
          ),
        ],
      ),
    );
  }

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.only(bottom: 3),
        child: Row(
          children: [
            Expanded(
                child: Text(k,
                    style: TextStyle(fontSize: 13.5, color: cInkSoft))),
            Text(v,
                style: TextStyle(
                    fontSize: 14, fontWeight: FontWeight.w700, color: cInk)),
          ],
        ),
      );

  void _submit(int shares, double price, double fee, double tax) {
    final s = MarketRepository.instance.series(_stockId!);
    if (s == null || price <= 0 || shares <= 0) return;
    final gross = price * shares;

    if (_side == 'buy') {
      final need = gross + fee;
      if (need > _acc.cash) {
        _snack('現金不足：需要 ${money(need)} 元，帳上只有 ${money(_acc.cash)} 元。');
        return;
      }
      _acc.cash -= need;
      final pos = _acc.positions[s.id];
      if (pos == null) {
        _acc.positions[s.id] =
            PaperPosition(s.id, s.name, shares, need / shares);
      } else {
        final newShares = pos.shares + shares;
        pos.avgCost = (pos.avgCost * pos.shares + need) / newShares;
        pos.shares = newShares;
      }
      _acc.trades.insert(
        0,
        PaperTrade(
          id: '${DateTime.now().millisecondsSinceEpoch}',
          stockId: s.id,
          stockName: s.name,
          side: 'buy',
          price: price,
          shares: shares,
          fee: fee,
          tax: 0,
          time: nowStamp(),
        ),
      );
    } else {
      final pos = _acc.positions[s.id];
      if (pos == null || pos.shares < shares) {
        _snack('持倉不足：目前只有 ${pos?.shares ?? 0} 股。');
        return;
      }
      final net = gross - fee - tax;
      final realized = net - pos.avgCost * shares;
      _acc.cash += net;
      _acc.realizedPnl += realized;
      pos.shares -= shares;
      if (pos.shares <= 0) _acc.positions.remove(s.id);
      _acc.trades.insert(
        0,
        PaperTrade(
          id: '${DateTime.now().millisecondsSinceEpoch}',
          stockId: s.id,
          stockName: s.name,
          side: 'sell',
          price: price,
          shares: shares,
          fee: fee,
          tax: tax,
          time: nowStamp(),
          realized: realized,
        ),
      );
    }
    _persist();
    setState(() {});
    _snack(_side == 'buy'
        ? '已模擬買進 ${s.name} ${shares} 股（${money(gross)} 元）'
        : '已模擬賣出 ${s.name} ${shares} 股');
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(m), duration: const Duration(seconds: 3)),
      );

  Future<void> _reset() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('重置模擬帳戶？'),
        content: const Text('所有模擬持倉與紀錄會清空，本金回到 100 萬元。'),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('取消')),
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text('確定重置')),
        ],
      ),
    );
    if (ok != true) return;
    PaperStore.reset();
    setState(() => _acc = PaperStore.load());
  }

  Widget _positionCard() {
    final list = _acc.positions.values.toList();
    return SectionCard(
      title: '目前持倉（${list.length} 檔）',
      icon: Icons.inventory_2_rounded,
      child: list.isEmpty
          ? Text('還沒有任何持倉。可以先用上面的「買進」模擬一筆。',
              style: TextStyle(fontSize: 14, color: cInkSoft))
          : Column(
              children: [
                for (final p in list)
                  Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: cLine),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('${p.stockName}（${p.stockId}）',
                                  style: TextStyle(
                                      fontSize: 15.5,
                                      fontWeight: FontWeight.w800,
                                      color: cInk)),
                              Text(
                                '$p.shares 股・成本 ${p.avgCost.toStringAsFixed(2)}'
                                '・現價 ${_priceOf(p.stockId).toStringAsFixed(2)}',
                                style: TextStyle(
                                    fontSize: 12.5, color: cInkSoft),
                              ),
                            ],
                          ),
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(
                              money((_priceOf(p.stockId) - p.avgCost) * p.shares),
                              style: TextStyle(
                                  fontSize: 14.5,
                                  fontWeight: FontWeight.w800,
                                  color: _priceOf(p.stockId) >= p.avgCost
                                      ? AppColors.up
                                      : AppColors.down),
                            ),
                            Text(
                              signedPct(p.avgCost <= 0
                                  ? 0
                                  : (_priceOf(p.stockId) / p.avgCost - 1) * 100),
                              style: TextStyle(
                                  fontSize: 12,
                                  color: _priceOf(p.stockId) >= p.avgCost
                                      ? AppColors.up
                                      : AppColors.down),
                            ),
                          ],
                        ),
                        const SizedBox(width: 6),
                        TextButton(
                          onPressed: () {
                            setState(() {
                              _side = 'sell';
                              _stockId = p.stockId;
                              _sharesCtrl.text = '${p.shares}';
                            });
                          },
                          child: const Text('賣出'),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
    );
  }

  Widget _historyCard() {
    return SectionCard(
      title: '交易紀錄（${_acc.trades.length} 筆）',
      icon: Icons.receipt_long_rounded,
      child: _acc.trades.isEmpty
          ? Text('還沒有交易紀錄。',
              style: TextStyle(fontSize: 14, color: cInkSoft))
          : Column(
              children: [
                for (final t in _acc.trades.take(12))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(
                      children: [
                        Container(
                          width: 40,
                          padding: const EdgeInsets.symmetric(vertical: 3),
                          decoration: BoxDecoration(
                            color: (t.side == 'buy'
                                    ? AppColors.up
                                    : AppColors.down)
                                .withOpacity(0.12),
                            borderRadius: BorderRadius.circular(5),
                          ),
                          child: Center(
                            child: Text(t.side == 'buy' ? '買' : '賣',
                                style: TextStyle(
                                    fontSize: 12.5,
                                    fontWeight: FontWeight.w800,
                                    color: t.side == 'buy'
                                        ? AppColors.up
                                        : AppColors.down)),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                  '${t.stockName} ${t.shares} 股 @ ${t.price.toStringAsFixed(2)}',
                                  style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w700,
                                      color: cInk)),
                              Text(t.time,
                                  style: TextStyle(
                                      fontSize: 11.5, color: cInkSoft)),
                            ],
                          ),
                        ),
                        if (t.side == 'sell')
                          Text(
                            '${t.realized >= 0 ? '+' : ''}${money(t.realized)}',
                            style: TextStyle(
                                fontSize: 13.5,
                                fontWeight: FontWeight.w800,
                                color: t.realized >= 0
                                    ? AppColors.up
                                    : AppColors.down),
                          ),
                      ],
                    ),
                  ),
                if (_acc.trades.length > 12)
                  Text('（只顯示最近 12 筆）',
                      style: TextStyle(fontSize: 12, color: cInkSoft)),
              ],
            ),
    );
  }
}
