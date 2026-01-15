from src.backtester.trading.signal_handler import SignalHandler
from src.trading_engine.core.signal import Signal
from src.trading_engine.core.enums import Direction
from decimal import Decimal


def test_entry_opens_position(
    mock_builder,
    mock_manager,
    mock_logger,
):
    handler = SignalHandler(mock_manager, mock_builder, mock_logger)

    signal = Signal.entry(
        source="STRATEGY",
        direction=Direction.LONG,
        entry_price=Decimal("100"),  # 100,
        volume=Decimal("10"),
        take_profits=[],
        stop_losses=[],
    )

    positions = {}
    bar = [0, 0, 0, 100]

    positions = handler.handle(signal, positions, bar)

    assert len(positions) == 1
