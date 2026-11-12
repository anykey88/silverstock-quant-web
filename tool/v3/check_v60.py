"""V6.0 報告體檢：直接沿用 auto_check.py 的 check_file 與七項口徑。

不放寬標準、不另立一套。技術版保留代號，故「長輩版術語洩漏」該項不適用。
用法：python3.11 tool/v3/check_v60.py
輸出：silverstock_quant_web/v60_report_check.json
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from auto_check import CHECK_NAMES, _opencc, check_file

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
SRC = ROOT / "v60_income_research.json"
OUT = ROOT / "v60_report_check.json"

FILES = [
    {"file": WORKSPACE / "V6.0_創收方法與出路.html", "html": True, "elder": True},
    {"file": WORKSPACE / "V6.0_創收方法與出路決策卡.md", "html": False, "elder": True},
    {"file": ROOT / "docs" / "V6.0_INCOME_PATHS.md", "html": False, "elder": False},
]


def main() -> None:
    cc = _opencc()
    try:
        json.loads(SRC.read_text(encoding="utf-8"))
        result_ok = True
    except Exception:
        result_ok = False

    rows, n_fail, n_na, n_checks = [], 0, 0, 0
    for f in FILES:
        r = check_file(f["file"], f["html"], f["elder"], result_ok, cc)
        rows.append(r)
        n_fail += sum(1 for c in r["checks"] if not c["ok"])
        n_na += r.get("na", 0)
        n_checks += len(r["checks"])

    d = {
        "version": "V6.0",
        "generated_at": date.today().isoformat(),
        "purpose": "沿用 V5.1 auto_check.py 的七項口徑檢查新報告，標準沒放寬。",
        "standard": "技術版保留代號與 URL，故術語檢查與標籤閉合該項不適用。",
        "check_names": CHECK_NAMES,
        "result_file": SRC.name,
        "result_readable": result_ok,
        "n_files": len(rows),
        "n_checks": n_checks,
        "n_fail": n_fail,
        "n_not_applicable": n_na,
        "all_pass": n_fail == 0 and result_ok,
        "results": rows,
    }
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"產出 {OUT.name}｜{d['n_files']} 份檔、{n_checks} 項檢查、"
          f"失敗 {n_fail} 項、不適用 {n_na} 項、全部通過＝{d['all_pass']}")
    for r in rows:
        bad = [c for c in r["checks"] if not c["ok"]]
        print(f"  {r['file']}: {'通過' if r['passed'] else '!! 未通過'}")
        for c in bad:
            print(f"      - {c['name']}：{c['note']}")


if __name__ == "__main__":
    main()
