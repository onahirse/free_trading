from decimal import Decimal
from src.trading_engine.core.signal import Signal
from src.trading_engine.core.enums import Direction, SignalType


def test_no_signal():
    """ Пустой сигнал - стратегия ничего не делает """
    s = Signal.no_signal("STRATEGY")
    assert s.signal_type == SignalType.NO_SIGNAL
    assert s.is_no_signal()


def test_entry_signal():
    """ Сигнал входа в позицию """
    s = Signal.entry(
        source="STRATEGY",
        direction=Direction.LONG,
        entry_price=Decimal("100"),
        volume=Decimal("10"),
        take_profits=[],
        stop_losses=[],
    )

    assert s.signal_type == SignalType.ENTRY
    assert s.direction == Direction.LONG
    assert s.price == Decimal("100")
    assert s.volume == Decimal("10")
    assert s.source == "STRATEGY"

def test_close_signal():
    """ Сигнал закрытия позиции """
    s = Signal.close(
        source="STRATEGY",
        metadata={"info": "close"},
    )

    assert s.signal_type == SignalType.CLOSE
    assert s.source == "STRATEGY"
    assert s.metadata == {"info": "close"}

def test_close_all_signal():
    """ Сигнал закрытия позиции """
    s = Signal.close_all(
        source="STRATEGY",
        metadata={"info": "close_all"},
    )

    assert s.signal_type == SignalType.CLOSE_ALL
    assert s.source == "STRATEGY"
    assert s.metadata == {"info": "close_all"}

def test_hedge_open_signal():
    """ Сигнал входа в хедж-позицию """
    s = Signal.hadge_entry(
        direction=Direction.SHORT,
        entry_price=Decimal("100"),
        volume=Decimal("10"),
        take_profits=[],
        stop_losses=[],
        source="headge",
        metadata={"is_hedge": True},
    )

    assert s.signal_type == SignalType.HEDGE_ENTRY
    assert s.direction == Direction.SHORT
    assert s.source == "headge"
    assert s.metadata == {"is_hedge": True}
    
