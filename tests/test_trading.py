"""
Unit and Integration Test Suite
Validates Object-Oriented models, financial math, order execution,
validation rules, SQLite persistence, and JSON backup/restore.
"""

import os
import shutil
import unittest
import tempfile
from models.stock import Stock
from models.transaction import Transaction, TransactionType
from models.portfolio import Portfolio, Holding, PortfolioSnapshot
from models.user import User
from engine.market_simulator import MarketSimulator
from engine.trading_engine import TradingEngine
from storage.database import DatabaseManager


class TestStockModel(unittest.TestCase):
    def setUp(self):
        self.stock = Stock(
            symbol="TEST",
            name="Test Corp",
            sector="Technology",
            initial_price=100.0,
            volatility=0.01,
        )

    def test_initial_values(self):
        self.assertEqual(self.stock.symbol, "TEST")
        self.assertEqual(self.stock.price, 100.0)
        self.assertEqual(self.stock.previous_close, 100.0)
        self.assertEqual(self.stock.change, 0.0)
        self.assertEqual(self.stock.change_percent, 0.0)
        self.assertGreater(self.stock.volume, 0)
        self.assertGreater(len(self.stock.history), 0)

    def test_price_tick_updates_high_low_and_history(self):
        initial_history_len = len(self.stock.history)
        new_price = self.stock.update_price(market_sentiment=0.05)
        self.assertGreater(new_price, 0)
        self.assertEqual(len(self.stock.history), initial_history_len + 1)
        self.assertGreaterEqual(self.stock.day_high, new_price)
        self.assertLessEqual(self.stock.day_low, new_price)

    def test_stock_serialization(self):
        d = self.stock.to_dict()
        self.assertEqual(d["symbol"], "TEST")
        self.assertEqual(d["price"], 100.0)
        reconstructed = Stock.from_dict(d)
        self.assertEqual(reconstructed.symbol, "TEST")
        self.assertEqual(reconstructed.price, 100.0)


class TestPortfolioModel(unittest.TestCase):
    def setUp(self):
        self.portfolio = Portfolio(user_id="user_123", initial_cash=10000.0)

    def test_deposit_and_withdrawal(self):
        self.portfolio.deposit(2500.0)
        self.assertEqual(self.portfolio.cash, 12500.0)

        success, msg = self.portfolio.withdraw(5000.0)
        self.assertTrue(success)
        self.assertEqual(self.portfolio.cash, 7500.0)

        # Overdraft attempt should fail
        fail_success, fail_msg = self.portfolio.withdraw(10000.0)
        self.assertFalse(fail_success)
        self.assertEqual(self.portfolio.cash, 7500.0)

    def test_buy_execution_and_cost_basis(self):
        # Buy 10 shares @ $100
        tx1 = self.portfolio.execute_buy("AAPL", 10, 100.0)
        self.assertEqual(self.portfolio.cash, 9000.0)
        self.assertIn("AAPL", self.portfolio.holdings)
        self.assertEqual(self.portfolio.holdings["AAPL"].quantity, 10)
        self.assertEqual(self.portfolio.holdings["AAPL"].average_cost, 100.0)
        self.assertEqual(tx1.total_amount, 1000.0)

        # Buy 10 more shares @ $200 (weighted avg cost should become $150)
        tx2 = self.portfolio.execute_buy("AAPL", 10, 200.0)
        self.assertEqual(self.portfolio.cash, 7000.0)
        self.assertEqual(self.portfolio.holdings["AAPL"].quantity, 20)
        self.assertEqual(self.portfolio.holdings["AAPL"].average_cost, 150.0)

    def test_insufficient_funds_buy_rejection(self):
        can_buy, msg = self.portfolio.can_buy("EXPENSIVE", 10, 2000.0)  # Needs $20k, has $10k
        self.assertFalse(can_buy)
        with self.assertRaises(ValueError):
            self.portfolio.execute_buy("EXPENSIVE", 10, 2000.0)

    def test_sell_execution_and_realized_pnl(self):
        # Buy 10 shares @ $100
        self.portfolio.execute_buy("TSLA", 10, 100.0)
        self.assertEqual(self.portfolio.cash, 9000.0)

        # Sell 5 shares @ $140 (gain = 5 * (140 - 100) = $200)
        tx = self.portfolio.execute_sell("TSLA", 5, 140.0)
        self.assertEqual(tx.transaction_type, TransactionType.SELL)
        self.assertEqual(self.portfolio.cash, 9700.0)  # 9000 + 700 proceeds
        self.assertEqual(self.portfolio.realized_pnl, 200.0)
        self.assertEqual(self.portfolio.holdings["TSLA"].quantity, 5)

        # Sell remaining 5 shares @ $80 (loss = 5 * (80 - 100) = -$100)
        self.portfolio.execute_sell("TSLA", 5, 80.0)
        self.assertEqual(self.portfolio.cash, 10100.0)
        self.assertEqual(self.portfolio.realized_pnl, 100.0)  # 200 - 100 = 100 net realized
        self.assertNotIn("TSLA", self.portfolio.holdings)

    def test_insufficient_shares_sell_rejection(self):
        can_sell, msg = self.portfolio.can_sell("NVDA", 5)
        self.assertFalse(can_sell)
        with self.assertRaises(ValueError):
            self.portfolio.execute_sell("NVDA", 5, 120.0)

    def test_portfolio_valuation_and_performance(self):
        stock = Stock("AAPL", "Apple", "Tech", 150.0)
        self.portfolio.execute_buy("AAPL", 10, 150.0)  # spent $1500, cash = $8500
        
        # Simulate price jump to $200
        stock.price = 200.0
        stocks_dict = {"AAPL": stock}

        stocks_val = self.portfolio.get_stocks_value(stocks_dict)
        self.assertEqual(stocks_val, 2000.0)

        net_worth = self.portfolio.get_total_net_worth(stocks_dict)
        self.assertEqual(net_worth, 10500.0)

        unrealized = self.portfolio.get_total_unrealized_pnl(stocks_dict)
        self.assertEqual(unrealized, 500.0)

        summary = self.portfolio.get_performance_summary(stocks_dict)
        self.assertEqual(summary["total_net_worth"], 10500.0)
        self.assertEqual(summary["total_return_pct"], 5.0)  # (10500 - 10000) / 10000 * 100


