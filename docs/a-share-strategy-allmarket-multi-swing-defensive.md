# a-share-strategy-allmarket-multi-swing-defensive

`a-share-strategy-allmarket-multi-swing-defensive` 是现有 `a-share-strategy-mainboard-multi-swing-defensive` 的全市场版本。

## 定位

- 沿用同一套日线 `trend_pullback` 信号逻辑
- 保留成本过滤与参数邻域鲁棒性过滤
- 输出口径与主板版一致，便于 Agent 与下游脚本复用
- 主要差异只在股票池

## 股票池范围

默认从高流动性 A 股中按成交额取前 `N` 只，覆盖：

- 沪市主板：`600/601/603/605`
- 深市主板：`000/001/002`
- 创业板：`300/301`
- 科创板：`688/689`

仍然过滤：

- `ST` / `*ST`
- 名称含“退”的退市整理标的

## 与主板版的区别

| 项目 | 主板版 | 全市场版 |
|------|--------|----------|
| Skill 目录 | `a-share-strategy-mainboard-multi-swing-defensive` | `a-share-strategy-allmarket-multi-swing-defensive` |
| 股票池 | 仅主板 | 主板 + 创业板 + 科创板 |
| 适用场景 | 偏稳健、限制在主板流动性池 | 想保留成长板与科创板机会，不做板块排除 |
| 脚本入口 | `get_mainboard_universe` | `get_all_market_universe` |

## 运行

```bash
SKILL_DIR="<本 skill 绝对路径>"
python3 "$SKILL_DIR/scripts/daily_decisions.py" --json
```

常见示例：

```bash
python3 "$SKILL_DIR/scripts/daily_decisions.py" --top-n 150 --json
python3 "$SKILL_DIR/scripts/daily_decisions.py" --top-n 150 --holdings "$HOME/my_holdings.txt"
python3 "$SKILL_DIR/scripts/realtime_quotes.py" 300750 688041 600519 --json
```

## 使用建议

- 如果你明确只做主板，继续用原主板版，避免把创业板和科创板的高波动样本混进来。
- 如果你希望趋势回踩候选覆盖成长板块与科创板，用这个全市场版。
- 两个 skill 的输出字段保持一致，便于并行比较不同股票池下的候选差异。
