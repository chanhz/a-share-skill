#!/usr/bin/env python3
"""多信号交叉验证的买入策略：替代单一"大笔买入"方案"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, time as dt_time
from typing import Any, Dict, List, Tuple

import pandas as pd
import requests


# ========== 信号定义 ==========

BUY_SIGNALS = {
    "火箭发射": 10,
    "封涨停板": 9,
    "大笔买入": 8,
    "有大买盘": 7,
    "快速反弹": 6,
    "60日新高": 6,
    "竞价上涨": 5,
    "高开5日线": 4,
    "向上缺口": 4,
}

SELL_SIGNALS = {
    "高台跳水": 10,
    "封跌停板": 9,
    "大笔卖出": 8,
    "有大卖盘": 7,
    "加速下跌": 6,
    "60日新低": 6,
    "竞价下跌": 5,
    "低开5日线": 4,
    "向下缺口": 4,
}

# 卖出信号严重等级
SELL_CRITICAL = {"高台跳水", "封跌停板"}  # 一票否决级
SELL_WARNING = {"大笔卖出", "有大卖盘"}     # 强警告
SELL_MINOR = {"加速下跌", "60日新低", "竞价下跌", "低开5日线", "向下缺口"}

UT = "7eea3edcaed734bea9cbfc24409ed989"


# ========== 数据获取 ==========

def extract_price(info_str: str) -> float:
    """从i字段中提取最可能的股票价格——i字段格式因异动类型而异"""
    try:
        parts = eval(info_str) if info_str else []
        if not isinstance(parts, (list, tuple)):
            return 0
        candidates = sorted([float(v) for v in parts if 0.1 < float(v) < 2000])
        if not candidates:
            return 0
        return candidates[len(candidates) // 2]
    except:
        return 0


def fetch_changes(change_type: str, date: str = "") -> pd.DataFrame:
    """获取指定异动类型的全市场数据"""
    CODE_MAP = {
        "火箭发射": "8201", "快速反弹": "8202", "大笔买入": "8193",
        "封涨停板": "4", "打开跌停板": "32", "有大买盘": "64",
        "竞价上涨": "8207", "高开5日线": "8209", "向上缺口": "8211",
        "60日新高": "8213", "60日大幅上涨": "8215",
        "加速下跌": "8204", "高台跳水": "8203", "大笔卖出": "8194",
        "封跌停板": "8", "打开涨停板": "16", "有大卖盘": "128",
        "竞价下跌": "8208", "低开5日线": "8210", "向下缺口": "8212",
        "60日新低": "8214", "60日大幅下跌": "8216",
    }
    type_code = CODE_MAP.get(change_type)
    if not type_code:
        return pd.DataFrame()

    try:
        params: dict = {"type": type_code, "pageindex": "0", "pagesize": "5000", "ut": UT, "dpt": "wzchanges"}
        if date:
            params["date"] = date
        resp = requests.get(
            "https://push2ex.eastmoney.com/getAllStockChanges",
            params=params,
            timeout=10,
        )
        data = resp.json()
        raw = data.get("data", {}).get("allstock", [])
        if not raw:
            return pd.DataFrame()
        rows = []
        for item in raw:
            tm = str(item.get("tm", "")).zfill(6)
            info = item.get("i", "")
            try:
                info_list = eval(info) if info else [0, 0, 0, 0]
            except:
                info_list = [0, 0, 0, 0]
            rows.append({
                "时间": f"{tm[:2]}:{tm[2:4]}:{tm[4:6]}",
                "代码": str(item.get("c", "")).zfill(6),
                "名称": item.get("n", ""),
                "异动类型": change_type,
                "强度分": BUY_SIGNALS.get(change_type, SELL_SIGNALS.get(change_type, 0)),
                "量": info_list[0] if len(info_list) > 0 else 0,
                "价格": extract_price(info),
                "涨幅": info_list[2] if len(info_list) > 2 else 0,
                "额": info_list[3] if len(info_list) > 3 else 0,
            })
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"  [{change_type}] 请求失败: {e}", file=sys.stderr)
        return pd.DataFrame()


def fetch_all_signals(buy_types: List[str], sell_types: List[str], date: str = "") -> pd.DataFrame:
    """并发获取所有买入+卖出信号"""
    all_dfs = []
    for typ in buy_types + sell_types:
        df = fetch_changes(typ, date=date)
        if not df.empty:
            df["买卖方向"] = "买入" if typ in BUY_SIGNALS else "卖出"
            all_dfs.append(df)
    if not all_dfs:
        return pd.DataFrame()
    return pd.concat(all_dfs, ignore_index=True)


# ========== 评分与过滤 ==========

def get_time_decay(t: str) -> float:
    """时间衰减：尾盘加分"""
    try:
        h, m, _ = t.split(":")
        minutes = int(h) * 60 + int(m)
    except:
        return 1.0
    if minutes < 660:
        return 1.0
    if minutes < 810:
        return 0.8
    if minutes < 870:
        return 1.0
    return 1.2


def calc_stock_scores(df: pd.DataFrame, window_minutes: int = 5) -> pd.DataFrame:
    """按股票聚合，计算滑动窗口内的多信号评分"""
    if df.empty:
        return pd.DataFrame()

    # 时间转分钟偏移
    def to_minutes(t):
        try:
            h, m, s = t.split(":")
            return int(h) * 60 + int(m) + int(s) / 60
        except:
            return 0

    df["分钟"] = df["时间"].apply(to_minutes)
    df["衰减分"] = df["强度分"] * df["时间"].apply(get_time_decay)

    results = []
    # 按股票分组
    for code, grp in df.groupby("代码"):
        grp = grp.sort_values("分钟")
        name = grp["名称"].iloc[0]
        mins = grp["分钟"].values
        scores = grp["衰减分"].values
        directions = grp["买卖方向"].values
        types = grp["异动类型"].values
        amounts = grp["额"].values
        prices = grp["价格"].values
        times = grp["时间"].values

        # 滑动窗口分析：以每条信号为锚点，看前 window_minutes 分钟内的状态
        for i in range(len(grp)):
            window_start = mins[i] - window_minutes
            window_end = mins[i]

            mask = (mins >= window_start) & (mins <= window_end)
            buy_score = sum(scores[j] for j in range(len(mask)) if mask[j] and directions[j] == "买入")
            sell_score = sum(scores[j] for j in range(len(mask)) if mask[j] and directions[j] == "卖出")
            buy_types_in_window = set(types[j] for j in range(len(mask)) if mask[j] and directions[j] == "买入")
            sell_types_in_window = set(types[j] for j in range(len(mask)) if mask[j] and directions[j] == "卖出")
            total_amount = sum(amounts[j] for j in range(len(mask)) if mask[j])

            # === 卖出针对性分析 ===

            # 严重卖出标志（高台跳水/封跌停板）
            has_critical_sell = bool(sell_types_in_window & SELL_CRITICAL)

            # 最近3笔信号中卖出的占比
            recent_start = max(0, i - 2)
            recent_dirs = directions[recent_start:i+1]
            recent_sell_ratio = sum(1 for d in recent_dirs if d == "卖出") / len(recent_dirs) if len(recent_dirs) > 0 else 0

            # 连续卖出计数（窗口内最大连续卖出笔数）
            max_consec_sell = 0
            cur_consec = 0
            for d in directions:
                if d == "卖出":
                    cur_consec += 1
                    max_consec_sell = max(max_consec_sell, cur_consec)
                else:
                    cur_consec = 0

            # 卖出多样性
            sell_diversity = len(sell_types_in_window)

            net_score = buy_score - sell_score

            # === 卖出扣分 ===
            sell_penalty = 0
            if recent_sell_ratio >= 0.67:
                sell_penalty += 10  # 最近3笔大多数是卖出
            if max_consec_sell >= 2:
                sell_penalty += 8   # 连续卖出
            if sell_diversity >= 3:
                sell_penalty += 8   # 多种卖出方式
            if has_critical_sell and sell_score > buy_score * 0.3:
                sell_penalty += 15  # 严重卖出且占比不低

            adjusted_net = net_score - sell_penalty

            # === 一票否决 ===
            veto = False
            if has_critical_sell and recent_sell_ratio >= 0.5:
                veto = True
            if max_consec_sell >= 3:
                veto = True

            results.append({
                "代码": code,
                "名称": name,
                "当前时间": times[i],
                "当前价格": prices[i],
                "窗口分钟": window_minutes,
                "买入强度": round(buy_score, 1),
                "卖出强度": round(sell_score, 1),
                "净强度": round(adjusted_net, 1),
                "卖出扣分": sell_penalty,
                "买入类型数": len(buy_types_in_window),
                "买入类型": ",".join(sorted(buy_types_in_window)),
                "卖出类型数": sell_diversity,
                "卖出类型": ",".join(sorted(sell_types_in_window)),
                "严重卖出": has_critical_sell,
                "最近卖出比": round(recent_sell_ratio, 2),
                "连续卖出": max_consec_sell,
                "一票否决": veto,
                "累计额": total_amount,
            })

    result_df = pd.DataFrame(results)
    if result_df.empty:
        return result_df

    # 每个股票只保留最新（最强）的一条记录
    # 按净强度降序，取每个代码净强度最高的窗口
    result_df = result_df.sort_values("净强度", ascending=False).drop_duplicates(subset="代码", keep="first")
    return result_df


def filter_candidates(df: pd.DataFrame, min_net: int = 20, min_types: int = 2,
                      exclude_st: bool = True) -> pd.DataFrame:
    """买入候选过滤"""
    if df.empty:
        return df

    # 一票否决
    no_veto = ~df["一票否决"]

    net_ok = df["净强度"] >= min_net

    # 买入多样性
    types_ok = df["买入类型数"] >= min_types

    # 买卖力量对比（用调整后的净强度而非原始买卖比）
    force_ok = df["净强度"] > df["卖出强度"] * 1.2

    # 卖出扣分不过度
    penalty_ok = df["卖出扣分"] < 20

    conditions = no_veto & net_ok & types_ok & force_ok & penalty_ok

    if exclude_st:
        conditions &= (~df["名称"].str.startswith("*")) & (~df["名称"].str.startswith("S"))

    df = df[conditions].copy()
    df["评级"] = df.apply(lambda r: grade_signal(r)[0], axis=1)
    GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "X": 4}
    df["_等级排序"] = df["评级"].map(GRADE_ORDER)
    df = df.sort_values(["_等级排序", "净强度"], ascending=[True, False])
    df = df.drop(columns=["_等级排序"])
    return df


# ========== 输出 ==========

GRADE_COLORS = {
    "A": "🟢",
    "B": "🔵",
    "C": "🟡",
    "D": "⚪",
}


def grade_signal(row) -> Tuple[str, str]:
    """对买入候选分档（结合卖出分析）"""
    net = row["净强度"]
    types = row["买入类型数"]
    penalty = row["卖出扣分"]
    veto = row["一票否决"]
    consec_sell = row["连续卖出"]
    recent_sell = row["最近卖出比"]

    if veto:
        return "X", f"一票否决（严重卖出+连续{consec_sell}笔）"

    base_grade = "D"
    reason = "信号不足，观望"

    if net >= 50 and types >= 3 and penalty < 5:
        base_grade = "A"
        reason = "多信号共振，卖出干扰极少"
    elif net >= 30 and types >= 2 and penalty < 10:
        base_grade = "B"
        reason = "买入信号协同，卖出可控"
    elif net >= 20 and types >= 2 and penalty < 15:
        base_grade = "C"
        reason = "有买入信号，注意卖出干扰"

    # 扣分较多时降级
    if base_grade == "A" and penalty >= 5:
        base_grade = "B"
        reason = "原A级，因卖出干扰降为B"
    if base_grade == "B" and penalty >= 10:
        base_grade = "C"
        reason = "原B级，因卖出干扰降为C"

    return base_grade, reason


def format_output(df: pd.DataFrame) -> str:
    if df.empty:
        return "无符合条件的买入候选"

    lines = []
    lines.append(f"{'='*80}")
    lines.append(f"  多信号买入策略候选  ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    lines.append(f"{'='*80}")
    lines.append("")
    lines.append(f"{'评分':>4} {'代码':>8} {'名称':<8} {'净强度':>7} {'扣分':>5} {'卖出强度':>8} {'卖类型':>6} {'严重卖':>6} {'连卖':>4} {'买入类型':<20} {'价':>8}")
    lines.append("-" * 95)

    for _, row in df.head(30).iterrows():
        grade = row["评级"]
        color = GRADE_COLORS.get(grade, "⚪")
        lines.append(
            f"{color}{grade:>3} "
            f"{row['代码']:>8} "
            f"{row['名称']:<8} "
            f"{row['净强度']:>7.1f} "
            f"{row['卖出扣分']:>5} "
            f"{row['卖出强度']:>8.1f} "
            f"{row['卖出类型数']:>6} "
            f"{'Y' if row['严重卖出'] else 'N':>6} "
            f"{row['连续卖出']:>4} "
            f"{row['买入类型']:<20} "
            f"{row['当前价格']:>8.2f}"
        )

    lines.append("")
    lines.append("评级说明：")
    lines.append("  🟢 A: 净强度≥50 + ≥3种 + 卖出扣分<5，多信号共振且卖出干扰极少")
    lines.append("  🔵 B: 净强度≥30 + ≥2种 + 卖出扣分<10，买入信号协同，卖出可控")
    lines.append("  🟡 C: 净强度≥20 + ≥2种 + 卖出扣分<15，需观察确认")
    lines.append("  ⚪ D: 信号不足，观望")
    lines.append("  ⛔ X: 一票否决（严重卖出/连续卖出）")
    lines.append("")
    lines.append("过滤条件：")
    lines.append("  - 净强度 ≥ 20（已扣除卖出干扰分）")
    lines.append("  - 买入类型 ≥ 2 种（避免单信号骗线）")
    lines.append('  - 无"一票否决"（严重卖出+近3笔占比≥50% / 连续卖出≥3笔）')
    lines.append("  - 卖出扣分 < 20")
    lines.append("  - 净强度 > 卖出强度 × 1.2")
    lines.append("")
    lines.append("卖出扣分规则：")
    lines.append("  - 近3笔中卖出≥2笔 → -10")
    lines.append("  - 连续卖出≥2笔 → -8")
    lines.append("  - ≥3种卖出类型 → -8")
    lines.append("  - 严重卖出（高台跳水/封跌停板）且卖占比不低 → -15")
    lines.append("")

    return "\n".join(lines)


# ========== 主流程 ==========

def main():
    parser = argparse.ArgumentParser(description="多信号交叉验证买入策略（注意：全市场数据不支持历史，只支持周末前一个交易日和当日）")
    parser.add_argument("--min-net", type=int, default=20, help="最低净强度(默认20)")
    parser.add_argument("--min-types", type=int, default=2, help="最少买入信号种类(默认2)")
    parser.add_argument("--window", type=int, default=5, help="分析窗口分钟数(默认5)")
    parser.add_argument("--date", type=str, default="", help="日期 YYYYMMDD（全市场数据不支持历史，只支持周末前一个交易日和当日，默认今天）")
    parser.add_argument("--cutoff", type=str, default="", help="截断时间 HH:MM（如 10:00，仅分析该时间点前的数据）")
    parser.add_argument("--json", action="store_true", dest="output_json", help="JSON输出")
    args = parser.parse_args()

    print(f"获取全市场异动信号{'(' + args.date + ')' if args.date else '...'}", file=sys.stderr)

    buy_types = list(BUY_SIGNALS.keys())
    sell_types = list(SELL_SIGNALS.keys())
    all_data = fetch_all_signals(buy_types, sell_types, date=args.date)

    if all_data.empty:
        print("无数据")
        return

    print(f"  共获取 {len(all_data)} 条异动记录", file=sys.stderr)

    # 时间截断
    if args.cutoff:
        before = len(all_data)
        all_data = all_data[all_data["时间"] <= args.cutoff]
        print(f"  截断至 {args.cutoff} 前: {len(all_data)}/{before} 条", file=sys.stderr)

    scored = calc_stock_scores(all_data, window_minutes=args.window)
    print(f"  评分后 {len(scored)} 只股票有有效信号", file=sys.stderr)

    candidates = filter_candidates(scored, min_net=args.min_net, min_types=args.min_types)

    if args.output_json:
        output = candidates.head(50).to_dict(orient="records")
        for item in output:
            item["评级理由"] = grade_signal(item)[1]
        print(json.dumps(output, ensure_ascii=False, default=str))
    else:
        print(format_output(candidates))


if __name__ == "__main__":
    main()
