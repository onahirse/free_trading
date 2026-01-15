"""Валидации и проверки пригодности сигнала для live-торговли.

Здесь реализована логика, которая раньше была в `BaseStrategy.can_execute`.
Перенос в отдельный модуль позволяет легко заменять/расширять набор проверок
без изменения базового класса стратегии.
"""
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple

from src.trading_engine.core.signal import Signal


def can_execute(
    strategy,
    signal: Signal,
    positions: list,
    trading_context: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """Проверяет, можно ли отправлять `signal` в рынок при live-торговле.

    Возвращает (True, 'ok') или (False, reason).
    """
    if not getattr(strategy, 'live_enabled', False):
        return False, "strategy_live_disabled"

    if getattr(strategy, 'dry_run', True):
        return False, "dry_run_enabled"

    meta_symbol = None
    if trading_context is not None:
        meta_symbol = trading_context.get('symbol')

    allowed_symbols = getattr(strategy, 'allowed_symbols', None)
    if allowed_symbols is not None and meta_symbol is not None:
        if meta_symbol not in allowed_symbols:
            return False, f"symbol_not_allowed:{meta_symbol}"

    # Проверка баланса/риска
    if trading_context is not None:
        balance = trading_context.get('available_balance') or trading_context.get('balance')
        try:
            if balance is not None and signal.price is not None and signal.volume is not None:
                notional = Decimal(str(signal.price)) * Decimal(str(signal.volume))
                max_notional = getattr(strategy, 'max_notional', None)
                if max_notional is not None and notional > Decimal(str(max_notional)):
                    return False, "notional_exceeds_max_notional"
                max_risk_fraction = getattr(strategy, 'max_risk_fraction', 0.0)
                if balance is not None:
                    bal = Decimal(str(balance))
                    max_allowed = bal * Decimal(str(max_risk_fraction))
                    if notional > max_allowed:
                        return False, "notional_exceeds_max_risk_fraction"
        except Exception:
            return False, "validation_error"

    return True, "ok"


__all__ = ['can_execute']
