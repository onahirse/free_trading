"""Адаптер стратегии ZigZag + Fibonacci к BaseStrategy.

Этот модуль предоставляет класс `ZigZagFiboStrategy`, который является обёрткой
над существующей реализацией `zigzag_and_fibo` и совместим с `BaseStrategy`
и системой бэктестинга/валидаторов.

Особенности:
- не трогает исходный `zigzag_and_fibo.py` — использует его функции `calculate_indicators`
- возвращает объект `Signal` совместимый с остальной системой
- поддерживает `trading_context` и отдаёт в `Signal.metadata` информацию о стратегии
- использует `RiskManager` для расчёта объёма (как в оригинале)

Пример использования:

    from src.logical.strategy.zigzag_fibo.zigzag_fibo_strategy import ZigZagFiboStrategy
    strategy = ZigZagFiboStrategy(coin)
    signal = strategy.run(data_numpy, positions, trading_context={...})

"""

from typing import List, Any, Optional
from decimal import Decimal
import pandas as pd

from src.trading_engine.core.signal import Signal
from src.trading_engine.core.enums import Direction
from src.utils.logger.logger import get_logger
from src.config.config import config

# Используем существующие расчёты индикаторов из оригинального модуля
from src.logical.strategy.zigzag_fibo.zigzag_and_fibo import calculate_indicators, shift_timestamp
from src.logical.strategy.risk_manager.risk_manager import RiskManager

from src.logical.strategy.base import BaseStrategy

logger = get_logger(__name__)


class ZigZagFiboStrategy(BaseStrategy):
    """Стратегия ZigZag + Fibonacci, адаптированная под BaseStrategy API."""

    def __init__(self, coin: dict):
        super().__init__(name=config.get_setting("STRATEGY_SETTINGS", "STRATEGY_NAME") or "zigzag_fibo")
        self.coin = coin
        self.symbol = (coin.get("SYMBOL") or "").upper() + "/USDT"
        self.timeframe = coin.get("TIMEFRAME") or "1"
        self.allowed_min_bars = config.get_setting("STRATEGY_SETTINGS", "MINIMUM_BARS_FOR_STRATEGY_CALCULATION") or 0
        self.ALLOWED_Z2_OFFSET = config.get_setting("STRATEGY_SETTINGS", "Z2_INDEX_OFFSET") or 0
        # risk manager как у оригинальной стратегии
        self.risk_manager = RiskManager(coin)

    def run(self, data: Any, positions: List[Any], trading_context: Optional[dict] = None) -> Signal:
        """Запуск стратегии — возвращает Signal (entry / no_signal).

        Ожидает `data` как numpy-массив (open, high, low, close, timestamp) или pandas.DataFrame.
        """

        # ? Если есть открытые позиции не отправляем сигнал
        if len(positions) > 0:
            logger.debug("ZigZagFiboStrategy: уже есть открытые позиции, сигнал не генерируется")
            return Signal.no_signal(source=self.name)
        
        # Приведение к DataFrame (как в оригинале)
        if isinstance(data, pd.DataFrame):
            data_df = data.copy()
        else:
            try:
                data_values = data[:, :-1]
                timestamps = data[:, -1]
                data_df = pd.DataFrame(data_values, columns=["open", "high", "low", "close"])
                data_df.index = pd.to_datetime(timestamps)
            except Exception as e:
                logger.error(f"ZigZagFiboStrategy: невозможно привести data к DataFrame: {e}")
                return Signal.no_signal(source=self.name)

        # Минимальное количество баров
        if len(data_df) < int(self.allowed_min_bars):
            logger.debug("Недостаточно баров для расчёта стратегии ZigZagFibo")
            return Signal.no_signal(source=self.name)

        # Рассчитываем индикаторы
        zigzag, fiboLev = calculate_indicators(data_df, self.coin)
        if zigzag is None or fiboLev is None:
            return Signal.no_signal(source=self.name)

        direction_zigzag = zigzag["direction"]
        z2_index = zigzag["z2_index"]

        # текущая цена — последний close
        entry_price = Decimal(str(data_df['close'].iloc[-1]))
        volume = self.risk_manager.calculate_position_size(entry_price)

        current_index = pd.Timestamp(data_df.index[-1])

        allowed_shifted = shift_timestamp(current_index, int(self.ALLOWED_Z2_OFFSET), self.timeframe, direction=-1)
        if not (z2_index == current_index or z2_index == allowed_shifted):
            logger.debug(f"ZigZagFibo: z2_index {z2_index} not in allowed window (current {current_index})")
            return Signal.no_signal(source=self.name)

        direction = None
        # Проверки по Fib level (используем уровень 78.6 как в оригинале)
        lvl = fiboLev.get(78.6)
        if lvl is None:
            logger.debug("ZigZagFibo: уровень 78.6 отсутствует в расчётах фибоначчи")
            return Signal.no_signal(source=self.name)

        level_price = lvl['level_price']

        if direction_zigzag == -1:
            # сигнал на LONG
            if float(entry_price) < float(level_price):
                direction = Direction.LONG
            else:
                return Signal.no_signal(source=self.name)

        if direction_zigzag == 1:
            # сигнал на SHORT
            if float(entry_price) > float(level_price):
                direction = Direction.SHORT
            else:
                return Signal.no_signal(source=self.name)

        if direction is None:
            return Signal.no_signal(source=self.name)

        # Собираем TP/SL как в оригинале
        tps = []
        sls = []
        for value in fiboLev.values():
            info = {"price": value['level_price'], "volume": value.get('volume')}
            if value.get('tp'):
                if value.get('tp_to_break'):
                    info['tp_to_break'] = True
                tps.append(info)
            if value.get('sl'):
                sls.append(info)

        signal = Signal.entry(
            direction=direction,
            entry_price=entry_price,
            volume=volume,
            take_profits=tps,
            stop_losses=sls,
            source=self.name,
            metadata={"z2_index": z2_index},
        )

        # Проставим информацию для валидаторов
        signal.metadata.setdefault('strategy_live', {})
        signal.metadata['strategy_live'].update({
            'live_enabled': self.live_enabled,
            'dry_run': self.dry_run,
        })

        return signal
