#!/usr/bin/env python3
"""
测试缠论辅助判断功能
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from market_analysis import (
    analyze_bull_bear, 
    analyze_hot_cold,
    detect_fractals,
    check_bearish_divergence,
    check_bullish_divergence
)

print("=" * 60)
print("StockMaster 缠论辅助判断功能测试")
print("=" * 60)

# 测试 1：牛熊判断（含缠论）
print("\n【测试 1】牛熊判断（融合缠论）")
print("-" * 60)
bull_bear = analyze_bull_bear()

print(f"趋势：{bull_bear['trend']}")
print(f"基础得分：{bull_bear['bull_score']}/{bull_bear['bull_total']}")
print(f"缠论评分：{bull_bear['chanlun_score']}")
print(f"修正后得分：{bull_bear['adjusted_score']}")
print(f"阈值：{bull_bear['threshold']}")
print(f"置信度：{bull_bear['confidence']}%")

print("\n缠论信号详情:")
chanlun_signals = bull_bear['chanlun_signals']
print(f"  - 顶分型：{chanlun_signals['fractals']['top_fractal']}")
print(f"  - 底分型：{chanlun_signals['fractals']['bottom_fractal']}")
print(f"  - 顶分型确认：{chanlun_signals['fractals']['top_confirmed']}")
print(f"  - 底分型确认：{chanlun_signals['fractals']['bottom_confirmed']}")
print(f"  - 顶背离：{chanlun_signals['bearish_divergence']}")
print(f"  - 底背离：{chanlun_signals['bullish_divergence']}")

# 测试 2：冷热判断（含量价）
print("\n【测试 2】冷热判断（融合量价背驰）")
print("-" * 60)
hot_cold = analyze_hot_cold()

print(f"温度：{hot_cold['temperature']}")
print(f"基础得分：{hot_cold['hot_score']}/{hot_cold['hot_total']}")
print(f"量价评分：{hot_cold['volume_price_score']}")
print(f"修正后得分：{hot_cold['adjusted_score']}")
print(f"阈值：{hot_cold['threshold']}")
print(f"置信度：{hot_cold['confidence']}%")

print("\n量价背驰分析:")
vp_analysis = hot_cold['volume_price_analysis']
print(f"  - 信号：{vp_analysis['signal']}")
print(f"  - 评分：{vp_analysis['score']}")

# 测试 3：综合判断
print("\n【测试 3】综合判断")
print("-" * 60)
trend = bull_bear['trend']
temperature = hot_cold['temperature']

print(f"市场状态：{trend} + {temperature}")
print(f"最终判断：趋势={trend}, 温度={temperature}")
print(f"缠论影响：{'有' if bull_bear['chanlun_score'] != 0 else '无'}")
print(f"量价影响：{'有' if hot_cold['volume_price_score'] != 0 else '无'}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
