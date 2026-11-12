# -*- coding: utf-8 -*-
"""V3.0 交易計畫引擎（富邦新一代 API 整合 · 第一階段可跑原型）

職責（單一、可審計）：
  1. 台股交易成本精算（手續費 / 證交稅 / 低收門檻 / 折扣）
  2. 建倉、加碼、減碼的股數規劃（整張 1000 股 or 零股 1~999 股）
  3. 由規則引擎產出「AI 交易決策」（每筆附目的與理由，可解釋、可覆寫）
  4. 風控閘門（RiskGate）：未通過就不會產生任何可送出券商的下單物件
  5. 模擬回測與含成本損益計算

設計前提（領港人 2026-11-06 同意）：
  「簽署授權書 + 本人連線測試 + 風險可控範圍內由 AI 做出交易決策」。
  因此 AI 決策不是黑箱：每筆決策都帶 purpose / reason / 依據數值，
  且必須通過風控、留痕、可一鍵急停。真實下單由 fubon_bridge.py 負責，
  本檔完全不連線、不碰憑證、不碰真錢。

費率依據（營業員 2026-11-05 回覆 + 官方文件／法源查證）：
  買進手續費 1.425/1000、賣出手續費 1.425/1000（富邦營業員回覆之牌告價）。
  賣出證交稅 3/1000（個股）、1/1000（ETF／受益憑證，證交稅條例第 2 條第 2 款）、
  現股當沖 0.15%（另可設定）。此為「稅」不是「費」，折扣不影響它。
  ⚠️ 富邦另有「單筆最低手續費」：整股 20 元、盤中/盤後零股 1 元
     （營業員 2026-11-05 09:25 明確回覆「零股手續費最低收 1 元」）。
     1000 元起始若誤用整股 20 元低收，成本立刻吃掉 2%——這是本引擎要擋的坑。
  實際費用以券商交割單為準；本引擎對費用採「無條件進位到元」的保守估計。
  2026-11-06 修正：0050 為 ETF，先前 demo 誤用個股 3‰ 高估賣出稅，
  改由 FeeConfig.for_symbol() 自動判別商品別。

僅用 Python 標準庫，方便在泰哥本機 / 測試環境直接跑。
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional

TPE = timezone(timedelta(hours=8))

# ---------------------------------------------------------------------------
# 一、費率與成本
# ---------------------------------------------------------------------------

FEE_RATE = 0.001425          # 1.425 / 1000（買、賣皆收）
TAX_RATE_STOCK = 0.003       # 3 / 1000（賣出個股）
TAX_RATE_ETF = 0.001         # 1 / 1000（賣出 ETF／受益憑證）
TAX_RATE_DAYTRADE = 0.0015   # 現股當沖賣出

MIN_FEE_ODD = 1              # 富邦盤中／盤後零股，單筆未滿 1 元以 1 元計
MIN_FEE_ROUND = 20           # 整股單筆未滿 20 元以 20 元計

# 證交稅依「商品別」而非「券商」課徵（證券交易稅條例第 2 條）：
#   第 1 款 股票 3‰；第 2 款 受益憑證／ETF 1‰（買進不課，僅賣方課）。
#   法源：財政部台財稅第 791182786 號函、金管會稅式支出評估報告、
#         證交所 2025 Guide to Investing in Taiwan（ETF 0.1%，債券 ETF 除外）。
# 台股 ETF／受益憑證代碼皆以 "00" 起頭（0050、0056、006208、00878、00929…），
# 個股代碼無 00 起頭，故以此簡化判定。⚠️ 實盤仍應以券商回報的商品別為準；
# 債券 ETF 證交稅免徵至 2026-12-31，日後再依公告調整。
def is_etf_symbol(symbol: str) -> bool:
    s = str(symbol).strip()
    return s.startswith("00") and len(s) >= 4


@dataclass
class FeeConfig:
    """可依泰哥實際帳戶折扣調整。預設採牌告（無折扣）最保守。

    請用 FeeConfig.for_symbol(symbol) 建立，讓 ETF 自動套 1‰ 而非 3‰。
    """
    fee_rate: float = FEE_RATE
    fee_discount: float = 1.0      # 6 折填 0.6；新戶 1.8 折填 0.18
    min_fee_odd: int = MIN_FEE_ODD
    min_fee_round: int = MIN_FEE_ROUND
    tax_rate: float = TAX_RATE_STOCK
    is_etf: bool = False
    round_up_to_dollar: bool = True   # 保守估計：費用無條件進位到元

    @classmethod
    def for_symbol(cls, symbol: str, **overrides) -> "FeeConfig":
        """依標的代碼自動判定 ETF 稅率；overrides 可覆寫折扣／低收等。"""
        return cls(is_etf=is_etf_symbol(symbol), **overrides)

    def tax(self) -> float:
        return TAX_RATE_ETF if self.is_etf else self.tax_rate

    def min_fee(self, is_odd: bool) -> int:
        return self.min_fee_odd if is_odd else self.min_fee_round

    def fee(self, amount: float, is_odd: bool) -> int:
        raw = amount * self.fee_rate * self.fee_discount
        v = math.ceil(raw) if self.round_up_to_dollar else round(raw)
        return max(v, self.min_fee(is_odd))

    def tax_amount(self, amount: float) -> int:
        raw = amount * self.tax()
        return math.ceil(raw) if self.round_up_to_dollar else round(raw)


@dataclass
class CostBreakdown:
    amount: float          # 成交價金
    fee: int               # 手續費
    tax: int               # 證交稅（買進為 0）
    total: float           # 買進：實付；賣出：實收
    is_odd: bool
    qty: int

    @property
    def cost_ratio(self) -> float:
        """來回成本佔成交金額比例（僅供單筆估算）。"""
        return (self.fee + self.tax) / self.amount if self.amount else 0.0


def buy_cost(price: float, qty: int, cfg: FeeConfig) -> CostBreakdown:
    is_odd = qty < 1000
    amount = round(price * qty, 4)
    fee = cfg.fee(amount, is_odd)
    return CostBreakdown(amount, fee, 0, amount + fee, is_odd, qty)


def sell_proceeds(price: float, qty: int, cfg: FeeConfig) -> CostBreakdown:
    is_odd = qty < 1000
    amount = round(price * qty, 4)
    fee = cfg.fee(amount, is_odd)
    tax = cfg.tax_amount(amount)
    return CostBreakdown(amount, fee, tax, amount - fee - tax, is_odd, qty)


def breakeven_move(price: float, qty: int, cfg: FeeConfig) -> float:
    """損益平衡所需漲幅（%）：把買+賣的所有成本算進去。"""
    b = buy_cost(price, qty, cfg)
    s = sell_proceeds(price, qty, cfg)
    total_cost = (b.total - b.amount) + (s.amount - s.total)
    return total_cost / b.total * 100 if b.total else 0.0


def tick_size(price: float) -> float:
    """台股價格跳動單位（2020 後制）。"""
    if price < 10:
        return 0.01
    if price < 50:
        return 0.05
    if price < 100:
        return 0.1
    if price < 500:
        return 0.5
    if price < 1000:
        return 1.0
    if price < 10000:
        return 5.0
    return 10.0


def round_to_tick(price: float) -> float:
    t = tick_size(price)
    return round(round(price / t) * t, 2)


# ---------------------------------------------------------------------------
# 二、股數規劃
# ---------------------------------------------------------------------------

@dataclass
class SizePlan:
    qty: int
    market_type: str        # Common（整張）/ IntradayOdd（盤中零股）/ Odd（盤後零股）
    is_odd: bool
    est_cost: float
    reason: str


def plan_buy_size(cash: float, price: float, cfg: FeeConfig,
                  prefer_odd: bool = True, allow_round: bool = True,
                  session: str = "盤中") -> Optional[SizePlan]:
    """以可用現金反推可買股數，預留手續費，絕不超支。

    零股 1~999 股；整張為 1000 的倍數（FubonNeo quantity 一律為「股數」）。
    """
    odd_type = "IntradayOdd" if session == "盤中" else "Odd"
    if price <= 0:
        return None

    # 先試整張（現金足夠且允許）
    if allow_round and not prefer_odd:
        lots = int(cash // (price * 1000))
        for n in range(lots, 0, -1):
            qty = n * 1000
            c = buy_cost(price, qty, cfg)
            if c.total <= cash:
                return SizePlan(qty, "Common", False, c.total,
                                f"資金足夠買 {n} 張整股，手續費低收 {cfg.min_fee_round} 元")

    # 零股：由現金倒推，扣掉可能的最低手續費
    cap = min(cash - cfg.min_fee_odd, cash * 0.999)
    qty = min(int(cap // price), 999)
    for q in range(qty, 0, -1):
        c = buy_cost(price, q, cfg)
        if c.total <= cash:
            return SizePlan(q, odd_type, True, c.total,
                            f"資金 {cash:.0f} 元僅能買零股 {q} 股（{odd_type}），"
                            f"手續費低收 {cfg.min_fee_odd} 元")
    return None


# ---------------------------------------------------------------------------
# 三、AI 交易決策（規則式、可解釋）
# ---------------------------------------------------------------------------

Action = Literal["Buy", "Sell"]
Purpose = Literal["建倉", "加碼", "減碼", "停利", "停損", "定期定額", "不動作"]


@dataclass
class TradeIntent:
    date: int
    symbol: str
    action: Action
    purpose: Purpose
    qty: int
    price: float
    market_type: str
    reason: str                 # 給人看的依據（可審計）
    indicators: dict = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(TPE).isoformat(timespec="seconds"))


@dataclass
class StrategyConfig:
    ma_window: int = 20
    buy_below_ma_pct: float = 0.02     # 跌破均線 2% 建倉
    add_below_ma_pct: float = 0.05    # 再跌 5% 加碼
    take_profit_pct: float = 0.06     # 停利 6%
    stop_loss_pct: float = 0.05       # 停損 5%
    trim_ratio: float = 0.5           # 減碼賣出持股比例
    max_add_times: int = 1            # 最多加碼次數
    periodic_every_n_bars: int = 0    # >0 時啟用定期定額（每 N 根 K 棒）
    allow_short_signal: bool = False


def _ma(values: list[float], n: int) -> Optional[float]:
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def decide(hist: list[tuple[int, float]], cash: float, position_qty: int,
           avg_cost: float, add_times: int, bar_idx: int,
           cfg_fee: FeeConfig, cfg_s: StrategyConfig,
           symbol: str = "0050", session: str = "盤中") -> Optional[TradeIntent]:
    """依歷史收盤價產出決策。只回傳意圖，不下單、不改帳。"""
    if len(hist) < cfg_s.ma_window + 1:
        return None
    date, close = hist[-1]
    closes = [c for _, c in hist]
    ma = _ma(closes[:-1], cfg_s.ma_window)
    if ma is None or ma <= 0:
        return None
    dev = (close / ma - 1)
    ind = {"close": close, "ma20": round(ma, 3), "dev_pct": round(dev * 100, 3),
           "bar_idx": bar_idx, "position_qty": position_qty, "avg_cost": round(avg_cost, 3)}

    # ---- 出場優先：停損 > 停利 > 減碼 ----
    if position_qty > 0:
        ret = close / avg_cost - 1 if avg_cost > 0 else 0
        ind["return_pct"] = round(ret * 100, 3)
        if ret <= -cfg_s.stop_loss_pct:
            return TradeIntent(date, symbol, "Sell", "停損", position_qty,
                               round_to_tick(close), "IntradayOdd" if position_qty < 1000 else "Common",
                               f"虧損 {ret*100:.2f}% 觸及停損線 {-cfg_s.stop_loss_pct*100:.1f}%，全數出場", ind)
        if ret >= cfg_s.take_profit_pct:
            q = max(1, int(position_qty * cfg_s.trim_ratio))
            return TradeIntent(date, symbol, "Sell", "停利", q,
                               round_to_tick(close), "IntradayOdd" if q < 1000 else "Common",
                               f"獲利 {ret*100:.2f}% 達停利 {cfg_s.take_profit_pct*100:.1f}%，減碼 {q} 股", ind)

    # ---- 進場：建倉 / 加碼 / 定期定額 ----
    periodic = (cfg_s.periodic_every_n_bars > 0
                and bar_idx > 0 and bar_idx % cfg_s.periodic_every_n_bars == 0)
    if position_qty == 0:
        if dev <= -cfg_s.buy_below_ma_pct:
            plan = plan_buy_size(cash, close, cfg_fee, prefer_odd=True, session=session)
            if plan:
                return TradeIntent(date, symbol, "Buy", "建倉", plan.qty,
                                   round_to_tick(close), plan.market_type,
                                   f"收盤 {close} 低於 {cfg_s.ma_window} 日均線 {ma:.2f} {abs(dev)*100:.2f}%，"
                                   f"觸發建倉；{plan.reason}", ind)
        if periodic:
            plan = plan_buy_size(cash, close, cfg_fee, prefer_odd=True, session=session)
            if plan:
                return TradeIntent(date, symbol, "Buy", "定期定額", plan.qty,
                                   round_to_tick(close), plan.market_type,
                                   f"定期定額第 {bar_idx} 期；{plan.reason}", ind)
    else:
        if dev <= -cfg_s.add_below_ma_pct and add_times < cfg_s.max_add_times:
            plan = plan_buy_size(cash, close, cfg_fee, prefer_odd=True, session=session)
            if plan:
                return TradeIntent(date, symbol, "Buy", "加碼", plan.qty,
                                   round_to_tick(close), plan.market_type,
                                   f"續跌至均線下方 {abs(dev)*100:.2f}%，第 {add_times+1} 次加碼；{plan.reason}", ind)
    return None


# ---------------------------------------------------------------------------
# 四、風控閘門（AI 決策之後、下單之前的唯一通道）
# ---------------------------------------------------------------------------

@dataclass
class RiskConfig:
    mode: Literal["backtest", "dry_run", "live"] = "dry_run"
    kill_switch: bool = False
    initial_capital: float = 1000.0
    max_order_amount: float = 1000.0      # 單筆上限（含費用）
    max_daily_amount: float = 2000.0      # 每日累計上限
    max_orders_per_day: int = 3
    max_position_pct: float = 0.8         # 持股市值 / 總權益上限
    whitelist: tuple[str, ...] = ("0050", "2330", "2881", "2412", "2882")
    allow_round_lot: bool = False         # 1000 元起始：預設只准零股
    require_fresh_quote: bool = True      # 與 V2.8 資料時效規格連動
    max_quote_age_seconds: int = 300      # 盤中報價不得舊於 5 分鐘
    allow_session: tuple[str, ...] = ("盤中",)   # 預設只在盤中下單
    # ⚠️ V3.2 起：要不要「人工逐筆確認」改由 authorization.py 的授權層決定。
    # 本檔只判斷「這筆風險能不能接受」，不再摻入授權決策，避免兩邊規則打架。
    require_human_confirm: bool = True    # deprecated：保留相容，勿再作為下單依據


@dataclass
class GateResult:
    approved: bool
    reasons: list[str] = field(default_factory=list)


def risk_gate(intent: TradeIntent, cash: float, position_value: float,
              daily_amount: float, daily_orders: int,
              cfg: RiskConfig, fee: FeeConfig,
              quote_age_seconds: float = 0.0, session: str = "盤中") -> GateResult:
    r: list[str] = []
    if cfg.kill_switch:
        r.append("急停開關已啟動")
    # 人工確認／額度授權由 authorization.authorize() 判斷，這裡不重複攔截。
    if intent.symbol not in cfg.whitelist:
        r.append(f"{intent.symbol} 不在白名單")
    if session not in cfg.allow_session:
        r.append(f"目前 {session} 非允許交易時段")
    if cfg.require_fresh_quote and quote_age_seconds > cfg.max_quote_age_seconds:
        r.append(f"報價已舊 {quote_age_seconds:.0f} 秒（上限 {cfg.max_quote_age_seconds} 秒）")
    if daily_orders >= cfg.max_orders_per_day:
        r.append(f"當日已達 {cfg.max_orders_per_day} 筆上限")
    if daily_amount >= cfg.max_daily_amount:
        r.append("當日累計金額已達上限")
    if intent.action == "Buy":
        c = buy_cost(intent.price, intent.qty, fee)
        if c.total > cfg.max_order_amount:
            r.append(f"單筆 {c.total:.0f} 元超過上限 {cfg.max_order_amount:.0f} 元")
        if c.total > cash:
            r.append(f"現金不足（需 {c.total:.0f}，有 {cash:.0f}）")
        if intent.qty >= 1000 and not cfg.allow_round_lot:
            r.append("目前設定只允許零股，禁止整張下單")
        equity = cash + position_value
        if equity > 0 and (position_value + c.amount) / equity > cfg.max_position_pct:
            r.append(f"買後持股比重將超過 {cfg.max_position_pct*100:.0f}%")
    else:
        if intent.qty <= 0:
            r.append("賣出股數為 0")
    return GateResult(not r, r)


# ---------------------------------------------------------------------------
# 五、模擬帳本與含成本損益
# ---------------------------------------------------------------------------

@dataclass
class Ledger:
    cash: float
    position_qty: int = 0
    avg_cost: float = 0.0        # 每股成本（含買進手續費）
    add_times: int = 0
    realized_pnl: float = 0.0
    trades: list[dict] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)

    def equity(self, price: float, fee: FeeConfig) -> float:
        """總權益 = 現金 + 持股市值 − 預估賣出成本（誠實扣除未實現的交易成本）。"""
        if self.position_qty <= 0:
            return self.cash
        s = sell_proceeds(price, self.position_qty, fee)
        return self.cash + s.total

    def buy(self, intent: TradeIntent, fee: FeeConfig):
        c = buy_cost(intent.price, intent.qty, fee)
        new_qty = self.position_qty + intent.qty
        self.avg_cost = (self.avg_cost * self.position_qty + c.total) / new_qty
        self.position_qty = new_qty
        self.cash -= c.total
        if intent.purpose == "加碼":
            self.add_times += 1
        self.trades.append({"date": intent.date, "action": "Buy", "purpose": intent.purpose,
                            "qty": intent.qty, "price": intent.price, "amount": c.amount,
                            "fee": c.fee, "tax": 0, "cash_after": round(self.cash, 2),
                            "reason": intent.reason})

    def sell(self, intent: TradeIntent, fee: FeeConfig):
        q = min(intent.qty, self.position_qty)
        if q <= 0:
            return
        s = sell_proceeds(intent.price, q, fee)
        cost_basis = self.avg_cost * q
        self.realized_pnl += s.total - cost_basis
        self.position_qty -= q
        self.cash += s.total
        if self.position_qty == 0:
            self.avg_cost = 0.0
            self.add_times = 0
        self.trades.append({"date": intent.date, "action": "Sell", "purpose": intent.purpose,
                            "qty": q, "price": intent.price, "amount": s.amount,
                            "fee": s.fee, "tax": s.tax, "cash_after": round(self.cash, 2),
                            "realized_pnl": round(s.total - cost_basis, 2),
                            "reason": intent.reason})


def run_backtest(bars: list[tuple[int, float]], fee: FeeConfig,
                 risk: RiskConfig, strat: StrategyConfig,
                 symbol: str = "0050", session: str = "盤中") -> dict:
    """純離線模擬：不連券商、不碰憑證、不碰真錢。"""
    led = Ledger(cash=risk.initial_capital)
    daily_amount, daily_orders, last_date = 0.0, 0, None
    intents: list[dict] = []

    for i in range(strat.ma_window + 1, len(bars) + 1):
        hist = bars[:i]
        date = bars[i - 1][0]
        if date != last_date:
            daily_amount, daily_orders, last_date = 0.0, 0, date
        price = bars[i - 1][1]
        position_value = led.position_qty * price

        intent = decide(hist, led.cash, led.position_qty, led.avg_cost,
                        led.add_times, i, fee, strat, symbol, session)
        if intent is None:
            continue
        g = risk_gate(intent, led.cash, position_value, daily_amount,
                      daily_orders, risk, fee, 0.0, session)
        rec = {"date": date, "purpose": intent.purpose, "action": intent.action,
               "qty": intent.qty, "price": intent.price, "market_type": intent.market_type,
               "approved": g.approved, "gate_reasons": g.reasons, "reason": intent.reason,
               "indicators": intent.indicators}
        intents.append(rec)
        if not g.approved:
            led.rejected.append(rec)
            continue
        if risk.mode == "dry_run":
            # 只留決策與風控結果，不改帳（這是預設）
            continue
        if intent.action == "Buy":
            c = buy_cost(intent.price, intent.qty, fee)
            daily_amount += c.total
            led.buy(intent, fee)
        else:
            s = sell_proceeds(intent.price, intent.qty, fee)
            daily_amount += s.amount
            led.sell(intent, fee)
        daily_orders += 1

    last_price = bars[-1][1]
    equity = led.equity(last_price, fee)
    return {
        "symbol": symbol, "mode": risk.mode,
        "initial_capital": risk.initial_capital,
        "bars": len(bars), "first_date": bars[0][0], "last_date": bars[-1][0],
        "last_price": last_price,
        "cash": round(led.cash, 2), "position_qty": led.position_qty,
        "avg_cost": round(led.avg_cost, 4), "realized_pnl": round(led.realized_pnl, 2),
        "equity": round(equity, 2),
        "net_pnl": round(equity - risk.initial_capital, 2),
        "net_return_pct": round((equity / risk.initial_capital - 1) * 100, 3),
        "trades": led.trades, "rejected": led.rejected, "intents": intents,
        "fee_config": asdict(fee), "risk_config": asdict(risk),
        "strategy_config": asdict(strat),
    }


if __name__ == "__main__":
    # 最小自我檢查：1000 元買 0050（ETF 1‰）／2330（個股 3‰）零股的費用與損益平衡
    for name, cfg in (("0050 ETF  1‰", FeeConfig.for_symbol("0050")),
                      ("2330 個股 3‰", FeeConfig.for_symbol("2330"))):
        for qty in (9, 1000):
            c = buy_cost(106.9, qty, cfg)
            print(f"{name} 買 {qty:>4} 股 @106.9：價金 {c.amount:>9.2f} 手續費 {c.fee:>3} 元 "
                  f"實付 {c.total:>9.2f}｜損益平衡需漲 {breakeven_move(106.9, qty, cfg):.2f}%")
