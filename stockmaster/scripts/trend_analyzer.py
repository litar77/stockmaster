#!/usr/bin/env python3
"""
StockMaster - 牛熊冷热趋势分析器
判断当前A股市场状态：牛/熊 × 热/冷
"""

import json
import sys
from datetime import datetime

try:
    import akshare as ak
    import pandas as pd
    import ta
except ImportError:
    print(json.dumps({"error": "请先安装依赖: pip install akshare pandas ta"}, ensure_ascii=False))
    sys.exit(1)


def analyze_bull_bear():
    """
    牛熊判断（0-5分，>=3为牛）
    """
    scores = {}
    details = {}

    # 1. 上证指数与MA60
    try:
        sh_df = ak.stock_zh_index_daily(symbol="sh000001")
        sh_df = sh_df.tail(260).copy()
        sh_df['close'] = sh_df['close'].astype(float)
        sh_df['MA60'] = sh_df['close'].rolling(60).mean()
        sh_df['MA250'] = sh_df['close'].rolling(250).mean()

        latest = sh_df.iloc[-1]
        ma60_prev = sh_df['MA60'].iloc[-5]

        # 指标1: 上证 > MA60 且 MA60 向上
        sh_above_ma60 = latest['close'] > latest['MA60'] and latest['MA60'] > ma60_prev
        scores['sh_above_ma60'] = sh_above_ma60
        details['sh_close'] = round(float(latest['close']), 2)
        details['sh_ma60'] = round(float(latest['MA60']), 2)

        # 指标2: 上证 > MA250
        if pd.notna(latest['MA250']):
            sh_above_ma250 = latest['close'] > latest['MA250']
            scores['sh_above_ma250'] = sh_above_ma250
            details['sh_ma250'] = round(float(latest['MA250']), 2)

        # 指标4: 近20日涨幅
        close_20d_ago = sh_df['close'].iloc[-20]
        gain_20d = (latest['close'] - close_20d_ago) / close_20d_ago * 100
        scores['recent_20d_gain'] = gain_20d > 0
        details['recent_20d_gain'] = round(gain_20d, 2)

        # 指标5: 周线MACD (用日线近5日收盘均值模拟)
        macd_indicator = ta.trend.MACD(sh_df['close'])
        dif = macd_indicator.macd().iloc[-1]
        dea = macd_indicator.macd_signal().iloc[-1]
        hist = macd_indicator.macd_diff().iloc[-1]
        weekly_macd_positive = hist > 0 or dif > dea
        scores['weekly_macd_positive'] = weekly_macd_positive
        details['macd_hist'] = round(float(hist), 4)

    except Exception as e:
        details['sh_error'] = str(e)

    # 3. 创业板指与MA60
    try:
        cy_df = ak.stock_zh_index_daily(symbol="sz399006")
        cy_df = cy_df.tail(120).copy()
        cy_df['close'] = cy_df['close'].astype(float)
        cy_df['MA60'] = cy_df['close'].rolling(60).mean()
        ma60_prev_cy = cy_df['MA60'].iloc[-5]

        cy_latest = cy_df.iloc[-1]
        cy_above_ma60 = cy_latest['close'] > cy_latest['MA60'] and cy_latest['MA60'] > ma60_prev_cy
        scores['cy_above_ma60'] = cy_above_ma60
        details['cy_close'] = round(float(cy_latest['close']), 2)
        details['cy_ma60'] = round(float(cy_latest['MA60']), 2)

    except Exception as e:
        details['cy_error'] = str(e)

    bull_score = sum(1 for v in scores.values() if v)
    total = len(scores)
    threshold = max(3, total * 0.6)  # 动态阈值
    is_bull = bull_score >= threshold

    return {
        "trend": "bull" if is_bull else "bear",
        "bull_score": bull_score,
        "bull_total": total,
        "scores": {k: bool(v) for k, v in scores.items()},
        "details": details
    }


