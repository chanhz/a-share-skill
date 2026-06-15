#!/usr/bin/env python3
"""个股盘口强度分析：基于盘口异动的买卖力量对比、强度评分、主力方向判断"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Tuple

DATA_DIR = os.environ.get(
    "PANKOU_SKILL_DIR",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)
FETCH_SCRIPT = os.path.join(DATA_DIR, "scripts", "fetch_pankou_changes.py")

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


def get_time_decay(time_str: str) -> float:
    if not time_str or len(time_str) < 5:
        return 1.0
    h = int(time_str[:2])
    m = int(time_str[3:5])
    minutes = h * 60 + m
    if minutes < 660:
        return 1.0
    if minutes < 810:
        return 0.8
    if minutes < 870:
        return 1.0
    return 1.2


def run_fetch(args: List[str]) -> List[Dict[str, Any]]:
    cmd = [sys.executable, FETCH_SCRIPT] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        if isinstance(data, dict):
            return [data]
        return data if isinstance(data, list) else []
    except Exception:
        return []


def calc_strength(changes: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not changes:
        return {
            "总异动次数": 0, "买入信号": 0, "卖出信号": 0, "中性信号": 0,
            "买入强度": 0, "卖出强度": 0, "净强度": 0,
            "判定": "无数据", "信号明细": [],
        }

    buy_count = 0
    sell_count = 0
    neutral_count = 0
    buy_score = 0.0
    sell_score = 0.0
    details = []

    for ch in changes:
        ch_type = ch.get("异动类型", "")
        time_str = ch.get("时间", "")
        decay = get_time_decay(time_str)
        strength = SIGNAL_STRENGTH.get(ch_type, 0)
        weighted = strength * decay

        if ch_type in BUY_SIGNALS:
            buy_count += 1
            buy_score += weighted
        elif ch_type in SELL_SIGNALS:
            sell_count += 1
            sell_score += weighted
        else:
            neutral_count += 1

        details.append({
            "时间": time_str,
            "异动类型": ch_type,
            "强度分": strength,
            "衰减系数": round(decay, 2),
            "加权分": round(weighted, 1),
        })

    net_score = round(buy_score - sell_score, 1)

    if net_score >= 20:
        verdict = "极强 - 主力明确做多"
    elif net_score >= 10:
        verdict = "偏强 - 主力试探做多"
    elif net_score >= -9:
        verdict = "中性 - 多空平衡"
    elif net_score >= -19:
        verdict = "偏弱 - 主力试探离场"
    else:
        verdict = "极弱 - 主力明确做空"

    return {
        "总异动次数": len(changes),
        "买入信号": buy_count,
        "卖出信号": sell_count,
        "中性信号": neutral_count,
        "买入强度": round(buy_score, 1),
        "卖出强度": round(sell_score, 1),
        "净强度": net_score,
        "判定": verdict,
        "信号明细": sorted(details, key=lambda x: x["时间"]),
    }


def format_strength_report(stock: str, date: str, result: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"【盘口强度分析 - {stock} - {date}】")
    lines.append(f"总异动: {result['总异动次数']}次 | 买入: {result['买入信号']}次({result['买入强度']}分) | 卖出: {result['卖出信号']}次({result['卖出强度']}分) | 中性: {result['中性信号']}次")
    lines.append(f"净强度: {result['净强度']} → {result['判定']}")
    lines.append("")

    if result["信号明细"]:
        lines.append("信号明细:")
        for d in result["信号明细"]:
            lines.append(f"  {d['时间']}  {d['异动类型']:　<8s}  强度:{d['强度分']}  加权:{d['加权分']}")
    lines.append("")
    return "\n".join(lines)


def scan_from_changes(change_type: str, min_strength: int, top_n: int) -> List[Dict[str, Any]]:
    from fetch_pankou_changes import fetch_market_changes

    df = fetch_market_changes(change_type)
    if df.empty:
        return []

    codes = df["代码"].unique().tolist()
    date = datetime.now().strftime("%Y%m%d")
    results = []

    for code in codes[:30]:
        changes = run_fetch(["--stock", code, "--date", date, "--json"])
        if not changes:
            continue
        result = calc_strength(changes)
        result["代码"] = code
        result["名称"] = changes[0].get("名称", "")
        results.append(result)

    results.sort(key=lambda x: x["净强度"], reverse=True)
    return [r for r in results if r["净强度"] >= min_strength][:top_n]


def main() -> None:
    parser = argparse.ArgumentParser(description="个股盘口强度分析")
    parser.add_argument("--stock", type=str, help="个股代码")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y%m%d"), help="日期 YYYYMMDD")
    parser.add_argument("--from-changes", type=str, help="从某类异动中筛选，如'大笔买入'")
    parser.add_argument("--min-strength", type=int, default=5, help="最低强度分(默认5)")
    parser.add_argument("--top", type=int, default=10, help="返回前N只(默认10)")
    parser.add_argument("--json", action="store_true", dest="output_json", help="JSON输出")
    args = parser.parse_args()

    if args.from_changes:
        results = scan_from_changes(args.from_changes, args.min_strength, args.top)
        if args.output_json:
            print(json.dumps(results, ensure_ascii=False, default=str))
        else:
            print(f"=== 从 [{args.from_changes}] 中筛选强度≥{args.min_strength} 的个股 ===")
            for r in results:
                print(f"  {r.get('代码','')} {r.get('名称','')}  净强度:{r['净强度']}  {r['判定']}")
        return

    if args.stock:
        changes = run_fetch(["--stock", args.stock, "--date", args.date, "--json"])
        result = calc_strength(changes)
        if args.output_json:
            print(json.dumps(result, ensure_ascii=False, default=str))
        else:
            print(format_strength_report(args.stock, args.date, result))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
