#!/usr/bin/env python3
"""持仓卖出信号实时监控：每3分钟检查一次，触发即报警"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Set

SKILL_DIR = os.environ.get(
    "PANKOU_SKILL_DIR",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)
FETCH_SCRIPT = os.path.join(SKILL_DIR, "scripts", "fetch_pankou_changes.py")
NOTIFY_SCRIPT = os.path.join(
    os.environ.get("NOTIFY_SKILL_DIR", os.path.expanduser("~/.opencode/skills/notification")),
    "scripts", "send_notification.py",
)
DEFAULT_WEBHOOK = os.environ.get("WX_WEBHOOK", "")

SELL_SIGNALS = {"高台跳水", "大笔卖出", "封跌停板", "有大卖盘", "加速下跌", "竞价下跌", "低开5日线", "向下缺口", "60日新低", "60日大幅下跌"}
SIGNAL_STRENGTH: Dict[str, int] = {
    "火箭发射": 10, "高台跳水": 10, "封涨停板": 9, "封跌停板": 9,
    "大笔买入": 8, "大笔卖出": 8, "有大买盘": 7, "有大卖盘": 7,
    "快速反弹": 6, "加速下跌": 6, "60日新高": 6, "60日新低": 6,
    "60日大幅上涨": 5, "60日大幅下跌": 5, "竞价上涨": 5, "竞价下跌": 5,
    "高开5日线": 4, "低开5日线": 4, "向上缺口": 4, "向下缺口": 4,
    "打开涨停板": 2, "打开跌停板": 2,
}


def fetch_changes(code: str, date: str) -> List[Dict[str, Any]]:
    r = subprocess.run(
        [sys.executable, FETCH_SCRIPT, "--stock", code, "--date", date, "--json"],
        capture_output=True, text=True, timeout=15,
    )
    if r.returncode != 0:
        return []
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return []


def filter_new(changes: List[Dict[str, Any]], seen_times: Set[str]) -> List[Dict[str, Any]]:
    """过滤出未见过的新异动"""
    new = []
    for c in changes:
        key = f"{c.get('时间','')}_{c.get('异动类型','')}"
        if key not in seen_times:
            seen_times.add(key)
            new.append(c)
    return new


def filter_by_time(changes: List[Dict[str, Any]], cutoff: str) -> List[Dict[str, Any]]:
    """仅保留截止到指定时间的数据（含该时间）"""
    return [c for c in changes if c.get("时间", "") <= cutoff]


def check_sell(changes_since_open: List[Dict[str, Any]]) -> Dict[str, Any]:
    """检查卖出条件，返回报警信息"""
    sell_count = 0
    sell_score = 0
    buy_count = 0
    reasons = []
    consecutive_sells = 0
    max_consecutive = 0
    has_gaotai = False
    has_dabi_sell = False
    has_feng_die = False
    last_sell_time = ""
    last_sell_price = 0

    for c in changes_since_open:
        typ = c.get("异动类型", "")
        t = c.get("时间", "")
        p = c.get("价格", 0)
        s = SIGNAL_STRENGTH.get(typ, 0)

        if typ in SELL_SIGNALS:
            sell_count += 1
            sell_score += s
            consecutive_sells += 1
            max_consecutive = max(max_consecutive, consecutive_sells)
            last_sell_time = t
            last_sell_price = p

            if typ == "高台跳水":
                has_gaotai = True
                reasons.append(f"[{t}] 高台跳水! 价{p:.2f}")
            elif typ == "大笔卖出":
                has_dabi_sell = True
            elif typ == "封跌停板":
                has_feng_die = True
                reasons.append(f"[{t}] 封跌停板! 价{p:.2f}")
        else:
            consecutive_sells = 0
            if typ in {"有大买盘", "大笔买入", "火箭发射", "封涨停板"}:
                buy_count += 1

    score = 0
    if sell_score >= 15:
        score += 3
    elif sell_score >= 10:
        score += 2
    elif sell_score >= 5:
        score += 1

    if has_gaotai:
        score += 3
    if has_feng_die:
        score += 3
    if has_dabi_sell:
        score += 2
    if max_consecutive >= 3:
        score += 2
        if not reasons:
            reasons.append(f"连续{max_consecutive}笔卖出信号")
    if buy_count == 0 and sell_count >= 3:
        score += 1
        if not reasons:
            reasons.append("纯卖出无买入")

    is_alert = score >= 4
    level = "🔴 强烈卖出" if score >= 7 else ("🟠 卖出" if score >= 5 else ("🟡 关注" if score >= 4 else ""))

    return {
        "报警": is_alert,
        "级别": level,
        "评分": score,
        "卖出次数": sell_count,
        "卖出强度": sell_score,
        "连续卖出": max_consecutive,
        "理由": reasons,
        "最后卖出时间": last_sell_time,
        "最后卖出价": last_sell_price,
    }


def load_portfolio(path: str) -> Dict[str, str]:
    """从文件加载持仓，格式：每行 代码 名称"""
    holdings = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 1:
                code = parts[0]
                name = parts[1] if len(parts) >= 2 else code
                holdings[code] = name
    return holdings


def print_banner(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def send_alert(result: Dict[str, Any], code: str, name: str, webhook: str):
    """发送卖出报警到微信"""
    level = result.get("级别", "").strip()
    score = result["评分"]
    reasons = result.get("理由", [])
    sell_count = result["卖出次数"]
    last_price = result.get("最后卖出价", 0)
    last_time = result.get("最后卖出时间", "")

    msg_lines = [
        f"🚨 {level} {code} {name}",
        f"触发时间: {last_time}  评分: {score}  卖出: {sell_count}次",
    ]
    if last_price:
        msg_lines.append(f"价格: {last_price:.2f}")
    for r in reasons[:3]:
        msg_lines.append(f"  {r}")

    msg = "\n".join(msg_lines)
    print(f"\n  发送微信通知...", end="")
    r = subprocess.run(
        [sys.executable, NOTIFY_SCRIPT, "--msg", msg, "--webhook", webhook],
        capture_output=True, text=True, timeout=10,
    )
    if r.returncode == 0:
        print("OK")
    else:
        print(f"失败: {r.stderr.strip()}")


def run_simulation(holdings: Dict[str, str], date: str, webhook: str = "") -> str:
    """逐秒仿真回测：按时间顺序逐个异动重放，记录信号变化时刻"""
    lines = []
    lines.append(f"【逐秒仿真】{date}  按异动时间顺序重放")
    lines.append("=" * 80)

    for code, name in holdings.items():
        changes = fetch_changes(code, date)
        if not changes:
            lines.append(f"\n{code} {name}: 无数据")
            continue

        chrono = sorted(changes, key=lambda c: c.get("时间", ""))
        lines.append(f"\n{code} {name}  (当日异动 {len(chrono)} 笔)")
        lines.append("-" * 80)
        lines.append(f"{'时间':>10} {'异动类型':<12} {'方向':>4} {'价':>8} {'累计卖':>6} {'累计买入':>8} {'连卖':>4} {'评分':>4} {'信号':<12}")
        lines.append("-" * 80)

        cumulative = []
        prev_level = ""
        prev_score = 0
        triggered = False
        first_alert = None

        for c in chrono:
            cumulative.append(c)
            result = check_sell(cumulative)
            score = result["评分"]
            level = result.get("级别", "").strip()
            is_alert = result["报警"]

            t = c.get("时间", "")
            typ = c.get("异动类型", "")
            p = c.get("价格", 0)
            d = c.get("买卖方向", "")
            icon = "↓卖" if d == "卖出" else ("↑买" if d == "买入" else "· -")
            sell_cnt = result["卖出次数"]
            buy_cnt = sum(1 for x in cumulative if x.get("异动类型","") in {"有大买盘","大笔买入","火箭发射","封涨停板"})
            consec = result["连续卖出"]
            sig_display = level if level else ""

            show_trigger = False
            if is_alert and not triggered:
                triggered = True
                show_trigger = True
                first_alert = {
                    "时间": t, "价格": p, "评分": score,
                    "级别": level, "卖出次数": sell_cnt,
                    "理由": result["理由"],
                    "连续卖出": consec, "卖出强度": result["卖出强度"],
                }
                # 首次触发时立即发送微信通知
                if webhook:
                    send_alert(result, code, name, webhook)

            lines.append(
                f"{t:>10} {typ:<12} {icon:>4} {p:>8.2f} {sell_cnt:>6} {buy_cnt:>8} {consec:>4} {score:>4} {sig_display:<12}"
            )

            if show_trigger:
                for r in result["理由"]:
                    lines.append(f"  → {r}")
            elif score != prev_score and is_alert:
                # 评分变化时列出变化原因
                new_reasons = result["理由"]
                if new_reasons and score > prev_score:
                    for r in new_reasons:
                        lines.append(f"  → {r}")
                elif not is_alert and prev_level:
                    lines.append(f"  → 信号解除")

            prev_level = level
            prev_score = score

        lines.append("-" * 80)
        # 最终总结
        final = check_sell(chrono)
        lines.append(f"最终: 评分{final['评分']} {final.get('级别','').strip()} 卖出{final['卖出次数']}次 强度{final['卖出强度']} 连续卖出{final['连续卖出']}")
        if final["理由"]:
            for r in final["理由"]:
                lines.append(f"  {r}")
        if first_alert:
            lines.append(f"首次触发: {first_alert['时间']} @ {first_alert['价格']:.2f} 评分{first_alert['评分']}")
        if webhook and final["报警"] and not first_alert:
            send_alert(final, code, name, webhook)

    lines.append("\n")
    return "\n".join(lines)


def format_holdings_report(holdings: Dict[str, str], date: str, cutoff: str) -> str:
    """回测模式：指定时间点输出所有持仓信号"""
    lines = []
    lines.append(f"【持仓回测】{date} 截止 {cutoff}")
    lines.append(f"{'代码':>8} {'名称':<8} {'异动':>4} {'买入':>4} {'卖出':>4} {'卖出强度':>8} {'连续卖':>6} {'评分':>4} {'信号':>12} {'最后卖出价':>10}")
    lines.append("-" * 75)

    for code, name in holdings.items():
        changes = fetch_changes(code, date)
        if not changes:
            lines.append(f"{code:>8} {name:<8} 无数据")
            continue

        # 按回测时间截断
        if cutoff:
            changes = filter_by_time(changes, cutoff)
        if not changes:
            lines.append(f"{code:>8} {name:<8} 截断后无数据")
            continue

        result = check_sell(changes)
        sig = result.get("级别", "")
        lines.append(
            f"{code:>8} {name:<8} "
            f"{len(changes):>4} "
            f"{sum(1 for c in changes if c.get('异动类型','') in {'有大买盘','大笔买入','火箭发射','封涨停板'}):>4} "
            f"{result['卖出次数']:>4} "
            f"{result['卖出强度']:>8} "
            f"{result['连续卖出']:>6} "
            f"{result['评分']:>4} "
            f"{sig:>12} "
            f"{result['最后卖出价']:>10.2f}"
        )

        if result["理由"]:
            for r in result["理由"]:
                lines.append(f"  {'':>20}{r}")

    lines.append("")
    return "\n".join(lines)


def main_loop(holdings: Dict[str, str], interval: int, date: str, webhook: str = ""):
    """主循环：每interval秒检查一次"""
    seen: Dict[str, Set[str]] = {code: set() for code in holdings}
    
    print_banner(f"持仓监控启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"持仓: {', '.join(f'{c}({n})' for c,n in holdings.items())}")
    print(f"检查间隔: {interval}秒  日期: {date}")
    print(f"卖出报警阈值: 评分≥4")

    cycle = 0
    while True:
        cycle += 1
        now = datetime.now()
        print(f"\n[{now.strftime('%H:%M:%S')}] 第{cycle}轮检查 {'-'*30}")

        for code, name in holdings.items():
            changes = fetch_changes(code, date)
            if not changes:
                print(f"  {code} {name}: 无数据")
                continue
            
            new_items = filter_new(changes, seen[code])
            if not new_items:
                print(f"  {code} {name}: 无新异动")
                continue

            # 记录新异动
            for c in new_items:
                typ = c.get("异动类型", "")
                t = c.get("时间", "")
                p = c.get("价格", 0)
                d = c.get("买卖方向", "")
                icon = "↓" if d == "卖出" else ("↑" if d == "买入" else "·")
                print(f"  {code} {name} {icon} {t} {typ}  {p:.2f}")

            # 检查卖出
            result = check_sell(changes)
            if result["报警"]:
                print_banner(f"{result['级别']} {code} {name}")
                print(f"  评分: {result['评分']}")
                print(f"  卖出: {result['卖出次数']}次, 强度:{result['卖出强度']}, 连续卖出:{result['连续卖出']}")
                for r in result["理由"]:
                    print(f"    {r}")
                if result["最后卖出价"]:
                    print(f"  最后卖出价: {result['最后卖出价']:.2f} @ {result['最后卖出时间']}")
                if webhook:
                    send_alert(result, code, name, webhook)

        # 等待下一轮
        if cycle > 0:
            next_time = now.timestamp() + interval
            print(f"\n  下次检查: {datetime.fromtimestamp(next_time).strftime('%H:%M:%S')}")
            time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="持仓卖出信号实时监控/回测")
    parser.add_argument("--portfolio", type=str, required=True, help="持仓文件路径，每行：代码 名称")
    parser.add_argument("--interval", type=int, default=5, help="检查间隔秒数(默认5秒)")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y%m%d"), help="日期 YYYYMMDD")
    parser.add_argument("--backtest-time", type=str, help="回测时间点，如 10:00、14:30（指定后只跑一次，不循环）")
    parser.add_argument("--simulate", action="store_true", help="逐秒仿真：按时间顺序重放异动，追踪信号触发过程")
    parser.add_argument("--webhook", type=str, default=DEFAULT_WEBHOOK, help="企业微信 webhook URL (默认: $WX_WEBHOOK)")
    args = parser.parse_args()

    if not os.path.exists(args.portfolio):
        print(f"error: 持仓文件不存在 {args.portfolio}")
        sys.exit(1)

    holdings = load_portfolio(args.portfolio)
    if not holdings:
        print("error: 持仓文件为空")
        sys.exit(1)

    if args.simulate:
        print(run_simulation(holdings, args.date, args.webhook))
        sys.exit(0)

    if args.backtest_time:
        print(format_holdings_report(holdings, args.date, args.backtest_time))
        sys.exit(0)

    try:
        main_loop(holdings, args.interval, args.date, args.webhook)
    except KeyboardInterrupt:
        print("\n\n监控已停止")
