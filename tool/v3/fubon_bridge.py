# -*- coding: utf-8 -*-
"""V3.0 富邦新一代 API（Fubon Neo API）橋接層 · 安全骨架

⚠️ 這是「唯一可以碰真實下單」的檔案，因此設計上層層設防：
  · 憑證／密碼只從環境變數讀，檔案內绝不寫死、也不接受貼在對話裡的值
  · 預設模式 = sandbox（富邦官方測試環境，零真錢），不是 live
  · 任何下單都必須攜帶「已通過 RiskGate」＋「該筆意圖」＋「授權結果」
  · M2 逐筆人工確認；M3 額度內自動（免逐筆確認，見 authorization.py）
  · SDK 未安裝時明確報錯並給安裝指引，不模擬成功、不假裝成交
  · 成交回報以 on_filled 為主、get_order_results 為對帳安全網
  · 所有送出與回報寫入 audit log（JSONL），可事後逐筆稽核

為什麼 Flutter Web 不能直接呼叫 SDK：
  fubon_neo 是 Python / C# / Node SDK，需要本機 PFX 憑證與長連線 WebSocket；
  瀏覽器（Dart/JS）既無法安全存放憑證，也受限於 CORS。
  所以架構是：泰哥本機常駐一個 bridge 服務 → 網頁只跟本機 HTTPS / WS 溝通。
  詳見 /workspace/V3.0_富邦API整合規格.md。

官方依據（2026-11-06 查證）：
  https://www.fbs.com.tw/TradeAPI/docs/trading/prepare/
  https://www.fbs.com.tw/TradeAPI/docs/trading/library/python/EnumMatrix/
  測試環境：wss://neoapitest.fbs.com.tw/TASP/XCPXWS
  測試包：https://www.fbs.com.tw/TradeAPI_SDK/sample_code/test_environment.zip
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from trade_plan_engine import TradeIntent, GateResult, FeeConfig, RiskConfig, TPE
from authorization import AuthResult, AuthLevel

SANDBOX_URL = "wss://neoapitest.fbs.com.tw/TASP/XCPXWS"
AUDIT_LOG = Path(__file__).with_name("audit_log.jsonl")


@dataclass
class BridgeConfig:
    mode: str = "sandbox"          # sandbox | paper | live
    personal_id: str = ""
    password: str = ""
    cert_path: str = ""
    cert_password: str = ""
    api_key: str = ""              # 選配（官方：API Key 為選擇性功能）
    sdk_version_ge_221: bool = True
    url: str = SANDBOX_URL

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        """憑證一律由環境變數提供，避免進對話、進 git、進 log。"""
        return cls(
            mode=os.getenv("FUBON_MODE", "sandbox"),
            personal_id=os.getenv("FUBON_PERSONAL_ID", ""),
            password=os.getenv("FUBON_PASSWORD", ""),
            cert_path=os.getenv("FUBON_CERT_PATH", ""),
            cert_password=os.getenv("FUBON_CERT_PASSWORD", ""),
            api_key=os.getenv("FUBON_API_KEY", ""),
            url=os.getenv("FUBON_WS_URL", SANDBOX_URL),
        )

    def validate(self) -> list[str]:
        errs: list[str] = []
        if self.mode not in ("sandbox", "paper", "live"):
            errs.append("FUBON_MODE 必須是 sandbox / paper / live")
        if not self.personal_id:
            errs.append("缺 FUBON_PERSONAL_ID")
        if not self.password:
            errs.append("缺 FUBON_PASSWORD")
        if not self.cert_path or not Path(self.cert_path).is_file():
            errs.append("FUBON_CERT_PATH 不是有效檔案（.pfx / .p12）")
        if not self.cert_password:
            errs.append("缺 FUBON_CERT_PASSWORD")
        if self.mode == "live" and not self.cert_path.startswith("/"):
            # 善意提醒：live 憑證應放在權限受控的本機路徑
            pass
        return errs


def _audit(event: str, payload: dict):
    rec = {"ts": datetime.now(TPE).isoformat(timespec="seconds"),
           "event": event, **payload}
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


class FubonBridge:
    """封裝 SDK 生命週期；SDK 缺席時降級為可稽核的 paper 模式。"""

    def __init__(self, cfg: BridgeConfig):
        self.cfg = cfg
        self.sdk = None
        self.accounts = None
        self.account = None
        self.realtime_ready = False

    # ---- 連線 -------------------------------------------------------------
    def connect(self) -> dict:
        problems = self.cfg.validate()
        if problems:
            _audit("connect_failed", {"errors": problems, "mode": self.cfg.mode})
            return {"ok": False, "errors": problems}

        try:
            from fubon_neo.sdk import FubonSDK
        except ImportError:
            _audit("sdk_missing", {"mode": self.cfg.mode})
            return {
                "ok": False,
                "errors": [
                    "找不到 fubon_neo SDK。官方 SDK 不在 PyPI，請至 "
                    "https://www.fbs.com.tw/TradeAPI/docs/download/download-sdk 下載 "
                    "對應 Python 版本的 .whl 後安裝（Python 3.8–3.13，勿用 3.14）。",
                ],
            }

        # v2.2.1+ 需 FubonSDK(30, 2, url=...)；舊版用 FubonSDK(url=...)
        if self.cfg.sdk_version_ge_221:
            self.sdk = FubonSDK(30, 2, url=self.cfg.url)
        else:
            self.sdk = FubonSDK(url=self.cfg.url)

        res = self.sdk.login(self.cfg.personal_id, self.cfg.password,
                             self.cfg.cert_path, self.cfg.cert_password)
        ok = bool(getattr(res, "is_success", True)) and bool(getattr(res, "data", None))
        if ok:
            self.accounts = res.data
            self.account = next((a for a in self.accounts
                                 if getattr(a, "account_type", "stock") == "stock"),
                                self.accounts[0])
        _audit("connect", {"ok": ok, "mode": self.cfg.mode,
                           "url": self.cfg.url, "account_count": len(self.accounts or [])})
        return {"ok": ok, "message": getattr(res, "message", None),
                "accounts": len(self.accounts or [])}

    def init_realtime(self) -> bool:
        if self.sdk is None:
            return False
        self.sdk.init_realtime()
        self.realtime_ready = True
        _audit("realtime_ready", {})
        return True

    def quote(self, symbol: str) -> dict:
        """行情：正式環境用 intraday.quote；測試環境須用 query_symbol_quote 取可下單參考價。"""
        if self.sdk is None or self.account is None:
            return {"ok": False, "error": "尚未連線"}
        try:
            if self.cfg.mode == "sandbox":
                q = self.sdk.stock.query_symbol_quote(self.account, symbol)
                return {"ok": True, "source": "query_symbol_quote",
                        "limitup_price": getattr(q, "limitup_price", None),
                        "limitdown_price": getattr(q, "limitdown_price", None),
                        "reference_price": getattr(q, "reference_price", None)}
            rest = self.sdk.marketdata.rest_client.stock
            q = rest.intraday.quote(symbol=symbol)
            d = getattr(q, "data", q)
            return {"ok": True, "source": "intraday.quote",
                    "data": str(d)[:500]}
        except Exception as e:
            _audit("quote_error", {"symbol": symbol, "error": str(e)})
            return {"ok": False, "error": str(e)}

    # ---- 下單（唯一出口）-------------------------------------------------
    def place_from_intent(self, intent: TradeIntent, gate: GateResult,
                          fee: FeeConfig, risk: RiskConfig,
                          human_confirmed: bool = False,
                          auth: Optional[AuthResult] = None) -> dict:
        """送出券商的最後一關：風控 + 授權 + 確認條件 + 非急停 + SDK 就緒。

        V3.2：M3 額度內自動模式下，授權層把 needs_human_confirm 設為 False，
        此時不需人逐筆按確認；其餘模式一律要人確認。
        未帶 auth 時採 fail-closed（不放行），避免繞過授權層。
        """
        needs_confirm = True if auth is None else auth.needs_human_confirm
        checks = {
            "gate_approved": gate.approved,
            "authorization_allowed": bool(auth and auth.allowed),
            "human_confirmation_satisfied": human_confirmed or not needs_confirm,
            "kill_switch_off": not risk.kill_switch,
            "mode_allowed": self.cfg.mode in ("sandbox", "live"),
            "sdk_ready": self.sdk is not None and self.account is not None,
        }
        failed = [k for k, v in checks.items() if not v]
        if failed:
            _audit("order_blocked", {"symbol": intent.symbol, "action": intent.action,
                                    "purpose": intent.purpose, "failed": failed,
                                    "auth_level": auth.effective_level.value if auth else None,
                                    "grant_id": auth.grant_id if auth else None,
                                    "reason": intent.reason})
            return {"ok": False, "sent": False, "blocked_by": failed}

        try:
            from fubon_neo.sdk import Order
            from fubon_neo.constant import (BSAction, MarketType, PriceType,
                                            TimeInForce, OrderType)
        except ImportError:
            return {"ok": False, "sent": False, "blocked_by": ["sdk_missing"]}

        mt = {
            "Common": MarketType.Common,
            "IntradayOdd": MarketType.IntradayOdd,
            "Odd": MarketType.Odd,
        }[intent.market_type]

        order = Order(
            buy_sell=BSAction.Buy if intent.action == "Buy" else BSAction.Sell,
            symbol=intent.symbol,
            quantity=intent.qty,                 # FubonNeo 一律「股數」：1 張 = 1000 股
            price=str(intent.price),             # 限價單需填
            market_type=mt,
            price_type=PriceType.Limit,
            time_in_force=TimeInForce.ROD,
            order_type=OrderType.Stock,
            user_def="AIplan",                  # ≤10 字元、不含中文，便於對帳辨識
        )
        _audit("order_submit", {"mode": self.cfg.mode, "symbol": intent.symbol,
                                "action": intent.action, "purpose": intent.purpose,
                                "qty": intent.qty, "price": intent.price,
                                "market_type": intent.market_type, "reason": intent.reason,
                                "grant_id": auth.grant_id,
                                "auth_level": auth.effective_level.value,
                                "auto_executed": auth.auto_executed,
                                "quota": auth.quota})

        if self.cfg.mode == "sandbox" and not risk.mode == "live":
            # 測試環境可真實送出（假帳號、假庫存）；若只想純紙上，請用 paper 模式
            pass
        res = self.sdk.stock.place_order(self.account, order)
        out = {"ok": bool(getattr(res, "is_success", False)), "sent": True,
               "message": getattr(res, "message", None),
               "order_result": str(getattr(res, "data", ""))[:600]}
        _audit("order_result", out)
        return out

    def reconcile(self) -> dict:
        """成交回報以 callback 為主，這裡做 30 秒週期的對帳安全網。"""
        if self.sdk is None or self.account is None:
            return {"ok": False}
        try:
            res = self.sdk.stock.get_order_results(self.account)
            data = getattr(res, "data", []) or []
            rows = [{"order_no": getattr(o, "order_no", ""),
                     "status": getattr(o, "status", None),       # 30 = 已刪單
                     "filled_qty": getattr(o, "filled_qty", 0),
                     "filled_money": getattr(o, "filled_money", 0)} for o in data]
            _audit("reconcile", {"rows": len(rows)})
            return {"ok": True, "rows": rows}
        except Exception as e:
            return {"ok": False, "error": str(e)}


def smoke_test() -> dict:
    """不連線的自檢：列出目前環境是否具備條件，與缺少什麼。"""
    cfg = BridgeConfig.from_env()
    return {
        "mode": cfg.mode,
        "url": cfg.url,
        "config_errors": cfg.validate(),
        "sdk_installed": _sdk_installed(),
        "python_ok": _python_ok(),
        "hint": "測試環境憑證請用官方 test_environment.zip；"
                "正式環境需先完成 API 聲明書簽署 + 連線測試 + 隔日開通。",
    }


def _sdk_installed() -> bool:
    try:
        import fubon_neo  # noqa: F401
        return True
    except ImportError:
        return False


def _python_ok() -> bool:
    import sys
    return (3, 8) <= sys.version_info[:2] <= (3, 13)


if __name__ == "__main__":
    print(json.dumps(smoke_test(), ensure_ascii=False, indent=2))
