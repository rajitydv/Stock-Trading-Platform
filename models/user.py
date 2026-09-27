"""
User Model Module
Encapsulates trader identities, associated portfolios, watchlists,
and account metadata.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from models.portfolio import Portfolio


class User:
    """
    Represents an investor/trader on the platform.
    Has an encapsulated Portfolio and personal stock Watchlist.
    """

    def __init__(
        self,
        username: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        user_id: Optional[str] = None,
        created_at: Optional[str] = None,
        portfolio: Optional[Portfolio] = None,
        watchlist: Optional[List[str]] = None,
    ):
        self.user_id: str = user_id or str(uuid.uuid4())[:8]
        self.username: str = username.strip().lower()
        self.display_name: str = display_name or username.strip().capitalize()
        self.email: str = email or f"{self.username}@trading.local"
        self.created_at: str = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.portfolio: Portfolio = portfolio or Portfolio(user_id=self.user_id)
        self.watchlist: List[str] = [s.upper() for s in (watchlist or ["AAPL", "NVDA", "TSLA", "MSFT"])]

    def add_to_watchlist(self, symbol: str) -> bool:
        """Adds a symbol to user's favorites/watchlist."""
        sym = symbol.upper()
        if sym not in self.watchlist:
            self.watchlist.append(sym)
            return True
        return False

    def remove_from_watchlist(self, symbol: str) -> bool:
        """Removes a symbol from user's watchlist."""
        sym = symbol.upper()
        if sym in self.watchlist:
            self.watchlist.remove(sym)
            return True
        return False

    def to_dict(self, include_portfolio: bool = True) -> Dict[str, Any]:
        """Serializes user to dictionary."""
        data = {
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "email": self.email,
            "created_at": self.created_at,
            "watchlist": self.watchlist,
        }
        if include_portfolio:
            data["portfolio"] = self.portfolio.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Reconstructs user instance from dictionary."""
        portfolio = None
        if "portfolio" in data and isinstance(data["portfolio"], dict):
            portfolio = Portfolio.from_dict(data["portfolio"])

        return cls(
            username=data["username"],
            display_name=data.get("display_name"),
            email=data.get("email"),
            user_id=data.get("user_id"),
            created_at=data.get("created_at"),
            portfolio=portfolio,
            watchlist=data.get("watchlist", []),
        )

    def __repr__(self) -> str:
        return f"<User {self.username} (ID: {self.user_id})>"
