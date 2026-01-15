"""Шаблон расширяемой стратегии для бэктестинга.

Этот модуль предоставляет лёгкий базовый класс `BaseStrategy` и вспомогательные
инструменты для построения стратегий как последовательности условий (rules).
Идея: не редактировать существующие стратегии — вместо этого писать новые
стратегии как набор условных правил или унаследовать `BaseStrategy`.

Главные возможности:
- хранение списка условий (condition functions) с возможностью добавлять/удалять
- выполнение условий в контролируемом порядке
- фабрика создания сигнала (использует класс `Signal` из проекта)
- небольшие примеры условий (пересечение уровней, минимальное количество баров)

Пример использования:

    from src.logical.strategy.strategy_template import BaseStrategy, min_bars_condition

    strategy = BaseStrategy(name="example")
    strategy.add_condition(min_bars_condition(100))

    # кастомная проверка как функция
    def price_above_ma(data_df, ctx):
        ma = data_df['close'].rolling(20).mean()
        return data_df['close'].iloc[-1] > ma.iloc[-1]

    strategy.add_condition(price_above_ma)

    signal = strategy.run(data_numpy, positions)

Файл не изменяет существующие стратегии и предназначен для включения в систему
бэктестинга как дополнительный расширяемый модуль.
"""

"""Обёртка экспорта для модульной стратегии.

Этот файл сохраняет обратную совместимость — импортируя `BaseStrategy` и
помощники из отдельных модулей `base`, `conditions` и `validators`.
"""

from .base import BaseStrategy
from .conditions import (
    min_bars_condition,
    close_above_ma_condition,
    example_set_volume,
)
from .types import Condition

__all__ = [
    'BaseStrategy',
    'Condition',
    'min_bars_condition',
    'close_above_ma_condition',
    'example_set_volume',
]

