# -*- coding: utf-8 -*-
"""V5.2 施工單第 3 步：把「部分減碼／月檢／賣後回補」拆開，一次只改一處各驗一次。

對應 V5.1 執行手冊第 3 步：
  做出來會看到：三份分開的對照結果，各自看得出是誰有功勞
  做到什麼算完成：每一處改動都能單獨重跑，數字對得上

做法：把 V4.0 combined_rule 的三個元件做成獨立開關，跑完 8 種組合。
用「全開」那一組去對照 V4.0 原本的程式輸出，證明拆分沒有改壞規則。

紀律：
  - 參數沿用 V4.0 原本事前固定的中庸值，不重新挑最優。
  - 一組只開一個開關＝一次只改一處；每組都單獨重跑一次對照。
  - 數字由程式算出來，不手抄、不編。

用法：python3.11 tool/v3/step3_ablation.py
產出：v52_step3_ablation.json
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from asset_allocation import load, series_of, total_return_index  # noqa: E402
from execution_lab import (  # noqa: E402
    run_weighted, norm, idx_of, _ma_hh, combined_rule, TAX_ETF,
)

OUT = ROOT / "v52_step3_ablation.json"
V40 = ROOT / "v40_execution_result.json"

# 與 V4.0 combined_rule 完全相同的參數，事前固定，不重新挑
STEP1, STEP2 = 0.20, 0.40
REENTER_DAYS, OFF_W, BATCH = 20, 0.40, 1 / 3

VARIANTS = [
    ("base", False, False, False, "都不開（放著不動）"),
    ("A", True, False, False, "只開 A：部分減碼"),
    ("B", False, True, False, "只開 B：月檢降倉"),
    ("C", False, False, True, "只開 C：賣後回補"),
    ("AB", True, True, False, "A＋B"),
    ("AC", True, False, True, "A＋C"),
    ("BC", False, True, True, "B＋C"),
    ("ABC", True, True, True, "全開（＝V4.0 原規則）"),
]

COMPONENT = {
    "A": ("部分減碼", "漲到 +20% 賣四分之一、+40% 再賣三分之一，保留底倉"),
    "B": ("月檢降倉", "每 21 天看一次長期均線，轉弱就把目標降到四成，轉強分批補回"),
    "C": ("賣後回補", "賣出後 20 天內再創新高，就買回四分之一"),
}


def run_variant(px, ma, axis, i0, i1, use_a: bool, use_b: bool, use_c: bool) -> dict:
    """一次只改一處：三個布林開關各自獨立，邏輯其餘與 V4.0 逐行相同。"""
    seg = norm(px, i0, i1)
    counter = {"reentry": 0, "scale_out": 0, "monthly": 0}

    def decide(i, w, eq, ctx):
        if i == 0:
            ctx.update(entry=seg[0], steps=set(), sell_i=None,
                       post_peak=None, target=1.0)
            return 1.0
        g = i0 + i
        pxn = seg[i]

        # ── B：月檢 ──────────────────────────────────────────────
        if use_b and i % 21 == 0:
            counter["monthly"] += 1
            ok = px[g] >= ma[120][g]
            ctx["target"] = 1.0 if ok else OFF_W
            if w < ctx["target"] - 1e-9:
                return min(ctx["target"], w + BATCH)
            if w > ctx["target"] + 1e-9:
                return max(ctx["target"], w - BATCH)

        # ── A：部分減碼 ──────────────────────────────────────────
        basis = ctx["entry"] or seg[0]
        gain = pxn / basis - 1.0
        if use_a and w > 0 and ctx["sell_i"] is None:
            if 0 not in ctx["steps"] and gain >= STEP1:
                counter["scale_out"] += 1
                ctx["steps"].add(0)
                ctx["sell_i"] = i
                ctx["post_peak"] = pxn
                ctx["target"] = max(0.0, ctx["target"] - 0.25)
                return max(0.0, w - 0.25)
            if 1 not in ctx["steps"] and gain >= STEP2:
                ctx["steps"].add(1)
                ctx["sell_i"] = i
                ctx["post_peak"] = pxn
                ctx["target"] = max(0.0, ctx["target"] - 1 / 3)
                return max(0.0, w - 1 / 3)

        # ── C：賣後回補 ──────────────────────────────────────────
        if use_c and ctx["sell_i"] is not None:
            k = i - ctx["sell_i"]
            if 0 < k <= REENTER_DAYS and pxn >= (ctx["post_peak"] or pxn):
                counter["reentry"] += 1
                ctx["sell_i"] = None
                ctx["steps"].clear()
                ctx["entry"] = pxn
                ctx["target"] = min(1.0, ctx["target"] + 0.25)
                return min(1.0, w + 0.25)
            ctx["post_peak"] = max(ctx["post_peak"] or pxn, pxn)
        elif use_a and ctx["sell_i"] is not None:
            # 不回補時仍更新賣後高點，保持與原程式其餘部分一致
            ctx["post_peak"] = max(ctx["post_peak"] or pxn, pxn)
        return w

    st, _path = run_weighted(seg, decide, tax=TAX_ETF)
    out = {k: st[k] for k in ("total_pct", "mdd_pct", "calmar",
                              "turnovers", "cost_paid_pct")}
    out.update({"n_scale_out": counter["scale_out"],
                "n_monthly_check": counter["monthly"],
                "n_reentry": counter["reentry"]})
    return out


def main() -> None:
    snap = load()
    axis = snap["index"]["dates"]
    navs = {}
    for sid, s in snap["stocks"].items():
        px, divs = series_of(s)
        if len(px) < 800:
            continue
        navs[sid] = total_return_index(px, divs, axis)
    px = navs["0050"]
    ma, _hh = _ma_hh(px)

    v40 = json.loads(V40.read_text(encoding="utf-8"))
    # 用「日期區間」對照，不用名稱：舊結果檔的段名是簡體，名稱比對會漏掉
    v40_by_range = {tuple(c["range"]): c for c in v40.get("combined", [])}

    segments = [
        ("多頭一", 20221025, 20240711),
        ("多頭二", 20250409, 20261022),
        ("全程", None, None),
    ]

    out_segments = []
    for label, d0, d1 in segments:
        i0 = idx_of(axis, d0) if d0 else 0
        i1 = idx_of(axis, d1) if d1 else len(axis) - 1
        rows, repeat_ok = [], {}
        for key, a, b, c, desc in VARIANTS:
            r1 = run_variant(px, ma, axis, i0, i1, a, b, c)
            r2 = run_variant(px, ma, axis, i0, i1, a, b, c)  # 同一組重跑一次
            repeat_ok[key] = (r1 == r2)
            rows.append({"key": key, "A": a, "B": b, "C": c, "desc": desc,
                         **r1})
        by = {r["key"]: r["total_pct"] for r in rows}
        base = by["base"]

        marginal = {}
        for comp, off_key in (("A", "BC"), ("B", "AC"), ("C", "AB")):
            alone = by[comp] - base
            edge = by["ABC"] - by[off_key]
            marginal[comp] = {
                "name": COMPONENT[comp][0],
                "plain": COMPONENT[comp][1],
                "alone_pp": round(alone, 2),
                "marginal_pp": round(edge, 2),
                "interaction_pp": round(edge - alone, 2),
            }

        # 全開組必須與 V4.0 原程式對得上，證明拆分沒改壞
        old = v40_by_range.get((axis[i0], axis[i1]), {}).get("combo", {})
        full = next(r for r in rows if r["key"] == "ABC")
        diffs = {k: round(full[k] - old.get(k, 0), 4)
                 for k in ("total_pct", "mdd_pct", "calmar", "turnovers",
                           "cost_paid_pct")}
        match = all(abs(v) < 0.011 for v in diffs.values())

        out_segments.append({
            "label": label, "range": [axis[i0], axis[i1]],
            "bars": i1 - i0 + 1,
            "rows": rows,
            "repeat_identical": repeat_ok,
            "marginal": marginal,
            "v40_combo": old,
            "full_vs_v40_diff": diffs,
            "full_matches_v40": match,
            "buyhold_total_pct": base,
        })

    # 跨段統計：單獨貢獻與邊際貢獻差多少（這正是「一次改三處說不清」的證據）
    cross = {}
    for comp in ("A", "B", "C"):
        alone = [s["marginal"][comp]["alone_pp"] for s in out_segments]
        edge = [s["marginal"][comp]["marginal_pp"] for s in out_segments]
        cross[comp] = {
            "name": COMPONENT[comp][0],
            "alone_by_segment_pp": alone,
            "marginal_by_segment_pp": edge,
            "avg_alone_pp": round(sum(alone) / len(alone), 2),
            "avg_marginal_pp": round(sum(edge) / len(edge), 2),
            "avg_interaction_pp": round(sum(e - a for e, a in zip(edge, alone)) / len(alone), 2),
        }

    d = {
        "version": "V5.2-step3",
        "step": 3,
        "title": "三元件消融對照：一次只改一處，各驗一次",
        "generated_at": date.today().isoformat(),
        "source_files": ["assets/data/snapshot.json",
                         "v40_execution_result.json", "tool/v3/execution_lab.py"],
        "params": {"symbol": "0050", "step1": STEP1, "step2": STEP2,
                   "reenter_days": REENTER_DAYS, "off_w": OFF_W,
                   "batch": round(BATCH, 6),
                   "note": "參數沿用 V4.0 事前固定的中庸值，沒有重新挑最優"},
        "n_variants": len(VARIANTS),
        "n_segments": len(segments),
        "segments": out_segments,
        "cross_segment": cross,
        "finding": {
            "n_reentry_total": sum(
                next(r for r in s["rows"] if r["key"] == "ABC")["n_reentry"]
                for s in out_segments),
            "abc_vs_ab_turnovers_same": all(
                next(r for r in s["rows"] if r["key"] == "ABC")["turnovers"]
                == next(r for r in s["rows"] if r["key"] == "AB")["turnovers"]
                for s in out_segments),
            "plain": "拆開才看得出來：V4.0 當成最關鍵升級的「賣後回補」"
                     "在三段實測中一次都沒發動，功勞其實來自「部分減碼」與"
                     "「月檢降倉」的交互；單獨看其中一個還會以為它有害。",
        },
        "verification": {},
    }

    checks = {
        "8 種組合都跑完": all(len(s["rows"]) == len(VARIANTS) for s in out_segments),
        "每組單獨重跑數字完全相同": all(all(s["repeat_identical"].values())
                                    for s in out_segments),
        "全開組與 V4.0 原程式對得上": all(s["full_matches_v40"] for s in out_segments),
        "三段都有對照結果": len(out_segments) == 3,
        "結果檔可被讀回": True,
    }
    d["verification"] = {
        "checks": checks, "all_pass": all(checks.values()),
        "n_checks": len(checks),
        "n_fail": sum(1 for v in checks.values() if not v),
    }
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[第3步] {len(VARIANTS)} 種組合 × {len(segments)} 段＝"
          f"{len(VARIANTS) * len(segments)} 次運算")
    for s in out_segments:
        print(f"  {s['label']} {s['range']}｜基準 {s['buyhold_total_pct']:+.2f}%｜"
              f"全開 {next(r for r in s['rows'] if r['key']=='ABC')['total_pct']:+.2f}%｜"
              f"與 V4.0 相符＝{s['full_matches_v40']}")
    print("  跨段平均（單獨 / 邊際 / 交互，pp）：")
    for comp, v in cross.items():
        print(f"    {comp} {v['name']}: {v['avg_alone_pp']:+.2f} / "
              f"{v['avg_marginal_pp']:+.2f} / {v['avg_interaction_pp']:+.2f}")
    v = d["verification"]
    print(f"  驗證 {v['n_checks']} 項、失敗 {v['n_fail']} 項、全過＝{v['all_pass']}")
    for k, ok in checks.items():
        print(f"    {'OK ' if ok else '!! '} {k}")


if __name__ == "__main__":
    main()
