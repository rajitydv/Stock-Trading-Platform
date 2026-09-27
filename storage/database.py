"""
Database & Persistence Layer
Handles relational SQLite persistence for users, portfolios, transactions,
and portfolio valuation snapshots, as well as JSON export and import.
"""

import json
import os
import sqlite3
from typing import Dict, List, Any, Optional
from models.stock import Stock
from models.transaction import Transaction, TransactionType
from models.portfolio import Portfolio, Holding, PortfolioSnapshot
from models.user import User


class DatabaseManager:
    """
    Manages SQLite database storage and JSON data backups for the platform.
    """

    def __init__(self, db_path: str = "data/trading_platform.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns SQLite connection with row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Creates tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    display_name TEXT,
                    email TEXT,
                    created_at TEXT
                )
            """)

            # User portfolios table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolios (
                    user_id TEXT PRIMARY KEY,
                    initial_cash REAL NOT NULL,
                    cash REAL NOT NULL,
                    realized_pnl REAL DEFAULT 0.0,
                    watchlist_json TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            # Holdings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS holdings (
                    user_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    average_cost REAL NOT NULL,
                    PRIMARY KEY (user_id, symbol),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            # Transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    type TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price_per_share REAL NOT NULL,
                    fee REAL DEFAULT 0.0,
                    total_amount REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            # Portfolio snapshots for performance over time
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    cash REAL NOT NULL,
                    stocks_value REAL NOT NULL,
                    total_value REAL NOT NULL,
                    unrealized_pnl REAL DEFAULT 0.0,
                    realized_pnl REAL DEFAULT 0.0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            # Stock catalog table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stocks (
                    symbol TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    sector TEXT NOT NULL,
                    price REAL NOT NULL,
                    previous_close REAL NOT NULL,
                    day_high REAL NOT NULL,
                    day_low REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    volatility REAL NOT NULL,
                    last_updated TEXT
                )
            """)

            conn.commit()

    def save_user(self, user: User) -> None:
        """Saves or updates user, portfolio, holdings, and watchlist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (user_id, username, display_name, email, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    email = excluded.email
                """,
                (user.user_id, user.username, user.display_name, user.email, user.created_at),
            )

            cursor.execute(
                """
                INSERT INTO portfolios (user_id, initial_cash, cash, realized_pnl, watchlist_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    cash = excluded.cash,
                    realized_pnl = excluded.realized_pnl,
                    watchlist_json = excluded.watchlist_json
                """,
                (
                    user.user_id,
                    user.portfolio.initial_cash,
                    user.portfolio.cash,
                    user.portfolio.realized_pnl,
                    json.dumps(user.watchlist),
                ),
            )

            # Sync holdings: delete and re-insert current active holdings
            cursor.execute("DELETE FROM holdings WHERE user_id = ?", (user.user_id,))
            for sym, holding in user.portfolio.holdings.items():
                cursor.execute(
                    """
                    INSERT INTO holdings (user_id, symbol, quantity, average_cost)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user.user_id, sym, holding.quantity, holding.average_cost),
                )

            # Sync transactions (insert if not present)
            for tx in user.portfolio.transactions:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO transactions
                    (id, user_id, symbol, type, quantity, price_per_share, fee, total_amount, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tx.id,
                        tx.user_id,
                        tx.symbol,
                        tx.transaction_type.value,
                        tx.quantity,
                        tx.price_per_share,
                        tx.fee,
                        tx.total_amount,
                        tx.timestamp,
                    ),
                )

            conn.commit()

    def load_user(self, identifier: str) -> Optional[User]:
        """
        Loads a user by either username or user_id.
        Reconstitutes portfolio, holdings, transactions, and snapshots.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE user_id = ? OR username = ?",
                (identifier, identifier.lower()),
            )
            u_row = cursor.fetchone()
            if not u_row:
                return None

            user_id = u_row["user_id"]
            cursor.execute("SELECT * FROM portfolios WHERE user_id = ?", (user_id,))
            p_row = cursor.fetchone()

            initial_cash = p_row["initial_cash"] if p_row else Portfolio.DEFAULT_INITIAL_CASH
            cash = p_row["cash"] if p_row else initial_cash
            realized_pnl = p_row["realized_pnl"] if p_row else 0.0
            watchlist = json.loads(p_row["watchlist_json"]) if p_row and p_row["watchlist_json"] else ["AAPL", "NVDA", "TSLA"]

            portfolio = Portfolio(
                user_id=user_id,
                initial_cash=initial_cash,
                cash=cash,
                realized_pnl=realized_pnl,
            )

            # Load holdings
            cursor.execute("SELECT * FROM holdings WHERE user_id = ?", (user_id,))
            for h_row in cursor.fetchall():
                portfolio.holdings[h_row["symbol"]] = Holding(
                    symbol=h_row["symbol"],
                    quantity=h_row["quantity"],
                    average_cost=h_row["average_cost"],
                )

            # Load transactions
            cursor.execute(
                "SELECT * FROM transactions WHERE user_id = ? ORDER BY timestamp ASC",
                (user_id,),
            )
            for t_row in cursor.fetchall():
                portfolio.transactions.append(
                    Transaction(
                        transaction_id=t_row["id"],
                        user_id=t_row["user_id"],
                        symbol=t_row["symbol"],
                        transaction_type=t_row["type"],
                        quantity=t_row["quantity"],
                        price_per_share=t_row["price_per_share"],
                        fee=t_row["fee"],
                        timestamp=t_row["timestamp"],
                    )
                )

            # Load snapshots
            cursor.execute(
                "SELECT * FROM portfolio_snapshots WHERE user_id = ? ORDER BY id ASC",
                (user_id,),
            )
            for s_row in cursor.fetchall():
                portfolio.history.append(
                    PortfolioSnapshot(
                        timestamp=s_row["timestamp"],
                        cash=s_row["cash"],
                        stocks_value=s_row["stocks_value"],
                        total_value=s_row["total_value"],
                        unrealized_pnl=s_row["unrealized_pnl"],
                        realized_pnl=s_row["realized_pnl"],
                    )
                )

            user = User(
                user_id=user_id,
                username=u_row["username"],
                display_name=u_row["display_name"],
                email=u_row["email"],
                created_at=u_row["created_at"],
                portfolio=portfolio,
                watchlist=watchlist,
            )
            return user

    def record_snapshot(self, user_id: str, snapshot: PortfolioSnapshot) -> None:
        """Stores a portfolio valuation snapshot in SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO portfolio_snapshots
                (user_id, timestamp, cash, stocks_value, total_value, unrealized_pnl, realized_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    snapshot.timestamp,
                    snapshot.cash,
                    snapshot.stocks_value,
                    snapshot.total_value,
                    snapshot.unrealized_pnl,
                    snapshot.realized_pnl,
                ),
            )
            conn.commit()

    def save_transaction(self, tx: Transaction) -> None:
        """Saves a single transaction."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO transactions
                (id, user_id, symbol, type, quantity, price_per_share, fee, total_amount, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tx.id,
                    tx.user_id,
                    tx.symbol,
                    tx.transaction_type.value,
                    tx.quantity,
                    tx.price_per_share,
                    tx.fee,
                    tx.total_amount,
                    tx.timestamp,
                ),
            )
            conn.commit()

    def list_users(self) -> List[Dict[str, Any]]:
        """Lists all registered users."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, username, display_name, email, created_at FROM users")
            return [dict(row) for row in cursor.fetchall()]

    def export_portfolio_json(self, user: User, filepath: str) -> bool:
        """
        Exports the entire user profile, portfolio, holdings, transaction ledger,
        and performance snapshots to a human-readable JSON file.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            data = user.to_dict(include_portfolio=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting portfolio to JSON: {e}")
            return False

    def import_portfolio_json(self, filepath: str) -> Optional[User]:
        """
        Imports and restores a user and portfolio state from a JSON backup file,
        and commits it to the SQLite database.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            user = User.from_dict(data)
            self.save_user(user)
            # Re-save snapshots
            for snap in user.portfolio.history:
                self.record_snapshot(user.user_id, snap)
            return user
        except Exception as e:
            print(f"Error importing portfolio from JSON: {e}")
            return None