def analyze_hot_cold():
    """
    冷热判断（0-5分，>=3为热）
    """
    scores = {}
    details = {}

    # 指标1: 成交量比（上证指数日K线，稳定可靠）
    try:
        sh_df = ak.stock_zh_index_daily(symbol="sh000001")
        sh_df = sh_df.tail(30).copy()
        sh_df['volume'] = sh_df['volume'].astype(float)
        vol_ma20 = sh_df['volume'].rolling(20).mean().iloc[-1]
        vol_today = sh_df['volume'].iloc[-1]
        vol_ratio = vol_today / vol_ma20 if vol_ma20 > 0 else 0
        scores['volume_ratio'] = vol_ratio > 1.2
        details['volume_ratio'] = round(vol_ratio, 2)
    except Exception as e:
        details['volume_error'] = str(e)

    # 指标2+3: 涨跌比 + 涨停数量（乐股市场活跃度，无代理问题）
    try:
        activity_df = ak.stock_market_activity_legu()
        activity = dict(zip(activity_df['item'], activity_df['value']))

        advance = int(float(activity.get('上涨', 0)))
        decline = int(float(activity.get('下跌', 0)))
        zt_count = int(float(activity.get('涨停', 0)))

        ad_ratio = advance / max(decline, 1)
        scores['advance_decline_ratio'] = ad_ratio > 1.5
        details['advance'] = advance
        details['decline'] = decline
        details['ad_ratio'] = round(ad_ratio, 2)

        scores['zt_count'] = zt_count > 80
        details['zt_count'] = zt_count
        details['dt_count'] = int(float(activity.get('跌停', 0)))

        activity_pct = activity.get('活跃度', '0%')
        details['market_activity'] = activity_pct
    except Exception as e:
        details['activity_error'] = str(e)

    # 指标4: 主力资金流向（大盘资金流向）
    try:
        fund_df = ak.stock_market_fund_flow()
        if len(fund_df) > 0:
            latest = fund_df.iloc[-1]
            main_net_flow = float(latest['主力净流入-净额'])
            scores['main_fund_positive'] = main_net_flow > 0
            details['main_net_flow'] = round(main_net_flow / 1e8, 2)  # 转换为亿元
            details['main_net_flow_pct'] = float(latest['主力净流入-净占比'])
    except Exception as e:
        details['fund_error'] = str(e)

    # 指标5: 北向资金
    try:
        north_df = ak.stock_hsgt_fund_flow_summary_em()
        north_rows = north_df[north_df['资金方向'] == '北向']
        if len(north_rows) > 0:
            total_net_buy = north_rows['成交净买额'].astype(float).sum()
            scores['north_flow_positive'] = total_net_buy > 0
            details['north_flow'] = round(total_net_buy, 2)
    except Exception as e:
        details['north_error'] = str(e)

    hot_score = sum(1 for v in scores.values() if v)
    total = len(scores)
    threshold = max(3, total * 0.6)
    is_hot = hot_score >= threshold

    return {
        "temperature": "hot" if is_hot else "cold",
        "hot_score": hot_score,
        "hot_total": total,
        "scores": {k: bool(v) for k, v in scores.items()},
        "details": details
    }


STRATEGY_MAP = {
    ("bull", "hot"): "aggressive",
    ("bull", "cold"): "cautious",
    ("bear", "hot"): "conservative",
    ("bear", "cold"): "defensive",
}

STRATEGY_NAME_CN = {
    "aggressive": "进攻策略（牛+热）",
    "cautious": "谨慎乐观（牛+冷）",
    "conservative": "保守观望（熊+热）",
    "defensive": "空仓关注（熊+冷）",
}


def main():
    print("StockMaster 趋势分析器 - 正在获取数据...", file=sys.stderr)

    bull_bear = analyze_bull_bear()
    hot_cold = analyze_hot_cold()

    trend = bull_bear["trend"]
    temperature = hot_cold["temperature"]
    strategy = STRATEGY_MAP[(trend, temperature)]

    result = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "trend": trend,
        "temperature": temperature,
        "strategy": strategy,
        "strategy_cn": STRATEGY_NAME_CN[strategy],
        "bull_score": bull_bear["bull_score"],
        "bull_total": bull_bear["bull_total"],
        "hot_score": hot_cold["hot_score"],
        "hot_total": hot_cold["hot_total"],
        "bull_details": bull_bear,
        "hot_details": hot_cold
    }

    # 边界提示
    if bull_bear["bull_score"] == 3 or (bull_bear["bull_total"] > 0 and bull_bear["bull_score"] == int(bull_bear["bull_total"] * 0.6)):
        result["warning"] = "牛熊判断处于临界状态，建议使用更保守的策略"

    if hot_cold["hot_score"] == 3 or (hot_cold["hot_total"] > 0 and hot_cold["hot_score"] == int(hot_cold["hot_total"] * 0.6)):
        if "warning" in result:
            result["warning"] += "；冷热判断也处于临界状态"
        else:
            result["warning"] = "冷热判断处于临界状态，关注市场温度变化"

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
