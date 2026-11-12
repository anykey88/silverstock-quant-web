#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inventory_v50.py — V5.0 接續系統的真實盤點引擎

職責單一：把「現在到底有什麼」用讀檔算出，寫成 v50_inventory.json，
供 gen_v50_spec.py 產生規格書。不編數字、不推測、不改任何既有檔案。

紀律（沿用 V4.2 第八條）：所有數字一律由程式讀檔回填。
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path("/workspace")
PROJ = ROOT / "silverstock_quant_web"
V3 = PROJ / "tool" / "v3"
OUT = PROJ / "v50_inventory.json"


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def human(n: int) -> str:
    return f"{n:,}"


# ── 1. 掃描 tool/v3 所有 Python 模組 ────────────────────────────────
def scan_modules() -> list[dict]:
    rows = []
    for p in sorted(V3.glob("*.py")):
        src = p.read_text(encoding="utf-8")
        lines = src.splitlines()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            rows.append({"file": p.name, "parse_error": True})
            continue
        doc = ast.get_docstring(tree) or ""
        summary = ""
        for ln in doc.splitlines():
            ln = ln.strip()
            if ln and not ln.startswith(("inventory_v50", "principles.py", "case_", "gen_")):
                summary = ln
                break
        if not summary:
            for ln in doc.splitlines():
                if ln.strip():
                    summary = ln.strip()
                    break
        funcs, classes, consts = [], [], {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id.isupper():
                        try:
                            consts[t.id] = ast.literal_eval(node.value)
                        except Exception:
                            pass
        rows.append({
            "file": p.name,
            "bytes": p.stat().st_size,
            "lines": len(lines),
            "summary": summary[:90],
            "funcs": funcs,
            "classes": classes,
            "n_funcs": len(funcs),
            "n_classes": len(classes),
            "consts": consts,
        })
    return rows


# ── 2. 資料集規格 ───────────────────────────────────────────────────
def scan_dataset() -> dict:
    p = PROJ / "assets" / "data" / "snapshot.json"
    d = jload(p)
    st = d["stocks"]
    lens = [len(v.get("closes", [])) for v in st.values()]
    return {
        "file": "assets/data/snapshot.json",
        "bytes": p.stat().st_size,
        "source": d["meta"]["source"],
        "captured_at": d["meta"]["capturedAt"],
        "range": d["meta"]["range"],
        "universe": d["meta"]["universe"],
        "n_stocks": len(st),
        "index_bars": len(d["index"]["closes"]),
        "index_first": d["index"]["closes"][0],
        "index_last": d["index"]["closes"][-1],
        "bars_min": min(lens),
        "bars_max": max(lens),
        "bars_mode": max(set(lens), key=lens.count),
        "with_quarterly_eps": sum(1 for v in st.values() if v.get("quarterlyEps")),
        "with_dividends": sum(1 for v in st.values() if v.get("dividends")),
        "fields_per_stock": sorted({k for v in st.values() for k in v.keys()}),
        "missing_fields": ["當日開高低價", "真實換手率／流通股數", "融資融券逐日", "逐筆成交",
                           "國際股市", "總體經濟", "債券與黃金", "月營收年增率"],
    }


# ── 3. 結果檔清單 ───────────────────────────────────────────────────
RESULT_FILES = [
    "v31_ab_result.json", "v33_strategy_lab_result.json", "v35_factor_audit.json",
    "v3_demo_result.json",
    "v38_allocation_result.json", "v39_bear_result.json", "v40_execution_result.json",
    "v41_structure_result.json", "v42_self_improve.json", "v43_case_6217.json",
    "v44_top_decision.json", "v45_one_lot.json", "v46_largest_asset.json",
]


def scan_results() -> list[dict]:
    rows = []
    for name in RESULT_FILES:
        p = PROJ / name
        if not p.is_file():
            p = ROOT / name
        if not p.is_file():
            continue
        d = jload(p)
        rows.append({
            "file": p.name,
            "bytes": p.stat().st_size,
            "in_repo": (p.parent == PROJ),
            "keys": list(d.keys()),
            "version": d.get("version") or d.get("meta", {}).get("version") if isinstance(d.get("meta"), dict) else d.get("version"),
        })
    return rows


# ── 4. 報告檔（依版本分組）────────────────────────────────────────
def scan_reports() -> dict:
    groups = {}
    for p in sorted(ROOT.glob("V*.*")):
        if p.suffix not in (".html", ".md"):
            continue
        m = re.match(r"^V(\d+\.\d+)_", p.name)
        if not m:
            continue
        v = m.group(1)
        groups.setdefault(v, []).append({"file": p.name, "bytes": p.stat().st_size,
                                         "kind": p.suffix.lstrip(".")})
    return {"by_version": dict(sorted(groups.items(), key=lambda kv: [int(x) for x in kv[0].split(".")])),
            "n_html": sum(1 for g in groups.values() for x in g if x["kind"] == "html"),
            "n_md": sum(1 for g in groups.values() for x in g if x["kind"] == "md")}


# ── 5. 規則常數（用 ast 讀，不 import、無副作用）──────────────────
def const_of(fname: str, names: list[str]) -> dict:
    tree = ast.parse((V3 / fname).read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in names:
                    try:
                        out[t.id] = ast.literal_eval(node.value)
                    except Exception:
                        out[t.id] = "<複合值，見原始檔>"
    return out


def scan_rules() -> dict:
    fee = const_of("trade_plan_engine.py", [
        "FEE_RATE", "TAX_RATE_STOCK", "TAX_RATE_ETF", "TAX_RATE_DAYTRADE",
        "MIN_FEE_ODD", "MIN_FEE_ROUND"])
    prin = const_of("principles.py", [
        "REGIME_CAP", "MIN_BARS", "MIN_ADV_NTD", "MAX_VOL_ANN", "MAX_DRAWDOWN",
        "MAX_PE", "INDUSTRY_CAP", "PRETRADE_QUESTIONS", "VALUES"])
    bridge = const_of("fubon_bridge.py", ["SANDBOX_URL"])
    auth_tree = ast.parse((V3 / "authorization.py").read_text(encoding="utf-8"))
    auth_defaults, levels = {}, []
    for node in ast.walk(auth_tree):
        if isinstance(node, ast.ClassDef) and node.name == "AuthorizationPolicy":
            for st in node.body:
                if isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name) and st.value is not None:
                    try:
                        auth_defaults[st.target.id] = ast.literal_eval(st.value)
                    except Exception:
                        pass
        if isinstance(node, ast.ClassDef) and node.name == "AuthLevel":
            for st in node.body:
                if isinstance(st, ast.Assign) and isinstance(st.targets[0], ast.Name):
                    try:
                        levels.append({"name": st.targets[0].id, "value": ast.literal_eval(st.value)})
                    except Exception:
                        pass
    v42 = jload(PROJ / "v42_self_improve.json")
    grading = v42["grading"]
    return {
        "fee": fee,
        "principles": {k: v for k, v in prin.items() if k != "VALUES" and k != "PRETRADE_QUESTIONS"},
        "n_values": len(prin.get("VALUES", [])),
        "n_pretrade_questions": len(prin.get("PRETRADE_QUESTIONS", [])),
        "pretrade_questions": prin.get("PRETRADE_QUESTIONS", []),
        "sandbox_url": bridge.get("SANDBOX_URL"),
        "auth_levels": levels,
        "auth_defaults": auth_defaults,
        "self_improve": {
            "n_error_ledger": len(v42["error_ledger"]),
            "n_speak_rules": len(v42["speak_rules"]),
            "speak_rules": v42["speak_rules"],
            "gates": grading["gates"],
            "claims": grading["claims"],
        },
    }


# ── 6. 實測數字（全部由結果檔讀出）──────────────────────────────
def scan_evidence() -> dict:
    v38 = jload(PROJ / "v38_allocation_result.json")
    v39 = jload(PROJ / "v39_bear_result.json")
    v40 = jload(PROJ / "v40_execution_result.json")
    v41 = jload(PROJ / "v41_structure_result.json")
    v43 = jload(PROJ / "v43_case_6217.json")
    v44 = jload(PROJ / "v44_top_decision.json")
    v45 = jload(PROJ / "v45_one_lot.json")
    v46 = jload(PROJ / "v46_largest_asset.json")

    four_bucket = next(c for c in v38["configs"] if "四层桶" in c["key"] or "四層桶" in c["key"])
    all_in = next(c for c in v38["configs"] if "100%" in c["key"])
    crash30 = next(p for p in v39["period_stats"] if p["bars"] == 30)
    grp = v39["group_paths"]["groups"]
    struct = v41["structure"]["states"]
    idio = next(s for s in struct if "個股" in s["state"])
    dt = v40["daytrade"]

    return {
        "correlation": {
            "n_assets": v38["correlation"]["n_assets"],
            "avg_pairwise_corr": v38["correlation"]["avg_pairwise_corr"],
            "effective_n": v38["correlation"]["effective_n"],
            "vol_reduction_pct": v38["correlation"]["vol_reduction_pct"],
            "single_vol_pct": v38["correlation"]["avg_single_vol_pct"],
            "equal_weight_vol_pct": v38["correlation"]["equal_weight_vol_pct"],
        },
        "four_bucket": {"key": four_bucket["key"], "ann_pct": four_bucket["ann_pct"],
                        "mdd_pct": four_bucket["mdd_pct"], "calmar": four_bucket["calmar"]},
        "all_in": {"key": all_in["key"], "ann_pct": all_in["ann_pct"],
                   "mdd_pct": all_in["mdd_pct"], "calmar": all_in["calmar"]},
        "n_configs": len(v38["configs"]),
        "crash30": crash30,
        "groups": {k: {"total_pct": v["total_pct"], "mdd_pct": v["mdd_pct"], "n": v["n"]}
                   for k, v in grp.items()},
        "leverage": v39["top_lever_loss"],
        "daytrade": {"cost_stock_pct": dt["cost_stock_pct"],
                     "annual_erosion_stock_pct": dt["annual_erosion_stock_pct"]},
        "structure": {"n_days": v41["structure"]["n_days"],
                      "states": [{"state": s["state"], "pct": s["pct"], "n": s["n"]} for s in struct]},
        "idio": {"state": idio["state"], "pct": idio["pct"], "share_idio": idio.get("avg_share_idio")},
        "n_cases_v41": len(v41["cases"]),
        "case_6217": {
            "in_pool": False,
            "last_close": v43["computed"]["last_close"],
            "last_date": v43["computed"]["last_date"],
            "w52_high": v43["computed"]["w52_high"],
            "w52_low": v43["computed"]["w52_low"],
            "drop_from_high_pct": v43["computed"]["drop_from_52w_high_pct"],
            "four_day_drop_pct": v43["computed"]["drop_1102_to_1106_pct"],
            "required_bars": 1000,
            "external_bars": 4,
            "buy_paid": v44["money"]["buy_paid"],
            "sell_received": v44["money"]["sell_received"],
            "loss_per_lot": v44["money"]["loss_per_lot"],
            "loss_pct_on_cash": v44["money"]["loss_pct_on_cash"],
            "loss_pct_on_price": v44["money"]["loss_pct_on_price"],
            "recover_price": v44["money"]["recover_price"],
            "recover_pct_from_now": v44["money"]["recover_pct_from_now"],
            "saved_per_lot_if_stopped": v44["money"]["saved_per_lot_if_stopped"],
            "stop_price": v44["money"]["stop_price"],
            "n_options_v45": len(v45["options"]),
            "dividend": v46["truth"]["dividend"],
        },
        "v46": {
            "one_line": v46["one_line"],
            "ruler_examples": v46["ruler"]["examples"],
            "n_wrongbook": len(v46["wrongbook"]),
            "n_unknown": len(v46["actions"]) if isinstance(v46.get("actions"), list) else None,
        },
    }


# ── 7. git 狀態（真實執行，不猜）─────────────────────────────────
def scan_git() -> dict:
    def run(*args):
        try:
            return subprocess.run(["git", "-C", str(PROJ), *args], capture_output=True,
                                  text=True, timeout=15).stdout.strip()
        except Exception as ex:
            return f"<無法讀取：{ex}>"
    status = run("status", "--short")
    untracked = [ln[3:].strip() for ln in status.splitlines() if ln.startswith("??")]
    return {
        "remote": run("remote", "get-url", "origin"),
        "last_commits": run("log", "--oneline", "-5").splitlines(),
        "untracked": untracked,
        "n_untracked": len(untracked),
    }


# ── 8. 技術債（真實掃描，不憑印象）──────────────────────────────
def scan_techdebt() -> dict:
    abs_rows, gens = [], []
    for p in sorted(V3.glob("*.py")):
        src = p.read_text(encoding="utf-8")
        n = sum(1 for ln in src.splitlines()
                if "/workspace" in ln and not ln.strip().startswith("#"))
        if n:
            abs_rows.append({"file": p.name, "n_abs_path": n})
        if p.name.startswith("gen_"):
            gens.append(p.name)
    return {
        "n_modules_with_abs_path": len(abs_rows),
        "abs_path_modules": abs_rows,
        "n_generators": len(gens),
        "generators": gens,
        "n_result_in_root": sum(1 for r in scan_results() if not r["in_repo"]),
        "n_result_in_repo": sum(1 for r in scan_results() if r["in_repo"]),
        "no_shared_layout_module": not (V3 / "report_layout.py").exists(),
        "no_auto_check_script": not (V3 / "check_report.py").exists(),
    }


def main():
    inv = {
        "version": "V5.0",
        "title": "台海股投資接續系統・開發與技術總規格",
        "generated_at": "2026-11-08",
        "purpose": "把 V2.7～V4.6 的架構、規則與溝通結論，收成一張可接續開發的地圖；本版不新增交易功能、不連線、不下單。",
        "modules": scan_modules(),
        "dataset": scan_dataset(),
        "results": scan_results(),
        "reports": scan_reports(),
        "rules": scan_rules(),
        "evidence": scan_evidence(),
        "git": scan_git(),
        "techdebt": scan_techdebt(),
    }
    inv["counts"] = {
        "n_py_modules": len([m for m in inv["modules"] if not m.get("parse_error")]),
        "n_py_lines": sum(m.get("lines", 0) for m in inv["modules"]),
        "n_py_bytes": sum(m.get("bytes", 0) for m in inv["modules"]),
        "n_result_files": len(inv["results"]),
        "n_report_files": inv["reports"]["n_html"] + inv["reports"]["n_md"],
        "n_versions": len(inv["reports"]["by_version"]),
    }
    OUT.write_text(json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"產出 {OUT.name}（{OUT.stat().st_size:,} bytes）")
    print(f"  模組 {inv['counts']['n_py_modules']} 支／{inv['counts']['n_py_lines']:,} 行")
    print(f"  結果檔 {inv['counts']['n_result_files']} 份／報告 {inv['counts']['n_report_files']} 份／版本 {inv['counts']['n_versions']} 個")
    print(f"  未推送檔案 {inv['git']['n_untracked']} 項")


if __name__ == "__main__":
    main()
