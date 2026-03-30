#!/usr/bin/env python3
"""
StockMaster - 市场行情分析模块
生成当日市场行情分析报告 (HQ_yymmdd.md) 和当日策略 (CL_yymmdd.md)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import akshare as ak
    import pandas as pd
    import ta
except ImportError:
    print(json.dumps({"error": "请先安装依赖：pip install akshare pandas ta"}, ensure_ascii=False))
    sys.exit(1)


def analyze_bull_bear():
    """
    牛熊判断（0-5 分，>=3 为牛）
    融合缠论辅助评分（-2 到 +2）
    """
    scores = {}
    details = {}

    # 1. 上证指数与 MA60
    try:
        sh_df = ak.stock_zh_index_daily(symbol="sh000001")
        sh_df = sh_df.tail(260).copy()
        sh_df['close'] = sh_df['close'].astype(float)
        sh_df['MA60'] = sh_df['close'].rolling(60).mean()
        sh_df['MA250'] = sh_df['close'].rolling(250).mean()

        latest = sh_df.iloc[-1]
        ma60_prev = sh_df['MA60'].iloc[-5]

        # 指标 1: 上证 > MA60 且 MA60 向上
        sh_above_ma60 = latest['close'] > latest['MA60'] and latest['MA60'] > ma60_prev
        scores['sh_above_ma60'] = sh_above_ma60
        details['sh_close'] = round(float(latest['close']), 2)
        details['sh_ma60'] = round(float(latest['MA60']), 2)

        # 指标 2: 上证 > MA250
        if pd.notna(latest['MA250']):
            sh_above_ma250 = latest['close'] > latest['MA250']
            scores['sh_above_ma250'] = sh_above_ma250
            details['sh_ma250'] = round(float(latest['MA250']), 2)

        # 指标 4: 近 20 日涨幅
        close_20d_ago = sh_df['close'].iloc[-20]
        gain_20d = (latest['close'] - close_20d_ago) / close_20d_ago * 100
        scores['recent_20d_gain'] = gain_20d > 0
        details['recent_20d_gain'] = round(gain_20d, 2)

        # 指标 5: 周线 MACD (用日线近 5 日收盘均值模拟)
        macd_indicator = ta.trend.MACD(sh_df['close'])
        dif = macd_indicator.macd().iloc[-1]
        dea = macd_indicator.macd_signal().iloc[-1]
        hist = macd_indicator.macd_diff().iloc[-1]
        weekly_macd_positive = hist > 0 or dif > dea
        scores['weekly_macd_positive'] = weekly_macd_positive
        details['macd_hist'] = round(float(hist), 4)
        
        # 保存用于缠论分析
        sh_macd_hist = macd_indicator.macd_diff().values
        sh_close_prices = sh_df['close'].values

    except Exception as e:
        details['sh_error'] = str(e)
        sh_macd_hist = None
        sh_close_prices = None

    # 3. 创业板指与 MA60
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

    # 基础评分
    bull_score = sum(1 for v in scores.values() if v)
    total = len(scores)
    
    # ========== 缠论辅助评分 ==========
    chanlun_score = 0
    fractals = {'top_fractal': False, 'bottom_fractal': False, 'top_confirmed': False, 'bottom_confirmed': False}
    bearish_div = False
    bullish_div = False
    
    if sh_macd_hist is not None and sh_close_prices is not None:
        # 使用上证指数数据计算缠论评分
        try:
            # 重新获取包含 high/low 的完整数据
            sh_full_df = ak.stock_zh_index_daily(symbol="sh000001").tail(60)
            if 'high' in sh_full_df.columns and 'low' in sh_full_df.columns:
                chanlun_score, fractals, bearish_div, bullish_div = chanlun_adjustment_score(
                    sh_full_df, sh_macd_hist[-len(sh_full_df):]
                )
                details['chanlun_enabled'] = True
        except Exception as e:
            details['chanlun_error'] = str(e)
    
    # 修正后得分
    adjusted_bull_score = bull_score + chanlun_score
    
    # 动态阈值调整（有缠论信号时降低门槛）
    threshold = 2.5 if chanlun_score != 0 else max(3, total * 0.6)
    is_bull = adjusted_bull_score >= threshold
    
    # 计算置信度
    base_confidence = 60
    if abs(chanlun_score) > 0:
        confidence_boost = abs(chanlun_score) * 12.5
        if bearish_div or bullish_div:
            confidence_boost += 5
        confidence = min(base_confidence + confidence_boost, 95)
    else:
        confidence = base_confidence

    return {
        "trend": "bull" if is_bull else "bear",
        "bull_score": bull_score,
        "chanlun_score": chanlun_score,
        "adjusted_score": adjusted_bull_score,
        "bull_total": total,
        "threshold": threshold,
        "confidence": confidence,
        "scores": {k: bool(v) for k, v in scores.items()},
        "chanlun_signals": {
            "fractals": fractals,
            "bearish_divergence": bearish_div,
            "bullish_divergence": bullish_div
        },
        "details": details
    }


def analyze_hot_cold():
    """
    冷热判断（0-5 分，>=3 为热）
    融合量价背驰评分（-2 到 +2）
    """
    scores = {}
    details = {}
    volume_price_signal = 'none'
    volume_price_score = 0

    # 指标 1: 成交量比
    try:
        sh_df = ak.stock_zh_index_daily(symbol="sh000001")
        sh_df = sh_df.tail(30).copy()
        sh_df['volume'] = sh_df['volume'].astype(float)
        vol_ma20 = sh_df['volume'].rolling(20).mean().iloc[-1]
        vol_today = sh_df['volume'].iloc[-1]
        vol_ratio = vol_today / vol_ma20 if vol_ma20 > 0 else 0
        scores['volume_ratio'] = vol_ratio > 1.2
        details['volume_ratio'] = round(vol_ratio, 2)
        
        # 量价背驰分析
        volume_price_signal = volume_price_divergence(sh_df)
        if volume_price_signal == 'bearish':
            volume_price_score = -1
            details['volume_price_signal'] = '看空警示'
        elif volume_price_signal == 'bullish':
            volume_price_score = +1
            details['volume_price_signal'] = '见底信号'
        else:
            details['volume_price_signal'] = '正常'
    except Exception as e:
        details['volume_error'] = str(e)
        details['volume_price_signal'] = '分析失败'

    # 指标 2+3: 涨跌比 + 涨停数量
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

    # 指标 4: 主力资金流向
    try:
        fund_df = ak.stock_market_fund_flow()
        if len(fund_df) > 0:
            latest = fund_df.iloc[-1]
            main_net_flow = float(latest['主力净流入 - 净额'])
            scores['main_fund_positive'] = main_net_flow > 0
            details['main_net_flow'] = round(main_net_flow / 1e8, 2)
            details['main_net_flow_pct'] = float(latest['主力净流入 - 净占比'])
    except Exception as e:
        details['fund_error'] = str(e)

    # 指标 5: 北向资金
    try:
        north_df = ak.stock_hsgt_fund_flow_summary_em()
        north_rows = north_df[north_df['资金方向'] == '北向']
        if len(north_rows) > 0:
            total_net_buy = north_rows['成交净买额'].astype(float).sum()
            scores['north_flow_positive'] = total_net_buy > 0
            details['north_flow'] = round(total_net_buy, 2)
    except Exception as e:
        details['north_error'] = str(e)

    # 基础评分
    hot_score = sum(1 for v in scores.values() if v)
    total = len(scores)
    
    # 修正后得分（加入量价背驰评分）
    adjusted_hot_score = hot_score + volume_price_score
    
    # 动态阈值调整
    threshold = 2.5 if volume_price_score != 0 else max(3, total * 0.6)
    is_hot = adjusted_hot_score >= threshold
    
    # 计算置信度
    base_confidence = 60
    if volume_price_score != 0:
        confidence = min(base_confidence + abs(volume_price_score) * 10, 90)
    else:
        confidence = base_confidence

    return {
        "temperature": "hot" if is_hot else "cold",
        "hot_score": hot_score,
        "volume_price_score": volume_price_score,
        "adjusted_score": adjusted_hot_score,
        "hot_total": total,
        "threshold": threshold,
        "confidence": confidence,
        "scores": {k: bool(v) for k, v in scores.items()},
        "volume_price_analysis": {
            "signal": volume_price_signal,
            "score": volume_price_score
        },
        "details": details
    }


STRATEGY_MAP = {
    ("bull", "hot"): "aggressive",
    ("bull", "cold"): "cautious",
    ("bear", "hot"): "conservative",
    ("bear", "cold"): "defensive",
}

STRATEGY_NAME_CN = {
    "aggressive": "进攻策略（牛 + 热）",
    "cautious": "谨慎乐观（牛 + 冷）",
    "conservative": "保守观望（熊 + 热）",
    "defensive": "空仓关注（熊 + 冷）",
}


# ========== 缠论辅助判断函数 ==========

def find_top_fractal(high_prices, low_prices, i):
    """
    判断第 i 根 K 线是否形成顶分型
    
    参数:
        high_prices: 最高价序列
        low_prices: 最低价序列
        i: 当前 K 线索引
    
    返回:
        bool: 是否为顶分型
    """
    if i < 1 or i >= len(high_prices) - 1:
        return False
    
    # 中间 K 线最高价是三根中最高的
    if high_prices[i] > high_prices[i-1] and high_prices[i] > high_prices[i+1]:
        # 额外要求：三根 K 线有重叠区间（避免孤立尖峰）
        overlap_low = max(low_prices[i-1], low_prices[i], low_prices[i+1])
        overlap_high = min(high_prices[i-1], high_prices[i], high_prices[i+1])
        
        if overlap_low < overlap_high:  # 存在重叠
            return True
    
    return False


def find_bottom_fractal(high_prices, low_prices, i):
    """
    判断第 i 根 K 线是否形成底分型
    
    参数:
        high_prices: 最高价序列
        low_prices: 最低价序列
        i: 当前 K 线索引
    
    返回:
        bool: 是否为底分型
    """
    if i < 1 or i >= len(high_prices) - 1:
        return False
    
    # 中间 K 线最低价是三根中最低的
    if low_prices[i] < low_prices[i-1] and low_prices[i] < low_prices[i+1]:
        # 额外要求：三根 K 线有重叠区间
        overlap_low = max(low_prices[i-1], low_prices[i], low_prices[i+1])
        overlap_high = min(high_prices[i-1], high_prices[i], high_prices[i+1])
        
        if overlap_low < overlap_high:  # 存在重叠
            return True
    
    return False


def find_last_two_highs(prices):
    """
    找到最近两个价格高点
    
    返回:
        tuple: (第一个高点索引，第二个高点索引) 或 (None, None)
    """
    if len(prices) < 5:
        return None, None
    
    # 简单实现：找局部高点
    highs = []
    for i in range(1, len(prices) - 1):
        if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
            highs.append(i)
            if len(highs) == 2:
                break
    
    if len(highs) < 2:
        return None, None
    
    return highs[0], highs[1]


def find_last_two_lows(prices):
    """
    找到最近两个价格低点
    
    返回:
        tuple: (第一个低点索引，第二个低点索引) 或 (None, None)
    """
    if len(prices) < 5:
        return None, None
    
    # 简单实现：找局部低点
    lows = []
    for i in range(1, len(prices) - 1):
        if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
            lows.append(i)
            if len(lows) == 2:
                break
    
    if len(lows) < 2:
        return None, None
    
    return lows[0], lows[1]


def check_bearish_divergence(prices, macd_hist):
    """
    检测顶背离
    
    参数:
        prices: 价格序列
        macd_hist: MACD 柱状线序列
    
    返回:
        bool: 是否存在顶背离
    """
    high1_idx, high2_idx = find_last_two_highs(prices)
    
    if high2_idx is None:
        return False
    
    # 价格创新高
    price_higher = prices[high2_idx] > prices[high1_idx]
    
    # MACD 未创新高
    macd_lower = macd_hist[high2_idx] < macd_hist[high1_idx]
    
    return price_higher and macd_lower


def check_bullish_divergence(prices, macd_hist):
    """
    检测底背离
    
    参数:
        prices: 价格序列
        macd_hist: MACD 柱状线序列
    
    返回:
        bool: 是否存在底背离
    """
    low1_idx, low2_idx = find_last_two_lows(prices)
    
    if low2_idx is None:
        return False
    
    # 价格创新低
    price_lower = prices[low2_idx] < prices[low1_idx]
    
    # MACD 未创新低
    macd_higher = macd_hist[low2_idx] > macd_hist[low1_idx]
    
    return price_lower and macd_higher


def is_fractal_confirmed(prices, fractal_idx, fractal_type='top'):
    """
    判断分型是否被确认（后续 K 线突破）
    
    参数:
        prices: 价格序列
        fractal_idx: 分型位置索引
        fractal_type: 'top' 或 'bottom'
    
    返回:
        bool: 是否确认
    """
    if fractal_idx >= len(prices) - 1:
        return False
    
    if fractal_type == 'top':
        # 顶分型确认：跌破分型最低点
        fractal_low = min(prices[fractal_idx-1:fractal_idx+2])
        for i in range(fractal_idx + 1, len(prices)):
            if prices[i] < fractal_low:
                return True
    elif fractal_type == 'bottom':
        # 底分型确认：突破分型最高点
        fractal_high = max(prices[fractal_idx-1:fractal_idx+2])
        for i in range(fractal_idx + 1, len(prices)):
            if prices[i] > fractal_high:
                return True
    
    return False


def detect_fractals(df):
    """
    检测 K 线数据中的分型
    
    参数:
        df: 包含 high, low 列的 DataFrame
    
    返回:
        dict: 分型检测结果
    """
    if len(df) < 10:
        return {
            'top_fractal': False,
            'bottom_fractal': False,
            'top_confirmed': False,
            'bottom_confirmed': False
        }
    
    high_prices = df['high'].values
    low_prices = df['low'].values
    
    # 检测最近 5 根 K 线是否有分型
    recent_top = False
    recent_bottom = False
    top_idx = None
    bottom_idx = None
    
    for i in range(max(0, len(df) - 5), len(df)):
        if find_top_fractal(high_prices, low_prices, i):
            recent_top = True
            top_idx = i
        if find_bottom_fractal(high_prices, low_prices, i):
            recent_bottom = True
            bottom_idx = i
    
    # 检测分型确认
    top_confirmed = is_fractal_confirmed(low_prices, top_idx, 'top') if top_idx else False
    bottom_confirmed = is_fractal_confirmed(high_prices, bottom_idx, 'bottom') if bottom_idx else False
    
    return {
        'top_fractal': recent_top,
        'bottom_fractal': recent_bottom,
        'top_confirmed': top_confirmed,
        'bottom_confirmed': bottom_confirmed
    }


def chanlun_adjustment_score(df, macd_hist):
    """
    缠论辅助评分（-2 到 +2）
    
    参数:
        df: K 线数据 DataFrame
        macd_hist: MACD 柱状线序列
    
    返回:
        int: -2, -1, 0, +1, +2
    """
    score = 0
    
    # 检测分型
    fractals = detect_fractals(df)
    
    # 检测背驰
    prices = df['close'].values
    bearish_div = check_bearish_divergence(prices, macd_hist)
    bullish_div = check_bullish_divergence(prices, macd_hist)
    
    # 综合评分
    if fractals['top_fractal'] and fractals['top_confirmed'] and bearish_div:
        score = -2  # 强顶信号
    elif fractals['top_fractal'] and fractals['top_confirmed']:
        score = -1  # 普通顶信号
    elif fractals['bottom_fractal'] and fractals['bottom_confirmed'] and bullish_div:
        score = +2  # 强底信号
    elif fractals['bottom_fractal'] and fractals['bottom_confirmed']:
        score = +1  # 普通底信号
    
    return score, fractals, bearish_div, bullish_div


def volume_price_divergence(df):
    """
    检测量价背驰关系
    
    参数:
        df: 包含 close, volume 列的 DataFrame
    
    返回:
        str: 'bearish' (看空), 'bullish' (看多), 'none' (正常)
    """
    if len(df) < 10:
        return 'none'
    
    volume_data = df['volume'].values
    price_data = df['close'].values
    
    # 找到最近两个成交量峰值
    vol_peaks = find_last_two_highs(volume_data)
    price_peaks = find_last_two_highs(price_data)
    
    if vol_peaks[1] is None or price_peaks[1] is None:
        return 'none'
    
    # 情况 1: 放量但价格未新高 → 诱多警示（看空）
    if volume_data[vol_peaks[1]] > volume_data[vol_peaks[0]] * 1.2:  # 放量 20%
        if price_data[price_peaks[1]] < price_data[price_peaks[0]]:  # 价格未新高
            return 'bearish'
    
    # 情况 2: 缩量但价格企稳 → 见底信号（看多）
    if volume_data[vol_peaks[1]] < volume_data[vol_peaks[0]] * 0.8:  # 缩量 20%
        if price_data[price_peaks[1]] > price_data[price_peaks[0]] * 0.95:  # 价格企稳
            return 'bullish'
    
    return 'none'


def generate_market_report(bull_bear, hot_cold, output_dir=None):
    """
    生成当日市场行情分析报告 (HQ_yymmdd.md)
    
    参数:
        bull_bear: 牛熊判断结果
        hot_cold: 冷热判断结果
        output_dir: 输出目录，默认为 data/
    
    返回:
        str: 生成的文件路径
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    date_str = datetime.now().strftime("%y%m%d")
    filename = f"HQ_{date_str}.md"
    filepath = output_dir / filename
    
    # 生成报告内容
    trend = bull_bear["trend"]
    temperature = hot_cold["temperature"]
    strategy = STRATEGY_MAP[(trend, temperature)]
    strategy_cn = STRATEGY_NAME_CN[strategy]
    
    bull_details = bull_bear["details"]
    hot_details = hot_cold["details"]
    
    # 大盘概况数据
    sh_close = bull_details.get('sh_close', 'N/A')
    sh_change = bull_details.get('recent_20d_gain', 'N/A')
    cy_close = bull_details.get('cy_close', 'N/A')
    ad_ratio = hot_details.get('ad_ratio', 'N/A')
    advance = hot_details.get('advance', 'N/A')
    decline = hot_details.get('decline', 'N/A')
    zt_count = hot_details.get('zt_count', 'N/A')
    dt_count = hot_details.get('dt_count', 'N/A')
    vol_ratio = hot_details.get('volume_ratio', 'N/A')
    main_flow = hot_details.get('main_net_flow', 'N/A')
    north_flow = hot_details.get('north_flow', 'N/A')
    
    content = f"""# 市场行情分析报告

**报告日期**: {datetime.now().strftime("%Y-%m-%d")}  
**生成时间**: {datetime.now().strftime("%H:%M:%S")}

---

## 一、行情状态

| 维度 | 状态 | 得分 | 说明 |
|------|------|------|------|
| **趋势** | {"牛市 🐂" if trend == "bull" else "熊市 🐻"} | {bull_bear['bull_score']}/{bull_bear['bull_total']} | {"趋势向上" if trend == "bull" else "趋势向下"} |
| **温度** | {"热市 🔥" if temperature == "hot" else "冷市 ❄️"} | {hot_cold['hot_score']}/{hot_cold['hot_total']} | {"市场活跃" if temperature == "hot" else "市场冷清"} |
| **策略** | {strategy_cn} | - | 当前匹配策略 |

### 牛熊指标详情

| 指标 | 状态 | 数值/说明 |
|------|------|-----------|
| 上证指数 vs MA60 | {"✅" if bull_details.get('sh_close', 0) > bull_details.get('sh_ma60', 0) else "❌"} | {sh_close} / {bull_details.get('sh_ma60', 'N/A')} |
| 上证指数 vs MA250 | {"✅" if bull_bear['scores'].get('sh_above_ma250', False) else "❌"} | {bull_details.get('sh_ma250', 'N/A')} |
| 创业板指 vs MA60 | {"✅" if bull_bear['scores'].get('cy_above_ma60', False) else "❌"} | {cy_close} / {bull_details.get('cy_ma60', 'N/A')} |
| 近 20 日涨幅 | {"✅" if bull_bear['scores'].get('recent_20d_gain', False) else "❌"} | {sh_change}% |
| 周线 MACD | {"✅" if bull_bear['scores'].get('weekly_macd_positive', False) else "❌"} | {bull_details.get('macd_hist', 'N/A')} |

### 冷热指标详情

| 指标 | 状态 | 数值/说明 |
|------|------|-----------|
| 成交量比 | {"✅" if hot_cold['scores'].get('volume_ratio', False) else "❌"} | {vol_ratio} |
| 涨跌比 | {"✅" if hot_cold['scores'].get('advance_decline_ratio', False) else "❌"} | {ad_ratio} ({advance}涨/{decline}跌) |
| 涨停数量 | {"✅" if hot_cold['scores'].get('zt_count', False) else "❌"} | {zt_count}家 (跌停：{dt_count}家) |
| 主力资金 | {"✅" if hot_cold['scores'].get('main_fund_positive', False) else "❌"} | {main_flow}亿元 |
| 北向资金 | {"✅" if hot_cold['scores'].get('north_flow_positive', False) else "❌"} | {north_flow}亿元 |

---

## 二、大盘概况

### 主要指数

| 指数 | 收盘点位 | 状态 |
|------|----------|------|
| 上证指数 | {sh_close} | {"MA60 上方" if bull_details.get('sh_close', 0) > bull_details.get('sh_ma60', 0) else "MA60 下方"} |
| 创业板指 | {cy_close} | {"MA60 上方" if bull_bear['scores'].get('cy_above_ma60', False) else "MA60 下方"} |

### 市场活跃度

- **涨跌分布**: {advance}家上涨 / {decline}家下跌
- **涨跌比**: {ad_ratio}
- **涨停家数**: {zt_count}家
- **跌停家数**: {dt_count}家
- **市场活跃度**: {hot_details.get('market_activity', 'N/A')}

### 资金流向

- **主力资金**: {main_flow}亿元 {"(净流入)" if main_flow != 'N/A' and main_flow > 0 else "(净流出)" if main_flow != 'N/A' else ""}
- **北向资金**: {north_flow}亿元 {"(净流入)" if north_flow != 'N/A' and north_flow > 0 else "(净流出)" if north_flow != 'N/A' else ""}
- **成交量比**: {vol_ratio} {"(放量)" if vol_ratio != 'N/A' and vol_ratio > 1.2 else "(缩量)" if vol_ratio != 'N/A' else ""}

### 近期表现

- **近 20 日涨幅**: {sh_change}%
- **MACD 柱状线**: {bull_details.get('macd_hist', 'N/A')}

---

**风险提示**: 本报告仅供参考，不构成投资建议。市场有风险，投资需谨慎。
"""
    
    # 写入文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return str(filepath)


