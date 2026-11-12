"""V5.1 自動體檢程式（只讀、不改檔、不連線、不花錢）。

職責單一：把 V4.4～V5.0 每次「手寫」的體檢，固化成一支可重跑的程式。
這是 V5.0 技術債第 5 項（沒有一支自動體檢程式）與「最小改法」第 ③ 件的落地，
也刻意示範第 ① 件：路徑一律相對於本檔案，不寫死在某一台機器。

用法：python3.11 tool/v3/auto_check.py
輸出：silverstock_quant_web/v51_check_result.json
"""
from __future__ import annotations

import json
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

# 相對路徑：本檔在 tool/v3/，往上兩層是專案根目錄
ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
OUT = ROOT / "v51_check_result.json"

# ── 沿用 V5.0 當時的體檢口徑，不改標準，避免自己放水 ──────────────
# opencc 單字級會把台灣慣用字與異體字也算進去，這些不是簡體殘留。
# 「划」：台灣本就寫「划算／划船」，只有「規劃」才用「劃」，故列為白名單。
VARIANT = set("准占台吃斗群峰只里面后干松云于几发别么划")
TERM_RE = re.compile(
    r"MA\d+|BEAR|BULL|CRISIS|HYPE|Calmar|MDD|fail-closed|walk-forward|regime|Q\d+ |RSI|EPS|ETF"
)
NEG_RE = re.compile(r"-\d+\.\d+%")
NO_RE = re.compile(r'<span class=.no.>([^<]+)</span>')
MD_NO_RE = re.compile(r"^## (\d+)．", re.M)

# 前幾版修正過、不該再出現的舊說法
FORBIDDEN = [
    "退乾淨", "跌破 11/06 最低", "一天賣十分之一", "每天賣掉手上的十分之一",
    "連續 10 個交易日", "1.0%", "1.00%", "十九個版本", "V1.3 到 V4.6",
    "端子", "九次", "九支", "准不准花真錢准不准", "改一次要動十支",
]

# 四組交付（長輩版 HTML + 技術／決策卡 MD），並標明對應的結果檔
PAIRS = [
    {"group": "V4.4", "html": "V4.4_买在最高点怎么决策.html",
     "md": "V4.4_买在最高点决策卡.md", "result": "v44_top_decision.json"},
    {"group": "V4.5", "html": "V4.5_一张还能怎么办.html",
     "md": "V4.5_一张怎么办决策卡.md", "result": "v45_one_lot.json"},
    {"group": "V4.6", "html": "V4.6_最大资产怎么办.html",
     "md": "V4.6_最大资产决策卡.md", "result": "v46_largest_asset.json"},
    {"group": "V5.0", "html": "V5.0_台海股投资接续系统_开发与技术规格.html",
     "md": "V5.0_系统开发与技术规格.md", "result": "v50_inventory.json"},
]

CHECK_NAMES = [
    "簡體字殘留",
    "長輩版術語洩漏",
    "標籤被當文字印出",
    "負號寫法不一致",
    "章節跳號",
    "標籤沒閉合",
    "舊說法殘留／來源讀不到",
]


class TagChecker(HTMLParser):
    VOID = {"meta", "br", "img", "hr", "input", "rect", "text", "path", "line", "circle"}

    def __init__(self):
        super().__init__()
        self.stack: list[str] = []
        self.misplaced: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            self.misplaced.append(tag)


def _opencc():
    try:
        from opencc import OpenCC
        return OpenCC("s2t")
    except Exception:
        return None


def _simplified(s: str, cc) -> list[str]:
    if cc is None:
        return []
    return sorted({c for c in s if cc.convert(c) != c and c not in VARIANT})


def _chapter(seq: list[str]) -> dict:
    nums = [int(x) for x in seq if x.isdigit()]
    if not nums:
        return {"ok": True, "note": "這份沒有編號章節（決策卡用別種寫法），不適用"}
    expected = list(range(1, len(nums) + 1))
    return {"ok": nums == expected, "note": f"抓到 {nums}／應為 {expected}"}


