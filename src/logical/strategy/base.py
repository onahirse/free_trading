"""Базовый класс стратегии (BaseStrategy).

Содержит реализацию `run` и сохраняет параметры, важные для live-торговли.
Метод `can_execute` делегирует проверку модулю `validators`.
"""
from typing import List, Any, Dict, Optional
from decimal import Decimal
import pandas as pd

from src.trading_engine.core.signal import Signal
from src.trading_engine.core.enums import Direction
from src.utils.logger import get_logger

from .types import Condition
from . import validators

logger = get_logger(__name__)


class BaseStrategy:
    def __init__(self, name: str = "base_strategy"):
        self.name = name
        self.conditions: List[Condition] = []
        # Параметры, важные для live-торговли
        self.live_enabled: bool = False
        self.dry_run: bool = True
        self.max_risk_fraction: float = 0.02
        self.max_notional: Optional[Decimal] = None
        self.allowed_symbols: Optional[List[str]] = None

    # -----------------
    # Управление условиями
    # -----------------
    def add_condition(self, cond: Condition) -> None:
        self.conditions.append(cond)

    def insert_condition(self, index: int, cond: Condition) -> None:
        self.conditions.insert(index, cond)

    def remove_condition(self, cond: Condition) -> None:
        try:
            self.conditions.remove(cond)
        except ValueError:
            logger.debug("Попытка удалить несуществующее условие из стратегии")

    def clear_conditions(self) -> None:
        self.conditions.clear()

    # -----------------
    # Исполнение стратегии
    # -----------------
    def run(self, data: Any, positions: List[Any], trading_context: Optional[Dict[str, Any]] = None) -> Signal:
        # Преобразуем вход в DataFrame, если нужно
        if isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            try:
                data_values = data[:, :-1]
                timestamps = data[:, -1]
                df = pd.DataFrame(data_values, columns=["open", "high", "low", "close"])
                df.index = pd.to_datetime(timestamps)
            except Exception as e:
                logger.error(f"Невозможно привести data к DataFrame: {e}")
                return Signal.no_signal(source=self.name)

        ctx: Dict[str, Any] = {}
        ctx['positions'] = positions
        if trading_context is not None:
            ctx['trading_context'] = trading_context

        for cond in self.conditions:
            try:
                result = cond(df, ctx)
            except Exception as e:
                logger.exception(f"Ошибка в условии стратегии {self.name}: {e}")
                return Signal.no_signal(source=self.name)

            ok = bool(result)
            if not ok:
                logger.debug(f"Условие {getattr(cond, '__name__', str(cond))} не выполнено")
                return Signal.no_signal(source=self.name)

        try:
            entry_price = Decimal(str(df['close'].iloc[-1]))
        except Exception:
            logger.error("Не удалось взять цену закрытия для формирования сигнала")
            return Signal.no_signal(source=self.name)

        volume = ctx.get('volume') or Decimal('0')
        tps = ctx.get('take_profits') or []
        sls = ctx.get('stop_losses') or []
        direction = ctx.get('direction') or Direction.LONG

        signal = Signal.entry(
            direction=direction,
            entry_price=entry_price,
            volume=volume,
            take_profits=tps,
            stop_losses=sls,
            source=self.name,
            metadata=ctx.get('metadata', {}),
        )

        signal.metadata.setdefault('strategy_live', {})
        signal.metadata['strategy_live'].update({
            'live_enabled': self.live_enabled,
            'dry_run': self.dry_run,
            'max_risk_fraction': float(self.max_risk_fraction),
            'max_notional': float(self.max_notional) if self.max_notional is not None else None,
        })

        return signal

    def can_execute(self, signal: Signal, positions: List[Any], trading_context: Optional[Dict[str, Any]] = None):
        return validators.can_execute(self, signal, positions, trading_context)


__all__ = ['BaseStrategy']
