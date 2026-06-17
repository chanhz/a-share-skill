# a-share-skill

面向 AI 工具的 A 股数据分析、量化选股与模拟交易 skill 集合，适合 stock analysis、quant trading、paper trading、A-share strategy workflow：

- `a-share-data`：数据查询与分析
- `a-share-strategy-mainboard-multi-swing-defensive`：主板趋势回踩信号
- `a-share-strategy-allmarket-multi-swing-defensive`：全市场趋势回踩信号
- `a-share-paper-trading`：模拟盘执行与回测

```bash
a-share-skill/
  a-share-data/                                   # A股综合数据分析
  a-share-paper-trading/                          # 模拟盘交易与回测
  a-share-strategy-mainboard-multi-swing-defensive/  # 主板动态池趋势回踩：买卖决策信号
  macd-second-golden-cross/                       # MACD 底背离 + 零轴下二次金叉
  macd-trend-resonance-stock-picker/              # 均线 + MACD 趋势共振选股
  tuige-shortline-trading/                        # 退哥短线场景化交易决策
  pankou_stock_change/                            # 盘口异动与主力资金跟随策略
  README.md
```

说明：当前仓库已采用扁平结构，每个 skill 目录直接位于仓库根目录下；每个 skill 内部保持 `SKILL.md + scripts/ + references/` 的标准结构。

当前包含的 Skill：

- `a-share-data`：A 股综合数据分析 Skill  
  - **主要能力**（摘自 `SKILL.md`）：  
    - 实时行情快照（分钟K线聚合 + 市场状态）、今日分钟K线、批量实时行情  
    - 分钟 / 日 / 周 K 线（腾讯/新浪 API + 东方财富 akshare）  
    - 12 类技术指标（MA / EMA / MACD / KDJ / RSI / WR / BOLL / BIAS / CCI / ATR / DMI / TAQ）  
    - 盈利 / 成长 / 偿债 / 现金流 / 杜邦等六维财务报表  
    - 热点概念板块、北向资金、龙虎榜、涨停板 / 连板股、个股资金流向  
    - 沪深300 / 上证50 / 中证500 指数成分股、存款利率 / 货币供应量等宏观数据  
  - **典型使用场景**：  
    - 帮用户做单只股票的综合分析（行情 + 技术面 + 基本面）  
    - 盘中情绪与热点跟踪（指数、涨跌停统计、热点板块、北向资金、龙虎榜）  
    - 为量化 / 回测准备历史行情与财务因子数据

- `a-share-paper-trading`：A 股模拟交易与回测 Skill  
  - **主要能力**：  
    - 创建/重置模拟账户，管理资金与持仓  
    - 限价单/市价单下单、撤单、订单与成交查询  
    - 交易规则约束（100股整数倍、T+1、涨跌停校验、收盘过期）  
    - 账户估值与净值快照、简单策略回测  
  - **典型使用场景**：  
    - 在不动真资金的情况下做交易流程演练  
    - 验证撮合、冻结资金、可卖数量等账户逻辑  
    - 快速回测单票策略并观察收益曲线

- `a-share-strategy-mainboard-multi-swing-defensive`：主板流动性池 + 日线 `trend_pullback` 的**选股与买卖信号** Skill  
  - **主要能力**（见该目录 `SKILL.md`）：  
    - 从主板高成交额股票中取前 N 只构成股票池（`MarketDataProvider.get_mainboard_universe`）  
    - 输出「上一交易日收盘 entry」与「最新收盘 entry」两类买入参考，默认按 `score` 各取前 5 只（可调 `--max-buys`）  
    - 可选读取持仓文件，标注最新日线是否满足策略 `exit`（卖出参考）  
  - **典型使用场景**：  
    - 盘前或盘后生成当日可关注标的与减仓参考  
    - 与 `a-share-paper-trading` 配合时：先跑信号脚本，再按需向模拟盘下单（本 skill 不自动下单）  
  - **说明**：不包含混合回测；策略参数在 `scripts/strategy_lab/strategy_params.py`

