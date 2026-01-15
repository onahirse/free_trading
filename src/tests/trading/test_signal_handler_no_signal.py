from src.backtester.trading.signal_handler import SignalHandler
from src.trading_engine.core.signal import Signal


def test_no_signal_does_nothing(mock_builder, mock_manager, mock_logger):
    handler = SignalHandler(mock_manager, mock_builder, mock_logger)

    positions = {}
    bar = [0, 0, 0, 100]

    result = handler.handle(Signal.no_signal("STRATEGY"), positions, bar)

    assert result == {}
