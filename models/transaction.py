"""
Transaction Model Module
Encapsulates individual trade executions (Buy and Sell orders)
with audit details, pricing, timestamps, and fees.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class Transaction:
    """
    Represents an executed order within the trading platform.
    """

    def __init__(
        self,
        user_id: str,
        symbol: str,
        transaction_type: TransactionType | str,
        quantity: int,
        price_per_share: float,
        fee: float = 0.0,
        transaction_id: str | None = None,
        timestamp: str | None = None,
    ):
        self.id: str = transaction_id or str(uuid.uuid4())[:8].upper()
        self.user_id: str = user_id
        self.symbol: str = symbol.upper()
        
        if isinstance(transaction_type, str):
            self.transaction_type: TransactionType = TransactionType(transaction_type.upper())
        else:
            self.transaction_type = transaction_type

        self.quantity: int = int(quantity)
        self.price_per_share: float = round(float(price_per_share), 2)
        self.fee: float = round(float(fee), 2)

        # For BUY: Total outflow = (quantity * price) + fee
        # For SELL: Total inflow = (quantity * price) - fee
        gross = self.quantity * self.price_per_share
        if self.transaction_type == TransactionType.BUY:
            self.total_amount: float = round(gross + self.fee, 2)
        else:
            self.total_amount: float = round(gross - self.fee, 2)

        self.timestamp: str = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> Dict[str, Any]:
        """Converts transaction to serializable dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "transaction_type": self.transaction_type.value,
            "quantity": self.quantity,
            "price_per_share": self.price_per_share,
            "fee": self.fee,
            "total_amount": self.total_amount,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        """Instantiates transaction from serialized dictionary."""
        return cls(
            transaction_id=data["id"],
            user_id=data["user_id"],
            symbol=data["symbol"],
            transaction_type=data["transaction_type"],
            quantity=data["quantity"],
            price_per_share=data["price_per_share"],
            fee=data.get("fee", 0.0),
            timestamp=data["timestamp"],
        )

    def summary(self) -> str:
        """Formatted summary of the transaction."""
        action = "BOUGHT" if self.transaction_type == TransactionType.BUY else "SOLD"
        return (
            f"[{self.timestamp}] {action} {self.quantity} {self.symbol} @ "
            f"${self.price_per_share:.2f} (Total: ${self.total_amount:.2f})"
        )

    def __repr__(self) -> str:
        return f"<Transaction {self.id} | {self.transaction_type.value} {self.quantity}x {self.symbol} @ ${self.price_per_share:.2f}>"
