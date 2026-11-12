#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
principles.py — 选股与操作原则的「可执行版本」

把 V3.7 提炼的七条核心价值观，翻译成机器可校验的规则：
  · 市场状态判定（regime）→ 决定总仓位上限
  · 选股漏斗（screen）→ 决定「可以看哪些」
  · 交易前 12 问（pretrade_check）→ 决定「今天能不能动手」

设计立场（本档最重要的部分）：
  1) 规则的作用不是「选出会涨的股票」，是「排除不该碰的股票」。
     前面五年的实测已证明：择时讯号没有稳定优势，选股的离散度却高达
     2,117 个百分点——力气要花在「筛掉」，不是「预测」。
  2) 所有门槛都是事前写死的常数，不允许盘中调整。
  3) 无法用数据回答的，一律判 fail（fail-closed）。宁可错过，不可放宽。

被 trade_plan_engine.py / authorization.py 引用时只读、无副作用。
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path

# ══════════════════════════════════════════════════════════════════
# 一、七条核心价值观（从案例提炼，逐条对应可执行规则）
# ══════════════════════════════════════════════════════════════════

VALUES = [
    ("V1", "先活下来，再谈报酬",
     "破产是唯一不可逆的错误；任何策略先问「最坏亏多少」",
     "仓位上限 + 熔断线写死，触发即停，隔日不自动复机"),
    ("V2", "能力圈内下注，圈外一律不做",
     "不懂的生意不买，看不懂的行情不做",
     "白名单 + 产业上限 + 无法解释理由即拒单"),
    ("V3", "时间是复利的朋友，是交易成本的敌人",
     "巴菲特 60 年 19.7%，靠的是不中断；不是每年第一",
     "单日笔数上限 + 换手缓冲 + 成本前置计算"),
    ("V4", "纪律优先于预测",
     "规则在盘前写死，盘中只执行；预测留给别人",
     "参数 frozen，盘中改参数需换发新授权"),
    ("V5", "只承担「赔得起且有补偿」的风险",
     "波动不等于风险，永久的资本损失才是风险",
     "波动/回撤门槛 + 单一标的敞口上限"),
    ("V6", "代价必须算清楚才进场",
     "手续费、税、滑点先扣，剩下的才是你的",
     "买卖成本前置到「打平需涨 N%」，未达即不做"),
    ("V7", "承认自己会错，并让错误变便宜",
     "所有大师都错过大钱；差别是错的时候小，对的时候大",
     "停损交券商托管 + 逐笔留痕 + 盘后复盘强制记录"),
]

# ══════════════════════════════════════════════════════════════════
# 二、市场状态与仓位上限（写死，不允许盘中修改）
# ══════════════════════════════════════════════════════════════════

REGIME_CAP = {
    "BULL": 0.80,      # 距高点回撤 < 8%、站上年线
    "NEUTRAL": 0.60,   # 回撤 8–15%
    "BEAR": 0.40,      # 回撤 15–25%，或跌破年线
    "CRISIS": 0.20,    # 回撤 > 25%，或 20 日年化波动 > 45%
}

REGIME_NOTE = {
    "BULL": "顺势持有，但不加杠杆、不追高；新仓只在回调时分批",
    "NEUTRAL": "减码高波动、保留核心；新仓减半，等确认再补",
    "BEAR": "现金是仓位；只留能领息的核心，反弹不追，破线减码",
    "CRISIS": "先活下来。不抄底、不摊平、不杠杆；等波动收敛再谈",
}

# 选股漏斗门槛（写死）
MIN_BARS = 1000        # 至少 4 年日线，避开新上市样本
MIN_ADV_NTD = 3e8      # 近 60 日均成交额 ≥ 3 亿（可进可出）
MAX_VOL_ANN = 0.45     # 年化波动 ≤ 45%
MAX_DRAWDOWN = 0.55    # 五年最大回撤 ≤ 55%
MAX_PE = 40.0          # 本益比上限（景气循环股例外需人工覆写）
INDUSTRY_CAP = 0.25    # 单产业不超过选股池 25%


# ── 基础统计 ────────────────────────────────────────────────────────
def _ma(xs, n):
    n = min(n, len(xs))
    return sum(xs[-n:]) / n if n else 0.0


def _max_drawdown(xs):
    peak, mdd = xs[0], 0.0
    for x in xs:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1.0)
    return mdd


def _ann_vol(xs, window=60):
    w = xs[-window:] if len(xs) > window else xs
    rets = [w[i] / w[i - 1] - 1.0 for i in range(1, len(w)) if w[i - 1] > 0]
    return statistics.pstdev(rets) * math.sqrt(252) if len(rets) > 2 else 0.0