- `macd-trend-resonance-stock-picker`：基于“均线定方向，MACD 定节奏”的趋势共振选股 Skill  
  - **主要能力**：  
    - 先按 60 日线方向与股价相对位置做趋势硬过滤  
    - 再按 MACD（0 轴位置、金叉/红柱、日线与 60 分钟共振）做节奏确认  
    - 输出 A/B/C/D 四档候选分级、触发条件、失效条件与风控提示  
    - 提供 100 分评分框架与 `EXECUTE/LIGHT/OBSERVE/AVOID` 动作映射  
  - **典型使用场景**：  
    - 盘前生成候选池并区分强弱优先级  
    - 盘中结合触发条件识别回踩再上或突破买点  
    - 盘后复盘顶背离减仓与趋势失效信号

- `macd-second-golden-cross`：基于“MACD 底背离 + 零轴下二次金叉”的修复型交易决策 Skill  
  - **主要能力**：  
    - 将“第一脚/第二脚/水下二次金叉”结构转成可执行的三档决策（观察 / 试错 / 放弃）  
    - 提供盘中检查单（10 条）与判定阈值（7 条以上可试错）  
    - 输出触发条件、入场方式、失效信号、止损位与仓位建议模板  
  - **典型使用场景**：  
    - 用户问“这个位置是不是二次金叉能不能做”时快速分档  
    - 低位修复与超跌反弹场景下，先结构验证再轻仓试错  
    - 避免情绪化抄底，统一到条件触发与纪律止损框架

- `tuige-shortline-trading`：基于退哥体系的 A 股短线**场景化交易决策** Skill  
  - **主要能力**：  
    - 以 `market-regime -> stock-selection -> 场景模块 -> exit/discipline` 形成统一决策流  
    - 场景模块覆盖趋势回踩、涨停后回调、连板接力、洗盘末端确认  
    - 输出统一口径：`trigger / invalidation / risk / position_grade`  
    - 提供独立术语口径文档，减少"高位、有效跌破、缩倍量"等词义漂移  
  - **典型使用场景**：  
    - 盘前先筛环境，再决定今天可做哪些场景  
    - 对单只个股快速归类当前结构，并输出触发与失效条件  
    - 盘中避免情绪化追单，回到统一退出与仓位纪律框架

你可以直接让 AI：

- 查个股实时行情、历史走势、技术指标、事件和行业信息
- 扫描主板或全市场候选，输出买入参考和持仓卖出参考
- 创建 `calm1` 模拟账户，查看账户详情、全部交易记录并下模拟单
- 结合大盘、候选、持仓和账户状态，判断今天该买、卖、持有还是不动


- `pankou_stock_change`：基于东方财富盘口异动数据的**主力资金跟随策略** Skill  
  - **主要能力**：  
    - 全市场 22 种盘口异动扫描（火箭发射/大笔买入/高台跳水/封涨停板等）  
    - 个股异动明细查询，按买卖方向与强度分（1~10）量化  
    - 个股盘口强度评分（买入强度 - 卖出强度，含时间衰减）  
    - 主力资金跟随策略：买入/卖出/持仓信号的生成  
    - 持仓卖出信号实时监控（每3分钟轮询，新异动触发即报警）  
    - **逐秒仿真回测**：按时间顺序重放全天异动，追踪信号触发与升级的完整过程  
  - **典型使用场景**：  
    - 全市场扫描"大笔买入"异动快速发现主力标的  
    - 对持仓股做盘口强度分析，判断主力是否转向  
    - 尾盘评估个股是否具备开仓条件（剔除涨停股后）  
    - 回测历史日期，验证信号在何时触发、是否领先于价格下跌  
  - **数据源**：东方财富盘口异动 API（独立于 a-share-data）

### pankou_stock_change 仿真回测用法

该 skill 的 `monitor_portfolio.py` 支持三种模式：

```bash
# 1. 实时监控：每3分钟检查持仓卖出信号
python3 pankou_stock_change/scripts/monitor_portfolio.py \
  --portfolio holdings.txt

# 2. 快照回测：指定时间点查看持仓信号
python3 pankou_stock_change/scripts/monitor_portfolio.py \
  --portfolio holdings.txt --date 20260611 --backtest-time 14:50

# 3. 逐秒仿真：按时间顺序重放全天异动，追踪信号完整演变
python3 pankou_stock_change/scripts/monitor_portfolio.py \
  --portfolio holdings.txt --date 20260611 --simulate
```

