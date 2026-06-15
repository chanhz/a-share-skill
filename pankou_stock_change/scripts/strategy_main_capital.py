#!/usr/bin/env python3
"""主力资金跟随策略：基于盘口异动强度生成买入/卖出/持仓信号"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

DATA_DIR = os.environ.get(
    "PANKOU_SKILL_DIR",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)
FETCH_SCRIPT = os.path.join(DATA_DIR, "scripts", "fetch_pankou_changes.py")
ANALYZE_SCRIPT = os.path.join(DATA_DIR, "scripts", "analyze_stock_strength.py")

BUY_SIGNALS = {"火箭发射", "大笔买入", "封涨停板", "有大买盘", "快速反弹", "竞价上涨", "高开5日线", "向上缺口", "60日新高", "60日大幅上涨"}
SELL_SIGNALS = {"高台跳水", "大笔卖出", "封跌停板", "有大卖盘", "加速下跌", "竞价下跌", "低开5日线", "向下缺口", "60日新低", "60日大幅下跌"}

SIGNAL_STRENGTH: Dict[str, int] = {
    "火箭发射": 10, "高台跳水": 10,
    "封涨停板": 9, "封跌停板": 9,
    "大笔买入": 8, "大笔卖出": 8,
    "有大买盘": 7, "有大卖盘": 7,
    "快速反弹": 6, "加速下跌": 6,
    "60日新高": 6, "60日新低": 6,
    "60日大幅上涨": 5, "60日大幅下跌": 5,
    "竞价上涨": 5, "竞价下跌": 5,
    "高开5日线": 4, "低开5日线": 4,
    "向上缺口": 4, "向下缺口": 4,
    "打开涨停板": 2, "打开跌停板": 2,
}


def run_script(script_path: str, args: List[str]) -> Any:
    cmd = [sys.executable, script_path] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except Exception:
        return None


def buy_signal(stock: str, name: str, analysis: Dict[str, Any], changes: List[Dict[str, Any]]) -> Dict[str, Any]:
    net = analysis.get("净强度", 0)
    buy_count = analysis.get("买入信号", 0)
    sell_count = analysis.get("卖出信号", 0)
    recent_buy = [c for c in changes if c.get("异动类型") in BUY_SIGNALS and c.get("异动类型") not in ("竞价上涨", "竞价下跌")]
    recent_buy_30min = [c for c in recent_buy if c.get("时间", "") >= "10:30"] if any(c.get("时间", "") >= "10:30" for c in recent_buy) else recent_buy

    reasons = []
    score = 0

    if net >= 15:
        score += 3
        reasons.append(f"净强度{net}≥15，主力做多明确")
    elif net >= 10:
        score += 2
        reasons.append(f"净强度{net}≥10，偏强")
    elif net >= 5:
        score += 1
        reasons.append(f"净强度{net}≥5，略偏多")

    if len(recent_buy_30min) >= 3:
        score += 2
        reasons.append(f"近30分钟{len(recent_buy_30min)}次买入信号，主力持续介入")
    elif len(recent_buy_30min) >= 2:
        score += 1
        reasons.append(f"近30分钟{len(recent_buy_30min)}次买入信号")

    if sell_count == 0 and buy_count >= 3:
        score += 1
        reasons.append("无卖出信号，纯买入方向")

    if "火箭发射" in [c.get("异动类型") for c in changes]:
        score += 2
        reasons.append("出现火箭发射，主力急拉")

    if "封涨停板" in [c.get("异动类型") for c in changes]:
        score += 2
        reasons.append("出现封涨停板，主力封板坚决")

    is_buy = score >= 4
    level = "强烈" if score >= 6 else ("中等" if score >= 4 else "弱")

    return {
        "股票代码": stock,
        "股票名称": name,
        "信号": "买入" if is_buy else "观望",
        "信号强度": level,
        "评分": score,
        "净强度": net,
        "买入次数": buy_count,
        "卖出次数": sell_count,
        "核心理由": reasons,
        "时间": datetime.now().strftime("%H:%M:%S"),
    }


def sell_signal(stock: str, name: str, analysis: Dict[str, Any], changes: List[Dict[str, Any]]) -> Dict[str, Any]:
    net = analysis.get("净强度", 0)
    buy_count = analysis.get("买入信号", 0)
    sell_count = analysis.get("卖出信号", 0)

    reasons = []
    score = 0

    if net <= -15:
        score += 3
        reasons.append(f"净强度{net}≤-15，主力明确做空")
    elif net <= -10:
        score += 2
        reasons.append(f"净强度{net}≤-10，偏弱")
    elif net <= -5:
        score += 1
        reasons.append(f"净强度{net}≤-5，略偏空")

    change_types = [c.get("异动类型") for c in changes]

    if "高台跳水" in change_types:
        score += 3
        reasons.append("出现高台跳水，主力砸盘出货")

    if "大笔卖出" in change_types:
        score += 2
        reasons.append("出现大笔卖出")

    if "封跌停板" in change_types:
        score += 3
        reasons.append("出现封跌停板，主力坚决离场")

    consecutive_sells = 0
    for c in changes:
        if c.get("异动类型") in SELL_SIGNALS:
            consecutive_sells += 1
        else:
            consecutive_sells = 0
        if consecutive_sells >= 3:
            score += 2
            reasons.append("连续3笔卖出信号，资金持续出逃")
            break

    if buy_count == 0 and sell_count >= 3:
        score += 1
        reasons.append("无买入信号，纯卖出方向")

    is_sell = score >= 4
    level = "强烈" if score >= 6 else ("中等" if score >= 4 else "弱")

    return {
        "股票代码": stock,
        "股票名称": name,
        "信号": "卖出" if is_sell else "持有",
        "信号强度": level,
        "评分": score,
        "净强度": net,
        "买入次数": buy_count,
        "卖出次数": sell_count,
        "核心理由": reasons,
        "时间": datetime.now().strftime("%H:%M:%S"),
    }


def format_portfolio_signal(signals: List[Dict[str, Any]]) -> str:
    lines = [f"=== 主力资金跟随信号 - {datetime.now().strftime('%Y-%m-%d %H:%M')} ==="]
    for s in signals:
        sig = s["信号"]
        tag = "🟢" if sig == "买入" else ("🔴" if sig == "卖出" else "⚪")
        lines.append(f"\n{tag} {s['股票代码']} {s['股票名称']}")
        lines.append(f"  信号: {sig}({s['信号强度']})  评分: {s['评分']}  净强度: {s['净强度']}")
        lines.append(f"  买入:{s['买入次数']}次  卖出:{s['卖出次数']}次")
        for r in s["核心理由"]:
            lines.append(f"    - {r}")
    lines.append("")
    return "\n".join(lines)


def format_scan_result(signals: List[Dict[str, Any]], signal_type: str) -> str:
    lines = [f"=== 全市场{signal_type}候选 - {datetime.now().strftime('%Y-%m-%d %H:%M')} ==="]
    for s in signals:
        lines.append(f"  {s['股票代码']} {s['股票名称']:　<8s}  评分:{s['评分']}  净强度:{s['净强度']}  {s['信号强度']}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="主力资金跟随策略")
    parser.add_argument("--portfolio", type=str, help="持仓股票代码，逗号分隔")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y%m%d"), help="日期 YYYYMMDD")
    parser.add_argument("--scan-buy", action="store_true", help="全市场扫描买入候选")
    parser.add_argument("--scan-sell", action="store_true", help="全市场扫描卖出候选")
    parser.add_argument("--min-score", type=int, default=15, help="最低强度分(默认15)")
    parser.add_argument("--json", action="store_true", dest="output_json", help="JSON输出")
    args = parser.parse_args()

    if args.scan_buy:
        results = []
        for t in sorted(BUY_SIGNALS):
            data = run_script(FETCH_SCRIPT, ["--type", t, "--json"])
            if not data:
                continue
            for item in data:
                code = item.get("代码")
                if not code:
                    continue
                changes = run_script(FETCH_SCRIPT, ["--stock", code, "--date", args.date, "--json"])
                if not changes:
                    continue
                analysis = run_script(ANALYZE_SCRIPT, ["--stock", code, "--date", args.date, "--json"])
                if not analysis:
                    continue
                sig = buy_signal(code, item.get("名称", ""), analysis, changes)
                if sig["评分"] >= args.min_score:
                    results.append(sig)

        results.sort(key=lambda x: x["评分"], reverse=True)
        if args.output_json:
            print(json.dumps(results, ensure_ascii=False, default=str))
        else:
            print(format_scan_result(results, "买入"))
        return

    if args.scan_sell:
        results = []
        for t in sorted(SELL_SIGNALS):
            data = run_script(FETCH_SCRIPT, ["--type", t, "--json"])
            if not data:
                continue
            for item in data:
                code = item.get("代码")
                if not code:
                    continue
                changes = run_script(FETCH_SCRIPT, ["--stock", code, "--date", args.date, "--json"])
                if not changes:
                    continue
                analysis = run_script(ANALYZE_SCRIPT, ["--stock", code, "--date", args.date, "--json"])
                if not analysis:
                    continue
                sig = sell_signal(code, item.get("名称", ""), analysis, changes)
                if sig["评分"] >= args.min_score:
                    results.append(sig)

        results.sort(key=lambda x: x["评分"], reverse=True)
        if args.output_json:
            print(json.dumps(results, ensure_ascii=False, default=str))
        else:
            print(format_scan_result(results, "卖出"))
        return

    if args.portfolio:
        codes = [c.strip() for c in args.portfolio.split(",") if c.strip()]
        signals = []
        for code in codes:
            changes = run_script(FETCH_SCRIPT, ["--stock", code, "--date", args.date, "--json"])
            if not changes:
                continue
            analysis = run_script(ANALYZE_SCRIPT, ["--stock", code, "--date", args.date, "--json"])
            if not analysis:
                continue
            name = changes[0].get("名称", "") if changes else ""
            if analysis.get("净强度", 0) >= 0:
                sig = buy_signal(code, name, analysis, changes)
            else:
                sig = sell_signal(code, name, analysis, changes)
            signals.append(sig)

        if args.output_json:
            print(json.dumps(signals, ensure_ascii=False, default=str))
        else:
            print(format_portfolio_signal(signals))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
