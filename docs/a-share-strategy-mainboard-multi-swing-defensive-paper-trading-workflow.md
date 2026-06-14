# a-share-strategy-mainboard-multi-swing-defensive + a-share-paper-trading 组合使用

这份文档专门说明怎么让 AI 工具把：

- `a-share-strategy-mainboard-multi-swing-defensive`
- `a-share-paper-trading`

组合起来使用，形成一条从“扫描候选”到“结合 `calm1` 账户与持仓做买卖决策”的完整流程。

## 一句话版本

```text
先用 a-share-strategy-mainboard-multi-swing-defensive 扫描买入参考和卖出参考，再结合大盘情况和 calm1 当前账户、持仓、交易记录，判断今天该买入、卖出、持有还是不动；如果需要执行，就用 a-share-paper-trading 直接操作 calm1，并把理由、订单和账户状态一起汇总给我。
```

适用场景：

- 想让 AI 先跑主板趋势回踩策略
- 想让 AI 结合大盘情况决定今天是否适合买新票
- 想让 AI 同时检查 `calm1` 当前持仓，判断是否该卖出现有仓位
- 想让 AI 在需要时才给 `calm1` 模拟下单

## 组合流程

最常见的 AI 工作流是：

1. 用 `a-share-strategy-mainboard-multi-swing-defensive` 扫描股票池
2. 让 AI 结合大盘环境和候选强弱判断今天是否适合开新仓
3. 用 `a-share-paper-trading` 查看 `calm1` 的账户状态、当前持仓和交易记录
4. 让 AI 判断是买入新票、减仓旧票、卖出旧票，还是今天不交易
5. 如果需要执行，再用 `a-share-paper-trading` 对 `calm1` 下模拟单

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

- `先用 a-share-strategy-mainboard-multi-swing-defensive 分析今天是否适合买新票，再结合 calm1 当前账户和持仓情况，决定是买入、卖出还是不动`

### 更明确的问法

- `先用 a-share-strategy-mainboard-multi-swing-defensive 跑 daily_decisions，股票池 120，只看最终过滤后结果；然后结合大盘和 calm1 当前账户状态，决定今天是否给 calm1 开新仓`

- `用 a-share-strategy-mainboard-multi-swing-defensive 扫描今日候选；如果有 3 只以上，按 score、形态和大盘环境选最强的一只，再决定是否给 calm1 下单`

- `先检查 calm1 是否存在，不存在就创建 calm1，初始资金 1000000；然后看 calm1 当前持仓和账户状态，再用 a-share-strategy-mainboard-multi-swing-defensive 判断今天是加仓、开新仓、减仓还是空仓`

## 推荐的 AI 对话模板

下面这句最适合直接复制给 AI：

```text
先用 a-share-strategy-mainboard-multi-swing-defensive 扫描今天的买入参考和卖出参考，股票池 120，只看最终过滤后的结果。
再结合当前大盘环境，判断今天是否适合买新票。
然后用 a-share-paper-trading 查看 calm1 的账户详情、当前持仓、未完成订单和全部交易记录。
如果 calm1 账户不存在，就创建 calm1，初始资金 1000000。
最后综合候选、持仓、资金和大盘情况，判断今天对 calm1 是买入新票、卖出现有持仓、继续持有，还是不交易，并说明理由。
如果需要执行，就直接用 a-share-paper-trading 帮 calm1 下模拟单。
```

## 一个完整案例

### 案例：扫描候选并判断 `calm1` 今天该不该动

目标：

- 让 AI 自己完成扫描、判断、必要时下单、汇报

可以这样问：

```text
先用 a-share-strategy-mainboard-multi-swing-defensive 扫描今天的买入参考和卖出参考。
结合当前大盘情况，判断今天是否适合买新票，还是更适合减仓、卖出或者不交易。
然后用 a-share-paper-trading 查看 calm1 的账户详情、当前持仓、未完成订单和全部交易记录。
如果 calm1 账户不存在，就创建 calm1，初始资金 1000000。
如果适合买新票，就从候选里挑一只最合适做模拟的票，说明为什么选它，不选其他候选的原因是什么，再给 calm1 下模拟单。
如果更适合处理已有持仓，就告诉我 calm1 哪些持仓应该继续持有，哪些应该卖出，并在需要时直接执行模拟卖单。
最后把这次扫描结果、分析理由、执行结果和 calm1 当前账户状态一起汇总给我。
```

AI 正常会按这个顺序做：

1. 跑策略扫描
2. 看买入候选和卖出参考
3. 结合大盘情况判断今天更偏向进攻还是防守
4. 检查 `calm1` 是否存在
5. 查看 `calm1` 账户详情、持仓、订单和交易记录
6. 判断是买入、卖出、减仓、持有还是不动
7. 需要执行时再下模拟单
8. 返回账户和订单状态

## 分步问法

如果你不想一步到位，也可以拆成三问。

### 第一步：只扫描

- `用 a-share-strategy-mainboard-multi-swing-defensive 扫描今天的买入参考和卖出参考`

### 第二步：只分析动作

- `结合刚才的候选、大盘情况和 calm1 当前持仓，判断今天应该买入、卖出、持有还是不交易，并说清楚理由`

### 第三步：只执行

- `按照刚才的判断，用 a-share-paper-trading 给 calm1 执行对应的模拟买单或卖单，并返回订单状态`

## 适合加的约束

你可以在问题里继续加限制条件，让 AI 更稳一些：

- `如果 calm1 资金不足，就不要下单，先告诉我差多少`
- `如果今天没有 from_previous_day_close 候选，就不要勉强开新仓`
- `如果候选太多，只选 score 更高且形态更清晰的一只`
- `下单前先查看 calm1 当前持仓、未完成订单和全部交易记录，避免重复操作`
- `如果大盘环境偏弱，就优先检查 calm1 现有持仓是否该减仓或卖出`

## 更稳的版本

如果你担心 AI 直接下单太激进，可以这样问：

```text
先用 a-share-strategy-mainboard-multi-swing-defensive 扫描今天的买入参考和卖出参考。
结合当前大盘环境，判断今天对 calm1 更适合买入新票、卖出旧票、继续持有还是不交易。
然后先检查 calm1 的账户详情、持仓、未完成订单和全部交易记录。
只有在条件允许时，才用 a-share-paper-trading 执行对应的模拟买单或卖单。
如果条件不允许，就不要下单，直接告诉我原因。
```

## 输出里你应该看到什么

一轮完整结果里，AI 最好能给出这些内容：

- 扫描到了哪些买入候选
- 扫描到了哪些卖出参考
- 大盘环境偏强还是偏弱
- 最终建议是买入、卖出、持有还是不动
- 为什么这样判断
- `calm1` 是否已存在
- 是否新建了 `calm1`
- `calm1` 当前账户详情
- `calm1` 当前持仓情况
- `calm1` 的订单状态和交易记录
- 如果执行了，下单成功还是失败

## 什么时候适合用这个组合

适合：

- 盘前做候选扫描
- 盘中判断今天是否值得开新仓
- 盘后结合当前持仓做次日模拟计划
- 想把策略信号直接接进模拟盘，并让 AI 同时处理已有仓位

不适合：

- 你只想看信号，不想下单
- 你只想做历史回测，不想做账户维度的模拟执行
