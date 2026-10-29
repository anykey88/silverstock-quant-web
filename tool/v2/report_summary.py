#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SilverStock — 每日掃描的結果輸出工具

兩個用途，都給 GitHub Actions 用：
  python3 tool/v2/report_summary.py --format md      # 寫進 $GITHUB_STEP_SUMMARY
  python3 tool/v2/report_summary.py --format push    # 推到微信（PushPlus）

刻意做成獨立檔案而不是寫在 workflow 的 heredoc 裡：
YAML 的縮排規則和 Python 的縮排規則一起用，改一次錯一次，不如分開放。
"""

import argparse
import json
import os
import sys
import urllib.request

PICKS = "assets/data/daily_picks.json"


def load():
    try:
        with open(PICKS, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"讀不到 {PICKS}：{e}", file=sys.stderr)
        return None


def fmt_money(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    return f"{v:,.0f}" if v >= 100 else f"{v:.1f}"


def render_md(d):
    lines = []
    lines.append("### 每日掃描結果\n")
    lines.append(f"- 交易日：**{d.get('trade_date', '?')}**")
    lines.append(f"- 掃描 {d.get('universe', 0)} 檔，{d.get('analyzed', 0)} 檔通過門檻")
    lines.append(
        f"- 買進觀察 {len(d.get('buy', []))} 檔／減碼觀察 {len(d.get('trim', []))} 檔"
    )
    lines.append(f"- 未列入 {len(d.get('excluded', []))} 檔（原因見名單頁）\n")

    buys = d.get("buy", [])
    if buys:
        lines.append("| # | 代號 | 名稱 | 分數 | 估值合理區 | 現價 | 位置 |")
        lines.append("|---|---|---|---|---|---|---|")
        for i, p in enumerate(buys, 1):
            lo, hi, c = p.get("buyLow", 0), p.get("buyHigh", 0), p.get("close", 0)
            if c > hi:
                pos = f"高於上緣 {((c / hi - 1) * 100):.1f}%"
            elif c < lo:
                pos = f"低於下緣 {((1 - c / lo) * 100):.1f}%"
            else:
                pos = "**在區間內**"
            lines.append(
                f"| {i} | {p['id']} | {p['name']} | {p.get('buyScore', 0):.0f} | "
                f"{fmt_money(lo)}–{fmt_money(hi)} | {fmt_money(c)} | {pos} |"
            )
    else:
        lines.append("> 買進觀察：沒有標的同時通過四道門檻。")

    trims = d.get("trim", [])
    if trims:
        lines.append("\n**減碼觀察**\n")
        lines.append("| 代號 | 名稱 | 分數 | 減碼區間 | 現價 |")
        lines.append("|---|---|---|---|---|")
        for p in trims:
            lines.append(
                f"| {p['id']} | {p['name']} | {p.get('trimScore', 0):.0f} | "
                f"{fmt_money(p.get('trimLow', 0))}–{fmt_money(p.get('trimHigh', 0))} | "
                f"{fmt_money(p.get('close', 0))} |"
            )
    else:
        lines.append("\n> 減碼觀察：沒有標的達到警戒分數。")

    lines.append("\n<sub>量化條件篩選結果，非投資建議、非買賣推薦。</sub>")
    return "\n".join(lines)


def render_push(d):
    lines = [f"交易日 {d.get('trade_date', '?')}・掃描 {d.get('universe', 0)} 檔", ""]
    buys = d.get("buy", [])[:5]
    if buys:
        lines.append("【買進觀察】")
        for p in buys:
            lines.append(
                f"{p['name']} {p['id']}　{p.get('buyScore', 0):.0f}分　"
                f"合理區 {fmt_money(p.get('buyLow'))}–{fmt_money(p.get('buyHigh'))}　"
                f"現價 {fmt_money(p.get('close'))}"
            )
    trims = d.get("trim", [])[:3]
    if trims:
        lines.append("")
        lines.append("【減碼觀察】")
        for p in trims:
            lines.append(
                f"{p['name']} {p['id']}　{p.get('trimScore', 0):.0f}分　"
                f"減碼區 {fmt_money(p.get('trimLow'))}–{fmt_money(p.get('trimHigh'))}"
            )
    if not buys and not trims:
        lines.append("今天沒有標的通過門檻——這本身也是結論。")
    lines.append("")
    lines.append("量化條件篩選，非投資建議。")
    return "<br>".join(lines)


def push_wechat(d, token):
    body = {
        "token": token,
        "title": f"SilverStock 每日精選 {d.get('trade_date', '')}",
        "content": render_push(d),
        "template": "html",
    }
    req = urllib.request.Request(
        "https://www.pushplus.plus/send",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        print(r.read().decode("utf-8")[:400])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["md", "push", "text"], default="md")
    args = ap.parse_args()

    d = load()
    if d is None:
        print("沒有可用的名單檔")
        return

    if args.format == "md":
        print(render_md(d))
    elif args.format == "text":
        print(render_md(d))
    else:
        token = os.environ.get("PUSHPLUS_TOKEN", "").strip()
        if not token:
            print("未設定 PUSHPLUS_TOKEN，跳過推送")
            return
        push_wechat(d, token)


if __name__ == "__main__":
    main()