# ── 市场状态 ────────────────────────────────────────────────────────
def regime(closes, label=""):
    """输入：TAIEX 收盘价序列（由旧到新）；输出：状态判定 dict"""
    last = closes[-1]
    hh = max(closes[-252:]) if len(closes) >= 252 else max(closes)
    dd = last / hh - 1.0
    ma240 = _ma(closes, 240)
    ma60 = _ma(closes, 60)
    vol20 = _ann_vol(closes, 20)

    if dd <= -0.25 or vol20 >= 0.45:
        state = "CRISIS"
    elif dd <= -0.15 or last < ma240:
        state = "BEAR"
    elif dd <= -0.08:
        state = "NEUTRAL"
    else:
        state = "BULL"

    return {
        "label": label,
        "last": round(last, 2),
        "high_252": round(hh, 2),
        "drawdown_pct": round(dd * 100, 2),
        "ma240": round(ma240, 2),
        "ma60": round(ma60, 2),
        "above_ma240": last > ma240,
        "vol20_ann_pct": round(vol20 * 100, 2),
        "state": state,
        "position_cap_pct": round(REGIME_CAP[state] * 100),
        "note": REGIME_NOTE[state],
    }


# ── 选股漏斗 ────────────────────────────────────────────────────────
@dataclass
class Pick:
    sid: str
    name: str
    industry: str
    close: float
    ret5y_pct: float
    mdd_pct: float
    vol_pct: float
    adv_yi: float          # 日均成交额（亿元）
    pe: float | None
    yield_pct: float | None
    above_ma240: bool
    score: float = 0.0
    passed: bool = True
    fail_reason: list = field(default_factory=list)


def _score(p: Pick):
    """把五项指标转成 0–100 分，仅用于同分排序，不代表预期报酬。"""
    def norm(v, lo, hi):
        if v is None:
            return 0.0
        return max(0.0, min(1.0, (v - lo) / (hi - lo)))

    trend = 1.0 if p.above_ma240 else 0.0
    low_vol = 1.0 - norm(p.vol_pct, 15, 60)
    low_dd = 1.0 - norm(abs(p.mdd_pct), 15, 70)
    cheap = 1.0 - norm(p.pe if p.pe else 99, 8, 40)
    div = norm(p.yield_pct or 0, 0, 6)
    return round(25 * trend + 20 * low_vol + 20 * low_dd + 20 * cheap + 15 * div, 1)


def screen(snapshot):
    snap = snapshot["stocks"]
    picks = []

    for sid, s in snap.items():
        closes, vols = s.get("closes") or [], s.get("volumes") or []
        if len(closes) < MIN_BARS:
            picks.append(Pick(sid, s.get("name", ""), s.get("industry", ""),
                              closes[-1] if closes else 0, 0, 0, 0, 0, None, None,
                              False, passed=False, fail_reason=["历史不足"]))
            continue

        close = closes[-1]
        adv = sum(v * 1000 * c for v, c in zip(vols[-60:], closes[-60:])) / max(1, len(vols[-60:]))
        latest = s.get("latest") or []
        pe = latest[2] if len(latest) >= 3 else None
        dy = latest[1] if len(latest) >= 2 else None

        p = Pick(
            sid=sid, name=s.get("name", ""), industry=s.get("industry", ""),
            close=close,
            ret5y_pct=round((close / closes[0] - 1) * 100, 1),
            mdd_pct=round(_max_drawdown(closes) * 100, 1),
            vol_pct=round(_ann_vol(closes) * 100, 1),
            adv_yi=round(adv / 1e8, 2),
            pe=round(pe, 1) if isinstance(pe, (int, float)) else None,
            yield_pct=round(dy, 2) if isinstance(dy, (int, float)) else None,
            above_ma240=close > _ma(closes, 240),
        )

        if p.adv_yi * 1e8 < MIN_ADV_NTD:
            p.passed = False; p.fail_reason.append("流动性不足")
        if p.vol_pct / 100 > MAX_VOL_ANN:
            p.passed = False; p.fail_reason.append("波动过高")
        if abs(p.mdd_pct) / 100 > MAX_DRAWDOWN:
            p.passed = False; p.fail_reason.append("回撤过深")
        if p.pe is None or p.pe <= 0 or p.pe > MAX_PE:
            p.passed = False; p.fail_reason.append("估值不合格")
        if not p.above_ma240:
            p.passed = False; p.fail_reason.append("跌破年线")
        picks.append(p)

    ok = [p for p in picks if p.passed]
    for p in ok:
        p.score = _score(p)
    ok.sort(key=lambda x: -x.score)

    # 产业上限：单一产业不超过 INDUSTRY_CAP（以通过档数为基数）
    cap_by_ind = max(2, int(len(ok) * INDUSTRY_CAP))
    ind_cnt, final = {}, []
    for p in ok:
        if ind_cnt.get(p.industry, 0) >= cap_by_ind:
            p.fail_reason.append(f"产业超限({p.industry}已{cap_by_ind}档)")
            continue
        ind_cnt[p.industry] = ind_cnt.get(p.industry, 0) + 1
        final.append(p)

    return picks, final


