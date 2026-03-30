#!/usr/bin/env python3
"""
StockMaster - 每日操盘报告生成器
汇总趋势分析 + 持仓监控，输出结构化的每日报告
"""

import json
import sys
import subprocess
import argparse
from datetime import datetime
from pathlib import Path


STRATEGY_CN = {
    "aggressive": "进攻策略（牛+热）",
    "cautious": "谨慎乐观（牛+冷）",
    "conservative": "保守观望（熊+热）",
    "defensive": "空仓关注（熊+冷）",
}

ACTION_EMOJI = {
    "sell": "🔴",
    "reduce": "🟡",
    "hold": "🟢",
    "add": "🔵",
    "buy": "⚪",
}


def run_trend_analyzer(scripts_dir):
    """运行市场分析"""
    script_path = scripts_dir / "hq_analysis.py"
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"error": result.stderr}
    except Exception as e:
        return {"error": str(e)}


def run_portfolio_monitor(scripts_dir, strategy, data_dir):
    """运行持仓监控"""
    script_path = scripts_dir / "portfolio_monitor.py"
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--strategy", strategy, "--data-dir", str(data_dir)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"error": result.stderr}
    except Exception as e:
        return {"error": str(e)}


def generate_markdown_report(trend_data, portfolio_data):
    """生成 Markdown 格式的每日报告"""
    date = datetime.now().strftime("%Y-%m-%d")
    strategy = trend_data.get("strategy", "unknown")
    strategy_cn = STRATEGY_CN.get(strategy, strategy)

    lines = []
    lines.append(f"# StockMaster 每日操盘报告")
    lines.append(f"## 日期：{date}")
    lines.append("")

    # 一、行情状态
    lines.append("## 一、行情状态")
    lines.append("")
    trend_cn = "牛市" if trend_data.get("trend") == "bull" else "熊市"
    temp_cn = "热" if trend_data.get("temperature") == "hot" else "冷"
    lines.append(f"- **趋势**：{trend_cn}（得分 {trend_data.get('bull_score', '?')}/{trend_data.get('bull_total', '?')}）")
    lines.append(f"- **温度**：{temp_cn}（得分 {trend_data.get('hot_score', '?')}/{trend_data.get('hot_total', '?')}）")
    lines.append(f"- **当前策略**：{strategy_cn}")

    if trend_data.get("warning"):
        lines.append(f"- **⚠️ 提示**：{trend_data['warning']}")

    lines.append("")

    # 二、大盘概况
    lines.append("## 二、大盘概况")
    lines.append("")
    bull_details = trend_data.get("bull_details", {}).get("details", {})
    if bull_details.get("sh_close"):
        lines.append(f"- 上证指数：{bull_details['sh_close']}（MA60: {bull_details.get('sh_ma60', 'N/A')}）")
    if bull_details.get("cy_close"):
        lines.append(f"- 创业板指：{bull_details['cy_close']}（MA60: {bull_details.get('cy_ma60', 'N/A')}）")
    if bull_details.get("recent_20d_gain") is not None:
        lines.append(f"- 近20日涨幅：{bull_details['recent_20d_gain']}%")

    hot_details = trend_data.get("hot_details", {}).get("details", {})
    if hot_details.get("volume_ratio"):
        lines.append(f"- 量比：{hot_details['volume_ratio']}（vs 20日均量）")
    if hot_details.get("ad_ratio"):
        lines.append(f"- 涨跌比：{hot_details['ad_ratio']}（涨{hot_details.get('advance', '?')} / 跌{hot_details.get('decline', '?')}）")
    if hot_details.get("zt_count") and isinstance(hot_details['zt_count'], int):
        lines.append(f"- 涨停家数：{hot_details['zt_count']}")
    if hot_details.get("north_flow"):
        direction = "流入" if hot_details['north_flow'] > 0 else "流出"
        lines.append(f"- 北向资金：净{direction} {abs(hot_details['north_flow'])} 亿")

    lines.append("")

    # 三、持仓操作指令
    lines.append("## 三、持仓操作指令")
    lines.append("")

    if "error" in portfolio_data:
        lines.append(f"持仓分析出错：{portfolio_data['error']}")
    elif portfolio_data.get("message") == "当前无持仓":
        lines.append("当前无持仓。")
        summary = portfolio_data.get("portfolio_summary", {})
        lines.append(f"- 总资金：{summary.get('total_capital', 'N/A')}")
        lines.append(f"- 可用现金：{summary.get('cash', 'N/A')}")
    else:
        # 持仓汇总
        summary = portfolio_data.get("portfolio_summary", {})
        lines.append(f"- 总资金：{summary.get('total_capital', 'N/A')}")
        lines.append(f"- 持仓市值：{summary.get('total_value', 'N/A')}")
        lines.append(f"- 仓位比例：{summary.get('position_ratio', 0):.1%}")
        lines.append(f"- 持股数量：{summary.get('holdings_count', 0)}")
        lines.append("")

        signals = portfolio_data.get("signals", [])
        if signals:
            lines.append("| 操作 | 股票 | 代码 | 现价 | 成本 | 盈亏% | 理由 |")
            lines.append("|------|------|------|------|------|-------|------|")
            for s in signals:
                emoji = ACTION_EMOJI.get(s.get("action", "hold"), "")
                action_cn = {"sell": "卖出", "reduce": "减仓", "hold": "持仓", "add": "加仓", "buy": "买入"}.get(s.get("action"), s.get("action"))
                lines.append(
                    f"| {emoji} {action_cn} | {s.get('name', '')} | {s.get('code', '')} | "
                    f"{s.get('current_price', 'N/A')} | {s.get('buy_price', 'N/A')} | "
                    f"{s.get('pnl_pct', 'N/A')}% | {s.get('reason', '')} |"
                )
            lines.append("")

        # 风险提示
        alerts = portfolio_data.get("risk_alerts", [])
        if alerts:
            lines.append("### 风险警报")
            for alert in alerts:
                severity_emoji = {"critical": "🚨", "high": "⚠️", "medium": "📢"}.get(alert.get("severity"), "ℹ️")
                lines.append(f"- {severity_emoji} {alert.get('message', '')}")
            lines.append("")

    # 四、风险提示
    lines.append("## 四、风险提示")
    lines.append("")
    lines.append("- 以上分析仅供参考，不构成投资建议")
    lines.append("- 系统基于历史数据和技术指标分析，无法预测突发事件")
    lines.append("- 请结合基本面分析和个人风险承受能力做最终决策")
    lines.append("- AKShare 数据可能存在延迟，请以交易所实时数据为准")
    lines.append("")
    lines.append("---")
    lines.append(f"*由 StockMaster 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="StockMaster 每日报告生成")
    parser.add_argument("--output", default=None, help="报告输出文件路径（默认输出到控制台）")
    parser.add_argument("--data-dir", default=None, help="数据目录路径")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="输出格式")
    args = parser.parse_args()

    scripts_dir = Path(__file__).parent
    skill_dir = scripts_dir.parent

    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = skill_dir / "data"

    # Step 1: 趋势分析
    print("Step 1/3: 运行趋势分析...", file=sys.stderr)
    trend_data = run_trend_analyzer(scripts_dir)
    if "error" in trend_data:
        print(f"趋势分析出错: {trend_data['error']}", file=sys.stderr)
        strategy = "conservative"  # 出错时默认保守
    else:
        strategy = trend_data.get("strategy", "conservative")

    # Step 2: 持仓监控
    print(f"Step 2/3: 运行持仓监控（策略：{strategy}）...", file=sys.stderr)
    portfolio_data = run_portfolio_monitor(scripts_dir, strategy, data_dir)

    # Step 3: 生成报告
    print("Step 3/3: 生成报告...", file=sys.stderr)

    if args.format == "json":
        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "trend": trend_data,
            "portfolio": portfolio_data,
        }
        output = json.dumps(report, ensure_ascii=False, indent=2)
    else:
        output = generate_markdown_report(trend_data, portfolio_data)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"报告已保存到：{output_path}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
