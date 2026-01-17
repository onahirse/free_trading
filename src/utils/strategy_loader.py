"""Утилиты для динамической загрузки стратегий по пути.

Поддерживает формат строки:
- "package.module:ClassName"
- "package.module.ClassName"

Если загружаемый объект — функция, автоматически возвращается адаптер-класс.
Если класс имеет метод `run` но не `find_entry_point`, при создании экземпляра мы обеспечим
совместимость (см. backtester), но loader возвращает класс/вызовщик — инстанцирование
делает вызывающий код (TestManager).
"""
import importlib
from types import FunctionType
from typing import Any, Callable, Optional, Protocol


def load_strategy_class(path: str) -> Any:
    """Загружает класс/функцию стратегии по строковому пути.

    Возвращает объект (класс или callable). Вызов/инстанцирование делает вызывающий код.
    """
    if not path or not isinstance(path, str):
        raise ValueError("strategy path must be a string like 'module.sub:ClassName'")

    # поддерживаем оба варианта разделителя
    if ':' in path:
        module_path, obj_name = path.split(':', 1)
    else:
        parts = path.split('.')
        module_path = '.'.join(parts[:-1])
        obj_name = parts[-1]

    module = importlib.import_module(module_path)
    obj = getattr(module, obj_name)

    # если это функция — возвращаем функцию (адаптер создаст класс)
    return obj


def function_to_class_adapter(func: Callable) -> Any:
    """Преобразует функцию в класс-адаптер с интерфейсом стратегии.

    Класс имеет __init__(coin, **kwargs) и метод find_entry_point(data_slice).
    """
    class FuncStrategy:
        def __init__(self, coin: Optional[dict] = None, **kwargs):
            self.coin = coin or {}
            # некоторые адаптеры могут читать kwargs
            self._params = kwargs
            # default allowed_min_bars for compatibility
            self.allowed_min_bars = int(self._params.get('allowed_min_bars', 0))

        def find_entry_point(self, data_slice):
            # делаем простой делегат: функция должна принимать (data, positions, trading_context)
            try:
                return func(data_slice, [], None)
            except TypeError:
                # возможно функция принимает только data
                return func(data_slice)

    return FuncStrategy


class StrategyProtocol(Protocol):
    """Минимальный контракт стратегии для BacktestEngine."""

    allowed_min_bars: int

    def find_entry_point(self, data_slice):  # pragma: no cover
        ...


def resolve_strategy_class(strategy_path: str) -> type:
    """Возвращает класс стратегии по строковому пути.

    - Если по пути лежит класс — возвращает его.
    - Если по пути лежит функция/callable — возвращает класс-адаптер.
    """
    obj = load_strategy_class(strategy_path)
    if not isinstance(obj, type) and callable(obj):
        return function_to_class_adapter(obj)
    if isinstance(obj, type):
        return obj
    raise TypeError(f"Loaded strategy object from '{strategy_path}' is not a class or callable")


def ensure_find_entry_point(strategy: Any) -> Any:
    """Гарантирует наличие метода find_entry_point у экземпляра стратегии.

    Если у стратегии нет find_entry_point, но есть run(data, positions, trading_context),
    привязывает совместимый wrapper. Иначе — бросает исключение.
    """
    if hasattr(strategy, 'find_entry_point'):
        return strategy

    if not hasattr(strategy, 'run'):
        raise RuntimeError("Loaded strategy has neither find_entry_point nor run method")

    import types

    def _find_entry(self, data_slice, positions=None):
        """Wrapper для метода run, делающий его совместимым с find_entry_point API.
        
        Args:
            data_slice: данные для анализа
            positions: список открытых позиций (опционально)
        """
        if positions is None:
            positions = []
        try:
            return self.run(data_slice, positions=positions, trading_context=None)
        except TypeError:
            # возможно run ожидает только (data, positions)
            return self.run(data_slice, positions)

    strategy.find_entry_point = types.MethodType(_find_entry, strategy)
    return strategy


__all__ = [
    'load_strategy_class',
    'function_to_class_adapter',
    'resolve_strategy_class',
    'ensure_find_entry_point',
    'StrategyProtocol',
]
