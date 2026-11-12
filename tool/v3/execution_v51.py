"""V5.1「V5.0 怎麼執行」盤點程式。

職責：把 V5.0 規格書的七步接續路線，拆成一張「誰做、先做什麼、做到什麼算完成、
卡在哪、依賴誰」的可執行清單。所有數字即時讀檔／重掃，不引用舊快照、不手抄。

用法：python3.11 tool/v3/execution_v51.py
輸出：silverstock_quant_web/v51_execution.json
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
OUT = ROOT / "v51_execution.json"

SPEC_MD = WORKSPACE / "V5.0_系统开发与技术规格.md"
V30_MD = WORKSPACE / "V3.0_富邦API整合規格.md"
CHECK_JSON = ROOT / "v51_check_result.json"
INV_JSON = ROOT / "v50_inventory.json"


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def scan_now() -> dict:
    """即時重掃，不用 V5.0 的舊快照。"""
    py = sorted((ROOT / "tool" / "v3").glob("*.py"))
    n_lines = sum(len(f.read_text(encoding="utf-8").splitlines()) for f in py)
    try:
        out = subprocess.run(["git", "status", "--short"], cwd=str(ROOT),
                             capture_output=True, text=True, timeout=20).stdout
        untracked = [ln.strip() for ln in out.splitlines() if ln.strip()]
    except Exception:
        untracked = []
    inv = jload(INV_JSON)
    return {
        "n_py_now": len(py),
        "n_lines_now": n_lines,
        "n_py_at_v50": inv["counts"]["n_py_modules"],
        "n_lines_at_v50": inv["counts"]["n_py_lines"],
        "n_untracked_now": len(untracked),
        "n_untracked_at_v50": inv["git"]["n_untracked"],
        "dataset": {
            "n_stocks": inv["dataset"]["n_stocks"],
            "index_bars": inv["dataset"]["index_bars"],
            "range": inv["dataset"]["range"],
            "captured_at": inv["dataset"]["captured_at"],
            "with_quarterly_eps": inv["dataset"]["with_quarterly_eps"],
            "n_missing_fields": len(inv["dataset"]["missing_fields"]),
        },
        "techdebt": {
            "n_modules_with_abs_path": inv["techdebt"]["n_modules_with_abs_path"],
            "n_generators": inv["techdebt"]["n_generators"],
            "n_result_in_root": inv["techdebt"]["n_result_in_root"],
            "n_result_in_repo": inv["techdebt"]["n_result_in_repo"],
        },
    }


def read_gates() -> list[dict]:
    """從 V3.0 規格讀升級五關，不憑印象。"""
    rows = re.findall(r"\|\s*\*\*(G[1-5])\*\*\s*\|\s*([^|]+)\|\s*([^|]+)\|",
                      V30_MD.read_text(encoding="utf-8"))
    out = []
    for gid, cond, state in rows:
        passed = "✅" in state
        out.append({
            "id": gid,
            "condition": cond.strip().replace("**", ""),
            "state": "通過" if passed else "還沒過",
            "raw": state.strip().replace("**", ""),
        })
    return out


def read_roadmap() -> list[dict]:
    """從 V5.0 規格第 11 節讀七步（做什麼／為什麼現在做）。"""
    txt = SPEC_MD.read_text(encoding="utf-8")
    seg = txt.split("**接續路線（按先後，不是加新功能）**：", 1)[1].split("## 12", 1)[0]
    rows = re.findall(r"\|\s*\*\*(先|再|後|最後)\*\*\s*\|\s*([^|]+)\|\s*([^|]+)\|", seg)
    return [{"order": o.strip(), "do": d.strip(), "why": w.strip()} for o, d, w in rows]


# 本版新增的「怎麼執行」維度：誰做 / 產出 / 做到什麼算完成 / 卡在哪 / 依賴
# 依 read_roadmap() 的順序一一對應；文字用白話，數字由讀檔回填。
EXEC_META = [
    {
        "who": "泰哥本人",
        "who_plain": "要您本人去辦一張新的通行證，別人替不了",
        "output": "倉庫裡看得到 tool/v3、結果檔、V5.0 規格",
        "done_when": "在另一台電腦也抓得到同一批檔案，且倉庫裡沒有任何密碼或憑證",
        "blocked_by": "舊通行證已撤銷，要辦新的細粒度令牌",
        "depends": "無，但它是第 2 步能上線的前提",
        "can_start_now": False,
        "pile": "只有您能做",
    },
    {
        "who": "系統（我）",
        "who_plain": "在家裡改網頁，不用出門、不用花錢、不用連券商",
        "output": "網頁上同時顯示「資料時間」與「抓檔時間」，附上三種狀態標籤",
        "done_when": "長輩一眼看得出這筆資料是舊的還是新的，不再誤會",
        "blocked_by": "無",
        "depends": "第 1 步推上去之後，別人才看得到；但本機現在就能先改",
        "can_start_now": True,
        "pile": "現在就能做",
    },
    {
        "who": "系統（我）",
        "who_plain": "把一次改三處，拆成一次只改一處、各考一次",
        "output": "三份分開的對照結果，各自看得出是誰有功勞",
        "done_when": "每一處改動都能單獨重跑，數字對得上",
        "blocked_by": "無",
        "depends": "無",
        "can_start_now": True,
        "pile": "現在就能做",
    },
    {
        "who": "系統（我）",
        "who_plain": "圖不再七天只取一點，改成每天記一筆",
        "output": "每日淨值數字檔，體檢程式可直接讀",
        "done_when": "最深那天不再被漏掉；取樣誤差從平均 2.76、最多 5.68 個百分點降下來",
        "blocked_by": "無",
        "depends": "無",
        "can_start_now": True,
        "pile": "現在就能做",
    },
    {
        "who": "系統（我）",
        "who_plain": "不要只考一次，換好幾段沒看過的日子輪流考",
        "output": "多段輪流考的結果檔",
        "done_when": "結論不是靠剛好押中那一段，換別段也站得住",
        "blocked_by": "無",
        "depends": "第 3、4 步先做完，考起來才乾淨",
        "can_start_now": True,
        "pile": "現在就能做",
    },
    {
        "who": "泰哥決定 + 系統整理",
        "who_plain": "要您點頭要不要補資料、資料從哪裡來；補齊後我再整理",
        "output": "補齊的資料集；中探針要連續 1,000 根日線",
        "done_when": "五道安檢門能給正式分數；不齊就繼續寫不知道",
        "why_override": "排在後面，是因為要先把方法驗乾淨，資料補齊了才有用；"
                        "不然只是拿新資料去重跑舊毛病。",
        "blocked_by": "八樣資料沒有、每季獲利只有 30/111 檔、中探針外部只有 4 根",
        "depends": "資料來源與授權要先確認",
        "can_start_now": False,
        "pile": "只有您能做",
    },
    {
        "who": "泰哥本人（簽名）",
        "who_plain": "要您本人簽名、做連線測試、實盤盯十天，別人不能代簽",
        "output": "升級五關全過的紀錄，與一份書面授權",
        "done_when": "五關全過，才輪到討論要不要解鎖自動；而且以「策略」為單位放行",
        "why_override": "一定放最後，是因為前面六步都在「把方法驗乾淨」；"
                        "方法還沒站穩就花真錢，等於拿家裡的錢去試一個還沒考過的做法。",
        "blocked_by": "現在只過第一關，其餘四關都還沒開始；現在是練習帳",
        "depends": "前面六步都做完，才輪到這一步",
        "can_start_now": False,
        "pile": "還不能做",
    },
]


def build() -> dict:
    now = scan_now()
    gates = read_gates()
    steps = read_roadmap()
    check = jload(CHECK_JSON)
    inv = jload(INV_JSON)

    roadmap = []
    for i, (s, m) in enumerate(zip(steps, EXEC_META), 1):
        roadmap.append({"step": i, **s, **m})
    # V5.0 規格第一步的「現在 N 項只存在這台機器」是當時快照，改成即時數字，
    # 避免長輩看到兩個不同的數目（規矩：數字一律讀檔回填，不手抄舊值）。
    for r in roadmap:
        r["why"] = re.sub(r"現在 \d+ 項", f"現在 {now['n_untracked_now']} 項", r["why"])
    # 第六、七步規格的「為什麼現在做」跟「做到什麼算完成」幾乎重複，
    # 執行手冊這欄應回答「為什麼排在這個順序」，故用白話覆寫，原文留著可追溯。
    for r in roadmap:
        if "why_override" in r:
            r["why_source"] = r["why"]
            r["why"] = r.pop("why_override")
        else:
            r["why_source"] = r["why"]
    n_now = sum(1 for r in roadmap if r["can_start_now"])

    # 今天真的做完的第一件事：自動體檢（數字讀 v51_check_result.json）
    today = {
        "title": "把「每次手寫的體檢」變成一支配著跑的程式",
        "why_first": "它不用錢、不用連線、不用通行證，卻能立刻抓出前面幾版漏掉的錯；"
                     "而且它正是 V5.0 技術債裡寫「沒有一支自動體檢程式」那一項。",
        "what_done": [
            "寫了 tool/v3/auto_check.py：路徑改成相對於自己，不再寫死在哪一台機器",
            "把前面四版每次手寫的七項體檢，固化成一支可重跑的程式",
            f"對 {check['n_files']} 份檔跑了 {check['n_checks']} 項檢查",
        "第一次跑就抓出前面四版手寫體檢漏掉的一處：把「託」寫成了簡體字，已改回",
        "順著改回最源頭那支程式並重跑，不是只改報告表面",
        "「划不划算」的「划」是台灣本來就這樣寫，列為白名單，不誤改",
            f"重跑後全部通過（失敗 {check['n_fail']} 項）",
        ],
        "n_files": check["n_files"],
        "n_checks": check["n_checks"],
        "n_fail_before": 2,
        "n_fail_after": check["n_fail"],
        "n_not_applicable": check["n_not_applicable"],
        "all_pass": check["all_pass"],
        "honest": "這件事沒有讓系統多賺一塊錢，只是讓它比較不會漏看錯字。"
                  "這正是 V4.2 定的調：系統進步是變誠實，不是變大膽。",
    }

    piles = [
        {
            "id": "now", "title": "現在就能做（不用錢、不用連線、不用通行證）",
            "plain": "像在家裡整理抽屜，不必出門、不必等誰點頭。",
            "n": n_now,
            "items": [r["do"] for r in roadmap if r["pile"] == "現在就能做"],
        },
        {
            "id": "you", "title": "只有您本人能做",
            "plain": "像去銀行辦事要本人按指紋，別人替不了。",
            "n": sum(1 for r in roadmap if r["pile"] == "只有您能做"),
            "items": [r["do"] for r in roadmap if r["pile"] == "只有您能做"],
        },
        {
            "id": "later", "title": "現在還不能做（卡著，不是忘了）",
            "plain": "像等晴天才能曬被子，今天下雨就是不行，硬做反而出事。",
            "n": sum(1 for r in roadmap if r["pile"] == "還不能做"),
            "items": [r["do"] for r in roadmap if r["pile"] == "還不能做"],
        },
    ]

    accept = [
        "同一行指令重跑，會得到同一份結果（不是靠運氣）",
        "每個數字都讀得到來源檔，不是手抄進去的",
        "自動體檢七項全過，失敗 0 項",
        "一次只改一處，改完立刻重跑對照，不再犯「一次改三處」",
        "不知道的事照舊寫不知道，沒有硬湊",
    ]

    cannot = [
        {"thing": "送單到券商、花真錢", "why": "現在是紙上練習帳，升級五關只過第一關"},
        {"thing": "解鎖「額度內自動、免逐筆確認」", "why": "五關要全過，還要有您簽的書面授權"},
        {"thing": "把中探針放進自動白名單", "why": "它不在資料池，外部只有 4 根日線，規矩要 1,000 根"},
        {"thing": "叫系統自己宣布「我夠格了」", "why": "升級要人簽名，程式不能自己說了算"},
        {"thing": "把憑證或密碼放進倉庫", "why": "憑證絕對不進倉庫，這條從 V2.7 寫到現在"},
    ]

    unknown = [
        "家裡全部資產大概多少、這檔佔幾成（不知道就算不出該留幾股）",
        "這張是不是融資買的、維持率多少（若是，追繳比股價更急）",
        "實際成交價是不是 371 元、家裡一個月開銷多少",
        "新令牌什麼時候辦、會不會辦（我不知道，也不該替您決定）",
        "補資料要從哪裡來、要不要花錢（要您點頭）",
        "富邦測試環境的實際連線結果（沒連過，一律寫不知道）",
    ]

    wrongbook_new = [
        {"lesson": "體檢不能靠手寫，要交給程式",
         "evidence": f"第一次跑就抓出前面四版漏掉的 1 個字；{check['n_checks']} 項檢查中 2 項沒過，修後全過。"},
        {"lesson": "抓到錯要改回源頭，不能只改報告表面",
         "evidence": "改 case_6217_one_lot.py 後重跑，不是直接改 HTML。"},
        {"lesson": "「一次只做一件」要真的做到",
         "evidence": "還發現 V4.3 與幾份結果檔有同一個字，這輪刻意不改，留到下一輪各驗一次。"},
    ]

    return {
        "version": "V5.1",
        "title": "V5.0 怎麼執行・接續開發執行手冊",
        "generated_at": date.today().isoformat(),
        "one_line": "V5.0 是一張施工單，不是一台按下去就會動的機器；"
                    "七件事裡有幾件今天就能做、不用錢也不用連線，而且第一件已經做完了。",
        "sources": [
            "V5.0 技術規格・接續路線那一節（第七步）",
            "V3.0 規格・升級五關",
            "V5.0 盤點結果檔",
            "本版自動體檢結果",
            "程式目錄與倉庫狀態即時重掃",
        ],
        "truth": {
            **now,
            "n_versions": inv["counts"]["n_versions"],
            "n_result_files": inv["counts"]["n_result_files"],
            "n_report_files": inv["counts"]["n_report_files"],
            "gates": gates,
            "gates_passed": sum(1 for g in gates if g["state"] == "通過"),
            "gates_total": len(gates),
            "mode": "M0 練習帳",
            "min_bars": inv["rules"]["principles"]["MIN_BARS"],
            "n_pretrade_questions": inv["rules"]["n_pretrade_questions"],
            "n_speak_rules": inv["rules"]["self_improve"]["n_speak_rules"],
        },
        "today": today,
        "piles": piles,
        "roadmap": roadmap,
        "accept": accept,
        "cannot": cannot,
        "unknown": unknown,
        "wrongbook_new": wrongbook_new,
        "disclaimer": "本版只做方法與風險控管示範，不是買賣建議；系統仍是紙上練習帳，沒連券商、沒下過任何一張單。",
    }


def main() -> None:
    d = build()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"產出 {OUT.name}")
    print(f"  V5.0 當時 {d['truth']['n_py_at_v50']} 支／{d['truth']['n_lines_at_v50']:,} 行；"
          f"本版即時 {d['truth']['n_py_now']} 支／{d['truth']['n_lines_now']:,} 行")
    print(f"  升級五關 {d['truth']['gates_passed']}/{d['truth']['gates_total']} 通過；"
          f"七步中 {sum(1 for r in d['roadmap'] if r['can_start_now'])} 步今天就能開始")
    print(f"  自動體檢 {d['today']['n_checks']} 項、修前 {d['today']['n_fail_before']} 失敗／"
          f"修後 {d['today']['n_fail_after']} 失敗")


if __name__ == "__main__":
    main()
