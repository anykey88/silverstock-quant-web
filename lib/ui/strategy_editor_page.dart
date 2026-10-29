// 交易策略編輯頁（個人自用版）
import 'package:flutter/material.dart';

import '../core/formatters.dart';
import '../models/trade_strategy.dart';
import '../services/strategy_store.dart';
import '../ui/widgets.dart';

class StrategyEditorPage extends StatefulWidget {
  final TradeStrategy? origin;
  const StrategyEditorPage({Key? key, this.origin}) : super(key: key);

  @override
  State<StrategyEditorPage> createState() => _StrategyEditorPageState();
}

class _StrategyEditorPageState extends State<StrategyEditorPage> {
  late TextEditingController _name;
  late bool _useYield, _usePer, _useRsi, _useTp, _useSl, _useExitYield, _reinvest;
  late double _yieldMin, _perRatio, _rsiMax, _maPct;
  late String _maMode;
  late double _addPct;
  late int _maxAdds;
  late double _tp, _sl, _exitYield;
  late double _capital, _tranche, _maxPos;
  late double _feeDiscount;
  late String _frequency;

  @override
  void initState() {
    super.initState();
    final s = widget.origin ??
        const TradeStrategy(id: 'new', name: '我的策略', note: '');
    _name = TextEditingController(text: s.name);
    _useYield = s.entryYieldMin != null;
    _usePer = s.entryPerRatio != null;
    _useRsi = s.entryRsiMax != null;
    _useTp = s.takeProfitPct != null;
    _useSl = s.stopLossPct != null;
    _useExitYield = s.exitYieldBelow != null;
    _reinvest = s.reinvestDividend;
    _yieldMin = s.entryYieldMin ?? 5;
    _perRatio = s.entryPerRatio ?? 1.0;
    _rsiMax = s.entryRsiMax ?? 60;
    _maMode = s.maMode;
    _maPct = s.maPct;
    _addPct = s.addOnDropPct == 0 ? 8 : s.addOnDropPct;
    _maxAdds = s.maxAdds == 0 ? 3 : s.maxAdds;
    _tp = s.takeProfitPct ?? 25;
    _sl = s.stopLossPct ?? 15;
    _exitYield = s.exitYieldBelow ?? 3;
    _capital = s.totalCapital;
    _tranche = s.trancheAmount;
    _maxPos = s.maxPositionPct;
    _feeDiscount = s.feeDiscount;
    _frequency = s.frequency;
  }

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  TradeStrategy _build() {
    final origin = widget.origin;
    return TradeStrategy(
      id: origin?.id ?? 'custom_${DateTime.now().millisecondsSinceEpoch}',
      name: _name.text.trim().isEmpty ? '未命名策略' : _name.text.trim(),
      note: origin?.note ?? '自訂策略',
      entryYieldMin: _useYield ? _yieldMin : null,
      entryPerRatio: _usePer ? _perRatio : null,
      maMode: _maMode,
      maPct: _maPct,
      entryRsiMax: _useRsi ? _rsiMax : null,
      addOnDropPct: _addPct,
      maxAdds: _maxAdds,
      takeProfitPct: _useTp ? _tp : null,
      stopLossPct: _useSl ? _sl : null,
      exitYieldBelow: _useExitYield ? _exitYield : null,
      totalCapital: _capital,
      trancheAmount: _tranche,
      maxPositionPct: _maxPos,
      feeDiscount: _feeDiscount,
      reinvestDividend: _reinvest,
      frequency: _frequency,
    );
  }

