# a-share-strategy-mainboard-multi-swing-defensive + a-share-paper-trading 组合使用

这份文档专门说明怎么让 AI 工具把：

- `a-share-strategy-mainboard-multi-swing-defensive`
- `a-share-paper-trading`

组合起来使用，形成一条从“扫描候选”到“给 `calm1` 模拟下单”的完整流程。

适用场景：

- 想让 AI 先跑主板趋势回踩策略
- 想让 AI 从候选里挑出更合适的标的
- 想直接把结果下到 `calm1` 模拟账户

## 组合流程

最常见的 AI 工作流是：

1. 用 `a-share-strategy-mainboard-multi-swing-defensive` 扫描股票池
2. 让 AI 从买入参考中筛一只更合适的票
3. 用 `a-share-paper-trading` 把这只票下到 `calm1`
4. 再用 `a-share-paper-trading` 跟踪订单、持仓和成交

这条链路里：

- 策略 skill 负责信号
- 模拟盘 skill 负责执行

## 安装

在 AI 工具里，至少要安装这两个 skill：

```bash
mkdir -p ~/.agents/skills
cp -R a-share-strategy-mainboard-multi-swing-defensive ~/.agents/skills/
cp -R a-share-paper-trading ~/.agents/skills/
```

如果你用的是 Cursor / Claude Code / OpenCode / openclaw / Qoder，只需要把路径替换成对应工具的 skills 目录。

## 让 AI 怎么做

你不需要把流程拆成很多步手动做，直接让 AI 顺着这个流程执行就行。

### 最短问法

- `先用 a-share-strategy-mainboard-multi-swing-defensive 扫描今天的买入候选，再从里面选一只最合适的，用 a-share-paper-trading 给 calm1 下模拟单`

### 更明确的问法

- `先用 a-share-strategy-mainboard-multi-swing-defensive 跑 daily_decisions，股票池 120，只看最终过滤后结果；然后从 from_previous_day_close 里选一只，用 a-share-paper-trading 给 calm1 下 100 股模拟买单`

- `用 a-share-strategy-mainboard-multi-swing-defensive 扫描今日候选；如果有 3 只以上，按 score 和形态选最强的一只，再用 a-share-paper-trading 给 calm1 下单`

- `先检查 calm1 是否存在，不存在就创建 calm1，初始资金 1000000；然后用 a-share-strategy-mainboard-multi-swing-defensive 扫描候选，再给 calm1 下模拟单`

## 推荐的 AI 对话模板

下面这句最适合直接复制给 AI：

```text
用 a-share-strategy-mainboard-multi-swing-defensive 先扫描今天的买入候选，股票池 120，只看最终过滤后的结果。
如果 calm1 账户不存在，就用 a-share-paper-trading 创建 calm1，初始资金 1000000。
然后从 from_previous_day_close 里选一只最合适的票，给出选择理由，再用 a-share-paper-trading 给 calm1 下 100 股模拟买单。
最后把账户状态、订单状态和这次下单依据一起告诉我。
```

## 一个完整案例

### 案例：扫描候选并给 `calm1` 下单

目标：

- 让 AI 自己完成扫描、选择、下单、汇报

可以这样问：

```text
先用 a-share-strategy-mainboard-multi-swing-defensive 扫描今天的买入参考。
如果 calm1 账户不存在，就创建 calm1，初始资金 1000000。
从 from_previous_day_close 里挑一只最适合做模拟的票，说明为什么选它，不选其他候选的原因是什么。
然后用 a-share-paper-trading 给 calm1 下 100 股模拟买单。
最后把这次扫描结果、选股理由、下单结果、calm1 当前账户状态一起汇总给我。
```

AI 正常会按这个顺序做：

1. 跑策略扫描
2. 看候选列表
3. 检查 `calm1` 是否存在
4. 必要时创建 `calm1`
5. 下模拟买单
6. 返回订单和账户状态

## 分步问法

如果你不想一步到位，也可以拆成三问。

### 第一步：只扫描

- `用 a-share-strategy-mainboard-multi-swing-defensive 扫描今天的候选，只看 from_previous_day_close`

### 第二步：只选股

- `从刚才的候选里选一只最适合做模拟交易的票，并说清楚理由`

### 第三步：只下单

- `用 a-share-paper-trading 给 calm1 下这只票的 100 股模拟买单，并返回订单状态`

## 适合加的约束

你可以在问题里继续加限制条件，让 AI 更稳一些：

- `如果 calm1 资金不足，就不要下单，先告诉我差多少`
- `如果今天没有 from_previous_day_close 候选，就不要勉强下单`
- `如果候选太多，只选 score 最高且形态更清晰的一只`
- `下单前先查看 calm1 当前持仓和未完成订单，避免重复下单`

## 更稳的版本

如果你担心 AI 直接下单太激进，可以这样问：

```text
先用 a-share-strategy-mainboard-multi-swing-defensive 扫描今天的买入参考。
从候选里选一只最适合的票，说明理由。
然后先检查 calm1 的账户资金、持仓和未完成订单。
如果条件允许，再用 a-share-paper-trading 下 100 股模拟买单。
如果条件不允许，就不要下单，直接告诉我原因。
```

## 输出里你应该看到什么

一轮完整结果里，AI 最好能给出这些内容：

- 扫描到了哪些候选
- 最终选了哪只票
- 为什么选它
- `calm1` 是否已存在
- 是否新建了 `calm1`
- 下单成功还是失败
- 当前订单状态
- 当前账户状态

## 什么时候适合用这个组合

适合：

- 盘前做候选扫描
- 盘后做次日模拟计划
- 想把策略信号直接接进模拟盘

不适合：

- 你只想看信号，不想下单
- 你只想做历史回测，不想做账户维度的模拟执行

## 一句话版本

如果你只想记一句话，就用这个：

```text
先用 a-share-strategy-mainboard-multi-swing-defensive 扫描候选，再从里面选一只最合适的票，用 a-share-paper-trading 给 calm1 下模拟单，并把理由、订单和账户状态一起汇总给我。
```