# ── 交易前 12 问（fail-closed） ──────────────────────────────────────
PRETRADE_QUESTIONS = [
    ("Q1", "这笔钱三年内不需要用到？"),
    ("Q2", "这是盘前计划里的动作，不是开盘后临时起意？"),
    ("Q3", "就算这笔归零，也不影响生活与家人？"),
    ("Q4", "单一标的占总资产在 20% 以内？"),
    ("Q5", "总仓位在本市场状态的额度内？"),
    ("Q6", "停损价位已设定，且能交给券商条件单托管？"),
    ("Q7", "含手续费与交易税后，打平所需涨幅低于预期幅度的一半？"),
    ("Q8", "买入理由能用一句话说清，且不含「听说／感觉／大家都在买」？"),
    ("Q9", "这家公司最近四季合计是获利的？"),
    ("Q10", "同产业持股没有超过上限？"),
    ("Q11", "不是因为它「跌很多」才想买？（接刀检测）"),
    ("Q12", "若明天再跌 10%，我的动作已写在计划里？"),
]


def pretrade_check(answers: dict, regime_state: str, position_pct: float):
    """answers: {Q编号: True/False/None}；None 一律视为 fail。"""
    issues = []
    for qid, text in PRETRADE_QUESTIONS:
        v = answers.get(qid)
        if v is not True:
            issues.append(f"{qid} {text} → {'未回答' if v is None else '否'}")
    cap = REGIME_CAP.get(regime_state, 0.0)
    if position_pct > cap:
        issues.append(f"Q5 总仓位 {position_pct:.0%} 超过 {regime_state} 上限 {cap:.0%}")
    return {"ok": not issues, "issues": issues}


# ══════════════════════════════════════════════════════════════════
# 三、自检：用真实数据跑一遍（不是示范，是真跑）
# ══════════════════════════════════════════════════════════════════
def _main():
    root = Path(__file__).resolve().parents[2]
    data = json.loads((root / "assets/data/snapshot.json").read_text(encoding="utf-8"))

    print("=== 一、市场状态（资料截至 2026-10-22，TAIEX）===")
    r1 = regime(data["index"]["closes"], "2026-10-22 收盘")
    for k, v in r1.items():
        if k not in ("note",):
            print(f"  {k:<16} {v}")
    print(f"  note             {r1['note']}")

    print("\n=== 二、同一公式套用到 2026-11-06 崩盘后 ===")
    # 以 10/22 序列为底，接上 11/5(41574.72)、11/6(39701.64) 两个公开收盘价
    ext = list(data["index"]["closes"]) + [41574.72, 39701.64]
    r2 = regime(ext, "2026-11-06 收盘")
    for k in ("last", "high_252", "drawdown_pct", "ma240", "above_ma240",
              "vol20_ann_pct", "state", "position_cap_pct"):
        print(f"  {k:<16} {r2[k]}")
    print(f"  note             {r2['note']}")
    print(f"  → 状态由 {r1['state']} 切换为 {r2['state']}，"
          f"仓位上限 {r1['position_cap_pct']}% → {r2['position_cap_pct']}%")

    print("\n=== 三、选股漏斗（111 档 → 通过者）===")
    picks, final = screen(data)
    fail = [p for p in picks if not p.passed]
    from collections import Counter
    reasons = Counter(r for p in fail for r in p.fail_reason)
    print(f"  总数 {len(picks)}｜通过 {len(final)}｜淘汰 {len(fail)}")
    print("  淘汰原因：", dict(reasons.most_common()))
    print(f"\n  {'代號':<6}{'名稱':<10}{'產業':<8}{'收盤':>8}{'5年%':>9}{'回撤%':>8}"
          f"{'波動%':>8}{'均額億':>8}{'PE':>7}{'息%':>6}{'評分':>7}")
    for p in final[:20]:
        print(f"  {p.sid:<6}{p.name[:8]:<10}{p.industry[:6]:<8}{p.close:>8.1f}"
              f"{p.ret5y_pct:>9.1f}{p.mdd_pct:>8.1f}{p.vol_pct:>8.1f}"
              f"{p.adv_yi:>8.1f}{(p.pe if p.pe else 0):>7.1f}"
              f"{(p.yield_pct or 0):>6.2f}{p.score:>7.1f}")
    if len(final) > 20:
        print(f"  …另有 {len(final) - 20} 档")

    print("\n=== 四、交易前 12 问（示范：全部未知 → 必须拒单）===")
    res = pretrade_check({}, r2["state"], position_pct=0.55)
    print(f"  结果：{'通过' if res['ok'] else '拒单'}")
    for i in res["issues"][:4]:
        print("   ", i)
    print(f"    …共 {len(res['issues'])} 项未通过")

    print("\n=== 五、诚实声明 ===")
    print("  · 本筛选是『排除法』，不是选股预测；通过 ≠ 会涨")
    print("  · 未含股息、未做样本外验证，不得据此直接下单")
    print("  · 11/5、11/6 两点为公开收盘价，仅用于状态判定，非数据源内容")


if __name__ == "__main__":
    _main()