  void _save() {
    final s = _build();
    StrategyStore.save(s);
    Navigator.of(context).pop(s);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            const PersonalRiskBar(),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(14, 12, 14, 40),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 820),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _topBar(),
                        _nameCard(),
                        _entryCard(),
                        _exitCard(),
                        _capitalCard(),
                        _costCard(),
                        const SizedBox(height: 8),
                        ActionButton(
                          label: '儲存策略',
                          icon: Icons.save_rounded,
                          onPressed: _save,
                        ),
                        const SizedBox(height: 10),
                        Text('提示：參數只是模擬設定，回測結果只代表過去，不代表未來。',
                            style:
                                TextStyle(fontSize: 12.5, color: cInkSoft)),
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
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(
          children: [
            IconButton(
              iconSize: 30,
              onPressed: () => Navigator.of(context).maybePop(),
              icon: const Icon(Icons.arrow_back_rounded),
            ),
            Expanded(
              child: Text(widget.origin == null ? '新增交易策略' : '編輯交易策略',
                  style: TextStyle(
                      fontSize: 20, fontWeight: FontWeight.w900, color: cInk)),
            ),
          ],
        ),
      );

  Widget _nameCard() => SectionCard(
        title: '策略名稱',
        icon: Icons.drive_file_rename_outline_rounded,
        child: TextField(
          controller: _name,
          style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
          decoration: const InputDecoration(hintText: '例如：我的高息分批'),
        ),
      );

  Widget _entryCard() {
    return SectionCard(
      title: '進場條件（同時符合才會買）',
      icon: Icons.login_rounded,
      subtitle: '留空表示不看該條件。多個條件是「而且」的關係。',
      child: Column(
        children: [
          _switchTile('殖利率 ≥ ${_yieldMin.toStringAsFixed(1)}%', _useYield,
              (v) => setState(() => _useYield = v)),
          if (_useYield)
            _slider(_yieldMin, 0, 9, 0.5, (v) => setState(() => _yieldMin = v)),
          _switchTile(
              '本益比 ≤ 自身 5 年中位數 × ${_perRatio.toStringAsFixed(2)}',
              _usePer,
              (v) => setState(() => _usePer = v)),
          if (_usePer)
            _slider(_perRatio, 0.5, 1.5, 0.05, (v) => setState(() => _perRatio = v)),
          const SizedBox(height: 6),
          Align(
            alignment: Alignment.centerLeft,
            child: Text('季線條件',
                style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: cInkSoft)),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              ChoicePill(
                label: '不限',
                selected: _maMode == 'any',
                onTap: () => setState(() => _maMode = 'any'),
              ),
              ChoicePill(
                label: '跌破季線',
                selected: _maMode == 'below',
                onTap: () => setState(() => _maMode = 'below'),
              ),
              ChoicePill(
                label: '站上季線',
                selected: _maMode == 'above',
                onTap: () => setState(() => _maMode = 'above'),
              ),
            ],
          ),
          if (_maMode != 'any')
            _slider(_maPct, 0, 15, 1,
                (v) => setState(() => _maPct = v),
                suffix: '%'),
          _switchTile('RSI ≤ ${_rsiMax.toStringAsFixed(0)}（避免追高）', _useRsi,
              (v) => setState(() => _useRsi = v)),
          if (_useRsi)
            _slider(_rsiMax, 20, 90, 5, (v) => setState(() => _rsiMax = v)),
        ],
      ),
    );
  }

  Widget _exitCard() {
    return SectionCard(
      title: '加碼與出場',
      icon: Icons.logout_rounded,
      subtitle: '出場條件每日檢查；停損優先於停利。',
      child: Column(
        children: [
          _switchTile('每再跌 ${_addPct.toStringAsFixed(0)}% 加一份', _maxAdds > 0,
              (v) => setState(() => _maxAdds = v ? 3 : 0)),
          if (_maxAdds > 0) ...[
            _slider(_addPct, 3, 20, 1, (v) => setState(() => _addPct = v), suffix: '%'),
            Row(
              children: [
                Expanded(
                  child: Text('最多加碼次數：$_maxAdds 次',
                      style: TextStyle(fontSize: 14, color: cInkSoft)),
                ),
                _stepper(_maxAdds, 0, 6, (v) => setState(() => _maxAdds = v)),
              ],
            ),
          ],
          const SizedBox(height: 6),
          _switchTile('停利 +${_tp.toStringAsFixed(0)}%', _useTp,
              (v) => setState(() => _useTp = v)),
          if (_useTp) _slider(_tp, 5, 80, 1, (v) => setState(() => _tp = v), suffix: '%'),
          _switchTile('停損 -${_sl.toStringAsFixed(0)}%', _useSl,
              (v) => setState(() => _useSl = v)),
          if (_useSl) _slider(_sl, 3, 40, 1, (v) => setState(() => _sl = v), suffix: '%'),
          _switchTile('殖利率跌破 ${_exitYield.toStringAsFixed(1)}% 出場', _useExitYield,
              (v) => setState(() => _useExitYield = v)),
          if (_useExitYield)
            _slider(_exitYield, 0, 6, 0.5, (v) => setState(() => _exitYield = v),
                suffix: '%'),
        ],
      ),
    );
  }

  Widget _capitalCard() {
    return SectionCard(
      title: '資金管理',
      icon: Icons.account_balance_wallet_rounded,
      child: Column(
        children: [
          _slider(_capital, 100000, 3000000, 50000,
              (v) => setState(() => _capital = v),
              label: '本金：${money(_capital)} 元'),
          _slider(_tranche, 10000, 300000, 10000,
              (v) => setState(() => _tranche = v),
              label: '每次投入：${money(_tranche)} 元'),
          _slider(_maxPos, 20, 100, 10, (v) => setState(() => _maxPos = v),
              label: '單檔持倉上限：${_maxPos.toStringAsFixed(0)}%'),
          Row(
            children: [
              Expanded(
                child: Text('檢查頻率',
                    style: TextStyle(fontSize: 14, color: cInkSoft)),
              ),
              Wrap(
                spacing: 8,
                children: [
                  for (final f in ['daily', 'weekly', 'monthly'])
                    ChoicePill(
                      label: f == 'daily' ? '每日' : (f == 'weekly' ? '每週' : '每月'),
                      selected: _frequency == f,
                      onTap: () => setState(() => _frequency = f),
                    ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _costCard() {
    return SectionCard(
      title: '成本假設',
      icon: Icons.receipt_rounded,
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: Text('手續費折扣（0.1425% × 折扣）',
                    style: TextStyle(fontSize: 14, color: cInkSoft)),
              ),
              Wrap(
                spacing: 8,
                children: [
                  for (final d in <double>[1.0, 0.6, 0.28])
                    ChoicePill(
                      label: d == 1.0 ? '無折扣' : '${(d * 10).toStringAsFixed(0)} 折',
                      selected: (_feeDiscount - d).abs() < 0.01,
                      onTap: () => setState(() => _feeDiscount = d),
                    ),
                ],
              ),
            ],
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: _reinvest,
            onChanged: (v) => setState(() => _reinvest = v),
            title: Text('股息再投入',
                style: TextStyle(
                    fontSize: 15, fontWeight: FontWeight.w700, color: cInk)),
            subtitle: Text('打開後，配息當天以收盤價買進（仍計手續費）',
                style: TextStyle(fontSize: 12.5, color: cInkSoft)),
          ),
        ],
      ),
    );
  }

  Widget _switchTile(String label, bool value, ValueChanged<bool> onChanged) {
    return SwitchListTile(
      contentPadding: EdgeInsets.zero,
      dense: true,
      value: value,
      onChanged: onChanged,
      title: Text(label,
          style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: value ? cInk : cInkSoft)),
    );
  }

  Widget _slider(
    double value,
    double min,
    double max,
    double step,
    ValueChanged<double> onChanged, {
    String? label,
    String suffix = '',
  }) {
    final display = label ??
        '${value.toStringAsFixed(value == value.roundToDouble() ? 0 : 1)}$suffix';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null)
          Align(
            alignment: Alignment.centerLeft,
            child: Text(display,
                style: TextStyle(fontSize: 13.5, color: cPrimary)),
          ),
        SliderTheme(
          data: SliderTheme.of(context).copyWith(
            trackHeight: 4,
            thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 10),
          ),
          child: Slider(
            value: value.clamp(min, max),
            min: min,
            max: max,
            divisions: ((max - min) / step).round(),
            label: value.toStringAsFixed(0),
            onChanged: (v) {
              onChanged(v);
              setState(() {});
            },
          ),
        ),
      ],
    );
  }

  Widget _stepper(int value, int min, int max, ValueChanged<int> onChanged) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(
          onPressed: value > min ? () => onChanged(value - 1) : null,
          icon: const Icon(Icons.remove_circle_outline_rounded),
        ),
        Text('$value',
            style: TextStyle(
                fontSize: 17, fontWeight: FontWeight.w800, color: cInk)),
        IconButton(
          onPressed: value < max ? () => onChanged(value + 1) : null,
          icon: const Icon(Icons.add_circle_outline_rounded),
        ),
      ],
    );
  }
}
