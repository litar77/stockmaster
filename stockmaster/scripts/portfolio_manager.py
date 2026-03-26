#!/usr/bin/env python3
"""
StockMaster - 投资组合管理工具
提供持仓和自选股的管理功能
"""

import json
import os
from datetime import datetime
from pathlib import Path


class PortfolioManager:
    DEFAULT_PORTFOLIO = {
        "account": {
            "total_capital": 0,
            "cash": 0,
            "last_updated": ""
        },
        "holdings": [],
        "watchlist": [],
        "history": []
    }

    def __init__(self, data_dir=None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        self.portfolio_file = self.data_dir / "portfolio.json"

    def _load(self):
        if self.portfolio_file.exists():
            with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self.DEFAULT_PORTFOLIO.copy()

    def _save(self, data):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.portfolio_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_portfolio(self):
        return self._load()

    def save_portfolio(self, portfolio):
        portfolio["account"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save(portfolio)

    def add_holding(self, code, name, buy_date, buy_price, quantity, stop_loss=None, target_profit=None, strategy=None, notes=None):
        portfolio = self._load()
        cost = round(buy_price * quantity, 2)
        holding = {
            "code": code,
            "name": name,
            "buy_date": buy_date,
            "buy_price": round(buy_price, 2),
            "quantity": quantity,
            "cost": cost,
            "stop_loss": round(stop_loss, 2) if stop_loss else None,
            "target_profit": round(target_profit, 2) if target_profit else None,
            "strategy": strategy,
            "notes": notes
        }
        portfolio["holdings"].append(holding)
        portfolio["account"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save(portfolio)
        return holding

    def remove_holding(self, code):
        portfolio = self._load()
        original_len = len(portfolio["holdings"])
        portfolio["holdings"] = [h for h in portfolio["holdings"] if h["code"] != code]
        removed = len(portfolio["holdings"]) < original_len
        if removed:
            portfolio["account"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save(portfolio)
        return removed

    def update_holding(self, code, **kwargs):
        portfolio = self._load()
        for holding in portfolio["holdings"]:
            if holding["code"] == code:
                for key, value in kwargs.items():
                    if key in holding and value is not None:
                        if key in ("buy_price", "stop_loss", "target_profit", "cost"):
                            holding[key] = round(value, 2)
                        elif key == "quantity":
                            holding[key] = value
                        else:
                            holding[key] = value
                if "buy_price" in kwargs or "quantity" in kwargs:
                    holding["cost"] = round(holding["buy_price"] * holding["quantity"], 2)
                portfolio["account"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._save(portfolio)
                return holding
        return None

    def add_to_watchlist(self, code, name, reason):
        portfolio = self._load()
        if any(w["code"] == code for w in portfolio["watchlist"]):
            return None
        watch_item = {
            "code": code,
            "name": name,
            "reason": reason,
            "added_date": datetime.now().strftime("%Y-%m-%d")
        }
        portfolio["watchlist"].append(watch_item)
        portfolio["account"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save(portfolio)
        return watch_item

    def remove_from_watchlist(self, code):
        portfolio = self._load()
        original_len = len(portfolio["watchlist"])
        portfolio["watchlist"] = [w for w in portfolio["watchlist"] if w["code"] != code]
        removed = len(portfolio["watchlist"]) < original_len
        if removed:
            portfolio["account"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save(portfolio)
        return removed


def load_portfolio(data_dir=None):
    manager = PortfolioManager(data_dir)
    return manager.load_portfolio()


def save_portfolio(portfolio, data_dir=None):
    manager = PortfolioManager(data_dir)
    manager.save_portfolio(portfolio)


def add_holding(code, name, buy_date, buy_price, quantity, stop_loss=None, target_profit=None, strategy=None, notes=None, data_dir=None):
    manager = PortfolioManager(data_dir)
    return manager.add_holding(code, name, buy_date, buy_price, quantity, stop_loss, target_profit, strategy, notes)


def remove_holding(code, data_dir=None):
    manager = PortfolioManager(data_dir)
    return manager.remove_holding(code)


def update_holding(code, data_dir=None, **kwargs):
    manager = PortfolioManager(data_dir)
    return manager.update_holding(code, **kwargs)


def add_to_watchlist(code, name, reason, data_dir=None):
    manager = PortfolioManager(data_dir)
    return manager.add_to_watchlist(code, name, reason)


def remove_from_watchlist(code, data_dir=None):
    manager = PortfolioManager(data_dir)
    return manager.remove_from_watchlist(code)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="StockMaster 投资组合管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    subparsers.add_parser("load", help="加载投资组合")

    subparsers.add_parser("save", help="保存投资组合")

    add_parser = subparsers.add_parser("add-holding", help="添加持仓")
    add_parser.add_argument("--code", required=True)
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--buy-date", required=True)
    add_parser.add_argument("--buy-price", type=float, required=True)
    add_parser.add_argument("--quantity", type=int, required=True)
    add_parser.add_argument("--stop-loss", type=float)
    add_parser.add_argument("--target-profit", type=float)
    add_parser.add_argument("--strategy")
    add_parser.add_argument("--notes")

    remove_parser = subparsers.add_parser("remove-holding", help="移除持仓")
    remove_parser.add_argument("--code", required=True)

    update_parser = subparsers.add_parser("update-holding", help="更新持仓")
    update_parser.add_argument("--code", required=True)
    update_parser.add_argument("--buy-price", type=float)
    update_parser.add_argument("--quantity", type=int)
    update_parser.add_argument("--stop-loss", type=float)
    update_parser.add_argument("--target-profit", type=float)
    update_parser.add_argument("--strategy")
    update_parser.add_argument("--notes")

    watchlist_parser = subparsers.add_parser("add-watchlist", help="添加到自选股")
    watchlist_parser.add_argument("--code", required=True)
    watchlist_parser.add_argument("--name", required=True)
    watchlist_parser.add_argument("--reason", required=True)

    remove_watch_parser = subparsers.add_parser("remove-watchlist", help="从自选股移除")
    remove_watch_parser.add_argument("--code", required=True)

    args = parser.parse_args()

    if args.command == "load":
        portfolio = load_portfolio()
        print(json.dumps(portfolio, ensure_ascii=False, indent=2))
    elif args.command == "add-holding":
        result = add_holding(
            args.code, args.name, args.buy_date, args.buy_price, args.quantity,
            args.stop_loss, args.target_profit, args.strategy, args.notes
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "remove-holding":
        result = remove_holding(args.code)
        print(json.dumps({"removed": result}, ensure_ascii=False, indent=2))
    elif args.command == "update-holding":
        kwargs = {}
        if args.buy_price is not None:
            kwargs["buy_price"] = args.buy_price
        if args.quantity is not None:
            kwargs["quantity"] = args.quantity
        if args.stop_loss is not None:
            kwargs["stop_loss"] = args.stop_loss
        if args.target_profit is not None:
            kwargs["target_profit"] = args.target_profit
        if args.strategy is not None:
            kwargs["strategy"] = args.strategy
        if args.notes is not None:
            kwargs["notes"] = args.notes
        result = update_holding(args.code, **kwargs)
        print(json.dumps(result, ensure_ascii=False, indent=2) if result else json.dumps({"error": "holding not found"}, ensure_ascii=False, indent=2))
    elif args.command == "add-watchlist":
        result = add_to_watchlist(args.code, args.name, args.reason)
        print(json.dumps(result, ensure_ascii=False, indent=2) if result else json.dumps({"error": "already exists"}, ensure_ascii=False, indent=2))
    elif args.command == "remove-watchlist":
        result = remove_from_watchlist(args.code)
        print(json.dumps({"removed": result}, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