class TestDatabaseAndPersistence(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_trading.db")
        self.db = DatabaseManager(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_load_user_with_portfolio(self):
        user = User(username="test_trader", display_name="Test Trader")
        user.portfolio.execute_buy("AAPL", 5, 200.0)
        user.portfolio.record_snapshot({"AAPL": Stock("AAPL", "Apple", "Tech", 200.0)})
        user.add_to_watchlist("TSLA")

        self.db.save_user(user)

        loaded = self.db.load_user("test_trader")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.username, "test_trader")
        self.assertEqual(loaded.portfolio.cash, user.portfolio.cash)
        self.assertIn("AAPL", loaded.portfolio.holdings)
        self.assertEqual(loaded.portfolio.holdings["AAPL"].quantity, 5)
        self.assertEqual(len(loaded.portfolio.transactions), 1)
        self.assertIn("TSLA", loaded.watchlist)

    def test_json_export_and_import(self):
        user = User(username="json_trader", display_name="JSON Trader")
        user.portfolio.execute_buy("MSFT", 8, 400.0)
        
        json_path = os.path.join(self.temp_dir, "backup.json")
        export_success = self.db.export_portfolio_json(user, json_path)
        self.assertTrue(export_success)
        self.assertTrue(os.path.exists(json_path))

        imported_user = self.db.import_portfolio_json(json_path)
        self.assertIsNotNone(imported_user)
        self.assertEqual(imported_user.username, "json_trader")
        self.assertIn("MSFT", imported_user.portfolio.holdings)
        self.assertEqual(imported_user.portfolio.holdings["MSFT"].quantity, 8)


class TestTradingEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_engine.db")
        self.engine = TradingEngine(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_engine_buy_and_sell(self):
        stock = self.engine.market.get_stock("AAPL")
        self.assertIsNotNone(stock)

        initial_cash = self.engine.active_user.portfolio.cash
        success, msg, tx = self.engine.buy_stock("AAPL", 5)
        self.assertTrue(success)
        self.assertIsNotNone(tx)
        self.assertLess(self.engine.active_user.portfolio.cash, initial_cash)

        # Sell 2 shares
        success_sell, msg_sell, tx_sell = self.engine.sell_stock("AAPL", 2)
        self.assertTrue(success_sell)
        self.assertEqual(self.engine.active_user.portfolio.holdings["AAPL"].quantity, 5 - 2 + (15 if "AAPL" in self.engine.active_user.portfolio.holdings else 0))

    def test_market_tick_updates_portfolio_snapshots(self):
        history_before = len(self.engine.active_user.portfolio.history)
        self.engine.tick_market(2)
        history_after = len(self.engine.active_user.portfolio.history)
        self.assertGreaterEqual(history_after, history_before + 2)


if __name__ == "__main__":
    unittest.main()
