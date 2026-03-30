#!/usr/bin/env python3
"""
StockMaster - 策略选择器
根据牛熊趋势和冷热温度选择对应投资策略
"""

import json
import os
from datetime import datetime

STRATEGY_MAP = {
    ("bull", "hot"): "aggressive",
    ("bull", "cold"): "cautious",
    ("bear", "hot"): "conservative",
    ("bear", "cold"): "defensive",
}

STRATEGY_NAME_CN = {
    "aggressive": "进攻策略（牛+热）",
    "cautious": "谨慎乐观策略（牛+冷）",
    "conservative": "保守观望策略（熊+热）",
    "defensive": "空仓关注策略（熊+冷）",
}

STRATEGY_INFO = {
    "aggressive": {
        "name": "aggressive",
        "name_cn": "进攻策略（牛+热）",
        "description": "在牛市配合市场热度较高时，采用积极进攻策略。满仓操作，把握市场上涨机会，追求收益最大化。",
        "trigger_condition": "牛市中市场情绪火热，赚钱效应明显，适合积极做多",
        "operation_guide": "1. 仓位管理：满仓操作\n2. 选股方向：强势股、热点板块龙头\n3. 操作频率：适当提高换手率，跟随市场热点\n4. 止损纪律：设置8%-10%止损线，及时止损",
        "risk_tips": "市场火热时保持理性，避免追高杀跌。注意市场情绪过热可能预示回调，做好仓位控制。"
    },
    "cautious": {
        "name": "cautious",
        "name_cn": "谨慎乐观策略（牛+冷）",
        "description": "在牛市但市场热度不足时，采用谨慎乐观策略。半仓操作，在看好后市的同时保留充足现金等待机会。",
        "trigger_condition": "牛市中市场温度较低，可能处于蓄力阶段，保留现金等待机会",
        "operation_guide": "1. 仓位管理：5成仓位\n2. 选股方向：基本面优秀的蓝筹股、白马股\n3. 操作频率：低频操作，等待确定性机会\n4. 止损纪律：设置10%止损线",
        "risk_tips": "市场热度不足时耐心等待，不盲目追涨。利用半仓优势，市场回调时加仓。"
    },
    "conservative": {
        "name": "conservative",
        "name_cn": "保守观望策略（熊+热）",
        "description": "在熊市但市场仍有热度时，采用保守观望策略。保持轻仓，参与短线热点炒作，严格控制风险。",
        "trigger_condition": "熊市中市场仍有局部热点，短线有赚钱机会但整体风险较大",
        "operation_guide": "1. 仓位管理：2-3成仓位\n2. 选股方向：市场热点板块、快进快出\n3. 操作频率：短线为主，快进快出\n4. 止损纪律：设置5%-8%止损线，短线必须严格止损",
        "risk_tips": "熊市中的反弹往往是逃命机会，切勿恋战。止损必须坚决，避免深度套牢。"
    },
    "defensive": {
        "name": "defensive",
        "name_cn": "空仓关注策略（熊+冷）",
        "description": "在熊市且市场冷清时，采用空仓关注策略。保持空仓或极低仓位，耐心等待市场见底信号。",
        "trigger_condition": "熊市中市场温度极低，赚钱效应差，保持防守等待机会",
        "operation_guide": "1. 仓位管理：空仓或1成仓位\n2. 选股方向：关注但不买入，等待右侧信号\n3. 操作频率：观望为主\n4. 止损纪律：不做买入则无止损问题",
        "risk_tips": "熊市空仓是最优策略。耐心等待市场底部信号，确认趋势反转后再逐步建仓。"
    }
}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "strategy_config.json")


