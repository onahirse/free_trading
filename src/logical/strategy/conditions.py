"""Набор простых условий (Condition helpers) для стратегий."""
from decimal import Decimal
from typing import Dict
import pandas as pd

from .types import Condition


def min_bars_condition(min_bars: int) -> Condition:
    """Условие: в данных должно быть не менее `min_bars` баров."""

    def _cond(df: pd.DataFrame, ctx: Dict[str, object]) -> bool:
        return len(df) >= min_bars

    _cond.__name__ = f"min_bars_{min_bars}"
    return _cond


def close_above_ma_condition(period: int) -> Condition:
    """Условие: закрытие выше скользящей средней с указанным периодом."""

    def _cond(df: pd.DataFrame, ctx: Dict[str, object]) -> bool:
        if len(df) < period:
            return False
        ma = df['close'].rolling(period).mean()
        ok = df['close'].iloc[-1] > ma.iloc[-1]
        ctx['ma'] = float(ma.iloc[-1])
        return bool(ok)

    _cond.__name__ = f"close_above_ma_{period}"
    return _cond


def example_set_volume(volume: Decimal) -> Condition:
    """Простое условие, которое всегда возвращает True и задаёт объём в контексте."""

    def _cond(df: pd.DataFrame, ctx: Dict[str, object]) -> bool:
        ctx['volume'] = volume
        return True

    _cond.__name__ = f"set_volume_{volume}"
    return _cond


__all__ = [
    'min_bars_condition',
    'close_above_ma_condition',
    'example_set_volume',
]
