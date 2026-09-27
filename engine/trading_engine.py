"""
Trading Engine Coordinator
Central orchestration layer that connects the Market Simulator,
User accounts, Order matching & validation, Portfolio tracking,
and Database persistence.
"""

import os
from typing import Dict, List, Any, Optional, Tuple
from engine.market_simulator import MarketSimulator
from storage.database import DatabaseManager
from models.user import User
from models.portfolio import Portfolio
from models.transaction import Transaction


class TradingEngine:
    """
    Coordinates market operations, user state, order execution,
    and automatic portfolio snapshotting.
    """

    def __init__(self, db_path: str = "data/trading_platform.db"):
        self.market: MarketSimulator = MarketSimulator()
        self.db: DatabaseManager = DatabaseManager(db_path=db_path)
        self.active_user: User = self._init_default_user()

        # Connect market tick listener to update active user's portfolio history
        self.market.add_tick_listener(self._on_market_tick)

    def _init_default_user(self) -> User:
        """Initializes or retrieves the default demo user."""
        default_username = "alex_investor"
        user = self.db.load_user(default_username)
        if not user:
            user = User(
                username=default_username,
                display_name="Alex Trader",
                email="alex@investor.com",
            )
            # Seed initial portfolio history for immediate chart display
            user.portfolio.seed_initial_history()
            
            # Execute a couple of starter seed holdings for instant engagement
            try:
                # Buy 15 shares of AAPL
                aapl = self.market.get_stock("AAPL")
                if aapl:
                    user.portfolio.execute_buy("AAPL", 15, aapl.price)
                # Buy 20 shares of NVDA
                nvda = self.market.get_stock("NVDA")
                if nvda:
                    user.portfolio.execute_buy("NVDA", 20, nvda.price)
                # Buy 10 shares of MSFT
                msft = self.market.get_stock("MSFT")
                if msft:
                    user.portfolio.execute_buy("MSFT", 10, msft.price)
            except Exception:
                pass

            # Record initial snapshot
            snap = user.portfolio.record_snapshot(self.market.stocks)
            self.db.save_user(user)
            self.db.record_snapshot(user.user_id, snap)
        return user

    def set_active_user(self, username: str, display_name: Optional[str] = None) -> User:
        """Switches active user or creates new user profile."""
        norm = username.strip().lower()
        user = self.db.load_user(norm)
        if not user:
            user = User(
                username=norm,
                display_name=display_name or norm.capitalize(),
            )
            user.portfolio.seed_initial_history()
            snap = user.portfolio.record_snapshot(self.market.stocks)
            self.db.save_user(user)
            self.db.record_snapshot(user.user_id, snap)
        self.active_user = user
        return self.active_user

    def _on_market_tick(self, stocks_dict: Dict[str, Any]) -> None:
        """Called automatically after each market tick."""
        if self.active_user:
            snap = self.active_user.portfolio.record_snapshot(stocks_dict)
            self.db.record_snapshot(self.active_user.user_id, snap)

    def tick_market(self, steps: int = 1) -> Dict[str, Any]:
        """Advances market simulation by N steps."""
        for _ in range(steps):
            self.market.tick()
        return self.get_market_state()

    def set_market_sentiment(self, sentiment: str) -> bool:
        """Changes market trend/sentiment."""
        return self.market.set_sentiment(sentiment)

    def buy_stock(self, symbol: str, quantity: int) -> Tuple[bool, str, Optional[Transaction]]:
        """
        Executes a buy order for the active user.
        Validates funds and live price, commits transaction, and updates SQLite.
        """
        sym = symbol.upper().strip()
        stock = self.market.get_stock(sym)
        if not stock:
            return False, f"Stock ticker '{sym}' not found on the exchange.", None

        valid, msg = self.active_user.portfolio.can_buy(sym, quantity, stock.price)
        if not valid:
            return False, msg, None

        try:
            tx = self.active_user.portfolio.execute_buy(sym, quantity, stock.price)
            # Record snapshot immediately after trade
            snap = self.active_user.portfolio.record_snapshot(self.market.stocks)
            # Persist to database
            self.db.save_user(self.active_user)
            self.db.record_snapshot(self.active_user.user_id, snap)
            return True, f"Successfully purchased {quantity} shares of {sym} at ${stock.price:.2f}.", tx
        except Exception as e:
            return False, str(e), None

    def sell_stock(self, symbol: str, quantity: int) -> Tuple[bool, str, Optional[Transaction]]:
        """
        Executes a sell order for the active user.
        Validates holdings, computes realized P&L, updates cash, and saves to SQLite.
        """
        sym = symbol.upper().strip()
        stock = self.market.get_stock(sym)
        if not stock:
            return False, f"Stock ticker '{sym}' not found on the exchange.", None

        valid, msg = self.active_user.portfolio.can_sell(sym, quantity)
        if not valid:
            return False, msg, None

        try:
            tx = self.active_user.portfolio.execute_sell(sym, quantity, stock.price)
            # Record snapshot immediately after trade
            snap = self.active_user.portfolio.record_snapshot(self.market.stocks)
            # Persist to database
            self.db.save_user(self.active_user)
            self.db.record_snapshot(self.active_user.user_id, snap)
            return True, f"Successfully sold {quantity} shares of {sym} at ${stock.price:.2f}.", tx
        except Exception as e:
            return False, str(e), None

    def deposit_cash(self, amount: float) -> Tuple[bool, str]:
        """Deposits funds into active user account."""
        if amount <= 0:
            return False, "Deposit amount must be positive."
        self.active_user.portfolio.deposit(amount)
        snap = self.active_user.portfolio.record_snapshot(self.market.stocks)
        self.db.save_user(self.active_user)
        self.db.record_snapshot(self.active_user.user_id, snap)
        return True, f"Deposited ${amount:,.2f} into account."

    def get_portfolio_state(self) -> Dict[str, Any]:
        """Returns complete portfolio metrics for the active user."""
        summary = self.active_user.portfolio.get_performance_summary(self.market.stocks)
        summary["user"] = {
            "user_id": self.active_user.user_id,
            "username": self.active_user.username,
            "display_name": self.active_user.display_name,
            "watchlist": self.active_user.watchlist,
        }
        return summary

    def get_market_state(self) -> Dict[str, Any]:
        """Returns comprehensive market data including all stocks and market summary."""
        stocks_data = [s.to_dict(include_history=True) for s in self.market.get_all_stocks()]
        summary = self.market.get_market_summary()
        return {
            "stocks": stocks_data,
            "summary": summary,
        }

    def toggle_watchlist(self, symbol: str) -> bool:
        """Toggles a stock in the active user's watchlist."""
        sym = symbol.upper()
        if sym in self.active_user.watchlist:
            self.active_user.remove_from_watchlist(sym)
            self.db.save_user(self.active_user)
            return False
        else:
            self.active_user.add_to_watchlist(sym)
            self.db.save_user(self.active_user)
            return True

    def export_data(self, filepath: Optional[str] = None) -> Tuple[bool, str]:
        """Exports portfolio data to JSON file."""
        path = filepath or f"data/export_{self.active_user.username}.json"
        success = self.db.export_portfolio_json(self.active_user, path)
        if success:
            return True, f"Portfolio successfully exported to '{path}'"
        return False, "Failed to export portfolio data."

    def import_data(self, filepath: str) -> Tuple[bool, str]:
        """Imports portfolio from JSON file."""
        user = self.db.import_portfolio_json(filepath)
        if user:
            self.active_user = user
            return True, f"Portfolio successfully loaded from '{filepath}'"
        return False, f"Failed to import data from '{filepath}'"
