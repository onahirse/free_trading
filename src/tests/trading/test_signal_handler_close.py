from src.backtester.trading.signal_handler import SignalHandler
from src.trading_engine.core.signal import Signal
from src.trading_engine.core.enums import Direction, SignalType
from decimal import Decimal
from unittest.mock import Mock

from src.tests.mocks.mock_position import MockPosition


def test_exit_closes_all_positions():
    """EXIT signal должен закрывать все позиции одного источника.

    Тест самодостаточный: создаём MockPosition, оборачиваем в словарь
    и передаём в SignalHandler вместе с простыми мок-объектами менеджера/билдера/логгера.
    """
    handler = SignalHandler(Mock(), Mock(), Mock())

    # Создаём тестовую позицию
    pos = MockPosition(
        direction=Direction.LONG,
        source="STRATEGY",
        is_hedge=False,
        price=Decimal("100")
    )

    positions = {pos.id: pos}

    # Создаём EXIT сигнал
    signal = Signal(
        signal_type=SignalType.CLOSE_ALL,
        source="STRATEGY"
    )

    bar = [0, 0, 0, Decimal("100")]

    result = handler.handle(signal, positions, bar)

    assert isinstance(result, dict)
    assert pos.id not in result
    assert len(result) == 0
    
# TODO закртие позиции по рынку определенной стратегии сигнала