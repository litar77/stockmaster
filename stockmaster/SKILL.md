---
name: stockmaster
version: "1.0.0"
description: >
  Analyzes A-share (Chinese stock) market conditions by scoring bull/bear and hot/cold indicators,
  selects the optimal trading strategy, monitors portfolio holdings, and generates daily operation
  signals (buy/sell/hold/add/reduce).

## 触发词

**中文关键词：**
市场分析、股票分析、持仓查询、止损止盈、买入信号、卖出信号、仓位管理、技术分析、缠论、趋势判断、牛熊、冷热

**English Keywords：**
market analysis, stock analysis, portfolio query, stop-loss/take-profit, buy signal, sell signal, position management, technical analysis, Chan Theory, trend judgment, bull/bear, hot/cold

Use when the user mentions stock analysis, A-share market, portfolio management, stock screening, buy/sell signals, position management, technical analysis, Chan Theory, market trends, stop-loss/take-profit, or any Chinese stock trading topic. Trigger even for casual requests like "how is the market today" or "analyze this stock".

## OpenClaw 命令定义

本项目支持通过 OpenClaw 命令调用，命令格式：`/stockmaster:<command>`

| 命令 | 功能 | 调用脚本 | 输出 |
|------|------|----------|------|
| `/stockmaster:hq` | 生成当日行情和策略 | `scripts/market_analysis.py` | HQ_yymmdd.md + CL_yymmdd.md |
| `/stockmaster:trend` | 判断市场趋势 | `scripts/trend_analyzer.py` | JSON 输出 |
| `/stockmaster:portfolio` | 持仓分析 | `scripts/portfolio_monitor.py` | JSON 输出 |
| `/stockmaster:report` | 生成每日报告 | `scripts/daily_report.py` | Markdown 报告 |

### 命令示例

**生成当日行情和策略：**
```bash
/stockmaster:hq
```

执行后生成：
- `data/HQ_yymmdd.md` - 市场行情分析报告
- `data/CL_yymmdd.md` - 当日策略
---

# StockMaster — A 股智能操盘系统

## 🚀 快速开始

**首次使用？请查看 [INSTALL.md](INSTALL.md) 获取详细的安装指南！**

**快速安装：**
```bash
# 运行自动安装脚本
python install.py

# 或手动安装依赖
pip install -r requirements.txt
```

## 系统概览

StockMaster 是一个模块化的A股分析系统，核心逻辑是：

```
判断行情状态 → 匹配操盘策略 → 执行选股/监控 → 生成操作指令
```

系统由6个模块组成，各模块可独立运行，也可通过工作流自动串联。

## 数据流

```
行情数据获取 → 趋势分析 → 策略匹配 → 持仓监控 → 信号生成 → 报告输出
```

- **行情数据获取**：通过 AKShare API 获取实时行情数据
- **趋势分析**：计算牛熊冷热指标，判断当前市场状态
- **策略匹配**：根据市场状态匹配对应操盘策略
- **持仓监控**：分析当前持仓，生成操作指令
- **信号生成**：输出买入/卖出/持仓/加仓/减仓信号
- **报告输出**：生成结构化每日操盘报告

## 依赖安装

首次运行前，安装所有依赖包：

```bash
pip install akshare pandas numpy ta matplotlib mplfinance
```

**核心依赖：**

| 包名 | 用途 |
|------|------|
| akshare | 行情数据获取 |
| pandas | 数据处理 |
| numpy | 数值计算 |
| ta | 技术指标计算 |
| matplotlib | 可视化（可选） |
| mplfinance | K线图绘制（可选） |

如果 akshare 安装失败，可尝试：
```bash
pip install akshare --upgrade
```

## 文件结构

```
stockmaster/
├── scripts/
│   ├── trend_analyzer.py      # 趋势分析脚本
│   ├── portfolio_monitor.py   # 持仓监控脚本
│   ├── daily_report.py        # 每日报告生成
│   └── fetch_market_data.py   # 行情数据获取
├── references/
│   ├── market_trend.md        # 行情趋势判断
│   ├── aggressive_strategy.md # 进攻策略
│   ├── cautious_strategy.md   # 谨慎乐观策略
│   ├── conservative_strategy.md # 保守观望策略
│   ├── defensive_strategy.md  # 空仓关注策略
│   ├── portfolio_management.md # 持仓管理
│   └── akshare_api.md        # AKShare API 参考
├── config/                    # 配置文件目录
├── data/
│   └── portfolio.json         # 持仓数据
├── tests/                     # 测试文件
└── SKILL.md                   # 本文件
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

## OpenClaw集成

此技能设计为可被 OpenClaw 智能体平台调度。推荐配置：

### 定时任务配置

```yaml
cron: "0 15:30 * * 1-5"
timezone: "Asia/Shanghai"
enabled: true
```

### 工作流配置

```yaml
workflow:
  name: "每日全流程分析"
  steps:
    - script: "trend_analyzer.py"
    - script: "portfolio_monitor.py"
    - script: "daily_report.py"
  output_format: "markdown"
```

### 推送配置

支持多种推送渠道：

**微信：**
```yaml
notify:
  channel: "wechat"
  webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=XXXX"
```

**邮件：**
```yaml
notify:
  channel: "email"
  smtp_server: "smtp.example.com"
  smtp_port: 587
  from: "stockmaster@example.com"
  to: ["user@example.com"]
```

**钉钉：**
```yaml
notify:
  channel: "dingtalk"
  webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=XXXX"
```

### 触发条件

- **触发时间**：每个交易日 15:30（收盘后）
- **执行工作流**：工作流一（全流程分析）
- **输出方式**：生成每日报告，推送至配置的渠道

## 策略触发条件

根据用户输入的关键词或问题类型，自动匹配对应的操盘策略：

| 用户输入 | 触发策略 | 说明 |
|----------|----------|------|
| 市场分析、行情怎么样、今天大盘 | 趋势判断 | 执行工作流一，获取市场状态 |
| 股票分析、帮我看股、分析XXX | 趋势判断 + 持仓分析 | 分析个股或市场整体 |
| 持仓查询、我的股票、仓位 | 持仓管理 | 分析当前持仓状态 |
| 止损止盈、怎么设置止损 | 持仓管理 | 提供止损止盈建议 |
| 买入信号、推荐股票、买什么 | 策略选股 | 根据当前策略推荐股票 |
| 卖出信号、要卖吗、什么时候卖 | 持仓管理 | 生成卖出建议 |
| 仓位管理、仓位多少合适 | 持仓管理 | 提供仓位管理建议 |
| 技术分析、K线、指标 | 趋势判断 | 进行技术分析 |
| 缠论、缠中说禅 | 趋势判断 | 应用缠论分析方法 |
| 趋势判断、牛熊 | 趋势判断 | 判断市场牛熊状态 |
| 冷热、市场热度 | 趋势判断 | 判断市场冷热状态 |

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
