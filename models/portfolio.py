"""
Portfolio Model Module
Tracks user holdings, cash balances, P&L (realized & unrealized),
asset allocation, and historical valuation snapshots over time.
"""

from datetime import datetime, timedelta
import random
from typing import Dict, List, Any, Tuple, Optional
from models.transaction import Transaction, TransactionType


class Holding:
    """
    Represents an open position in a specific stock.
    Tracks share count and average purchase cost basis.
    """

    def __init__(self, symbol: str, quantity: int, average_cost: float):
        self.symbol: str = symbol.upper()
        self.quantity: int = int(quantity)
        self.average_cost: float = round(float(average_cost), 2)

    @property
    def total_cost(self) -> float:
        """Total cost basis invested in this position."""
        return round(self.quantity * self.average_cost, 2)

    def current_value(self, current_price: float) -> float:
        """Current market valuation."""
        return round(self.quantity * float(current_price), 2)

    def unrealized_pnl(self, current_price: float) -> float:
        """Unrealized dollar profit/loss."""
        return round(self.current_value(current_price) - self.total_cost, 2)

    def unrealized_pnl_percent(self, current_price: float) -> float:
        """Unrealized percentage return."""
        if self.total_cost <= 0:
            return 0.0
        return round((self.unrealized_pnl(current_price) / self.total_cost) * 100.0, 2)

    def to_dict(self, current_price: Optional[float] = None) -> Dict[str, Any]:
        """Serializes holding to dictionary."""
        data = {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "average_cost": self.average_cost,
            "total_cost": self.total_cost,
        }
        if current_price is not None:
            data["current_price"] = round(current_price, 2)
            data["current_value"] = self.current_value(current_price)
            data["unrealized_pnl"] = self.unrealized_pnl(current_price)
            data["unrealized_pnl_percent"] = self.unrealized_pnl_percent(current_price)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Holding":
        return cls(
            symbol=data["symbol"],
            quantity=data["quantity"],
            average_cost=data["average_cost"],
        )


