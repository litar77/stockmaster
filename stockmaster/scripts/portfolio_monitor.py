#!/usr/bin/env python3
"""
StockMaster - 持仓监控与操作指令生成
结合当前策略，对每只持仓股生成操作建议
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

try:
    import akshare as ak
    import pandas as pd
    import ta
except ImportError:
    print(json.dumps({"error": "请先安装依赖: pip install akshare pandas ta"}, ensure_ascii=False))
    sys.exit(1)

# 各策略的仓位限制参数
STRATEGY_PARAMS = {
    "aggressive": {
        "max_position_ratio": 0.80,
        "max_single_ratio": 0.20,
        "max_holdings": 5,
        "stop_loss_pct": -5.0,
        "take_profit_pct": 15.0,
        "trailing_stop_pct": -5.0,  # 从最高点回落
    },
    "cautious": {
        "max_position_ratio": 0.60,
        "max_single_ratio": 0.15,
        "max_holdings": 6,
        "stop_loss_pct": -8.0,
        "take_profit_pct": 10.0,
        "trailing_stop_pct": -8.0,
    },
    "conservative": {
        "max_position_ratio": 0.30,
        "max_single_ratio": 0.10,
        "max_holdings": 2,
        "stop_loss_pct": -3.0,
        "take_profit_pct": 5.0,
        "trailing_stop_pct": -3.0,
        "max_hold_days": 5,
    },
    "defensive": {
        "max_position_ratio": 0.0,
        "max_single_ratio": 0.0,
        "max_holdings": 0,
        "stop_loss_pct": 0,
        "take_profit_pct": 0,
    },
}


def load_portfolio(data_dir):
    """加载持仓数据"""
    portfolio_path = Path(data_dir) / "portfolio.json"
    if not portfolio_path.exists():
        return {
            "account": {"total_capital": 100000, "cash": 100000, "last_updated": ""},
            "holdings": [],
            "watchlist": [],
            "history": []
        }
    with open(portfolio_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_portfolio(portfolio, data_dir):
    """保存持仓数据"""
    portfolio_path = Path(data_dir) / "portfolio.json"
    portfolio["account"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(portfolio_path, 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)


def get_stock_analysis(code):
    """获取单只股票的分析数据"""
    result = {}

    # 日K线+技术指标（优先东方财富源，后备腾讯源）
    kline_df = None
    try:
        kline_df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        kline_df = kline_df.tail(120).copy()
        close = kline_df['收盘'].astype(float)
        volume = kline_df['成交量'].astype(float)
    except Exception:
        pass

    if kline_df is None or len(kline_df) == 0:
        try:
            # 腾讯源后备：代码格式需要前缀 sh/sz
            prefix = "sh" if code.startswith("6") else "sz"
            tx_df = ak.stock_zh_a_hist_tx(symbol=f"{prefix}{code}")
            tx_df = tx_df.tail(120).copy()
            # 统一列名
            kline_df = tx_df.rename(columns={
                'date': '日期', 'open': '开盘', 'close': '收盘',
                'high': '最高', 'low': '最低', 'amount': '成交量'
            })
            close = kline_df['收盘'].astype(float)
            volume = kline_df['成交量'].astype(float)
            result['data_source'] = 'tencent'
        except Exception as e2:
            result['kline_error'] = str(e2)
            return result

    # 从K线获取最新收盘价
    result['current_price'] = round(float(close.iloc[-1]), 2)
    result['name'] = code
    if '涨跌幅' in kline_df.columns:
        result['change_pct'] = round(float(kline_df['涨跌幅'].iloc[-1]), 2)

    # 实时行情（增强数据，可选）
    try:
        spot_df = ak.stock_zh_a_spot_em()
        stock_row = spot_df[spot_df['代码'] == code]
        if len(stock_row) > 0:
            row = stock_row.iloc[0]
            result['current_price'] = float(row['最新价'])
            result['change_pct'] = float(row['涨跌幅'])
            result['turnover_rate'] = float(row['换手率'])
            result['name'] = row['名称']
    except Exception:
        pass  # K线数据已有最新价，实时行情失败可忽略

    try:

        # 均线
        for period in [5, 10, 20, 60]:
            if len(close) >= period:
                result[f'ma{period}'] = round(float(close.rolling(period).mean().iloc[-1]), 2)
                # MA方向（与5日前比较）
                if len(close) >= period + 5:
                    ma_now = close.rolling(period).mean().iloc[-1]
                    ma_5ago = close.rolling(period).mean().iloc[-6]
                    result[f'ma{period}_trend'] = "up" if ma_now > ma_5ago else "down"

        # MACD
        macd = ta.trend.MACD(close)
        result['macd_dif'] = round(float(macd.macd().iloc[-1]), 4)
        result['macd_dea'] = round(float(macd.macd_signal().iloc[-1]), 4)
        result['macd_hist'] = round(float(macd.macd_diff().iloc[-1]), 4)

        # RSI
        result['rsi_14'] = round(float(ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]), 2)

        # 量比
        vol_ma20 = volume.rolling(20).mean().iloc[-1]
        result['volume_ratio'] = round(float(volume.iloc[-1] / vol_ma20), 2) if vol_ma20 > 0 else 0

        # 分型检测（最近3根K线）
        if len(kline_df) >= 3:
            highs = kline_df['最高'].astype(float).tail(3).values
            lows = kline_df['最低'].astype(float).tail(3).values
            if highs[1] > highs[0] and highs[1] > highs[2]:
                result['fractal'] = 'top'
            elif lows[1] < lows[0] and lows[1] < lows[2]:
                result['fractal'] = 'bottom'
            else:
                result['fractal'] = 'none'

    except Exception as e:
        result['kline_error'] = str(e)

    return result


def generate_signal(holding, analysis, strategy, params):
    """根据策略和技术分析生成操作信号"""
    signal = {
        "code": holding["code"],
        "name": holding.get("name", analysis.get("name", "")),
        "current_price": analysis.get("current_price", 0),
        "buy_price": holding["buy_price"],
        "quantity": holding["quantity"],
        "action": "hold",
        "reason": "",
        "risk_level": "low",
        "priority": 0,  # 越高越紧急
    }

    current_price = analysis.get("current_price", 0)
    if current_price == 0:
        signal["action"] = "hold"
        signal["reason"] = "无法获取实时价格，保持现状"
        return signal

    buy_price = holding["buy_price"]
    pnl_pct = (current_price - buy_price) / buy_price * 100
    signal["pnl_pct"] = round(pnl_pct, 2)

    stop_loss = holding.get("stop_loss", buy_price * (1 + params["stop_loss_pct"] / 100))
    hold_days = (datetime.now() - datetime.strptime(holding["buy_date"], "%Y-%m-%d")).days

    # === 空仓关注策略：所有持仓都应清仓 ===
    if strategy == "defensive":
        if pnl_pct > 0:
            signal["action"] = "sell"
            signal["reason"] = "空仓策略：盈利中，逢高清仓"
            signal["priority"] = 8
        elif pnl_pct > -5:
            signal["action"] = "sell"
            signal["reason"] = "空仓策略：小幅亏损，直接清仓"
            signal["priority"] = 7
        else:
            signal["action"] = "sell"
            signal["reason"] = f"空仓策略：亏损{pnl_pct:.1f}%，评估后择机清仓"
            signal["priority"] = 6
        signal["risk_level"] = "high"
        return signal

    # === 通用止损检查（所有策略） ===
    if current_price <= stop_loss:
        signal["action"] = "sell"
        signal["reason"] = f"触发止损线（止损价{stop_loss:.2f}），无条件清仓"
        signal["risk_level"] = "critical"
        signal["priority"] = 10
        return signal

    if pnl_pct <= params["stop_loss_pct"]:
        signal["action"] = "sell"
        signal["reason"] = f"亏损达到{pnl_pct:.1f}%，触发止损阈值{params['stop_loss_pct']}%"
        signal["risk_level"] = "critical"
        signal["priority"] = 10
        return signal

    # === 保守观望策略特殊规则 ===
    if strategy == "conservative":
        max_hold = params.get("max_hold_days", 5)
        if hold_days > max_hold and pnl_pct <= 0:
            signal["action"] = "sell"
            signal["reason"] = f"持有超{max_hold}天且未盈利（{hold_days}天），时间止损"
            signal["risk_level"] = "high"
            signal["priority"] = 8
            return signal
        if pnl_pct >= params["take_profit_pct"]:
            signal["action"] = "sell"
            signal["reason"] = f"盈利{pnl_pct:.1f}%达到目标{params['take_profit_pct']}%，立即清仓"
            signal["priority"] = 7
            return signal

    # === 止盈检查 ===
    if pnl_pct >= params["take_profit_pct"]:
        signal["action"] = "reduce"
        signal["reason"] = f"盈利{pnl_pct:.1f}%达到目标{params['take_profit_pct']}%，减仓50%锁定利润"
        signal["priority"] = 6
        return signal

    # === 技术面判断 ===
    ma5 = analysis.get("ma5")
    ma10 = analysis.get("ma10")
    ma20 = analysis.get("ma20")
    ma5_trend = analysis.get("ma5_trend", "")
    fractal = analysis.get("fractal", "none")
    macd_hist = analysis.get("macd_hist", 0)
    rsi = analysis.get("rsi_14", 50)
    volume_ratio = analysis.get("volume_ratio", 1.0)

    # 顶分型 + MACD柱缩短 → 减仓警告
    if fractal == "top" and macd_hist < 0:
        signal["action"] = "reduce"
        signal["reason"] = "出现顶分型且MACD柱转负，有见顶风险，建议减仓"
        signal["risk_level"] = "medium"
        signal["priority"] = 5
        return signal

    # 量价背离（价格上涨但量能萎缩）
    change_pct = analysis.get("change_pct", 0)
    if change_pct > 1 and volume_ratio < 0.7:
        signal["action"] = "reduce"
        signal["reason"] = "量价背离（上涨但缩量），注意风险，建议减仓"
        signal["risk_level"] = "medium"
        signal["priority"] = 4
        return signal

    # 跌破MA5（进攻策略视为危险信号）
    if strategy == "aggressive" and ma5 and current_price < ma5 and ma5_trend == "down":
        signal["action"] = "sell"
        signal["reason"] = f"跌破MA5（{ma5}）且MA5向下，进攻策略下清仓"
        signal["risk_level"] = "high"
        signal["priority"] = 7
        return signal

    # 跌破MA60（谨慎乐观策略视为破位）
    if strategy == "cautious" and analysis.get("ma60") and current_price < analysis["ma60"]:
        signal["action"] = "sell"
        signal["reason"] = f"跌破MA60（{analysis['ma60']}），中期趋势破位，清仓止损"
        signal["risk_level"] = "high"
        signal["priority"] = 8
        return signal

    # 底分型 + 缩量企稳 → 加仓机会（仅进攻和谨慎策略）
    if strategy in ("aggressive", "cautious") and fractal == "bottom" and volume_ratio < 0.9:
        if pnl_pct > -3:  # 未深度亏损
            signal["action"] = "add"
            signal["reason"] = "出现底分型且缩量企稳，回调到位可加仓"
            signal["risk_level"] = "low"
            signal["priority"] = 3
            return signal

    # RSI超卖 + 趋势完好 → 加仓
    if strategy in ("aggressive", "cautious") and rsi < 30 and ma5_trend == "up":
        signal["action"] = "add"
        signal["reason"] = f"RSI超卖（{rsi}）但均线向上，短线超卖可加仓"
        signal["priority"] = 3
        return signal

    # 默认：持仓
    reasons = []
    if ma5 and current_price > ma5:
        reasons.append("站上MA5")
    if ma5_trend == "up":
        reasons.append("MA5向上")
    if macd_hist > 0:
        reasons.append("MACD柱为正")
    if not reasons:
        reasons.append("无明显异常信号")
    signal["action"] = "hold"
    signal["reason"] = "趋势正常：" + "，".join(reasons)
    signal["risk_level"] = "low"

    return signal


def check_portfolio_risk(portfolio, signals, strategy, params):
    """整体风险检查"""
    alerts = []
    total_capital = portfolio["account"]["total_capital"]
    total_holding_value = sum(
        s.get("current_price", 0) * next(
            (h["quantity"] for h in portfolio["holdings"] if h["code"] == s["code"]), 0
        ) for s in signals
    )
    position_ratio = total_holding_value / total_capital if total_capital > 0 else 0

    # 总仓位检查
    max_ratio = params["max_position_ratio"]
    if position_ratio > max_ratio:
        alerts.append({
            "type": "position_over_limit",
            "message": f"总仓位{position_ratio:.1%}超过{strategy}策略上限{max_ratio:.0%}，需减仓",
            "severity": "high"
        })

    # 单票集中度检查
    for holding in portfolio["holdings"]:
        stock_value = next(
            (s.get("current_price", 0) * holding["quantity"] for s in signals if s["code"] == holding["code"]), 0
        )
        stock_ratio = stock_value / total_capital if total_capital > 0 else 0
        if stock_ratio > params["max_single_ratio"] and params["max_single_ratio"] > 0:
            alerts.append({
                "type": "single_over_limit",
                "message": f"{holding.get('name', holding['code'])}仓位{stock_ratio:.1%}超过单票上限{params['max_single_ratio']:.0%}",
                "severity": "medium"
            })

    # 总亏损检查
    total_cost = sum(h["cost"] for h in portfolio["holdings"])
    if total_cost > 0:
        total_pnl_pct = (total_holding_value - total_cost) / total_cost * 100
        if total_pnl_pct < -10:
            alerts.append({
                "type": "total_loss_alert",
                "message": f"账户总浮亏{total_pnl_pct:.1f}%，超过10%警戒线",
                "severity": "critical"
            })

    return alerts, position_ratio, total_holding_value


def main():
    parser = argparse.ArgumentParser(description="StockMaster 持仓监控")
    parser.add_argument("--strategy", required=True,
                        choices=["aggressive", "cautious", "conservative", "defensive"],
                        help="当前策略")
    parser.add_argument("--data-dir", default=None, help="数据目录路径")
    args = parser.parse_args()

    # 确定数据目录
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = Path(__file__).parent.parent / "data"

    params = STRATEGY_PARAMS[args.strategy]
    portfolio = load_portfolio(data_dir)

    if not portfolio["holdings"]:
        result = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "strategy": args.strategy,
            "message": "当前无持仓",
            "portfolio_summary": {
                "total_capital": portfolio["account"]["total_capital"],
                "cash": portfolio["account"]["cash"],
                "position_ratio": 0,
            },
            "signals": [],
            "risk_alerts": [],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 分析每只持仓股
    signals = []
    for holding in portfolio["holdings"]:
        print(f"正在分析 {holding.get('name', holding['code'])}...", file=sys.stderr)
        analysis = get_stock_analysis(holding["code"])
        signal = generate_signal(holding, analysis, args.strategy, params)
        signals.append(signal)

    # 按优先级排序（高优先级在前）
    signals.sort(key=lambda s: s.get("priority", 0), reverse=True)

    # 风险检查
    alerts, position_ratio, total_value = check_portfolio_risk(
        portfolio, signals, args.strategy, params
    )

    result = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "strategy": args.strategy,
        "portfolio_summary": {
            "total_capital": portfolio["account"]["total_capital"],
            "total_value": round(total_value, 2),
            "cash": portfolio["account"]["cash"],
            "position_ratio": round(position_ratio, 4),
            "holdings_count": len(portfolio["holdings"]),
        },
        "signals": signals,
        "risk_alerts": alerts,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
