from src.backtester.trading.signal_handler import SignalHandler
from src.trading_engine.core.signal import Signal
from src.trading_engine.core.enums import Direction, SignalType
try:
    from src.tests.mocks.mock_position import MockPosition
except ImportError:
    from tests.mocks.mock_position import MockPosition
from decimal import Decimal


def test_hedge_open(
    mock_builder,
    mock_manager,
    mock_logger,
):
    """
    Тест: HEDGE_OPEN создает хедж-позицию
    """
    handler = SignalHandler(mock_manager, mock_builder, mock_logger)

    pos1 = MockPosition(
        direction=Direction.LONG,
        source="STRATEGY",
        price=Decimal("100")
    )
    
    positions = {pos1.id: pos1}

    signal = Signal.hadge_entry(
        direction=Direction.SHORT,
        entry_price=Decimal("100"),
        volume=Decimal("10"),
        take_profits=[],
        stop_losses=[],
        source="ALS",        
        metadata={"is_hedge": True},
    )

    bar = [0, 0, 0, 100]

    positions = handler.handle(signal, positions, bar)

    assert len(positions) > 1
    hedge = list(positions.values())[-1]
    assert signal.signal_type == SignalType.HEDGE_ENTRY
    assert hedge.is_hedge is True


def test_hedge_close(
    mock_builder,
    mock_manager,
    mock_logger,
):
    handler = SignalHandler(mock_manager, mock_builder, mock_logger)

    hedge = MockPosition(direction=Direction.SHORT, source="ALS", is_hedge=True)
    positions = {hedge.id: hedge}
    

    signal = Signal(
        signal_type=SignalType.HEDGE_CLOSE,
        source="ALS",
    )

    bar = [0, 0, 0, 100]

    positions = handler.handle(signal, positions, bar)

    assert positions == {}
    assert hedge.id in mock_manager.closed