class PortfolioSnapshot:
    """
    A point-in-time record of total portfolio net worth for performance charting.
    """

    def __init__(
        self,
        timestamp: str,
        cash: float,
        stocks_value: float,
        total_value: float,
        unrealized_pnl: float,
        realized_pnl: float,
    ):
        self.timestamp: str = timestamp
        self.cash: float = round(float(cash), 2)
        self.stocks_value: float = round(float(stocks_value), 2)
        self.total_value: float = round(float(total_value), 2)
        self.unrealized_pnl: float = round(float(unrealized_pnl), 2)
        self.realized_pnl: float = round(float(realized_pnl), 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "cash": self.cash,
            "stocks_value": self.stocks_value,
            "total_value": self.total_value,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PortfolioSnapshot":
        return cls(
            timestamp=data["timestamp"],
            cash=data["cash"],
            stocks_value=data["stocks_value"],
            total_value=data["total_value"],
            unrealized_pnl=data.get("unrealized_pnl", 0.0),
            realized_pnl=data.get("realized_pnl", 0.0),
        )


class Portfolio:
    """
    Manages user capital, active stock holdings, order execution,
    transaction audit history, and historical performance tracking.
    """

    DEFAULT_INITIAL_CASH: float = 50_000.00
    COMMISSION_FEE: float = 0.00  # Zero-commission modern trading

    def __init__(
        self,
        user_id: str,
        initial_cash: float = DEFAULT_INITIAL_CASH,
        cash: Optional[float] = None,
        realized_pnl: float = 0.0,
    ):
        self.user_id: str = user_id
        self.initial_cash: float = round(float(initial_cash), 2)
        self.cash: float = round(float(cash if cash is not None else initial_cash), 2)
        self.realized_pnl: float = round(float(realized_pnl), 2)
        self.holdings: Dict[str, Holding] = {}
        self.transactions: List[Transaction] = []
        self.history: List[PortfolioSnapshot] = []

    def deposit(self, amount: float) -> bool:
        """Deposits funds into trading cash balance."""
        if amount <= 0:
            return False
        self.cash = round(self.cash + amount, 2)
        return True

    def withdraw(self, amount: float) -> Tuple[bool, str]:
        """Withdraws cash if sufficient free balance exists."""
        if amount <= 0:
            return False, "Withdrawal amount must be greater than zero."
        if amount > self.cash:
            return False, f"Insufficient funds. Free cash: ${self.cash:,.2f}"
        self.cash = round(self.cash - amount, 2)
        return True, "Withdrawal successful."

    def can_buy(self, symbol: str, quantity: int, price: float, fee: float = COMMISSION_FEE) -> Tuple[bool, str]:
        """Validates if a buy order can be executed."""
        if quantity <= 0:
            return False, "Order quantity must be at least 1 share."
        if price <= 0:
            return False, "Invalid stock price."
        
        total_required = round((quantity * price) + fee, 2)
        if total_required > self.cash:
            return (
                False,
                f"Insufficient funds: Required ${total_required:,.2f} but available cash is ${self.cash:,.2f}.",
            )
        return True, "Order valid."

    def execute_buy(
        self, symbol: str, quantity: int, price: float, fee: float = COMMISSION_FEE
    ) -> Transaction:
        """
        Executes a BUY order, updates holdings and cash, and records the transaction.
        """
        valid, msg = self.can_buy(symbol, quantity, price, fee)
        if not valid:
            raise ValueError(msg)

        sym = symbol.upper()
        total_cost = round((quantity * price) + fee, 2)
        self.cash = round(self.cash - total_cost, 2)

        # Update or create holding
        if sym in self.holdings:
            existing = self.holdings[sym]
            new_qty = existing.quantity + quantity
            new_cost_basis = round(
                (existing.total_cost + (quantity * price)) / new_qty, 2
            )
            self.holdings[sym] = Holding(sym, new_qty, new_cost_basis)
        else:
            self.holdings[sym] = Holding(sym, quantity, price)

        # Create & record transaction
        tx = Transaction(
            user_id=self.user_id,
            symbol=sym,
            transaction_type=TransactionType.BUY,
            quantity=quantity,
            price_per_share=price,
            fee=fee,
        )
        self.transactions.append(tx)
        return tx

    def can_sell(self, symbol: str, quantity: int) -> Tuple[bool, str]:
        """Validates if a sell order can be executed."""
        sym = symbol.upper()
        if quantity <= 0:
            return False, "Order quantity must be at least 1 share."
        if sym not in self.holdings:
            return False, f"You do not own any shares of {sym}."
        
        owned = self.holdings[sym].quantity
        if quantity > owned:
            return (
                False,
                f"Insufficient shares: Attempting to sell {quantity} shares, but you only own {owned}.",
            )
        return True, "Order valid."

    def execute_sell(
        self, symbol: str, quantity: int, price: float, fee: float = COMMISSION_FEE
    ) -> Transaction:
        """
        Executes a SELL order, updates cash and holdings, calculates realized P&L,
        and logs the transaction.
        """
        valid, msg = self.can_sell(symbol, quantity)
        if not valid:
            raise ValueError(msg)

        sym = symbol.upper()
        holding = self.holdings[sym]

        # Calculate realized P&L on this sale
        cost_basis_sold = quantity * holding.average_cost
        gross_proceeds = quantity * price
        net_proceeds = round(gross_proceeds - fee, 2)
        realized_gain = round(net_proceeds - cost_basis_sold, 2)

        self.realized_pnl = round(self.realized_pnl + realized_gain, 2)
        self.cash = round(self.cash + net_proceeds, 2)

        # Update remaining holding
        remaining_qty = holding.quantity - quantity
        if remaining_qty > 0:
            self.holdings[sym] = Holding(sym, remaining_qty, holding.average_cost)
        else:
            del self.holdings[sym]

        # Record transaction
        tx = Transaction(
            user_id=self.user_id,
            symbol=sym,
            transaction_type=TransactionType.SELL,
            quantity=quantity,
            price_per_share=price,
            fee=fee,
        )
        self.transactions.append(tx)
        return tx

    def get_stocks_value(self, stocks_dict: Dict[str, Any]) -> float:
        """Computes current total market value of all held stocks."""
        total = 0.0
        for sym, holding in self.holdings.items():
            stock = stocks_dict.get(sym)
            price = stock.price if hasattr(stock, "price") else float(stock.get("price", holding.average_cost)) if isinstance(stock, dict) else holding.average_cost
            total += holding.current_value(price)
        return round(total, 2)

    def get_total_net_worth(self, stocks_dict: Dict[str, Any]) -> float:
        """Computes Total Net Worth = Cash + Total Market Value of Stocks."""
        return round(self.cash + self.get_stocks_value(stocks_dict), 2)

    def get_total_unrealized_pnl(self, stocks_dict: Dict[str, Any]) -> float:
        """Computes aggregate unrealized P&L across all positions."""
        total_cost = sum(h.total_cost for h in self.holdings.values())
        current_val = self.get_stocks_value(stocks_dict)
        return round(current_val - total_cost, 2)

    def record_snapshot(self, stocks_dict: Dict[str, Any], timestamp: Optional[str] = None) -> PortfolioSnapshot:
        """
        Captures a snapshot of current portfolio valuation.
        Used to build performance graphs over time.
        """
        ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stocks_val = self.get_stocks_value(stocks_dict)
        net_worth = round(self.cash + stocks_val, 2)
        unrealized = self.get_total_unrealized_pnl(stocks_dict)

        snapshot = PortfolioSnapshot(
            timestamp=ts,
            cash=self.cash,
            stocks_value=stocks_val,
            total_value=net_worth,
            unrealized_pnl=unrealized,
            realized_pnl=self.realized_pnl,
        )
        self.history.append(snapshot)
        # Retain last 300 snapshots for performance tracking
        if len(self.history) > 300:
            self.history.pop(0)
        return snapshot

    def seed_initial_history(self) -> None:
        """Generates historical snapshots for initial display if history is empty."""
        if self.history:
            return
        now = datetime.now()
        for i in range(14, 0, -1):
            ts = (now - timedelta(days=i)).strftime("%Y-%m-%d %H:%M:%S")
            # Slight random walk around initial cash
            drift = (14 - i) * 120.0 + random.uniform(-150.0, 200.0)
            val = round(self.initial_cash + drift, 2)
            self.history.append(
                PortfolioSnapshot(
                    timestamp=ts,
                    cash=self.initial_cash,
                    stocks_value=round(val - self.initial_cash, 2) if val > self.initial_cash else 0.0,
                    total_value=val,
                    unrealized_pnl=round(val - self.initial_cash, 2),
                    realized_pnl=0.0,
                )
            )

    def get_performance_summary(self, stocks_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates comprehensive performance metrics for UI dashboard and CLI.
        """
        stocks_val = self.get_stocks_value(stocks_dict)
        net_worth = round(self.cash + stocks_val, 2)
        unrealized = self.get_total_unrealized_pnl(stocks_dict)
        total_pnl = round(self.realized_pnl + unrealized, 2)
        
        # Calculate % return against initial balance
        total_return_pct = round(((net_worth - self.initial_cash) / self.initial_cash) * 100.0, 2) if self.initial_cash > 0 else 0.0

        # Detailed breakdown per position
        holdings_list = []
        for sym, h in self.holdings.items():
            stock = stocks_dict.get(sym)
            cur_price = stock.price if hasattr(stock, "price") else (stock.get("price", h.average_cost) if isinstance(stock, dict) else h.average_cost)
            stock_name = stock.name if hasattr(stock, "name") else (stock.get("name", sym) if isinstance(stock, dict) else sym)
            stock_change = stock.change_percent if hasattr(stock, "change_percent") else 0.0

            item = h.to_dict(cur_price)
            item["name"] = stock_name
            item["day_change_percent"] = stock_change
            item["portfolio_weight"] = round((item["current_value"] / net_worth * 100.0), 2) if net_worth > 0 else 0.0
            holdings_list.append(item)

        # Asset Allocation for Donut/Bar charts
        cash_weight = round((self.cash / net_worth * 100.0), 2) if net_worth > 0 else 100.0
        allocation = [{"label": "Cash", "value": self.cash, "percentage": cash_weight, "color": "#38bdf8"}]
        colors = ["#10b981", "#8b5cf6", "#f59e0b", "#ec4899", "#06b6d4", "#6366f1", "#14b8a6"]
        for idx, h in enumerate(holdings_list):
            allocation.append({
                "label": h["symbol"],
                "value": h["current_value"],
                "percentage": h["portfolio_weight"],
                "color": colors[idx % len(colors)],
            })

        return {
            "initial_cash": self.initial_cash,
            "cash": self.cash,
            "stocks_value": stocks_val,
            "total_net_worth": net_worth,
            "unrealized_pnl": unrealized,
            "realized_pnl": self.realized_pnl,
            "total_pnl": total_pnl,
            "total_return_pct": total_return_pct,
            "holdings": holdings_list,
            "holdings_count": len(self.holdings),
            "transactions_count": len(self.transactions),
            "transactions": [t.to_dict() for t in self.transactions],
            "asset_allocation": allocation,
            "performance_history": [s.to_dict() for s in self.history],
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serializes entire portfolio to dictionary for JSON or database export."""
        return {
            "user_id": self.user_id,
            "initial_cash": self.initial_cash,
            "cash": self.cash,
            "realized_pnl": self.realized_pnl,
            "holdings": {sym: h.to_dict() for sym, h in self.holdings.items()},
            "transactions": [t.to_dict() for t in self.transactions],
            "history": [s.to_dict() for s in self.history],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Portfolio":
        """Reconstructs portfolio from dictionary."""
        p = cls(
            user_id=data["user_id"],
            initial_cash=data.get("initial_cash", cls.DEFAULT_INITIAL_CASH),
            cash=data.get("cash", cls.DEFAULT_INITIAL_CASH),
            realized_pnl=data.get("realized_pnl", 0.0),
        )
        if "holdings" in data:
            for sym, hdata in data["holdings"].items():
                p.holdings[sym] = Holding.from_dict(hdata)

        if "transactions" in data:
            p.transactions = [Transaction.from_dict(t) for t in data["transactions"]]

        if "history" in data:
            p.history = [PortfolioSnapshot.from_dict(s) for s in data["history"]]

        return p
