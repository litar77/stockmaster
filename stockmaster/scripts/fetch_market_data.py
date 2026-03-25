#!/usr/bin/env python3
"""
StockMaster - 市场数据获取模块
获取大盘指数、个股行情、板块数据等
"""

import json
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    import akshare as ak
    import pandas as pd
except ImportError:
    print("请先安装依赖: pip install akshare pandas ta")
    sys.exit(1)


def get_index_data(symbol="sh000001", days=300):
    """获取指数日K线数据"""
    df = ak.stock_zh_index_daily(symbol=symbol)
    df = df.tail(days).copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    return df


def get_stock_kline(code, days=120, period="daily"):
    """获取个股日K线数据（前复权）"""
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
    df = ak.stock_zh_a_hist(
        symbol=code,
        period=period,
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"
    )
    df = df.tail(days).copy()
    return df


def get_realtime_quotes():
    """获取全市场实时行情"""
    df = ak.stock_zh_a_spot_em()
    return df


def get_zt_pool(date=None):
    """获取涨停池"""
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    try:
        df = ak.stock_zt_pool_em(date=date)
        return df
    except Exception:
        return pd.DataFrame()


def get_north_flow():
    """获取北向资金数据"""
    try:
        df = ak.stock_hsgt_north_net_flow_in_em(indicator="北上")
        return df
    except Exception:
        return pd.DataFrame()


def get_stock_fund_flow(code, market="sh"):
    """获取个股资金流向"""
    try:
        df = ak.stock_individual_fund_flow(stock=code, market=market)
        return df
    except Exception:
        return pd.DataFrame()


def calc_technical_indicators(df, close_col='收盘', vol_col='成交量', high_col='最高', low_col='最低'):
    """计算技术指标"""
    try:
        import ta
    except ImportError:
        print("请安装ta库: pip install ta")
        sys.exit(1)

    result = df.copy()

    # 均线
    for period in [5, 10, 20, 60, 120, 250]:
        col_name = f'MA{period}'
        if len(result) >= period:
            result[col_name] = result[close_col].rolling(period).mean()
        else:
            result[col_name] = None

    # MACD
    macd = ta.trend.MACD(result[close_col])
    result['MACD_DIF'] = macd.macd()
    result['MACD_DEA'] = macd.macd_signal()
    result['MACD_HIST'] = macd.macd_diff()

    # RSI
    result['RSI_14'] = ta.momentum.RSIIndicator(result[close_col], window=14).rsi()

    # 成交量均线
    result['VOL_MA5'] = result[vol_col].rolling(5).mean()
    result['VOL_MA20'] = result[vol_col].rolling(20).mean()
    if result['VOL_MA20'].iloc[-1] and result['VOL_MA20'].iloc[-1] > 0:
        result['VOLUME_RATIO'] = result[vol_col] / result['VOL_MA20']
    else:
        result['VOLUME_RATIO'] = None

    return result


def find_fractals(df, high_col='最高', low_col='最低'):
    """识别顶分型和底分型（缠论基础）"""
    tops = []
    bottoms = []
    for i in range(1, len(df) - 1):
        h_prev = df[high_col].iloc[i - 1]
        h_curr = df[high_col].iloc[i]
        h_next = df[high_col].iloc[i + 1]
        l_prev = df[low_col].iloc[i - 1]
        l_curr = df[low_col].iloc[i]
        l_next = df[low_col].iloc[i + 1]

        if h_curr > h_prev and h_curr > h_next and l_curr > l_prev and l_curr > l_next:
            tops.append({"index": i, "price": h_curr, "date": str(df.index[i]) if hasattr(df.index[i], 'strftime') else str(i)})
        if l_curr < l_prev and l_curr < l_next and h_curr < h_prev and h_curr < h_next:
            bottoms.append({"index": i, "price": l_curr, "date": str(df.index[i]) if hasattr(df.index[i], 'strftime') else str(i)})

    return tops, bottoms


def main():
    parser = argparse.ArgumentParser(description="StockMaster 数据获取")
    parser.add_argument("--type", choices=["index", "stock", "realtime", "zt", "north"],
                        default="index", help="数据类型")
    parser.add_argument("--symbol", default="sh000001", help="股票/指数代码")
    parser.add_argument("--days", type=int, default=120, help="获取天数")
    parser.add_argument("--output", default=None, help="输出JSON文件路径")
    args = parser.parse_args()

    if args.type == "index":
        df = get_index_data(args.symbol, args.days)
        data = {"type": "index", "symbol": args.symbol, "count": len(df)}
        print(json.dumps(data, ensure_ascii=False))
    elif args.type == "stock":
        df = get_stock_kline(args.symbol, args.days)
        df = calc_technical_indicators(df)
        data = {"type": "stock", "symbol": args.symbol, "count": len(df)}
        if args.output:
            df.to_csv(args.output, index=False)
            data["output_file"] = args.output
        print(json.dumps(data, ensure_ascii=False))
    elif args.type == "realtime":
        df = get_realtime_quotes()
        data = {"type": "realtime", "total_stocks": len(df)}
        print(json.dumps(data, ensure_ascii=False))
    elif args.type == "zt":
        df = get_zt_pool()
        data = {"type": "zt_pool", "count": len(df)}
        print(json.dumps(data, ensure_ascii=False))
    elif args.type == "north":
        df = get_north_flow()
        data = {"type": "north_flow", "count": len(df)}
        print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()