def _load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_config(config):
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def select_strategy(trend, temperature, bull_score=None, hot_score=None, bull_total=None, hot_total=None):
    """
    根据趋势和温度选择策略

    Args:
        trend: "bull" 或 "bear"
        temperature: "hot" 或 "cold"
        bull_score: 牛熊评分（可选）
        hot_score: 冷热评分（可选）
        bull_total: 牛熊总分（可选）
        hot_total: 冷热总分（可选）

    Returns:
        dict: 包含策略信息及边界警告的字典
    """
    trend = trend.lower().strip()
    temperature = temperature.lower().strip()

    if trend not in ("bull", "bear") or temperature not in ("hot", "cold"):
        return {
            "error": "无效的趋势或温度参数",
            "valid_trend": ["bull", "bear"],
            "valid_temperature": ["hot", "cold"]
        }

    strategy_name = STRATEGY_MAP.get((trend, temperature))
    if not strategy_name:
        return {"error": "未找到匹配的策略"}

    result = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trend": trend,
        "temperature": temperature,
        "strategy": strategy_name,
        "strategy_cn": STRATEGY_NAME_CN.get(strategy_name, ""),
        "strategy_info": STRATEGY_INFO.get(strategy_name, {})
    }

    if all(isinstance(x, int) for x in [bull_score, hot_score, bull_total, hot_total]):
        threshold = max(3, int(bull_total * 0.6)) if bull_total else 3
        if bull_score == threshold:
            result["warning"] = "牛熊判断处于临界状态，建议关注趋势变化"
            result["warning_type"] = "trend_boundary"

        hot_threshold = max(3, int(hot_total * 0.6)) if hot_total else 3
        if hot_score == hot_threshold:
            if "warning" in result:
                result["warning"] += "；冷热判断也处于临界状态"
            else:
                result["warning"] = "冷热判断处于临界状态，建议关注市场温度变化"
            result["warning_type"] = "temperature_boundary"

        if bull_score == threshold and hot_score == hot_threshold:
            result["warning"] = "牛熊和冷热判断均处于临界状态，市场方向不明，建议谨慎操作"
            result["warning_type"] = "both_boundary"

    return result


def get_strategy_by_name(name):
    """
    根据策略名称获取完整策略信息

    Args:
        name: 策略名称（如 "aggressive", "cautious" 等）

    Returns:
        dict: 策略完整信息，不存在则返回 None
    """
    name = name.lower().strip()
    if name in STRATEGY_INFO:
        info = STRATEGY_INFO[name]
        return {
            "name": info["name"],
            "name_cn": info["name_cn"],
            "description": info["description"],
            "trigger_condition": info["trigger_condition"],
            "operation_guide": info["operation_guide"],
            "risk_tips": info["risk_tips"]
        }
    return None


def format_strategy_report(strategy_info):
    """
    格式化策略报告为可读字符串

    Args:
        strategy_info: 策略信息字典（由 select_strategy 或 get_strategy_by_name 返回）

    Returns:
        str: 格式化的策略报告
    """
    if "error" in strategy_info:
        return f"错误: {strategy_info['error']}"

    if not strategy_info:
        return "策略信息为空"

    lines = []
    lines.append("=" * 50)
    lines.append("        StockMaster 策略选择报告")
    lines.append("=" * 50)
    lines.append(f"生成时间: {strategy_info.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}")
    lines.append("-" * 50)

    if "trend" in strategy_info and "temperature" in strategy_info:
        trend_cn = "牛市" if strategy_info["trend"] == "bull" else "熊市"
        temp_cn = "热" if strategy_info["temperature"] == "hot" else "冷"
        lines.append(f"市场状态: {trend_cn} + {temp_cn}")
        lines.append(f"推荐策略: {strategy_info.get('strategy_cn', strategy_info.get('strategy', ''))}")
        lines.append("")

    info = strategy_info.get("strategy_info") or strategy_info
    if "description" in info:
        lines.append("【策略描述】")
        lines.append(info["description"])
        lines.append("")

    if "trigger_condition" in info:
        lines.append("【触发条件】")
        lines.append(info["trigger_condition"])
        lines.append("")

    if "operation_guide" in info:
        lines.append("【操作指南】")
        for line in info["operation_guide"].split("\n"):
            lines.append(f"  {line}")
        lines.append("")

    if "risk_tips" in info:
        lines.append("【风险提示】")
        lines.append(info["risk_tips"])
        lines.append("")

    if "warning" in strategy_info:
        lines.append("-" * 50)
        lines.append(f"⚠️  边界警告: {strategy_info['warning']}")
        lines.append("-" * 50)

    lines.append("=" * 50)
    return "\n".join(lines)


def main():
    """命令行入口"""
    import sys

    if len(sys.argv) >= 3:
        trend = sys.argv[1]
        temperature = sys.argv[2]
        result = select_strategy(trend, temperature)
    else:
        from hq_analysis import analyze_bull_bear, analyze_hot_cold

        print("StockMaster 策略选择器 - 正在分析市场状态...", file=sys.stderr)

        bull_bear = analyze_bull_bear()
        hot_cold = analyze_hot_cold()

        trend = bull_bear["trend"]
        temperature = hot_cold["temperature"]

        result = select_strategy(
            trend,
            temperature,
            bull_score=bull_bear.get("bull_score"),
            hot_score=hot_cold.get("hot_score"),
            bull_total=bull_bear.get("bull_total"),
            hot_total=hot_cold.get("hot_total")
        )
        result["bull_details"] = bull_bear
        result["hot_details"] = hot_cold

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