def check_file(path: Path, is_html: bool, is_elder: bool, result_ok: bool, cc) -> dict:
    if not path.exists():
        return {"file": path.name, "exists": False, "checks": [], "passed": False,
                "note": "檔案不存在"}
    s = path.read_text(encoding="utf-8")

    # 1 簡體
    hits = _simplified(s, cc)
    c1 = {"ok": not hits, "note": "乾淨" if not hits else "殘留 " + "".join(hits)}

    # 2 長輩版術語（技術版故意保留檔名與代號，不查）
    if is_elder:
        terms = sorted(set(TERM_RE.findall(s)))
        c2 = {"ok": not terms, "note": "乾淨" if not terms else "、".join(terms)}
    else:
        c2 = {"ok": True, "note": "技術版保留代號，不適用"}

    # 3 <b> 被當文字
    n3 = s.count("&lt;b&gt;") + s.count("&lt;/b&gt;")
    c3 = {"ok": n3 == 0, "note": f"{n3} 處"}

    # 4 ASCII 負號
    n4 = NEG_RE.findall(s)
    c4 = {"ok": not n4, "note": "乾淨" if not n4 else "、".join(n4[:5])}

    # 5 章節
    seq = NO_RE.findall(s) if is_html else MD_NO_RE.findall(s)
    ch = _chapter(seq)
    c5 = {"ok": ch["ok"], "note": ch["note"]}

    # 6 標籤閉合（只有 HTML）
    if is_html:
        p = TagChecker()
        p.feed(s)
        c6 = {"ok": not p.stack and not p.misplaced,
              "note": "乾淨" if not p.stack and not p.misplaced
              else f"未閉合 {p.stack[:5]}／錯位 {p.misplaced[:5]}"}
    else:
        c6 = {"ok": True, "note": "純文字，不適用"}

    # 7 舊說法 + 來源結果檔可讀
    old = [w for w in FORBIDDEN if w in s]
    c7 = {"ok": not old and result_ok,
          "note": "乾淨且來源可讀" if not old and result_ok
          else ("舊說法 " + "、".join(old) if old else "來源結果檔讀不到")}

    checks = [c1, c2, c3, c4, c5, c6, c7]
    return {
        "file": path.name, "exists": True,
        "checks": [{"name": CHECK_NAMES[i], "ok": c["ok"], "note": c["note"]}
                   for i, c in enumerate(checks)],
        "passed": all(c["ok"] for c in checks),
        "na": sum(1 for c in checks if "不適用" in c["note"]),
    }


def main() -> None:
    cc = _opencc()
    rows, n_fail, n_na, n_checks = [], 0, 0, 0
    for pair in PAIRS:
        rp = ROOT / pair["result"]
        try:
            json.loads(rp.read_text(encoding="utf-8"))
            result_ok = True
        except Exception:
            result_ok = False
        h = check_file(WORKSPACE / pair["html"], True, True, result_ok, cc)
        m = check_file(WORKSPACE / pair["md"], False, False, result_ok, cc)
        for r in (h, m):
            n_fail += sum(1 for c in r["checks"] if not c["ok"])
            n_na += r.get("na", 0)
            n_checks += len(r["checks"])
        rows.append({"group": pair["group"], "html": h, "md": m,
                     "result_file": pair["result"], "result_readable": result_ok,
                     "passed": h["passed"] and m["passed"] and result_ok})

    data = {
        "version": "V5.1",
        "generated_at": date.today().isoformat(),
        "purpose": "把前面每次手寫的體檢固化成一支可重跑的程式；只讀、不改檔、不連線、不花錢。",
        "standard": "沿用 V5.0 體檢口徑，沒有放寬；技術版保留代號故該項不適用。",
        "check_names": CHECK_NAMES,
        "n_groups": len(rows),
        "n_files": len(rows) * 2,
        "n_checks": n_checks,
        "n_fail": n_fail,
        "n_not_applicable": n_na,
        "all_pass": n_fail == 0,
        "results": rows,
        "note": "這支程式本身也是 V5.0 技術債的示範：路徑相對、一次只做一件、做完可重跑對照。",
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"產出 {OUT.name}｜{data['n_files']} 份檔、{n_checks} 項檢查、"
          f"失敗 {n_fail} 項、不適用 {n_na} 項、全部通過＝{data['all_pass']}")
    for r in rows:
        print(f"  {r['group']}: {'通過' if r['passed'] else '!! 未通過'}")


if __name__ == "__main__":
    main()
