#!/usr/bin/env python3
"""东方财富盘口异动数据获取：全市场异动扫描、个股异动查询、板块异动概况"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

CHANGE_TYPE_MAP: Dict[str, str] = {
    "火箭发射": "8201",
    "快速反弹": "8202",
    "大笔买入": "8193",
    "封涨停板": "4",
    "打开跌停板": "32",
    "有大买盘": "64",
    "竞价上涨": "8207",
    "高开5日线": "8209",
    "向上缺口": "8211",
    "60日新高": "8213",
    "60日大幅上涨": "8215",
    "加速下跌": "8204",
    "高台跳水": "8203",
    "大笔卖出": "8194",
    "封跌停板": "8",
    "打开涨停板": "16",
    "有大卖盘": "128",
    "竞价下跌": "8208",
    "低开5日线": "8210",
    "向下缺口": "8212",
    "60日新低": "8214",
    "60日大幅下跌": "8216",
}

REVERSE_TYPE_MAP: Dict[str, str] = {v: k for k, v in CHANGE_TYPE_MAP.items()}

BUY_SIGNALS = {"火箭发射", "大笔买入", "封涨停板", "有大买盘", "快速反弹", "竞价上涨", "高开5日线", "向上缺口", "60日新高", "60日大幅上涨"}
SELL_SIGNALS = {"高台跳水", "大笔卖出", "封跌停板", "有大卖盘", "加速下跌", "竞价下跌", "低开5日线", "向下缺口", "60日新低", "60日大幅下跌"}
NEUTRAL_SIGNALS = {"打开涨停板", "打开跌停板"}

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

UT = "7eea3edcaed734bea9cbfc24409ed989"


def get_market_code(stock_code: str) -> int:
    prefix = stock_code[:3]
    if prefix in ("000", "001", "002", "003", "300", "301"):
        return 0
    if prefix in ("600", "601", "603", "605") or stock_code.startswith("688"):
        return 1
    if stock_code.startswith("8"):
        return 2
    return 1


def fetch_market_changes(change_type: str) -> pd.DataFrame:
    """全市场盘口异动扫描"""
    type_code = CHANGE_TYPE_MAP.get(change_type)
    if not type_code:
        print(f"error: 未知异动类型 '{change_type}'", file=sys.stderr)
        print(f"可用类型: {', '.join(CHANGE_TYPE_MAP.keys())}", file=sys.stderr)
        sys.exit(1)

    url = "https://push2ex.eastmoney.com/getAllStockChanges"
    params = {
        "type": type_code,
        "pageindex": "0",
        "pagesize": "5000",
        "ut": UT,
        "dpt": "wzchanges",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        raw_list = data.get("data", {}).get("allstock", [])
        if not raw_list:
            return pd.DataFrame()

        rows = []
        for item in raw_list:
            rows.append({
                "时间": str(item.get("tm", "")).zfill(6)[:2] + ":" + str(item.get("tm", "")).zfill(6)[2:4] + ":" + str(item.get("tm", "")).zfill(6)[4:6],
                "代码": item.get("c", ""),
                "名称": item.get("n", ""),
                "板块": REVERSE_TYPE_MAP.get(str(item.get("t", "")), str(item.get("t", ""))),
                "相关信息": item.get("i", ""),
            })
        df = pd.DataFrame(rows)
        df["异动类型"] = change_type
        df["买卖方向"] = "买入" if change_type in BUY_SIGNALS else ("卖出" if change_type in SELL_SIGNALS else "中性")
        return df
    except Exception as e:
        print(f"error: 获取全市场异动失败 - {e}", file=sys.stderr)
        return pd.DataFrame()


def fetch_stock_changes(stock_code: str, date: str) -> pd.DataFrame:
    """个股盘口异动明细"""
    market = get_market_code(stock_code)
    url = "https://push2ex.eastmoney.com/getStockChanges"
    params = {
        "cb": "jQuery",
        "ut": UT,
        "date": date,
        "dpt": "wzchanges",
        "code": stock_code,
        "market": market,
        "_": int(datetime.now().timestamp() * 1000),
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        match = re.search(r'\((\{.*\})\)', resp.text)
        if not match:
            print(f"error: 个股异动响应格式异常", file=sys.stderr)
            return pd.DataFrame()
        data = json.loads(match.group(1))
        if data.get("rc") != 0:
            print(f"error: 接口返回错误 {data.get('rc')}", file=sys.stderr)
            return pd.DataFrame()

        records = data.get("data", {}).get("data", [])
        stock_name = data.get("data", {}).get("n", "")
        if not records:
            return pd.DataFrame()

        rows = []
        market_names = {0: "深圳", 1: "上海", 2: "北交所"}
        for item in records:
            type_code = item.get("t", 0)
            type_name = REVERSE_TYPE_MAP.get(str(type_code), f"未知({type_code})")
            tm = str(item.get("tm", "")).zfill(6)
            time_str = f"{tm[:2]}:{tm[2:4]}:{tm[4:6]}"
            direction = "买入" if type_name in BUY_SIGNALS else ("卖出" if type_name in SELL_SIGNALS else "中性")
            rows.append({
                "时间": time_str,
                "代码": stock_code,
                "名称": stock_name,
                "市场": market_names.get(market, "未知"),
                "异动类型码": type_code,
                "异动类型": type_name,
                "买卖方向": direction,
                "强度分": SIGNAL_STRENGTH.get(type_name, 0),
                "价格": item.get("p", 0) / 1000 if item.get("p") else 0,
                "涨幅(%)": item.get("u", 0),
                "成交量(手)": item.get("v", 0),
                "异动详情": item.get("i", ""),
            })
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"error: 获取个股异动失败 - {e}", file=sys.stderr)
        return pd.DataFrame()


def fetch_board_changes() -> pd.DataFrame:
    """板块异动概况"""
    url = "https://push2ex.eastmoney.com/getAllBKChanges"
    params = {
        "ut": UT,
        "dpt": "wzchanges",
        "pageindex": "0",
        "pagesize": "5000",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        raw_list = data.get("data", {}).get("allbk", [])
        if not raw_list:
            return pd.DataFrame()

        rows = []
        for item in raw_list:
            ms = item.get("ms", {})
            direction_map = {0: "大笔买入", 1: "大笔卖出"}
            rows.append({
                "板块名称": item.get("bkname", ""),
                "涨跌幅": item.get("zdf", 0),
                "主力净流入": item.get("mfr", 0),
                "异动总次数": item.get("change_num", 0),
                "最频繁个股代码": ms.get("c", "") if ms else "",
                "最频繁个股名称": ms.get("n", "") if ms else "",
                "最频繁个股方向": direction_map.get(ms.get("m", 2), "未知") if ms else "",
            })
        df = pd.DataFrame(rows)
        for col in ["涨跌幅", "主力净流入", "异动总次数"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        print(f"error: 获取板块异动失败 - {e}", file=sys.stderr)
        return pd.DataFrame()


def format_changes(df: pd.DataFrame, title: str = "") -> str:
    if df.empty:
        return f"{title} 无数据"

    lines = [f"=== {title} ==="]
    cols = [c for c in df.columns if c != "异动类型"]
    display = df[cols] if "异动类型" in df.columns else df
    for _, row in display.head(50).iterrows():
        parts = [f"{k}:{v}" for k, v in row.items() if v is not None and str(v).strip()]
        lines.append("  " + " | ".join(parts))
    if len(df) > 50:
        lines.append(f"  ... 共 {len(df)} 条，仅显示前50条")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="盘口异动数据获取")
    parser.add_argument("--type", type=str, help="异动类型名称，如'大笔买入'")
    parser.add_argument("--type-code", type=str, help="异动类型代码，如8193")
    parser.add_argument("--stock", type=str, help="个股代码，如601318")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y%m%d"), help="日期 YYYYMMDD")
    parser.add_argument("--board", action="store_true", help="板块异动概况")
    parser.add_argument("--top", type=int, default=0, help="限制输出条数")
    parser.add_argument("--json", action="store_true", dest="output_json", help="JSON输出")
    parser.add_argument("--all-buy", action="store_true", help="扫描所有买入类异动")
    parser.add_argument("--all-sell", action="store_true", help="扫描所有卖出类异动")
    args = parser.parse_args()

    if args.type_code:
        args.type = REVERSE_TYPE_MAP.get(args.type_code)
        if not args.type:
            print(f"error: 未知异动类型代码 '{args.type_code}'")
            sys.exit(1)

    if args.board:
        df = fetch_board_changes()
        if args.output_json:
            print(df.head(args.top) if args.top > 0 else df.to_json(orient="records", force_ascii=False))
        else:
            print(format_changes(df, "板块异动概况"))
        return

    if args.stock:
        df = fetch_stock_changes(args.stock, args.date)
        if df.empty:
            print(f"股票 {args.stock} 在 {args.date} 无异动记录")
            return
        if args.top > 0:
            df = df.head(args.top)
        if args.output_json:
            print(df.to_json(orient="records", force_ascii=False))
        else:
            print(format_changes(df, f"个股盘口异动 {args.stock} {args.date}"))
        return

    if args.all_buy:
        results = []
        for t in sorted(BUY_SIGNALS):
            df = fetch_market_changes(t)
            if not df.empty:
                print(f"【{t}】{len(df)} 只股票", file=sys.stderr)
                results.append(df)
            if args.output_json:
                continue
        if args.output_json:
            combined = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
            print(combined.to_json(orient="records", force_ascii=False))
        return

    if args.all_sell:
        results = []
        for t in sorted(SELL_SIGNALS):
            df = fetch_market_changes(t)
            if not df.empty:
                print(f"【{t}】{len(df)} 只股票", file=sys.stderr)
                results.append(df)
        if args.output_json:
            combined = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
            print(combined.to_json(orient="records", force_ascii=False))
        return

    if args.type:
        df = fetch_market_changes(args.type)
        if df.empty:
            print(f"无 [{args.type}] 异动数据")
            return
        if args.top > 0:
            df = df.head(args.top)
        if args.output_json:
            print(df.to_json(orient="records", force_ascii=False))
        else:
            print(format_changes(df, f"全市场异动 [{args.type}]"))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
