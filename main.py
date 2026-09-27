import sys
import os
import argparse
import webbrowser
import unittest

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from engine.trading_engine import TradingEngine
from cli.interface import TradingCLI
from web.app import app


def run_tests():
    """Executes the test suite with verbose output."""
    print("\n" + "=" * 60)
    print(" [TESTS] RUNNING QUANTUM TRADE TEST SUITE")
    print("=" * 60 + "\n")
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


def run_cli():
    """Launches the interactive terminal UI."""
    cli = TradingCLI()
    cli.run()


def run_web(host="127.0.0.1", port=5000, open_browser=True):
    """Launches the Flask web dashboard."""
    url = f"http://{host}:{port}"
    print("\n" + "=" * 70)
    print(" [*] QUANTUM TRADE - MODERN FINANCIAL TERMINAL")
    print("=" * 70)
    print(f" * Web Dashboard URL:   {url}")
    print(f" * Mode:                 Live Stochastic Stock Simulation")
    print(f" * Database:             SQLite (data/trading_platform.db)")
    print(f" * REST API Docs:        GET {url}/api/market, GET {url}/api/portfolio")
    print("=" * 70)
    print(" Press Ctrl+C in terminal to shut down server.\n")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    app.run(host=host, port=port, debug=False)


def main():
    parser = argparse.ArgumentParser(
        description="Quantum Trade - Advanced Stock Trading Platform & Portfolio Simulator"
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Launch the interactive Command-Line Interface (CLI)",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Launch the modern Web Dashboard (default)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run comprehensive unit and integration test suite",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host interface for web server (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port for web server (default: 5000)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open default web browser when launching web mode",
    )

    args = parser.parse_args()

    if args.test:
        run_tests()
    elif args.cli:
        run_cli()
    else:
        # Default mode is web dashboard
        run_web(host=args.host, port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
