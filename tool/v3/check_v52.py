# -*- coding: utf-8 -*-
"""V5.2 新增報告的自動體檢：沿用 V5.1 既有七項口徑，不改標準、不改原程式。

刻意只呼叫 auto_check.check_file()，不修改 auto_check.py 本身：
一次只做一件，避免動到已經驗過的體檢規則。

用法：python3.11 tool/v3/check_v52.py
產出：v52_report_check.json
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from auto_check import (  # noqa: E402
    check_file, _opencc, CHECK_NAMES, ROOT as AC_ROOT,
    WORKSPACE as AC_WORKSPACE,
)

OUT = ROOT / "v52_report_check.json"

RESULTS = [
    "v52_step2_freshness.json",
    "v52_step3_ablation.json",
    "v52_step4_daily_nav.json",
    "v52_step5_multifold.json",
]
PAIR = {
    "group": "V5.2",
    "html": "V5.2_施工單編程結果.html",
    "md": "V5.2_施工單編程結果決策卡.md",
}


def main() -> None:
    cc = _opencc()
    readable = {}
    for name in RESULTS:
        try:
            json.loads((AC_ROOT / name).read_text(encoding="utf-8"))
            readable[name] = True
        except Exception:
            readable[name] = False
    result_ok = all(readable.values())

    h = check_file(AC_WORKSPACE / PAIR["html"], True, True, result_ok, cc)
    m = check_file(AC_WORKSPACE / PAIR["md"], False, False, result_ok, cc)

    n_fail = sum(1 for r in (h, m) for c in r["checks"] if not c["ok"])
    n_na = sum(r.get("na", 0) for r in (h, m))
    n_checks = sum(len(r["checks"]) for r in (h, m))
    d = {
        "version": "V5.2",
        "generated_at": date.today().isoformat(),
        "purpose": "沿用 V5.1 七項體檢口徑檢查本輪新增報告；不改原體檢程式。",
        "standard": "與 V5.1 完全相同，沒有放寬；技術版保留代號故該項不適用。",
        "check_names": CHECK_NAMES,
        "source_results_readable": readable,
        "n_files": 2,
        "n_checks": n_checks,
        "n_fail": n_fail,
        "n_not_applicable": n_na,
        "all_pass": n_fail == 0,
        "html": h,
        "md": m,
    }
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[V5.2 體檢] {n_checks} 項、失敗 {n_fail} 項、"
          f"不適用 {n_na} 項、全部通過＝{d['all_pass']}")
    for r in (h, m):
        print(f"  {r['file']}: {'通過' if r['passed'] else '!! 未通過'}")
        for c in r["checks"]:
            if not c["ok"]:
                print(f"    !! {c['name']}：{c['note']}")


if __name__ == "__main__":
    main()
