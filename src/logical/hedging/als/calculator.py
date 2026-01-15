# total ROI
# src/als/calculator.py

from decimal import Decimal


def calculate_roi(entry_price: Decimal, current_price: Decimal, direction: str) -> Decimal:
    if direction == "LONG":
        return (current_price - entry_price) / entry_price * Decimal("100")
    else:
        return (entry_price - current_price) / entry_price * Decimal("100")
