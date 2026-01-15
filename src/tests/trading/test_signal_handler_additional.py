"""
Дополнительные тесты для модуля signal_handler.py
Покрывают дополнительные сценарии обработки сигналов
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock

from src.backtester.trading.signal_handler import SignalHandler
from src.trading_engine.core.signal import Signal
from src.trading_engine.core.enums import Direction, SignalType
try:
    from src.tests.mocks.mock_position import MockPosition
except ImportError:
    from tests.mocks.mock_position import MockPosition

@pytest.fixture
def mock_position():
    """Фикстура для мок-position """
    return {
        "SYMBOL": "BTC",
        "MINIMAL_TICK_SIZE": "0.01",
        "LEVERAGE": "10",
        "START_DEPOSIT_USDT": "10000",
        "VOLUME_SIZE": "100"
    }
    
class TestSignalHandlerAdditional:
    """Дополнительные тесты для SignalHandler"""
        
    def test_hedge_open_without_direction_skips(
        self, mock_builder, mock_manager, mock_logger
    ):
        """Тест: HEDGE_OPEN без direction пропускается"""
        handler = SignalHandler(mock_manager, mock_builder, mock_logger)
        
        signal = Signal(
            signal_type=SignalType.HEDGE_ENTRY,
            source="ALS",
            direction=None,
            price=Decimal("100"),
        )
        
        positions = {}
        bar = [0, 0, 0, 100]
        
        result = handler.handle(signal, positions, bar)
        
        assert result == {}
        assert len(positions) == 0
        mock_logger.error.assert_called_once()
        assert "HEDGE_OPEN пропущен" in str(mock_logger.error.call_args)
    
        
    def test_exit_filters_by_source(
        self, mock_builder, mock_manager, mock_logger
    ):
        """Тест: EXIT закрывает только позиции с указанным source"""
        handler = SignalHandler(mock_manager, mock_builder, mock_logger)
        
        # Создаем позиции с разными источниками
        pos1 = MockPosition(
            direction=Direction.LONG,
            source="STRATEGY",
            is_hedge=False,
            price=Decimal("100")
        )
        pos2 = MockPosition(
            direction=Direction.LONG,
            source="ALS",
            is_hedge=False,
            price=Decimal("100")
        )
        
        positions = {pos1.id: pos1, pos2.id: pos2}
        
        # Закрываем только позиции STRATEGY
        signal = Signal.close(source="STRATEGY")
        bar = [0, 0, 0, 100]
        
        result = handler.handle(signal, positions, bar)
        
        # Должна остаться только позиция ALS
        assert len(result) == 1
        assert pos2.id in result
        assert pos1.id not in result
        assert pos1.id in mock_manager.closed
    
    def test_exit_closes_all_when_source_is_empty(
        self, mock_builder, mock_manager, mock_logger
    ):
        """Тест: EXIT с пустым source закрывает все позиции"""
        handler = SignalHandler(mock_manager, mock_builder, mock_logger)
        
        pos1 = MockPosition(
            direction=Direction.LONG,
            source="STRATEGY",
            is_hedge=False,
            price=Decimal("100")
        )
        pos2 = MockPosition(
            direction=Direction.LONG,
            source="ALS",
            is_hedge=False,
            price=Decimal("100")
        )
        
        positions = {pos1.id: pos1, pos2.id: pos2}
        
        # Создаем сигнал EXIT с пустым source (source="")
        signal = Signal(
            signal_type=SignalType.CLOSE_ALL,
            source="strategy",
        )
        bar = [0, 0, 0, 100]
        
        result = handler.handle(signal, positions, bar)
        
        # Все позиции должны быть закрыты
        assert len(result) == 0
        assert pos1.id in mock_manager.closed
        assert pos2.id in mock_manager.closed
    
    def test_hedge_close_filters_by_source(
        self, mock_builder, mock_manager, mock_logger
    ):
        """Тест: HEDGE_CLOSE закрывает только хедж-позиции с указанным source"""
        handler = SignalHandler(mock_manager, mock_builder, mock_logger)
        
        # Создаем хедж-позиции с разными источниками
        hedge1 = MockPosition(
            direction=Direction.SHORT,
            source="ALS",
            is_hedge=True,
            price=Decimal("100")
        )
        hedge2 = MockPosition(
            direction=Direction.SHORT,
            source="STRATEGY",
            is_hedge=True,
            price=Decimal("100")
        )
        main_pos = MockPosition(
            direction=Direction.LONG,
            source="ALS",
            is_hedge=False,
            price=Decimal("100")
        )
        
        positions = {hedge1.id: hedge1, hedge2.id: hedge2, main_pos.id: main_pos}
        
        # Закрываем только хедж-позиции ALS
        signal = Signal(
            signal_type=SignalType.HEDGE_CLOSE,
            source="ALS",
        )
        bar = [0, 0, 0, 100]
        
        result = handler.handle(signal, positions, bar)
        
        # Должны остаться hedge2 и main_pos
        assert len(result) == 2
        assert hedge2.id in result
        assert main_pos.id in result
        assert hedge1.id not in result
        assert hedge1.id in mock_manager.closed
        # main_pos не должна быть закрыта, так как это не хедж
        assert main_pos.id not in mock_manager.closed
    
    def test_hedge_close_closes_only_hedge_positions(
        self, mock_builder, mock_manager, mock_logger
    ):
        """Тест: HEDGE_CLOSE закрывает только хедж-позиции, игнорируя обычные"""
        handler = SignalHandler(mock_manager, mock_builder, mock_logger)
        
        hedge = MockPosition(
            direction=Direction.SHORT,
            source="ALS",
            is_hedge=True,
            price=Decimal("100")
        )
        main_pos = MockPosition(
            direction=Direction.LONG,
            source="ALS",
            is_hedge=False,
            price=Decimal("100")
        )
        
        positions = {hedge.id: hedge, main_pos.id: main_pos}
        
        signal = Signal(
            signal_type=SignalType.HEDGE_CLOSE,
            source="ALS",
        )
        bar = [0, 0, 0, 100]
        
        result = handler.handle(signal, positions, bar)
        
        # Должна остаться только основная позиция
        assert len(result) == 1
        assert main_pos.id in result
        assert hedge.id not in result
        assert hedge.id in mock_manager.closed
        assert main_pos.id not in mock_manager.closed
    
    def test_unknown_signal_type_logs_warning(
        self, mock_builder, mock_manager, mock_logger
    ):
        """Тест: неизвестный тип сигнала логирует предупреждение"""
        handler = SignalHandler(mock_manager, mock_builder, mock_logger)
        
        # Создаем сигнал с неизвестным типом (например, UPDATE)
        signal = Signal(
            signal_type=SignalType.UPDATE,
            source="STRATEGY",
        )
        
        positions = {}
        bar = [0, 0, 0, 100]
        
        result = handler.handle(signal, positions, bar)
        
        # Позиции не должны измениться
        assert result == {}
        mock_logger.warning.assert_called_once()
        assert "Неизвестный тип сигнала" in str(mock_logger.warning.call_args)