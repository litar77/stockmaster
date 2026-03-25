---
name: stockmaster
description: >
  Analyzes A-share (Chinese stock) market conditions by scoring bull/bear and hot/cold indicators,
  selects the optimal trading strategy, monitors portfolio holdings, and generates daily operation
  signals (buy/sell/hold/add/reduce). Use when the user mentions stock analysis, A-share market,
  portfolio management, stock screening, buy/sell signals, position management, technical analysis,
  Chan Theory, market trends, stop-loss/take-profit, or any Chinese stock trading topic.
  Trigger even for casual requests like "how is the market today" or "analyze this stock".
---

# StockMaster — A股智能操盘系统

## 系统概览

StockMaster 是一个模块化的A股分析系统，核心逻辑是：

```
判断行情状态 → 匹配操盘策略 → 执行选股/监控 → 生成操作指令
```

系统由6个模块组成，各模块可独立运行，也可通过工作流自动串联。

## 前置条件

首次运行前，检查并安装依赖：

```bash
pip install akshare pandas numpy matplotlib mplfinance ta
```

如果 akshare 安装失败，可尝试：
```bash
pip install akshare --upgrade
```

## 模块索引

| 模块 | 文件 | 功能 |
|------|------|------|
| 行情趋势判断 | `references/market_trend.md` | 判断当前市场状态：牛/熊 × 热/冷 |
| 进攻策略 | `references/aggressive_strategy.md` | 牛+热：龙头爆发，快进快出 |
| 谨慎乐观策略 | `references/cautious_strategy.md` | 牛+冷：低风险稳健盈利 |
| 保守观望策略 | `references/conservative_strategy.md` | 熊+热：严控风险，不亏为赢 |
| 空仓关注策略 | `references/defensive_strategy.md` | 熊+冷：清仓等待，关注底部信号 |
| 持仓管理 | `references/portfolio_management.md` | 持仓监控、操作指令生成 |
| 数据接口 | `references/akshare_api.md` | AKShare API 使用参考 |

## 核心工作流

### 工作流一：每日全流程分析（推荐作为定时任务）

这是最常用的工作流，适合作为 OpenClaw 定时任务每日执行：

**Step 1 — 判断行情状态**

读取 `references/market_trend.md`，使用 `scripts/trend_analyzer.py` 获取大盘数据并计算牛熊冷热状态。

```bash
python scripts/trend_analyzer.py
```

输出形如：`{"trend": "bull", "temperature": "hot", "strategy": "aggressive", "details": {...}}`

**Step 2 — 匹配操盘策略**

根据 Step 1 的结果，读取对应的策略参考文档：

| 状态 | 策略文档 |
|------|----------|
| bull + hot | `references/aggressive_strategy.md` |
| bull + cold | `references/cautious_strategy.md` |
| bear + hot | `references/conservative_strategy.md` |
| bear + cold | `references/defensive_strategy.md` |

**Step 3 — 持仓监控与操作指令**

读取 `references/portfolio_management.md`，使用 `scripts/portfolio_monitor.py` 分析当前持仓：

```bash
python scripts/portfolio_monitor.py --strategy <当前策略名>
```

对每只持仓股生成操作指令：买入、卖出、持仓、加仓、减仓。

**Step 4 — 生成每日报告**

```bash
python scripts/daily_report.py
```

汇总以上分析，生成结构化的每日操作报告。

### 工作流二：单独判断行情

只运行模块1，快速了解当前市场状态：
- 读取 `references/market_trend.md`
- 运行 `scripts/trend_analyzer.py`

### 工作流三：单独分析持仓

只运行模块6，对当前持仓进行分析：
- 读取 `references/portfolio_management.md`
- 运行 `scripts/portfolio_monitor.py --strategy <策略名>`

### 工作流四：策略选股

在确定策略后，根据对应策略文档的选股条件进行筛选：
- 读取对应策略的参考文档
- 使用 `scripts/fetch_market_data.py` 获取候选股数据
- 按策略规则筛选并排序

## 持仓数据

持仓记录保存在 `data/portfolio.json`，格式详见 `references/portfolio_management.md`。

用户可以通过以下方式管理持仓：
- 直接编辑 `data/portfolio.json`
- 告诉 Claude "我买了XXX，XXX股，成本价XXX"，Claude 会自动更新持仓文件

## OpenClaw 集成

此技能设计为可被 OpenClaw 智能体平台调度。推荐配置：

- **触发时间**：每个交易日 15:30（收盘后）
- **执行工作流**：工作流一（全流程分析）
- **输出方式**：生成每日报告，可推送至微信/邮件/钉钉

## 输出格式

每日报告采用以下结构：

```markdown
# StockMaster 每日操盘报告
## 日期：YYYY-MM-DD

## 一、行情状态
- 趋势：牛市/熊市
- 温度：热/冷
- 当前策略：进攻/谨慎乐观/保守观望/空仓关注

## 二、大盘概况
- 上证指数：XXXX（涨跌幅 X%）
- 创业板指：XXXX（涨跌幅 X%）
- 成交量：XXXX亿（vs 20日均量）

## 三、持仓操作指令
| 股票 | 代码 | 现价 | 成本 | 盈亏% | 操作 | 理由 |
|------|------|------|------|-------|------|------|
| XXX  | 600XXX | XX.XX | XX.XX | +X% | 持仓 | 趋势良好 |

## 四、选股推荐
| 股票 | 代码 | 现价 | 推荐理由 |
|------|------|------|----------|

## 五、风险提示
- ...
```

## 注意事项

- 所有分析仅供参考，不构成投资建议
- 系统依赖历史数据和技术指标，无法预测黑天鹅事件
- 建议结合基本面分析和个人风险承受能力做最终决策
- AKShare 数据可能有延迟，请以交易所实时数据为准