持仓文件格式 (`holdings.txt`)：
```
600519 贵州茅台
000858 五粮液
300750 宁德时代
```

仿真输出示例：
```
        时间 异动类型       方向   价    累计卖 累计买  连卖 评分 信号
  09:35:36 火箭发射        ↑买  44.98    0     1    0   0
  09:36:42 火箭发射        ↑买  45.88    0     2    0   0
  ...
  09:54:18 高台跳水        ↓卖  45.91    1     5    1   5 🟠 卖出      ← 首次触发
  → [09:54:18] 高台跳水! 价45.91
  09:59:18 火箭发射        ↑买  46.95    1     6    1   5 🟠 卖出
  09:59:18 有大卖盘        ↓卖  46.95    2     6    1   6 🟠 卖出      ← 评分升级
  ...
最终: 评分6 🟠 卖出 卖出3次 强度24
```

## 交流群

<img width="400" alt="39afc5617ddc27f26af912496edd3d34" src="https://github.com/user-attachments/assets/46d48fbf-6a9e-4d34-9966-0df52fe06a86" />

## 模拟仓一个半月 32 个点收益

<table>
  <tr>
    <td align="center" valign="top">
      <strong>4.16 初始化账户100w</strong><br/><br/>
      <img width="240" alt="7259c3d33aca6e81f948d90f89be5d15" src="https://github.com/user-attachments/assets/ef7d9b23-b9a3-4c49-afc2-3f81fd489058" />
    </td>
    <td align="center" valign="top">
      <strong>6.5 盘中 132w（持续更新中）</strong><br/>
      当前持仓：鹏鼎控股、华电辽能、太极实业、晶方科技<br/><br/>
      <img width="240" alt="510dc971161e47e91114bdf1a0cab2a7" src="https://github.com/user-attachments/assets/1a37359b-b7cf-4beb-b882-d44a452d3130" />
      <img width="240" alt="10a8b5bbfa7bbaba2ca2a9fc1b8aa98c" src="https://github.com/user-attachments/assets/cfb14495-7a46-4656-be20-d1e9779a9093" />
    </td>
  </tr>
</table>

## 四个核心 Skill

### `a-share-data`

适合问：

- 这只票现在怎么样
- 最近 60 天走势怎样
- 有没有事件驱动
- 沪深300、热点板块、北向资金现在怎么样

能做：

- 实时行情、历史 K 线、技术指标、事件、行业、指数与宏观数据

文档：

- [docs/A股数据安装使用文档.md](docs/A股数据安装使用文档.md)

### `a-share-strategy-mainboard-multi-swing-defensive`

适合问：

- 今天有哪些主板候选
- 我的持仓要不要卖
- 今天更适合买新票还是偏防守

能做：

- 主板池扫描、买入参考、卖出参考、批量现价快照

文档：

- [docs/主板趋势回踩策略安装使用文档.md](docs/主板趋势回踩策略安装使用文档.md)

### `a-share-strategy-allmarket-multi-swing-defensive`

适合问：

- 今天全市场有哪些趋势回踩候选
- 创业板和科创板要不要一起纳入扫描
- 同一套趋势回踩逻辑下，全市场和主板版差异是什么

能做：

- 全市场高流动性池扫描、买入参考、卖出参考、批量现价快照

文档：

- [docs/a-share-strategy-allmarket-multi-swing-defensive.md](docs/a-share-strategy-allmarket-multi-swing-defensive.md)

### `a-share-paper-trading`

适合问：

- 给 `calm1` 创建模拟账户
- 看 `calm1` 账户详情、持仓、订单、全部交易记录
- 给 `calm1` 下模拟买单或卖单
- 跑简单回测

能做：

- 账户管理、下单、撤单、持仓、订单、成交、账户估值、回测

文档：

- [docs/模拟仓安装使用文档.md](docs/模拟仓安装使用文档.md)

## 最短案例

