"""
Command-Line Interface (CLI) Module
Provides an interactive, colorized terminal console for trading stocks,
inspecting market quotes, monitoring portfolio performance,
and executing simulation steps.
"""

import sys
import os
from datetime import datetime
from typing import Optional

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLOR_ENABLED = True
except ImportError:
    COLOR_ENABLED = False
    class EmptyColor:
        def __getattr__(self, name):
            return ""
    Fore = Back = Style = EmptyColor()

from engine.trading_engine import TradingEngine


class TradingCLI:
    """
    Interactive Terminal User Interface for the Stock Trading Platform.
    """

    def __init__(self, engine: Optional[TradingEngine] = None):
        self.engine = engine or TradingEngine()

    def clear(self):
        """Clears the console screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_banner(self):
        """Displays stylized terminal header."""
        border = "=" * 76
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{border}")
        print(f"   [+]  QUANTUM TRADE TERMINAL  |  SIMULATED STOCK EXCHANGE")
        print(f"   Active User: {Fore.YELLOW}{self.engine.active_user.display_name} ({self.engine.active_user.username}){Fore.CYAN} | Market: {Fore.MAGENTA}{self.engine.market.sentiment.upper()}")
        print(f"{border}{Style.RESET_ALL}")

    def show_market_overview(self):
        """Renders live stock prices in a tabular format."""
        self.print_banner()
        market_state = self.engine.get_market_state()
        stocks = market_state["stocks"]
        summary = market_state["summary"]

        print(f"\n{Fore.WHITE}{Style.BRIGHT}--- LIVE MARKET QUOTES ---{Style.RESET_ALL}")
        print(f"Ticks: {summary['tick_count']} | Market Trend: {Fore.YELLOW}{summary.get('sentiment_label', 'Neutral')}{Style.RESET_ALL} | Index Change: {summary.get('market_index_change_percent', 0.0):+.2f}%\n")

        header = f"{'SYMBOL':<8} {'COMPANY':<24} {'SECTOR':<16} {'PRICE':>10} {'CHANGE':>10} {'% CHG':>10} {'VOLUME':>12}"
        print(f"{Fore.CYAN}{header}{Style.RESET_ALL}")
        print("-" * 96)

        for s in stocks:
            chg_val = s["change"]
            chg_pct = s["change_percent"]
            if chg_pct > 0:
                color = Fore.GREEN
                arrow = "+"
            elif chg_pct < 0:
                color = Fore.RED
                arrow = "-"
            else:
                color = Fore.WHITE
                arrow = " "

            row = (
                f"{Fore.YELLOW}{Style.BRIGHT}{s['symbol']:<8}{Style.RESET_ALL} "
                f"{s['name'][:23]:<24} "
                f"{s['sector'][:15]:<16} "
                f"${s['price']:>9.2f} "
                f"{color}{arrow} {chg_val:>8.2f}{Style.RESET_ALL} "
                f"{color}{chg_pct:>9.2f}%{Style.RESET_ALL} "
                f"{s['volume']:>12,}"
            )
            print(row)
        print("-" * 96)

    def show_stock_details(self):
        """Displays in-depth quote for a single stock."""
        sym = input(f"\n{Fore.CYAN}Enter stock symbol (e.g. AAPL, NVDA, TSLA): {Style.RESET_ALL}").strip().upper()
        stock = self.engine.market.get_stock(sym)
        if not stock:
            print(f"{Fore.RED}Stock '{sym}' not found!{Style.RESET_ALL}")
            return

        q = stock.to_dict(include_history=True)
        color = Fore.GREEN if q["change"] >= 0 else Fore.RED

        print(f"\n{Fore.YELLOW}{Style.BRIGHT}==================== {q['symbol']} - {q['name']} ===================={Style.RESET_ALL}")
        print(f"  Sector:           {q['sector']}")
        print(f"  Current Price:    ${q['price']:.2f} ({color}{q['change']:+.2f} / {q['change_percent']:+.2f}%{Style.RESET_ALL})")
        print(f"  Day Range:        ${q['day_low']:.2f} - ${q['day_high']:.2f}")
        print(f"  Bid / Ask:        ${q['bid']:.2f} / ${q['ask']:.2f}")
        print(f"  Trading Volume:   {q['volume']:,} shares")
        print(f"  Market Cap:       ${q['market_cap']:,.2f}")
        print(f"  Volatility:       {stock.volatility * 100:.1f}%")
        
        # Recent price history mini-sparkline / points
        history = q.get("history", [])
        if history:
            print(f"\n  Recent Price History (Last 5 Ticks):")
            for h in history[-5:]:
                print(f"    • {h['timestamp']}: ${h['price']:.2f} (Vol: {h.get('volume', 0):,})")
        print(f"{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}")

    def show_portfolio_summary(self):
        """Displays complete user portfolio performance, P&L, and asset allocation."""
        self.print_banner()
        data = self.engine.get_portfolio_state()

        net_worth = data["total_net_worth"]
        cash = data["cash"]
        stocks_val = data["stocks_value"]
        total_pnl = data["total_pnl"]
        return_pct = data["total_return_pct"]
        unrealized = data["unrealized_pnl"]
        realized = data["realized_pnl"]

        pnl_color = Fore.GREEN if total_pnl >= 0 else Fore.RED

        print(f"\n{Fore.WHITE}{Style.BRIGHT}--- PORTFOLIO PERFORMANCE SUMMARY ---{Style.RESET_ALL}")
        print(f"  Total Net Worth:     {Fore.YELLOW}{Style.BRIGHT}${net_worth:,.2f}{Style.RESET_ALL}")
        print(f"  Cash Balance:        ${cash:,.2f} ({cash / net_worth * 100:.1f}%)")
        print(f"  Invested in Stocks:  ${stocks_val:,.2f} ({stocks_val / net_worth * 100:.1f}%)")
        print(f"  Initial Capital:     ${data['initial_cash']:,.2f}")
        print(f"  Total P&L:           {pnl_color}${total_pnl:+,.2f} ({return_pct:+.2f}%){Style.RESET_ALL}")
        print(f"    ├─ Unrealized P&L: {Fore.GREEN if unrealized >= 0 else Fore.RED}${unrealized:+,.2f}{Style.RESET_ALL}")
        print(f"    └─ Realized P&L:   {Fore.GREEN if realized >= 0 else Fore.RED}${realized:+,.2f}{Style.RESET_ALL}")

        # Holdings Table
        holdings = data.get("holdings", [])
        print(f"\n{Fore.WHITE}{Style.BRIGHT}--- CURRENT HOLDINGS ({len(holdings)} positions) ---{Style.RESET_ALL}")
        if not holdings:
            print("  (No open positions. Use Buy Stock option to purchase shares.)")
        else:
            hdr = f"{'SYMBOL':<8} {'SHARES':>8} {'AVG COST':>10} {'PRICE':>10} {'VALUATION':>12} {'UNREALIZED P&L':>16} {'WEIGHT':>8}"
            print(f"{Fore.CYAN}{hdr}{Style.RESET_ALL}")
            print("-" * 80)
            for h in holdings:
                hpnl = h["unrealized_pnl"]
                hpnl_pct = h["unrealized_pnl_percent"]
                c = Fore.GREEN if hpnl >= 0 else Fore.RED
                pnl_str = f"{c}{hpnl:+,.2f} ({hpnl_pct:+.1f}%){Style.RESET_ALL}"
                print(
                    f"{Fore.YELLOW}{h['symbol']:<8}{Style.RESET_ALL} "
                    f"{h['quantity']:>8} "
                    f"${h['average_cost']:>9.2f} "
                    f"${h['current_price']:>9.2f} "
                    f"${h['current_value']:>11.2f} "
                    f"{pnl_str:>25} "
                    f"{h['portfolio_weight']:>7.1f}%"
                )
            print("-" * 80)

        # Performance History snapshots
        history = data.get("performance_history", [])
        if len(history) > 1:
            print(f"\n{Fore.WHITE}{Style.BRIGHT}--- HISTORICAL PERFORMANCE (Last 5 Snapshots) ---{Style.RESET_ALL}")
            for snap in history[-5:]:
                val = snap["total_value"]
                print(f"  • {snap['timestamp']}: Net Worth = ${val:,.2f} | Unrealized = ${snap['unrealized_pnl']:+,.2f}")

    def buy_stock_flow(self):
        """Interactive buy order workflow."""
        print(f"\n{Fore.WHITE}{Style.BRIGHT}--- BUY STOCK ---{Style.RESET_ALL}")
        sym = input("Enter stock symbol to BUY: ").strip().upper()
        stock = self.engine.market.get_stock(sym)
        if not stock:
            print(f"{Fore.RED}Stock '{sym}' does not exist!{Style.RESET_ALL}")
            return

        avail_cash = self.engine.active_user.portfolio.cash
        max_shares = int(avail_cash // stock.price)

        print(f"\nTicker: {Fore.YELLOW}{stock.symbol} ({stock.name}){Style.RESET_ALL}")
        print(f"Current Ask Price: ${stock.price:.2f}")
        print(f"Your Available Cash: ${avail_cash:,.2f}")
        print(f"Max Affordable Shares: {Fore.CYAN}{max_shares} shares{Style.RESET_ALL}")

        if max_shares <= 0:
            print(f"{Fore.RED}You do not have enough cash to buy even 1 share of {sym}.{Style.RESET_ALL}")
            return

        qty_input = input(f"Enter quantity of shares to buy (1 - {max_shares}): ").strip()
        try:
            qty = int(qty_input)
            if qty <= 0:
                print(f"{Fore.RED}Quantity must be at least 1.{Style.RESET_ALL}")
                return
        except ValueError:
            print(f"{Fore.RED}Invalid quantity.{Style.RESET_ALL}")
            return

        total_cost = qty * stock.price
        confirm = input(f"Confirm purchase of {qty} {sym} for ${total_cost:,.2f}? (y/N): ").strip().lower()
        if confirm == 'y':
            success, msg, tx = self.engine.buy_stock(sym, qty)
            if success:
                print(f"{Fore.GREEN}{Style.BRIGHT}[OK] SUCCESS: {msg}{Style.RESET_ALL}")
                print(f"Transaction ID: {tx.id} | Remaining Cash: ${self.engine.active_user.portfolio.cash:,.2f}")
            else:
                print(f"{Fore.RED}[FAILED] FAILED: {msg}{Style.RESET_ALL}")
        else:
            print("Purchase cancelled.")

    def sell_stock_flow(self):
        """Interactive sell order workflow."""
        print(f"\n{Fore.WHITE}{Style.BRIGHT}--- SELL STOCK ---{Style.RESET_ALL}")
        holdings = self.engine.active_user.portfolio.holdings
        if not holdings:
            print(f"{Fore.YELLOW}You currently have no open stock positions to sell.{Style.RESET_ALL}")
            return

        print("Your Active Positions:")
        for sym, h in holdings.items():
            stk = self.engine.market.get_stock(sym)
            cur_price = stk.price if stk else h.average_cost
            print(f"  • {sym}: {h.quantity} shares (Avg Cost: ${h.average_cost:.2f} | Current Price: ${cur_price:.2f})")

        sym = input("\nEnter symbol to SELL: ").strip().upper()
        if sym not in holdings:
            print(f"{Fore.RED}You do not own any shares of {sym}!{Style.RESET_ALL}")
            return

        holding = holdings[sym]
        stock = self.engine.market.get_stock(sym)
        cur_price = stock.price if stock else holding.average_cost

        qty_input = input(f"Enter quantity of shares to sell (1 - {holding.quantity}): ").strip()
        try:
            qty = int(qty_input)
            if qty <= 0 or qty > holding.quantity:
                print(f"{Fore.RED}Invalid quantity. You own {holding.quantity} shares.{Style.RESET_ALL}")
                return
        except ValueError:
            print(f"{Fore.RED}Invalid number entered.{Style.RESET_ALL}")
            return

        gross_proceeds = qty * cur_price
        est_cost_basis = qty * holding.average_cost
        est_gain = gross_proceeds - est_cost_basis

        gain_str = f"{Fore.GREEN}+${est_gain:,.2f}" if est_gain >= 0 else f"{Fore.RED}-${abs(est_gain):,.2f}"
        print(f"\nEstimated Proceeds: ${gross_proceeds:,.2f}")
        print(f"Estimated Realized P&L: {gain_str}{Style.RESET_ALL}")

        confirm = input(f"Confirm selling {qty} {sym}? (y/N): ").strip().lower()
        if confirm == 'y':
            success, msg, tx = self.engine.sell_stock(sym, qty)
            if success:
                print(f"{Fore.GREEN}{Style.BRIGHT}[OK] SUCCESS: {msg}{Style.RESET_ALL}")
                print(f"Transaction ID: {tx.id} | Updated Cash: ${self.engine.active_user.portfolio.cash:,.2f}")
            else:
                print(f"{Fore.RED}[FAILED] FAILED: {msg}{Style.RESET_ALL}")
        else:
            print("Sale cancelled.")

    def show_transactions(self):
        """Displays transaction audit history."""
        self.print_banner()
        txs = self.engine.active_user.portfolio.transactions
        print(f"\n{Fore.WHITE}{Style.BRIGHT}--- TRANSACTION AUDIT LEDGER ({len(txs)} records) ---{Style.RESET_ALL}")
        if not txs:
            print("  No transactions executed yet.")
            return

        hdr = f"{'TX ID':<10} {'TIMESTAMP':<20} {'TYPE':<6} {'SYMBOL':<8} {'QUANTITY':>8} {'PRICE':>10} {'TOTAL':>12}"
        print(f"{Fore.CYAN}{hdr}{Style.RESET_ALL}")
        print("-" * 80)
        for t in reversed(txs):
            color = Fore.GREEN if t.transaction_type.value == "BUY" else Fore.MAGENTA
            print(
                f"{t.id:<10} "
                f"{t.timestamp:<20} "
                f"{color}{t.transaction_type.value:<6}{Style.RESET_ALL} "
                f"{Fore.YELLOW}{t.symbol:<8}{Style.RESET_ALL} "
                f"{t.quantity:>8} "
                f"${t.price_per_share:>9.2f} "
                f"${t.total_amount:>11.2f}"
            )
        print("-" * 80)

    def advance_market_simulation(self):
        """Advances market simulation and displays price changes."""
        print(f"\n{Fore.WHITE}{Style.BRIGHT}--- ADVANCE MARKET SIMULATION ---{Style.RESET_ALL}")
        print("1. Tick Market (1 Step)")
        print("2. Advance Market (5 Steps)")
        print("3. Change Market Sentiment (Bullish / Bearish / Volatile / Neutral)")
        choice = input("Select an option (1-3): ").strip()

        if choice == '1':
            self.engine.tick_market(1)
            print(f"{Fore.GREEN}[OK] Market advanced 1 step. Prices updated!{Style.RESET_ALL}")
            self.show_market_overview()
        elif choice == '2':
            self.engine.tick_market(5)
            print(f"{Fore.GREEN}[OK] Market advanced 5 steps!{Style.RESET_ALL}")
            self.show_market_overview()
        elif choice == '3':
            print("\nAvailable Regimes:")
            print("  [B]ullish   - Upward trending market drift (+0.65%/tick)")
            print("  [S]elloff   - Bearish market drift (-0.65%/tick)")
            print("  [V]olatile  - High volatility regime (wide swings)")
            print("  [N]eutral   - Standard random walk")
            regime = input("Choose sentiment (B/S/V/N): ").strip().upper()
            mapping = {"B": "bullish", "S": "bearish", "V": "volatile", "N": "neutral"}
            if regime in mapping:
                self.engine.set_market_sentiment(mapping[regime])
                print(f"{Fore.GREEN}[OK] Market sentiment updated to: {mapping[regime].upper()}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Invalid selection.{Style.RESET_ALL}")

    def deposit_cash_flow(self):
        """Funds deposit workflow."""
        print(f"\n{Fore.WHITE}{Style.BRIGHT}--- DEPOSIT FUNDS ---{Style.RESET_ALL}")
        amt_str = input("Enter deposit amount ($): ").strip()
        try:
            amt = float(amt_str)
            success, msg = self.engine.deposit_cash(amt)
            if success:
                print(f"{Fore.GREEN}[OK] {msg}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}[FAILED] {msg}{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Invalid dollar amount.{Style.RESET_ALL}")

    def export_import_flow(self):
        """Data persistence JSON export/import."""
        print(f"\n{Fore.WHITE}{Style.BRIGHT}--- FILE I/O & DATA PERSISTENCE ---{Style.RESET_ALL}")
        print("1. Export Portfolio & Transactions to JSON")
        print("2. Import Portfolio from JSON")
        opt = input("Choose (1/2): ").strip()

        if opt == '1':
            default_path = f"data/{self.engine.active_user.username}_portfolio.json"
            path = input(f"File path [{default_path}]: ").strip() or default_path
            success, msg = self.engine.export_data(path)
            if success:
                print(f"{Fore.GREEN}[OK] {msg}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}[FAILED] {msg}{Style.RESET_ALL}")
        elif opt == '2':
            path = input("Enter JSON file path to import: ").strip()
            success, msg = self.engine.import_data(path)
            if success:
                print(f"{Fore.GREEN}[OK] {msg}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}[FAILED] {msg}{Style.RESET_ALL}")

    def switch_user_flow(self):
        """Switch active trader profile."""
        print(f"\n{Fore.WHITE}{Style.BRIGHT}--- SWITCH / CREATE USER ---{Style.RESET_ALL}")
        current_users = self.engine.db.list_users()
        if current_users:
            print("Existing Users:")
            for u in current_users:
                print(f"  • {u['username']} ({u['display_name']})")
        uname = input("\nEnter username to switch to or create: ").strip().lower()
        if uname:
            self.engine.set_active_user(uname)
            print(f"{Fore.GREEN}[OK] Switched to user: {self.engine.active_user.display_name}{Style.RESET_ALL}")

    def run(self):
        """Main terminal interaction loop."""
        while True:
            self.print_banner()
            print("\n  [1] Live Market Overview & Quotes")
            print("  [2] Stock Deep Dive (Details & Spread)")
            print("  [3] Portfolio Performance & Holdings")
            print("  [4] Buy Stock (Market Order)")
            print("  [5] Sell Stock (Market Order)")
            print("  [6] Transaction Audit History")
            print("  [7] Advance Market Simulation (Tick Engine)")
            print("  [8] Deposit Cash")
            print("  [9] Data Persistence (Export/Import JSON)")
            print("  [U] Switch / Create User Account")
            print("  [Q] Exit")

            choice = input(f"\n{Fore.CYAN}Select option (1-9, U, Q): {Style.RESET_ALL}").strip().upper()

            if choice == '1':
                self.show_market_overview()
                input(f"\n{Fore.CYAN}Press Enter to return to menu...{Style.RESET_ALL}")
            elif choice == '2':
                self.show_stock_details()
                input(f"\n{Fore.CYAN}Press Enter to return to menu...{Style.RESET_ALL}")
            elif choice == '3':
                self.show_portfolio_summary()
                input(f"\n{Fore.CYAN}Press Enter to return to menu...{Style.RESET_ALL}")
            elif choice == '4':
                self.buy_stock_flow()
                input(f"\n{Fore.CYAN}Press Enter to return to menu...{Style.RESET_ALL}")
            elif choice == '5':
                self.sell_stock_flow()
                input(f"\n{Fore.CYAN}Press Enter to return to menu...{Style.RESET_ALL}")
            elif choice == '6':
                self.show_transactions()
                input(f"\n{Fore.CYAN}Press Enter to return to menu...{Style.RESET_ALL}")
            elif choice == '7':
                self.advance_market_simulation()
                input(f"\n{Fore.CYAN}Press Enter to return to menu...{Style.RESET_ALL}")
            elif choice == '8':
                self.deposit_cash_flow()
                input(f"\n{Fore.CYAN}Press Enter to return to menu...{Style.RESET_ALL}")
            elif choice == '9':
                self.export_import_flow()
                input(f"\n{Fore.CYAN}Press Enter to return to menu...{Style.RESET_ALL}")
            elif choice == 'U':
                self.switch_user_flow()
                input(f"\n{Fore.CYAN}Press Enter to return to menu...{Style.RESET_ALL}")
            elif choice in ('Q', 'EXIT'):
                print(f"\n{Fore.YELLOW}Exiting Quantum Trade Terminal. Good day!{Style.RESET_ALL}\n")
                break
            else:
                print(f"{Fore.RED}Invalid option selected.{Style.RESET_ALL}")
