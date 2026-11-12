# -*- coding: utf-8 -*-
"""V3.2 授權額度層（Authorization Layer）· AI 免逐筆確認自動交易的唯一依據

領港人 2026-11-06 12:32 指示：
  「後續考慮 AI 在一定的授權額度做股票交易，不用逐筆授權確認，
    直接通過系統判斷，自行交易。」

本檔把這句話翻成可執行的硬約束。核心立場：
  ✅ 額度內自動放行（不需人逐筆按確認）
  ❌ 但「自動」不等於「無約束」，更不等於「AI 可以自己改額度」

五道不可繞過的防線：
  1. 額度不可變（frozen dataclass）— AI 決策流程只能讀，不能寫
  2. 升級需人的明確授權 + Gate 達標 — 程式不能自己把 M2 升成 M3
  3. 熔斷即降級 — 觸發任一熔斷，自動回到 M2（逐筆確認），且不自動復原
  4. 人隨時可收回 — revoke() 任何時刻優先於所有決策
  5. 逐筆留痕 — 自動模式下每筆仍帶 purpose/reason/額度消耗，可供稽核

職責邊界（三者串成一條鏈，缺一不可）：
  risk_gate()          → 這筆「風險」能不能接受
  authorize()          → 這筆有沒有「被授權」、額度夠不夠、要不要人按確認
  place_from_intent()  → 兩者都過了才送出券商

⚠️ 本檔完全不連券商、不讀憑證、不碰真錢；只做授權判定。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

from trade_plan_engine import (TradeIntent, GateResult, FeeConfig,
                               buy_cost, sell_proceeds, TPE)

AB_RESULT = Path("/workspace/v31_ab_result.json")


# ---------------------------------------------------------------------------
# 一、四級授權模式
# ---------------------------------------------------------------------------

class AuthLevel(str, Enum):
    M0_PAPER = "M0_paper"                # 模擬盤：零真錢（目前所在）
    M1_DRYRUN = "M1_dry_run"             # 只產決策、不送單
    M2_CONFIRM = "M2_live_confirm"       # 實盤、逐筆人工確認
    M3_AUTO = "M3_live_auto"             # 實盤、額度內自動（終局目標，尚未啟用）

    @property
    def can_send_order(self) -> bool:
        return self in (AuthLevel.M2_CONFIRM, AuthLevel.M3_AUTO)


@dataclass(frozen=True)
class AuthorizationPolicy:
    """人簽核的授權額度。frozen = 系統／AI 不可修改，只能由人換發新的 policy。

    換發條件：新的 grant_id + 新的 granted_by + 新的 expires_at，且留存舊版供稽核。
    """
    level: AuthLevel = AuthLevel.M0_PAPER
    granted_by: str = ""
    grant_id: str = ""
    granted_at: str = ""
    expires_at: str = ""                 # 沒填 = 未有效授權（fail-closed）
    max_total_exposure: float = 10_000.0  # 授權總額度：累計買進金額上限
    max_order_amount: float = 1_000.0     # 單筆上限（含費用）
    max_daily_amount: float = 2_000.0     # 單日累計金額
    max_orders_per_day: int = 3           # 單日筆數
    max_symbol_exposure: float = 3_000.0  # 單一標的累計曝險
    max_position_pct: float = 0.8         # 持股市值 / 總權益
    max_daily_loss: float = 300.0         # 單日已實現虧損熔斷
    max_consecutive_losses: int = 3       # 連續虧損筆數熔斷
    max_drawdown_pct: float = 0.08        # 自峰值權益回撤熔斷
    whitelist: tuple[str, ...] = ("0050", "2330", "2881", "2412", "2882")
    allow_round_lot: bool = False
    allow_session: tuple[str, ...] = ("盤中",)
    max_quote_age_seconds: int = 300     # 與 V2.8 資料時效規格連動
    note: str = ""

    def is_expired(self, now: datetime) -> bool:
        if not self.expires_at:
            return True
        try:
            exp = datetime.fromisoformat(self.expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=TPE)
            return now >= exp
        except (ValueError, TypeError):
            return True


@dataclass
class AccountState:
    """系統維護的『事實』，不是 AI 決策可以改的參數。

    AI 只能讀取；寫入只發生在成交回報（record_fill）與人的急停（revoke）。
    """
    date: int = 0
    cash: float = 0.0
    equity: float = 0.0
    peak_equity: float = 0.0
    daily_amount: float = 0.0
    daily_orders: int = 0
    daily_realized_pnl: float = 0.0
    consecutive_losses: int = 0
    total_buy_amount: float = 0.0
    symbol_exposure: dict[str, float] = field(default_factory=dict)
    total_fees: int = 0
    halted: bool = False
    halt_reason: str = ""
    downgraded_to: Optional[AuthLevel] = None

    def roll_date(self, date: int, cash: float, equity: float):
        if date != self.date:
            self.date = date
            self.daily_amount = 0.0
            self.daily_orders = 0
            self.daily_realized_pnl = 0.0
        self.cash = cash
        self.equity = equity
        self.peak_equity = max(self.peak_equity, equity)

    def record_fill(self, intent: TradeIntent, amount: float, fee: int, tax: int,
                    realized_pnl: float = 0.0):
        """成交回報後由橋接層呼叫，更新額度消耗（唯一寫入來源）。"""
        self.daily_amount += amount
        self.daily_orders += 1
        self.total_fees += fee + tax
        if intent.action == "Buy":
            self.total_buy_amount += amount
            self.symbol_exposure[intent.symbol] = (
                self.symbol_exposure.get(intent.symbol, 0.0) + amount)
        else:
            self.symbol_exposure[intent.symbol] = max(
                0.0, self.symbol_exposure.get(intent.symbol, 0.0) - amount)
        if realized_pnl:
            self.daily_realized_pnl += realized_pnl
            self.consecutive_losses = 0 if realized_pnl > 0 else self.consecutive_losses + 1

    def quota_usage(self, p: "AuthorizationPolicy") -> dict:
        def pct(a, b):
            return round(a / b * 100, 1) if b else 0.0
        return {
            "總額度": f"{self.total_buy_amount:,.0f} / {p.max_total_exposure:,.0f}（{pct(self.total_buy_amount, p.max_total_exposure)}%）",
            "單日金額": f"{self.daily_amount:,.0f} / {p.max_daily_amount:,.0f}（{pct(self.daily_amount, p.max_daily_amount)}%）",
            "單日筆數": f"{self.daily_orders} / {p.max_orders_per_day}",
            "單日已實現損益": f"{self.daily_realized_pnl:+,.0f} / 熔斷 {p.max_daily_loss:,.0f}",
            "連續虧損": f"{self.consecutive_losses} / {p.max_consecutive_losses}",
            "峰值回撤": f"{pct(max(0.0, self.peak_equity - self.equity), self.peak_equity)}% / {p.max_drawdown_pct*100:.0f}%",
        }


# ---------------------------------------------------------------------------
# 二、升級 Gate（M2 → M3 的達標條件，程式不能自己宣布達標）
# ---------------------------------------------------------------------------

@dataclass
class UpgradeEvidence:
    backtest_beat_benchmark: bool = False   # G1
    backtest_detail: str = ""
    sandbox_pipeline_passed: bool = False  # G2
    live_confirm_clean_days: int = 0       # G3：逐筆確認實盤、無風控違規天數
    signed_and_activated: bool = False     # G4：簽署 + 連線測試 + 隔日開通
    human_written_grant: bool = False      # G5：本人書面授權（額度、期限、標的）
    required_clean_days: int = 10

    def missing(self) -> list[str]:
        m = []
        if not self.backtest_beat_benchmark:
            m.append("G1 對照實驗／回測未跑贏買入持有基準")
        if not self.sandbox_pipeline_passed:
            m.append("G2 官方 sandbox 全鏈路（登入→行情→下單→回報→對帳→急停）未完成")
        if self.live_confirm_clean_days < self.required_clean_days:
            m.append(f"G3 逐筆確認實盤未滿 {self.required_clean_days} 個無違規交易日"
                     f"（目前 {self.live_confirm_clean_days}）")
        if not self.signed_and_activated:
            m.append("G4 未完成聲明書簽署／連線測試／隔日開通")
        if not self.human_written_grant:
            m.append("G5 未取得本人書面授權（額度、期限、標的、可收回條款）")
        return m


def load_experiment_evidence(path: Path = AB_RESULT) -> tuple[bool, str]:
    """從 V3.1 對照實驗結果判定 G1，讓升級 Gate 與真實資料連動，而非口頭宣稱。"""
    if not path.is_file():
        return False, "尚無對照實驗結果（/workspace/v31_ab_result.json）"
    try:
        r = json.loads(path.read_text(encoding="utf-8"))
        hold = next(t for t in r["tracks"] if t["name"] == "買入持有")
        ais = [t for t in r["tracks"] if t["name"].startswith("AI")]
        best = max(ais, key=lambda t: t["return_pct"])
        ok = best["return_pct"] > hold["return_pct"]
        detail = (f"{r['first_date']}～{r['last_date']}：最佳 AI 軌 "
                  f"{best['name']} {best['return_pct']:+.2f}% vs 買入持有 "
                  f"{hold['return_pct']:+.2f}% → {'通過' if ok else '未通過'}")
        return ok, detail
    except Exception as ex:
        return False, f"實驗結果讀取失敗：{ex}"


# ---------------------------------------------------------------------------
# 三、授權判定（fail-closed：任何一關沒過就不放行）
# ---------------------------------------------------------------------------

@dataclass
class AuthResult:
    allowed: bool
    needs_human_confirm: bool
    effective_level: AuthLevel
    reasons: list[str] = field(default_factory=list)   # 拒絕／攔下理由
    notes: list[str] = field(default_factory=list)     # 警示但不拒絕（如降級）
    quota: dict = field(default_factory=dict)
    grant_id: str = ""
    auto_executed: bool = False

    @property
    def decision(self) -> str:
        if not self.allowed:
            return "攔下"
        return "額度內自動放行" if self.auto_executed else "待人工確認"

    def audit_record(self, intent: TradeIntent) -> dict:
        return {
            "ts": datetime.now(TPE).isoformat(timespec="seconds"),
            "event": "authorization",
            "grant_id": self.grant_id,
            "level": self.effective_level.value,
            "decision": self.decision,
            "symbol": intent.symbol, "action": intent.action,
            "purpose": intent.purpose, "qty": intent.qty, "price": intent.price,
            "reason": intent.reason, "indicators": intent.indicators,
            "reasons": self.reasons, "notes": self.notes, "quota": self.quota,
        }


def _trip(state: AccountState, why: str) -> None:
    """熔斷：停單 + 降回 M2 + 不自動復原（要人重新授權）。"""
    state.halted = True
    state.halt_reason = why
    state.downgraded_to = AuthLevel.M2_CONFIRM


def authorize(intent: TradeIntent, policy: AuthorizationPolicy, state: AccountState,
              gate: GateResult, fee: FeeConfig, evidence: UpgradeEvidence, *,
              session: str = "盤中", quote_age_seconds: float = 0.0,
              now: Optional[datetime] = None) -> AuthResult:
    """判斷這筆要不要人按確認。回傳結果供 fubon_bridge 作為下單依據。"""
    now = now or datetime.now(TPE)
    lvl = policy.level
    quota = state.quota_usage(policy)
    blocked: list[str] = []
    notes: list[str] = []

    # 0) 人收回授權 / 先前已熔斷 —— 最高優先
    if state.halted:
        return AuthResult(False, True, AuthLevel.M2_CONFIRM,
                          [f"已急停／熔斷：{state.halt_reason}（需人重新授權才復原）"],
                          quota=quota, grant_id=policy.grant_id)

    # 1) 模式本身能不能送單（M0/M1 一律不出券商）
    if not lvl.can_send_order:
        return AuthResult(False, True, lvl,
                          [f"{lvl.value} 不送出券商（僅紙上模擬／決策演練）"],
                          quota=quota, grant_id=policy.grant_id)

    # 2) 授權有效期：過期或沒填 → 降 M2，且本筆不放行
    if policy.is_expired(now):
        _trip(state, "授權已到期或缺少有效期")
        return AuthResult(False, True, AuthLevel.M2_CONFIRM,
                          ["授權到期／未載明有效期，自動降回 M2 逐筆確認，需人重新簽核"],
                          quota=quota, grant_id=policy.grant_id)

    # 3) M3 必須 Gate 全數達標；未達標自動降為 M2（不是放行、也不是永久停機）
    if lvl == AuthLevel.M3_AUTO:
        miss = evidence.missing()
        if miss:
            lvl = AuthLevel.M2_CONFIRM
            state.downgraded_to = AuthLevel.M2_CONFIRM
            notes.append("M3 升級 Gate 未全數通過，本次降為逐筆確認：" + "；".join(miss))

    # 4) 風控閘門結果（上游 risk_gate 已算好）
    if not gate.approved:
        blocked.extend(f"風控：{x}" for x in gate.reasons)

    # 5) 熔斷檢查（用已成交的事實狀態）
    if state.daily_realized_pnl <= -abs(policy.max_daily_loss):
        why = f"單日已實現虧損 {state.daily_realized_pnl:+.0f} 元達熔斷線"
        _trip(state, why)
        return AuthResult(False, True, AuthLevel.M2_CONFIRM, [why + "，全部停單並降回 M2"],
                          notes=notes, quota=quota, grant_id=policy.grant_id)
    if state.consecutive_losses >= policy.max_consecutive_losses:
        why = f"連續虧損 {state.consecutive_losses} 筆達熔斷線"
        _trip(state, why)
        return AuthResult(False, True, AuthLevel.M2_CONFIRM, [why + "，全部停單並降回 M2"],
                          notes=notes, quota=quota, grant_id=policy.grant_id)
    if state.peak_equity > 0:
        dd = (state.peak_equity - state.equity) / state.peak_equity
        if dd > policy.max_drawdown_pct:
            why = f"權益自峰值回撤 {dd*100:.2f}% 超過 {policy.max_drawdown_pct*100:.0f}%"
            _trip(state, why)
            return AuthResult(False, True, AuthLevel.M2_CONFIRM, [why + "，全部停單並降回 M2"],
                              notes=notes, quota=quota, grant_id=policy.grant_id)

    # 6) 額度檢查（多層，任一超標即攔下）
    c = (buy_cost(intent.price, intent.qty, fee) if intent.action == "Buy"
         else sell_proceeds(intent.price, intent.qty, fee))
    amt = c.amount

    if intent.symbol not in policy.whitelist:
        blocked.append(f"{intent.symbol} 不在授權白名單")
    if session not in policy.allow_session:
        blocked.append(f"{session} 不在授權交易時段")
    if quote_age_seconds > policy.max_quote_age_seconds:
        blocked.append(f"報價已舊 {quote_age_seconds:.0f} 秒（上限 {policy.max_quote_age_seconds} 秒）")
    if intent.qty >= 1000 and not policy.allow_round_lot:
        blocked.append("未授權整張（1000 股）下單，僅限零股")
    if intent.qty <= 0:
        blocked.append("股數為 0")
    if c.total > policy.max_order_amount:
        blocked.append(f"單筆 {c.total:,.0f} 元 > 授權單筆上限 {policy.max_order_amount:,.0f} 元")
    if state.daily_amount + amt > policy.max_daily_amount:
        blocked.append(f"單日累計將達 {state.daily_amount + amt:,.0f} 元 > {policy.max_daily_amount:,.0f} 元")
    if state.daily_orders + 1 > policy.max_orders_per_day:
        blocked.append(f"單日筆數將達 {state.daily_orders + 1} > {policy.max_orders_per_day} 筆")
    if intent.action == "Buy":
        if state.total_buy_amount + amt > policy.max_total_exposure:
            blocked.append(f"累計買進將達 {state.total_buy_amount + amt:,.0f} 元 > 授權總額度 {policy.max_total_exposure:,.0f} 元")
        sym = state.symbol_exposure.get(intent.symbol, 0.0) + amt
        if sym > policy.max_symbol_exposure:
            blocked.append(f"{intent.symbol} 曝險將達 {sym:,.0f} 元 > 單一標的上限 {policy.max_symbol_exposure:,.0f} 元")
        eq = state.equity if state.equity > 0 else state.cash
        # 保守估計：以「累計買進 − 累計賣出」的成本基礎近似持股市值，
        # 實盤應由橋接層帶入即時市值覆蓋；寧可高估曝險，不可低估。
        pos_value = sum(state.symbol_exposure.values())
        if eq > 0 and (pos_value + amt) / eq > policy.max_position_pct:
            blocked.append(f"買後持股比重將超過 {policy.max_position_pct*100:.0f}%")
        if c.total > state.cash:
            blocked.append(f"現金不足（需 {c.total:,.0f}，有 {state.cash:,.0f}）")

    allowed = not blocked
    auto = allowed and lvl == AuthLevel.M3_AUTO
    return AuthResult(allowed, not auto, lvl, blocked, notes,
                      quota, policy.grant_id, auto)


# ---------------------------------------------------------------------------
# 四、人的開關（只有人能呼叫；系統／AI 決策流程不得呼叫）
# ---------------------------------------------------------------------------

def revoke(state: AccountState, by: str, why: str = "本人收回授權") -> None:
    """一鍵急停／收回授權。不可逆，復原只能由人換發新 policy。"""
    _trip(state, f"{why}（執行人：{by}）")


def grant_m3(*, by: str, grant_id: str, days: int = 30,
             now: Optional[datetime] = None, **limits) -> AuthorizationPolicy:
    """人換發 M3 授權。僅產生 policy 物件，不代表 Gate 已達標（authorize 仍會查）。

    這是唯一能產生 M3 的入口；需由人帶 grant_id / 姓名 / 期限呼叫，
    不接受來自決策流程的參數。
    """
    now = now or datetime.now(TPE)
    return AuthorizationPolicy(
        level=AuthLevel.M3_AUTO, granted_by=by, grant_id=grant_id,
        granted_at=now.isoformat(timespec="seconds"),
        expires_at=(now + timedelta(days=days)).isoformat(timespec="seconds"),
        note="本人書面授權，得隨時收回", **limits)


# ---------------------------------------------------------------------------
# 五、自檢：把 11 種情境跑一遍，證明規則真的會動
# ---------------------------------------------------------------------------

def _demo_intent(qty: int = 9, price: float = 106.9, symbol: str = "0050") -> TradeIntent:
    from trade_plan_engine import TradeIntent
    return TradeIntent(date=20261106, symbol=symbol, action="Buy", purpose="建倉",
                       qty=qty, price=price, market_type="IntradayOdd",
                       reason="收盤低於均線 2.3%，觸發建倉（自檢用）",
                       indicators={"ma20": 109.4, "dev_pct": -2.3})


def _ok_gate() -> GateResult:
    return GateResult(True, [])


def self_check() -> list[dict]:
    fee = FeeConfig()
    g1_ok, g1_detail = load_experiment_evidence()
    full_evidence = UpgradeEvidence(
        backtest_beat_benchmark=g1_ok, backtest_detail=g1_detail,
        sandbox_pipeline_passed=True, live_confirm_clean_days=12,
        signed_and_activated=True, human_written_grant=True)
    weak_evidence = UpgradeEvidence(
        backtest_beat_benchmark=g1_ok, backtest_detail=g1_detail)

    now = datetime(2026, 11, 6, 12, 30, tzinfo=TPE)
    base = dict(granted_by="黃翔泰（本人）", grant_id="GRANT-20261106-01",
                granted_at="2026-11-06T12:00:00+08:00",
                expires_at="2026-12-06T12:00:00+08:00")

    def fresh_policy(level=AuthLevel.M3_AUTO, **kw):
        return AuthorizationPolicy(level=level, **{**base, **kw})

    def fresh_state(cash=5000.0, equity=5000.0, **kw):
        s = AccountState(**kw)
        s.roll_date(20261106, cash, equity)
        return s

    cases = []

    def run(label, policy, state, intent=None, gate=None, evidence=None,
            session="盤中", quote_age=0.0, at=None, revoke_first=None):
        if revoke_first:
            revoke(state, revoke_first)
        r = authorize(intent or _demo_intent(), policy, state, gate or _ok_gate(),
                      fee, evidence if evidence is not None else full_evidence,
                      session=session, quote_age_seconds=quote_age, now=at or now)
        cases.append({"情境": label, "判定": r.decision,
                      "生效層級": r.effective_level.value,
                      "需人確認": "是" if r.needs_human_confirm else "否",
                      "理由": "；".join(r.reasons + r.notes)[:110] or "—"})
        return r

    # 1 現況：模擬盤
    run("① 現況 M0 模擬盤", fresh_policy(AuthLevel.M0_PAPER), fresh_state())
    # 2 理想：M3 + Gate 全過 + 額度內 → 免逐筆確認
    run("② M3 額度內自動", fresh_policy(), fresh_state())
    # 3 單筆超額
    run("③ 單筆超授權額度", fresh_policy(max_order_amount=500.0), fresh_state())
    # 4 單日金額用滿（roll_date 會重置當日欄位，故建立後再設值）
    s4 = fresh_state()
    s4.daily_amount = 1900.0
    run("④ 單日累計已滿", fresh_policy(), s4)
    # 5 總額度用滿
    run("⑤ 累計買進達總額度", fresh_policy(), fresh_state(total_buy_amount=9900.0))
    # 6 連虧熔斷
    s6 = fresh_state(consecutive_losses=3)
    run("⑥ 連虧 3 筆熔斷", fresh_policy(), s6)
    # 7 人急停
    run("⑦ 本人一鍵急停", fresh_policy(), fresh_state(),
        revoke_first="黃翔泰（本人）")
    # 8 授權過期
    run("⑧ 授權已過期", fresh_policy(), fresh_state(),
        at=datetime(2027, 1, 1, tzinfo=TPE))
    # 9 Gate 未達標 → 降為逐筆確認
    run("⑨ M3 但升級 Gate 未達標", fresh_policy(), fresh_state(),
        evidence=weak_evidence)
    # 10 風控未通過
    run("⑩ 風控閘門攔下", fresh_policy(), fresh_state(),
        gate=GateResult(False, ["報價已舊 900 秒"]))
    # 11 熔斷後「隔日」仍不自動復原（證明要人重新授權才能復機）
    s6.roll_date(20261107, 5000.0, 5000.0)
    run("⑪ 熔斷後隔日仍停單", fresh_policy(), s6)

    return cases, g1_detail, weak_evidence.missing()


if __name__ == "__main__":
    cases, g1, miss = self_check()
    print("=== G1 對照實驗證據 ===")
    print(g1)
    print("\n=== 目前 M3 升級 Gate 缺項 ===")
    for m in miss:
        print("  ✗", m)
    print("\n=== 授權層自檢（11 種情境）===")
    print(f"{'情境':<24}{'判定':<18}{'層級':<20}{'需人確認':<8}理由")
    print("-" * 130)
    for c in cases:
        print(f"{c['情境']:<24}{c['判定']:<18}{c['生效層級']:<20}{c['需人確認']:<8}{c['理由']}")
    print("\n※ 本檔僅做授權判定，未連券商、未送任何委託、零真錢。")
