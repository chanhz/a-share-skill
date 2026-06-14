# a-share-strategy-mainboard-multi-swing-defensive AI 使用流程

这份文档说明如何把 `a-share-strategy-mainboard-multi-swing-defensive` 配到常见 AI 工具里使用，并给出从安装到实际提问的最短路径。

适用场景：

- 想在 `Codex / Cursor / Claude Code / OpenCode / openclaw` 里直接调用这个 skill
- 想让 AI 帮你跑主板趋势回踩策略，输出买入参考和卖出参考
- 想先看信号，不想接入自动下单

## 这个 skill 做什么

这个 skill 负责三件事：

- 从主板高流动性股票中构建当日股票池
- 用日线 `trend_pullback` 产出两组买入参考
- 对持仓文件里的代码检查是否触发策略 `exit`

它不负责：

- 自动下单
- 混合回测
- 收益曲线分析

如果要把信号接到模拟盘执行，可以再配合 `a-share-paper-trading` 一起用。

## 安装到 AI 工具

以下命令都在仓库根目录执行。

### Codex

```bash
mkdir -p ~/.agents/skills
cp -R a-share-strategy-mainboard-multi-swing-defensive ~/.agents/skills/
```

### Cursor

```bash
mkdir -p ~/.cursor/skills
cp -R a-share-strategy-mainboard-multi-swing-defensive ~/.cursor/skills/
```

### Claude Code

```bash
mkdir -p ~/.claude/skills
cp -R a-share-strategy-mainboard-multi-swing-defensive ~/.claude/skills/
```

### Qoder

```bash
mkdir -p ~/.qoder/skills
cp -R a-share-strategy-mainboard-multi-swing-defensive ~/.qoder/skills/
```

### OpenCode

```bash
mkdir -p ~/.opencode/skills
cp -R a-share-strategy-mainboard-multi-swing-defensive ~/.opencode/skills/
```

### openclaw

```bash
mkdir -p ~/.openclaw/workspace/skills
cp -R a-share-strategy-mainboard-multi-swing-defensive ~/.openclaw/workspace/skills/
```

## AI 工具里怎么问

建议在问题里直接点名 skill，避免模型走错工具链。

### 最常用问法

- `用 a-share-strategy-mainboard-multi-swing-defensive 跑今天的买入参考，股票池 120，只看最终过滤后结果`
- `用 a-share-strategy-mainboard-multi-swing-defensive 输出上一交易日收盘触发 entry 的候选，按 score 排序`
- `用 a-share-strategy-mainboard-multi-swing-defensive 检查我的持仓是否触发卖出信号`
- `用 a-share-strategy-mainboard-multi-swing-defensive 给我看 from_previous_day_close_raw 和 from_last_close_raw`

### 带参数的问法

- `用 a-share-strategy-mainboard-multi-swing-defensive 跑 daily_decisions，top_n=200，max_buys=10，json 输出`
- `用 a-share-strategy-mainboard-multi-swing-defensive 跑 daily_decisions，roundtrip_cost_bps=35，entry_consensus_min=0.75`
- `用 a-share-strategy-mainboard-multi-swing-defensive 跑实时快照，查看 600519、000001、601318 的最新价格和涨跌幅`

### 持仓检查问法

如果你有一个持仓文件，例如 `~/my_holdings.txt`，内容是一行一个股票代码：

```text
600519
000001
601318
```

可以这样问：

- `用 a-share-strategy-mainboard-multi-swing-defensive 按 ~/my_holdings.txt 检查卖出信号`
- `用 a-share-strategy-mainboard-multi-swing-defensive 读取 ~/my_holdings.txt，告诉我哪些持仓触发 exit`

## AI 背后实际会跑什么

买卖信号主入口：

```bash
python3 "$SKILL_DIR/scripts/daily_decisions.py" --json
```

常用参数：

- `--top-n`: 股票池大小，默认 `120`
- `--history-count`: 每只股票拉多少根日线，默认 `120`
- `--workers`: 并发拉取历史数据线程数
- `--max-buys`: 每组买入结果最多保留多少只
- `--holdings`: 持仓文件路径
- `--roundtrip-cost-bps`: 往返成本估计
- `--entry-consensus-min`: 参数邻域一致性阈值
- `--disable-robust-check`: 关闭鲁棒性过滤
- `--json`: 输出结构化 JSON

现价快照入口：

```bash
python3 "$SKILL_DIR/scripts/realtime_quotes.py" 600519 000001 601318 --json
```

## 数据源说明

这个 skill 的行情适配在 `scripts/paper_trading/market_data.py`。

当前主板池链路：

- 优先 `akshare`
- `akshare` 超时或失败后，退腾讯批量行情
- 腾讯失败后，再退新浪批量行情

当前日线历史链路：

- 优先新浪 K 线
- 再试腾讯日线
- 最后日线兜底 `akshare`

这意味着：

- 你可以在 AI 工具里正常问策略问题，不需要自己手动切换数据源
- 但如果上游行情源整体异常，结果数量可能会下降

## 与模拟盘联动

如果你只看信号，这个 skill 单独就够了。

如果你还想把信号接到模拟盘，可以再安装 `a-share-paper-trading`，典型流程是：

1. 用本 skill 生成买入参考或卖出参考
2. 让 AI 根据结果挑选标的和仓位
3. 再调用 `a-share-paper-trading` 下模拟单

这两者关系是：

- `a-share-strategy-mainboard-multi-swing-defensive`: 负责信号
- `a-share-paper-trading`: 负责执行

## 建议放在 GitHub 哪

建议做法：

- 把这份文档放仓库根目录 `docs/`
- 在根 `README.md` 的该 skill 说明下挂一个链接
- 在 `a-share-strategy-mainboard-multi-swing-defensive/SKILL.md` 的运行说明附近再挂一个链接

这样入口清晰，GitHub 和 AI 工具用户都能找到。