def generate_daily_strategy(bull_bear, hot_cold, output_dir=None):
    """
    生成当日策略 (CL_yymmdd.md)
    
    参数:
        bull_bear: 牛熊判断结果
        hot_cold: 冷热判断结果
        output_dir: 输出目录，默认为 data/
    
    返回:
        str: 生成的文件路径
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    date_str = datetime.now().strftime("%y%m%d")
    filename = f"CL_{date_str}.md"
    filepath = output_dir / filename
    
    # 生成策略内容
    trend = bull_bear["trend"]
    temperature = hot_cold["temperature"]
    strategy = STRATEGY_MAP[(trend, temperature)]
    strategy_cn = STRATEGY_NAME_CN[strategy]
    
    content = f"""# 当日策略

**报告日期**: {datetime.now().strftime("%Y-%m-%d")}  
**当前策略**: {strategy_cn}

---

## 策略说明

根据当前市场状态：
- **趋势**: {"牛市 🐂" if trend == "bull" else "熊市 🐻"}
- **温度**: {"热市 🔥" if temperature == "hot" else "冷市 ❄️"}

匹配策略：**{strategy_cn}**

---

**详细策略手册请参考**: `references/{strategy}_strategy.md`
"""
    
    # 写入文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return str(filepath)


def main():
    """
    主函数：生成当日市场行情分析报告和当日策略
    """
    print("StockMaster 市场行情分析模块 - 正在分析市场状态...", file=sys.stderr)
    
    # 执行分析
    bull_bear = analyze_bull_bear()
    hot_cold = analyze_hot_cold()
    
    # 生成报告
    hq_path = generate_market_report(bull_bear, hot_cold)
    cl_path = generate_daily_strategy(bull_bear, hot_cold)
    
    # 输出结果
    result = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "trend": bull_bear["trend"],
        "temperature": hot_cold["temperature"],
        "strategy": STRATEGY_MAP[(bull_bear["trend"], hot_cold["temperature"])],
        "strategy_cn": STRATEGY_NAME_CN[STRATEGY_MAP[(bull_bear["trend"], hot_cold["temperature"])]],
        "reports": {
            "market_report": hq_path,
            "daily_strategy": cl_path
        }
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n✅ 已生成市场行情分析报告：{hq_path}", file=sys.stderr)
    print(f"✅ 已生成当日策略：{cl_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
