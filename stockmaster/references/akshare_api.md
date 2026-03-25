# AKShare 数据接口参考

## 简介

AKShare 是一个开源的 Python 财经数据接口库，提供A股行情、财务、资金流向等数据。本技能使用 AKShare 作为主要数据来源。

## 安装

```bash
pip install akshare --upgrade
```

## 常用接口

### 1. 大盘指数数据

```python
import akshare as ak

# 上证指数日K线
sh_df = ak.stock_zh_index_daily(symbol="sh000001")
# 返回字段：date, open, high, low, close, volume

# 创业板指日K线
cy_df = ak.stock_zh_index_daily(symbol="sz399006")

# 沪深300日K线
hs300_df = ak.stock_zh_index_daily(symbol="sh000300")
```

### 2. 个股实时行情

```python
# 全部A股实时行情
spot_df = ak.stock_zh_a_spot_em()
# 返回字段包括：代码, 名称, 最新价, 涨跌幅, 涨跌额, 成交量, 成交额,
#              振幅, 最高, 最低, 今开, 昨收, 量比, 换手率, 市盈率, 市净率

# 筛选特定股票
stock_row = spot_df[spot_df['代码'] == '600519']
```

### 3. 个股历史K线

```python
# 日K线（前复权）
kline_df = ak.stock_zh_a_hist(
    symbol="600519",
    period="daily",      # daily/weekly/monthly
    start_date="20240101",
    end_date="20240115",
    adjust="qfq"         # qfq前复权, hfq后复权, ""不复权
)
# 返回字段：日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
```

### 4. 涨停板数据

```python
# 涨停池
zt_df = ak.stock_zt_pool_em(date="20240115")
# 返回字段包括：代码, 名称, 涨停价, 最新价, 成交额, 流通市值, 首次涨停时间,
#              涨停原因, 连续涨停次数

# 跌停池
dt_df = ak.stock_zt_pool_dtgc_em(date="20240115")
```

### 5. 北向资金

```python
# 北向资金汇总（沪深港通）
north_df = ak.stock_hsgt_fund_flow_summary_em()
# 返回字段：交易日, 类型, 板块, 资金方向, 交易状态, 成交净买额, 资金净流入, ...
# 筛选北向资金：
north_rows = north_df[north_df['资金方向'] == '北向']
total_net_buy = north_rows['成交净买额'].astype(float).sum()  # 北向总净买额
```

### 6. 个股财务数据

```python
# 个股主要财务指标
finance_df = ak.stock_financial_abstract_ths(symbol="600519")
# 返回字段包括：营业总收入, 净利润, ROE, 资产负债率等

# 个股估值（从实时行情中获取PE、PB）
spot_df = ak.stock_zh_a_spot_em()
stock_pe = spot_df[spot_df['代码'] == '600519']['市盈率-动态'].values[0]
```

### 7. 行业板块

```python
# 行业板块行情
sector_df = ak.stock_board_industry_name_em()
# 返回行业板块列表

# 行业板块成分股
stocks_df = ak.stock_board_industry_cons_em(symbol="白酒")
```

### 8. 资金流向

```python
# 个股资金流向
flow_df = ak.stock_individual_fund_flow(stock="600519", market="sh")
# 返回字段：日期, 主力净流入, 超大单净流入, 大单净流入, 中单净流入, 小单净流入
```

## 技术指标计算

AKShare 不直接提供技术指标，需要使用 `ta` 库或手动计算：

```python
import pandas as pd
import ta

# 基于K线数据计算技术指标
df = ak.stock_zh_a_hist(symbol="600519", period="daily", adjust="qfq")

# 均线
df['MA5'] = df['收盘'].rolling(5).mean()
df['MA10'] = df['收盘'].rolling(10).mean()
df['MA20'] = df['收盘'].rolling(20).mean()
df['MA60'] = df['收盘'].rolling(60).mean()
df['MA120'] = df['收盘'].rolling(120).mean()
df['MA250'] = df['收盘'].rolling(250).mean()

# MACD
macd = ta.trend.MACD(df['收盘'])
df['MACD_DIF'] = macd.macd()
df['MACD_DEA'] = macd.macd_signal()
df['MACD_HIST'] = macd.macd_diff()

# RSI
df['RSI_14'] = ta.momentum.RSIIndicator(df['收盘'], window=14).rsi()

# 布林带
bollinger = ta.volatility.BollingerBands(df['收盘'])
df['BB_UPPER'] = bollinger.bollinger_hband()
df['BB_LOWER'] = bollinger.bollinger_lband()
df['BB_MID'] = bollinger.bollinger_mavg()

# 成交量均线
df['VOL_MA20'] = df['成交量'].rolling(20).mean()
df['VOLUME_RATIO'] = df['成交量'] / df['VOL_MA20']
```

## 缠论相关计算

缠论的笔、线段、中枢需要自行实现。基本思路：

```python
# 分型识别（简化版）
def find_fractals(df):
    """识别顶分型和底分型"""
    tops = []
    bottoms = []
    for i in range(1, len(df) - 1):
        if df['最高'].iloc[i] > df['最高'].iloc[i-1] and df['最高'].iloc[i] > df['最高'].iloc[i+1]:
            tops.append(i)
        if df['最低'].iloc[i] < df['最低'].iloc[i-1] and df['最低'].iloc[i] < df['最低'].iloc[i+1]:
            bottoms.append(i)
    return tops, bottoms

# 笔的构成：顶分型到底分型（或反之），中间至少有1根独立K线
# 中枢：至少3笔重叠的价格区间
# 背驰：进入中枢和离开中枢的力度比较（MACD面积比较）
```

## 注意事项

- AKShare 数据可能有15-30分钟延迟，非实时数据
- 部分接口有频率限制，建议请求间隔 > 1秒
- 接口名称和返回字段可能随版本更新变化，遇到错误时先 `pip install akshare --upgrade`
- 节假日和非交易时间调用行情接口会返回上一个交易日数据
- 建议将获取的数据缓存到本地，避免重复请求
