"""
Market Simulator Engine
Simulates real-time market dynamics, stochastic pricing algorithms,
sector movements, sentiment regimes, and benchmark indices.
"""

import random
from typing import Dict, List, Any, Optional, Callable
from models.stock import Stock


class MarketSimulator:
    """
    Simulates a live stock exchange with continuous price discovery,
    sentiment regimes (Bullish, Bearish, Volatile, Neutral),
    and aggregate market metrics.
    """

    SENTIMENT_PROFILES = {
        "neutral": {"drift": 0.0003, "vol_mult": 1.0, "label": "Neutral / Steady"},
        "bullish": {"drift": 0.0065, "vol_mult": 1.1, "label": "Bullish / Rally"},
        "bearish": {"drift": -0.0065, "vol_mult": 1.3, "label": "Bearish / Selloff"},
        "volatile": {"drift": 0.0000, "vol_mult": 2.5, "label": "High Volatility"},
    }

    def __init__(self):
        self.stocks: Dict[str, Stock] = {}
        self.sentiment: str = "neutral"
        self.tick_count: int = 0
        self.listeners: List[Callable[[Dict[str, Stock]], None]] = []
        self._seed_default_stocks()

    def _seed_default_stocks(self) -> None:
        """Seeds a diverse portfolio of marquee stocks across major market sectors."""
        seeds = [
            ("AAPL", "Apple Inc.", "Technology", 228.50, 0.016),
            ("NVDA", "NVIDIA Corporation", "Semiconductors", 124.80, 0.032),
            ("MSFT", "Microsoft Corp.", "Technology", 432.10, 0.015),
            ("GOOGL", "Alphabet Inc.", "Communication", 168.40, 0.018),
            ("AMZN", "Amazon.com Inc.", "Consumer Cyclical", 186.75, 0.021),
            ("TSLA", "Tesla Inc.", "Automotive", 242.30, 0.038),
            ("JPM", "JPMorgan Chase & Co.", "Financial", 215.60, 0.014),
            ("JNJ", "Johnson & Johnson", "Healthcare", 162.20, 0.011),
            ("XOM", "Exxon Mobil Corp.", "Energy", 118.90, 0.017),
            ("AMD", "Advanced Micro Devices", "Semiconductors", 154.20, 0.030),
            ("NFLX", "Netflix Inc.", "Entertainment", 685.40, 0.024),
            ("DIS", "The Walt Disney Co.", "Entertainment", 96.80, 0.019),
        ]

        for sym, name, sector, price, vol in seeds:
            self.stocks[sym] = Stock(
                symbol=sym,
                name=name,
                sector=sector,
                initial_price=price,
                volatility=vol,
            )

    def set_sentiment(self, sentiment: str) -> bool:
        """Sets the market sentiment regime."""
        norm = sentiment.lower().strip()
        if norm in self.SENTIMENT_PROFILES:
            self.sentiment = norm
            return True
        return False

    def add_stock(self, stock: Stock) -> None:
        """Adds or updates a stock in the simulated exchange."""
        self.stocks[stock.symbol] = stock

    def get_stock(self, symbol: str) -> Optional[Stock]:
        """Fetches a stock by ticker symbol."""
        return self.stocks.get(symbol.upper())

    def get_all_stocks(self) -> List[Stock]:
        """Returns all listed stocks."""
        return list(self.stocks.values())

    def tick(self) -> Dict[str, float]:
        """
        Advances the market by one discrete simulation tick.
        Calculates stochastic price movements for all stocks based on sentiment.
        """
        self.tick_count += 1
        profile = self.SENTIMENT_PROFILES.get(self.sentiment, self.SENTIMENT_PROFILES["neutral"])
        base_drift = profile["drift"]

        updated_prices = {}
        for sym, stock in self.stocks.items():
            # Add sector-level correlation
            sector_factor = random.gauss(0, 0.003)
            effective_sentiment = base_drift + sector_factor
            
            # Temporary volatility scaling if high volatility regime
            orig_vol = stock.volatility
            stock.volatility = orig_vol * profile["vol_mult"]
            
            new_price = stock.update_price(market_sentiment=effective_sentiment)
            stock.volatility = orig_vol
            updated_prices[sym] = new_price

        # Notify any subscribed listeners (e.g. portfolio updater)
        for listener in self.listeners:
            try:
                listener(self.stocks)
            except Exception:
                pass

        return updated_prices

    def add_tick_listener(self, callback: Callable[[Dict[str, Stock]], None]) -> None:
        """Registers a callback to be notified on every market tick."""
        self.listeners.append(callback)

    def get_market_summary(self) -> Dict[str, Any]:
        """
        Generates aggregate market statistics (Gainers, Losers, Market Index).
        """
        stocks_list = list(self.stocks.values())
        if not stocks_list:
            return {}

        sorted_by_change = sorted(stocks_list, key=lambda s: s.change_percent, reverse=True)
        top_gainers = [s.to_dict(include_history=False) for s in sorted_by_change[:3] if s.change_percent > 0]
        top_losers = [s.to_dict(include_history=False) for s in sorted_by_change[-3:] if s.change_percent < 0]
        top_losers.reverse()

        # Compute Composite Market Index (equal-weighted average performance)
        avg_change_pct = sum(s.change_percent for s in stocks_list) / len(stocks_list)
        total_market_volume = sum(s.volume for s in stocks_list)

        return {
            "tick_count": self.tick_count,
            "sentiment": self.sentiment,
            "sentiment_label": self.SENTIMENT_PROFILES.get(self.sentiment, {}).get("label", "Neutral"),
            "market_index_change_percent": round(avg_change_pct, 2),
            "total_volume": total_market_volume,
            "top_gainers": top_gainers,
            "top_losers": top_losers,
            "stocks_count": len(stocks_list),
        }