- `查数据`：用 `a-share-data` 看 600519 最新行情、最近 60 日日线和 MACD。
- `跑主板策略`：用 `a-share-strategy-mainboard-multi-swing-defensive` 扫今天主板候选，只看最终过滤结果。
- `跑全市场策略`：用 `a-share-strategy-allmarket-multi-swing-defensive` 扫今天全市场候选，只看最终过滤结果。
- `管模拟盘`：用 `a-share-paper-trading` 创建 `calm1`，初始资金 `1000000`，再查看 `calm1` 账户详情和全部交易记录。

## 组合使用

- `数据分析`
  - `a-share-data`
  - 适合做单票分析、市场状态观察和批量拉数

- `策略判断`
  - `a-share-data + a-share-strategy-mainboard-multi-swing-defensive`
  - 适合做主板候选扫描、持仓卖出参考和环境判断

- `更宽股票池判断`
  - `a-share-data + a-share-strategy-allmarket-multi-swing-defensive`
  - 适合把创业板和科创板一起纳入趋势回踩扫描

- `模拟执行闭环`
  - `a-share-strategy-mainboard-multi-swing-defensive + a-share-paper-trading`
  - 适合让 AI 先分析，再决定是否给 `calm1` 买入、卖出、减仓或不交易

详细案例：

- [主板趋势回踩策略与模拟仓联动案例](docs/主板趋势回踩策略与模拟仓联动案例.md)

## 安装

以下示例包含四个核心 skill：`a-share-data`、`a-share-strategy-mainboard-multi-swing-defensive`、`a-share-strategy-allmarket-multi-swing-defensive`、`a-share-paper-trading`。

### Codex

```bash
clawhub install a-share-trading
clawhub install a-share-paper-trading
```

发布页：
- `https://clawhub.ai/shouldnotappearcalm/a-share-trading`
- `https://clawhub.ai/shouldnotappearcalm/a-share-paper-trading`

方式二：从本仓库复制到全局目录

```bash
mkdir -p ~/.openclaw/workspace/skills
cp -R a-share-data ~/.openclaw/workspace/skills/
cp -R a-share-paper-trading ~/.openclaw/workspace/skills/
cp -R a-share-strategy-mainboard-multi-swing-defensive ~/.openclaw/workspace/skills/
cp -R macd-second-golden-cross ~/.openclaw/workspace/skills/
cp -R macd-trend-resonance-stock-picker ~/.openclaw/workspace/skills/
cp -R tuige-shortline-trading ~/.openclaw/workspace/skills/
cp -R pankou_stock_change ~/.openclaw/workspace/skills/
mkdir -p ~/.agents/skills
cp -R a-share-data ~/.agents/skills/
cp -R a-share-strategy-mainboard-multi-swing-defensive ~/.agents/skills/
cp -R a-share-strategy-allmarket-multi-swing-defensive ~/.agents/skills/
cp -R a-share-paper-trading ~/.agents/skills/
```

### Cursor

```bash
mkdir -p ~/.cursor/skills
cp -R a-share-data ~/.cursor/skills/
cp -R a-share-strategy-mainboard-multi-swing-defensive ~/.cursor/skills/
cp -R macd-second-golden-cross ~/.cursor/skills/
cp -R macd-trend-resonance-stock-picker ~/.cursor/skills/
cp -R tuige-shortline-trading ~/.cursor/skills/
cp -R pankou_stock_change ~/.cursor/skills/
cp -R a-share-strategy-allmarket-multi-swing-defensive ~/.cursor/skills/
cp -R a-share-paper-trading ~/.cursor/skills/
```

### Claude Code

```bash
mkdir -p ~/.claude/skills
cp -R a-share-data ~/.claude/skills/
cp -R a-share-strategy-mainboard-multi-swing-defensive ~/.claude/skills/
cp -R macd-second-golden-cross ~/.claude/skills/
cp -R macd-trend-resonance-stock-picker ~/.claude/skills/
cp -R tuige-shortline-trading ~/.claude/skills/
cp -R pankou_stock_change ~/.claude/skills/
cp -R a-share-strategy-allmarket-multi-swing-defensive ~/.claude/skills/
cp -R a-share-paper-trading ~/.claude/skills/
```

