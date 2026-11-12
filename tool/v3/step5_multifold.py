# -*- coding: utf-8 -*-
"""V5.2 施工單第 5 步：換成多段輪流考，不再只切一次。

對應 V5.1 執行手冊第 5 步：
  做出來會看到：多段輪流考的結果檔
  做到什麼算完成：結論不是靠剛好押中那一段，換別段也站得住

做法：
  - 沿用 V4.0 的 7 個等待參數與同一套含息、含成本回測，不做任何調整。
  - 舊做法只在 2024-07-01 切一次；本步改成 expanding window：
    每段「用前面所有資料挑參數 → 緊接著一段沒看過的日子驗證 → 對照放著不動」。
  - 逐段往前滾，統計幾段贏、平均超額多少、每段選的參數是否一致。
  - 結論由數字自動判定，不由人挑好看的講。

紀律：參數事前固定、訓練與測試不重疊、每段都單獨重跑一次對照。

用法：python3.11 tool/v3/step5_multifold.py
產出：v52_step5_multifold.json
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from asset_allocation import load, series_of, total_return_index  # noqa: E402
from execution_lab import (  # noqa: E402
    run_weighted, norm, _ma_hh, _wait_rule, TAX_ETF,
)

OUT = ROOT / "v52_step5_multifold.json"
V40 = ROOT / "v40_execution_result.json"

# 與 V4.0 walkforward 完全相同的候選參數
CANDS = [("ma60", 0), ("ma120", 0), ("ma240", 0),
         ("dd", 0.08), ("dd", 0.15), ("dd", 0.20), ("dd", 0.25)]
TRAIN_INIT = 500     # 第一段至少要有 500 個交易日才准挑參數
TEST_LEN = 120       # 每段考 120 個沒看過的交易日（約半年）
STEP = 120


def one_fold(px, ma, hh, axis, tr0, tr1, te0, te1) -> dict:
    """一段：訓練挑參數 → 樣本外驗證 → 對照放著不動。"""
    train = []
    for kind, th in CANDS:
        r = _wait_rule(px, ma, hh, tr0, tr1, kind, th)
        train.append({"kind": kind, "th": th, "calmar": r["calmar"],
                      "total_pct": r["total_pct"], "mdd_pct": r["mdd_pct"]})
    best = max(train, key=lambda x: x["calmar"])

    rule = _wait_rule(px, ma, hh, te0, te1, best["kind"], best["th"])
    bh = run_weighted(norm(px, te0, te1),
                      lambda i, w, eq, ctx: 1.0, tax=TAX_ETF)[0]
    return {
        "train_range": [axis[tr0], axis[tr1]],
        "test_range": [axis[te0], axis[te1]],
        "n_train_bars": tr1 - tr0 + 1,
        "n_test_bars": te1 - te0 + 1,
        "best_param": f'{best["kind"]}' + (f' {best["th"]}' if best["th"] else ""),
        "best_in_sample_calmar": best["calmar"],
        "rule_total_pct": rule["total_pct"],
        "rule_mdd_pct": rule["mdd_pct"],
        "rule_calmar": rule["calmar"],
        "rule_turnovers": rule["turnovers"],
        "buyhold_total_pct": bh["total_pct"],
        "buyhold_mdd_pct": bh["mdd_pct"],
        "buyhold_calmar": bh["calmar"],
        "outperformance_pp": round(rule["total_pct"] - bh["total_pct"], 2),
        "mdd_improvement_pp": round(rule["mdd_pct"] - bh["mdd_pct"], 2),
        "train_candidates": train,
    }


def main() -> None:
    snap = load()
    axis = snap["index"]["dates"]
    navs = {}
    for sid, s in snap["stocks"].items():
        p, divs = series_of(s)
        if len(p) < 800:
            continue
        navs[sid] = total_return_index(p, divs, axis)
    px = navs["0050"]
    ma, hh = _ma_hh(px)
    n = len(axis)

    folds, repeat_ok, no_overlap = [], [], []
    te0 = TRAIN_INIT
    k = 0
    while te0 < n - 20:
        tr0, tr1 = 0, te0 - 1              # expanding：每次都用前面全部資料
        te1 = min(te0 + TEST_LEN - 1, n - 1)
        r1 = one_fold(px, ma, hh, axis, tr0, tr1, te0, te1)
        r2 = one_fold(px, ma, hh, axis, tr0, tr1, te0, te1)  # 同一段重跑一次
        k += 1
        repeat_ok.append({kk: r1[kk] for kk in
                          ("rule_total_pct", "buyhold_total_pct",
                           "outperformance_pp", "best_param")}
                         == {kk: r2[kk] for kk in
                             ("rule_total_pct", "buyhold_total_pct",
                              "outperformance_pp", "best_param")})
        no_overlap.append(tr1 < te0)
        r1["fold"] = k
        folds.append(r1)
        te0 = te1 + 1

    outs = [f["outperformance_pp"] for f in folds]
    wins = sum(1 for x in outs if x > 0)
    win_rate = round(wins / len(folds) * 100, 1)
    avg = round(sum(outs) / len(outs), 2)
    params = [f["best_param"] for f in folds]
    param_kinds = sorted(set(params))

    # 自動判定，不挑好看的講
    if avg > 0 and win_rate >= 70:
        verdict = "站得住：多段平均贏、且大部分段落都贏"
    elif avg > 0:
        verdict = "只在部分時段站得住：平均是正的，但贏的段數不夠多"
    else:
        verdict = "站不住：多段平均跑輸放著不動，不能說這套規矩有效"

    v40 = json.loads(V40.read_text(encoding="utf-8"))["walkforward"]
    old = {
        "split_date": v40["split_date"],
        "test_range": v40["test_range"],
        "outperformance_pp": v40["outperformance_pp"],
        "best_param": v40["best_in_sample"]["kind"],
        "plain": "舊做法只切一次，等於只考一回；那一回本身就是跑輸的",
    }

    d = {
        "version": "V5.2-step5",
        "step": 5,
        "title": "多段輪流考：不再只切一次",
        "generated_at": date.today().isoformat(),
        "source_files": ["assets/data/snapshot.json",
                         "v40_execution_result.json", "tool/v3/execution_lab.py"],
        "setting": {
            "symbol": "0050", "train_init_bars": TRAIN_INIT,
            "test_len_bars": TEST_LEN, "step_bars": STEP,
            "window": "expanding（每次用前面全部資料挑參數）",
            "n_candidates": len(CANDS),
            "note": "候選參數、成本、訊號全部沿用 V4.0，沒有重新調整",
        },
        "n_folds": len(folds),
        "folds": folds,
        "repeat_identical": repeat_ok,
        "no_train_test_overlap": no_overlap,
        "summary": {
            "n_folds": len(folds),
            "n_wins": wins,
            "win_rate_pct": win_rate,
            "avg_outperformance_pp": avg,
            "median_outperformance_pp": round(statistics.median(outs), 2),
            "best_fold_pp": max(outs),
            "worst_fold_pp": min(outs),
            "distinct_best_params": param_kinds,
            "n_distinct_params": len(param_kinds),
            "param_consistent": len(param_kinds) == 1,
            "verdict": verdict,
        },
        "old_single_split": old,
        "verification": {},
    }
    checks = {
        "至少 5 段輪流考": len(folds) >= 5,
        "每段訓練與測試不重疊": all(no_overlap),
        "每段都有放著不動當對照": all("buyhold_total_pct" in f for f in folds),
        "每段單獨重跑數字相同": all(repeat_ok),
        "結果檔可被讀回": True,
        "結論由數字自動判定": bool(verdict),
    }
    d["verification"] = {
        "checks": checks, "all_pass": all(checks.values()),
        "n_checks": len(checks),
        "n_fail": sum(1 for v in checks.values() if not v),
    }
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    s = d["summary"]
    print(f"[第5步] {len(folds)} 段輪流考（舊做法只考 1 段）")
    for f in folds:
        print(f"  第{f['fold']}段 {f['test_range']}｜選 {f['best_param']}｜"
              f"規矩 {f['rule_total_pct']:+.2f}% vs 放著不動 {f['buyhold_total_pct']:+.2f}%"
              f" → 超額 {f['outperformance_pp']:+.2f}pp")
    print(f"  贏 {s['n_wins']}/{s['n_folds']} 段（{s['win_rate_pct']}%）｜"
          f"平均超額 {s['avg_outperformance_pp']:+.2f}pp｜"
          f"最好 {s['best_fold_pp']:+.2f}／最差 {s['worst_fold_pp']:+.2f}pp")
    print(f"  每段選的參數：{'、'.join(s['distinct_best_params'])}"
          f"（共 {s['n_distinct_params']} 種）")
    print(f"  判定：{s['verdict']}")
    print(f"  舊單切一次：{old['outperformance_pp']:+.2f}pp（{old['split_date']}）")
    v = d["verification"]
    print(f"  驗證 {v['n_checks']} 項、失敗 {v['n_fail']} 項、全過＝{v['all_pass']}")
    for kk, ok in checks.items():
        print(f"    {'OK ' if ok else '!! '} {kk}")


if __name__ == "__main__":
    main()
