"""
Stock Model Module
Represents individual financial instruments with stochastic price movement,
historical tracking, and market quote generation.
"""

import math
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class Stock:
    """
    Represents a publicly traded stock in the simulated market.
    Implements stochastic price dynamics (Geometric Brownian Motion with drift and volatility).
    """

    def __init__(
        self,
        symbol: str,
        name: str,
        sector: str,
        initial_price: float,
        volatility: float = 0.02,
        base_drift: float = 0.0005,
        dividend_yield: float = 0.015,
        shares_outstanding: int = 10_000_000,
    ):
        self.symbol: str = symbol.upper()
        self.name: str = name
        self.sector: str = sector
        self.price: float = round(float(initial_price), 2)
        self.previous_close: float = round(float(initial_price), 2)
        self.day_open: float = round(float(initial_price), 2)
        self.day_high: float = round(float(initial_price), 2)
        self.day_low: float = round(float(initial_price), 2)
        self.volume: int = random.randint(100_000, 1_500_000)
        self.volatility: float = volatility  # Typical standard deviation of price changes
        self.base_drift: float = base_drift  # Long-term upward/downward tendency
        self.dividend_yield: float = dividend_yield
        self.shares_outstanding: int = shares_outstanding

        # Historical price points: list of dicts with {"timestamp": iso_str, "price": float, "volume": int}
        self.history: List[Dict[str, Any]] = []
        self._initialize_historical_data()

    def _initialize_historical_data(self, points: int = 30) -> None:
        """Seeds historical price data for charting when the stock is first created."""
        now = datetime.now()
        current_sim_price = self.price * 0.92  # start slightly lower in history
        
        for i in range(points, 0, -1):
            timestamp = (now - timedelta(hours=i * 2)).strftime("%Y-%m-%d %H:%M")
            # Random walk backwards/forwards
            delta = current_sim_price * random.gauss(0.0008, self.volatility * 0.75)
            current_sim_price = max(1.0, current_sim_price + delta)
            self.history.append({
                "timestamp": timestamp,
                "price": round(current_sim_price, 2),
                "volume": random.randint(50_000, 300_000),
            })
        
        # Ensure latest history point matches current price
        self.history.append({
            "timestamp": now.strftime("%Y-%m-%d %H:%M"),
            "price": self.price,
            "volume": self.volume,
        })

    def update_price(self, market_sentiment: float = 0.0) -> float:
        """
        Simulate a price tick using Geometric Brownian Motion.
        
        :param market_sentiment: Bias from broader market trend (-0.05 to +0.05)
        :return: Updated price
        """
        # Drift combines stock's inherent drift and broad market sentiment
        total_drift = self.base_drift + market_sentiment
        
        # Stochastic shock: Normal distribution N(0, 1)
        shock = random.gauss(0, 1)
        
        # Geometric Brownian Motion formula approximation:
        # P_new = P_old * exp((drift - 0.5 * sigma^2) * dt + sigma * sqrt(dt) * Z)
        # For discrete tick:
        pct_change = total_drift + (self.volatility * shock)
        
        # Occasional market micro-events (earnings rumor, news)
        if random.random() < 0.03:
            news_factor = random.choice([-1, 1]) * random.uniform(0.02, 0.05)
            pct_change += news_factor
            
        old_price = self.price
        new_price = max(0.50, round(old_price * (1.0 + pct_change), 2))
        
        self.price = new_price
        
        # Update high, low, volume
        if self.price > self.day_high:
            self.day_high = self.price
        if self.price < self.day_low:
            self.day_low = self.price
            
        trade_volume = random.randint(1_000, 35_000)
        self.volume += trade_volume
        
        # Record into history (keep last 100 points for responsiveness)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.history.append({
            "timestamp": now_str,
            "price": self.price,
            "volume": self.volume,
        })
        if len(self.history) > 100:
            self.history.pop(0)
            
        return self.price

    @property
    def change(self) -> float:
        """Absolute dollar change from previous close."""
        return round(self.price - self.previous_close, 2)

    @property
    def change_percent(self) -> float:
        """Percentage change from previous close."""
        if self.previous_close == 0:
            return 0.0
        return round(((self.price - self.previous_close) / self.previous_close) * 100.0, 2)

    @property
    def market_cap(self) -> float:
        """Market capitalization."""
        return round(self.price * self.shares_outstanding, 2)

    @property
    def bid_price(self) -> float:
        """Bid price with narrow simulated spread."""
        spread = max(0.01, round(self.price * 0.0005, 2))
        return round(self.price - (spread / 2), 2)

    @property
    def ask_price(self) -> float:
        """Ask price with narrow simulated spread."""
        spread = max(0.01, round(self.price * 0.0005, 2))
        return round(self.price + (spread / 2), 2)

    def to_dict(self, include_history: bool = True) -> Dict[str, Any]:
        """Serializes stock instance to dictionary representation."""
        data = {
            "symbol": self.symbol,
            "name": self.name,
            "sector": self.sector,
            "price": self.price,
            "previous_close": self.previous_close,
            "change": self.change,
            "change_percent": self.change_percent,
            "day_high": self.day_high,
            "day_low": self.day_low,
            "volume": self.volume,
            "volatility": self.volatility,
            "market_cap": self.market_cap,
            "bid": self.bid_price,
            "ask": self.ask_price,
        }
        if include_history:
            data["history"] = self.history
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Stock":
        """Reconstructs stock instance from a dictionary."""
        stock = cls(
            symbol=data["symbol"],
            name=data["name"],
            sector=data["sector"],
            initial_price=data.get("price", 100.0),
            volatility=data.get("volatility", 0.02),
        )
        stock.price = data.get("price", stock.price)
        stock.previous_close = data.get("previous_close", stock.previous_close)
        stock.day_high = data.get("day_high", stock.price)
        stock.day_low = data.get("day_low", stock.price)
        stock.volume = data.get("volume", stock.volume)
        if "history" in data and isinstance(data["history"], list):
            stock.history = data["history"]
        return stock

    def __repr__(self) -> str:
        return f"<Stock {self.symbol} (${self.price:.2f} | {self.change_percent:+.2f}%)>"