### Qoder

```bash
mkdir -p ~/.opencode/skills
cp -R a-share-data ~/.opencode/skills/
cp -R a-share-paper-trading ~/.opencode/skills/
cp -R a-share-strategy-mainboard-multi-swing-defensive ~/.opencode/skills/
cp -R macd-second-golden-cross ~/.opencode/skills/
cp -R macd-trend-resonance-stock-picker ~/.opencode/skills/
cp -R tuige-shortline-trading ~/.opencode/skills/
cp -R pankou_stock_change ~/.opencode/skills/
mkdir -p ~/.qoder/skills
cp -R a-share-data ~/.qoder/skills/
cp -R a-share-strategy-mainboard-multi-swing-defensive ~/.qoder/skills/
cp -R a-share-strategy-allmarket-multi-swing-defensive ~/.qoder/skills/
cp -R a-share-paper-trading ~/.qoder/skills/
```

如果你用的是 OpenCode、openclaw 或其他支持 skills 的 AI 工具，只需要把路径替换成对应工具的 skills 目录。

## 文档导航
```bash
mkdir -p ~/.agents/skills
cp -R a-share-data ~/.agents/skills/
cp -R a-share-paper-trading ~/.agents/skills/
cp -R a-share-strategy-mainboard-multi-swing-defensive ~/.agents/skills/
cp -R macd-second-golden-cross ~/.agents/skills/
cp -R macd-trend-resonance-stock-picker ~/.agents/skills/
cp -R tuige-shortline-trading ~/.agents/skills/
cp -R pankou_stock_change ~/.agents/skills/
```
- [A股数据安装使用文档](docs/A股数据安装使用文档.md)
- [主板趋势回踩策略安装使用文档](docs/主板趋势回踩策略安装使用文档.md)
- [全市场趋势回踩策略说明](docs/a-share-strategy-allmarket-multi-swing-defensive.md)
- [模拟仓安装使用文档](docs/模拟仓安装使用文档.md)
- [主板趋势回踩策略与模拟仓联动案例](docs/主板趋势回踩策略与模拟仓联动案例.md)

## 其他 Skill

<<<<<<< HEAD
1. 确认目标目录下存在 `a-share-data/SKILL.md`、`a-share-paper-trading/SKILL.md`、`a-share-strategy-mainboard-multi-swing-defensive/SKILL.md`、`macd-second-golden-cross/SKILL.md`、`macd-trend-resonance-stock-picker/SKILL.md`、`tuige-shortline-trading/SKILL.md` 与 `pankou_stock_change/SKILL.md`
2. 新开会话后发一个明确请求，例如：
   - “用 a-share-data 拉取 600519 最近 20 个交易日的日线”
   - “用 a-share-paper-trading 创建模拟账户并下一个限价单”
   - “用 a-share-strategy-mainboard-multi-swing-defensive 跑 `daily_decisions.py` 看今日买入参考”
  - “用 macd-second-golden-cross 给我这只票做三档分级并给出止损位”
  - “用 macd-trend-resonance-stock-picker 生成今日 A/B/C/D 候选并给出触发与失效条件”
  - “用 tuige-shortline-trading 按场景给这只票做 trigger/invalidation/risk/position_grade 判断”
  - “用 pankou-stock-change 分析 603738 在 20260611 的盘口强度并给出买卖信号”
- `macd-second-golden-cross`
  - 适合判断“MACD 底背离 + 零轴下二次金叉”这类修复型机会

- `macd-trend-resonance-stock-picker`
  - 适合做“均线定方向，MACD 定节奏”的趋势共振选股

- `tuige-shortline-trading`
  - 适合按短线场景做 trigger / invalidation / risk / position_grade 判断

## 参考

- Cursor: [Agent Skills](https://www.trycursor.com/docs/context/skills)
- Claude Code: [Extend Claude with skills](https://code.claude.com/docs/en/skills.md)
- Codex: [Agent Skills](https://developers.openai.com/codex/skills)
- Qoder: [Skills](https://docs.qoder.com/extensions/skills)
