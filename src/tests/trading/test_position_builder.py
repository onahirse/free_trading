"""
Тесты для модуля position_builder.py
Проверяют создание позиций и ордеров на основе торговых сигналов
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC

from src.backtester.trading.position_builder import PositionBuilder
from src.trading_engine.core.signal import Signal
from src.trading_engine.core.enums import Direction, SignalType, OrderType
from src.trading_engine.core.position import Position


# @pytest.fixture
# def real_position_manager():
#     """Фикстура с реальным менеджером позиций"""
#     from src.trading_engine.managers.position_manager import PositionManager  # ← импортируйте реальный класс
#     return PositionManager()  # или с нужными параметрами

@pytest.fixture
def mock_position_manager():
    """Фикстура для мок-менеджера позиций с методом open_position"""
    manager = MagicMock()
    
    def open_position(symbol, source, direction, tick_size, open_bar, meta):
        position = Position(
            symbol=symbol,
            direction=direction,
            tick_size=tick_size,
            source=source,
            meta=meta
            
        )
        position.bar_opened = open_bar
        return position
    
    manager.open_position = MagicMock(side_effect=open_position)
    return manager


@pytest.fixture
def mock_coin():
    """Фикстура для мок-конфигурации монеты"""
    return {
        "SYMBOL": "BTC",
        "MINIMAL_TICK_SIZE": "0.01",
        "LEVERAGE": "10",
        "START_DEPOSIT_USDT": "10000",
        "VOLUME_SIZE": "100"
    }

@pytest.fixture
def mock_bar():
    """Фикстура для мок-бара OHLCV [open, high, low, close, timestamp]"""
    return [100, 105, 95, 102, datetime.now(UTC)]


class TestPositionBuilder:
    """Тесты для класса PositionBuilder"""
    
    def test_build_creates_position_with_entry_order(
        self, mock_position_manager, mock_coin, mock_bar
    ):
        """Тест: создание позиции с ордером на вход"""
        builder = PositionBuilder(mock_position_manager, mock_coin)
        
        signal = Signal.entry(
            direction=Direction.LONG,
            entry_price=Decimal("100"),
            volume=Decimal("10"),
            take_profits=[],
            stop_losses=[],
            source="strategy",
            metadata={"entry_price": Decimal("100")},
        )
        
        position = builder.build(signal, mock_bar)
        
        assert position is not None
        assert position.symbol == "BTC/USDT"
        assert position.direction == Direction.LONG
        assert position.source == "strategy"
        assert len(position.orders) == 1
        assert position.orders[0].type == OrderType.ENTRY
        assert position.orders[0].price == Decimal("100")
        assert position.orders[0].direction == Direction.LONG
    
    def test_build_creates_position_with_take_profits(
        self, mock_position_manager, mock_coin, mock_bar
    ):
        """Тест: создание позиции с тейк-профитами"""
        builder = PositionBuilder(mock_position_manager, mock_coin)
        
        signal = Signal.entry(
            source="strategy",
            direction=Direction.LONG,
            entry_price=Decimal("100"),
            volume=Decimal("10"),
            take_profits=[
                {"price": "110", "volume": "0.5"},
                {"price": "120", "volume": "0.5"},
            ],
            stop_losses=[],
        )
        
        position = builder.build(signal, mock_bar)
        
        # Должен быть 1 ENTRY + 2 TP = 3 ордера
        assert len(position.orders) == 3
        tp_orders = [o for o in position.orders if o.type == OrderType.TAKE_PROFIT]
        assert len(tp_orders) == 2
        assert tp_orders[0].price == Decimal("110")
        assert tp_orders[1].price == Decimal("120")
    
    def test_build_creates_position_with_stop_losses(
        self, mock_position_manager, mock_coin, mock_bar
    ):
        """Тест: создание позиции со стоп-лоссами"""
        builder = PositionBuilder(mock_position_manager, mock_coin)
        
        signal = Signal.entry(
            source="strategy",
            direction=Direction.LONG,
            entry_price=Decimal("100"),
            volume=Decimal("10"),
            take_profits=[],
            stop_losses=[
                {"price": "90", "volume": "1.0"},
            ],
        )
        
        position = builder.build(signal, mock_bar)
        
        # Должен быть 1 ENTRY + 1 SL = 2 ордера
        assert len(position.orders) == 2
        sl_orders = [o for o in position.orders if o.type == OrderType.STOP_LOSS]
        assert len(sl_orders) == 1
        assert sl_orders[0].price == Decimal("90")
    
    def test_build_creates_position_with_tp_and_sl(
        self, mock_position_manager, mock_coin, mock_bar
    ):
        """Тест: создание позиции с тейк-профитами и стоп-лоссами"""
        builder = PositionBuilder(mock_position_manager, mock_coin)
        
        signal = Signal.entry(
            source="strategy",
            direction=Direction.LONG,
            entry_price=Decimal("100"),
            volume=Decimal("10"),
            take_profits=[
                {"price": "110", "volume": "0.5"},
            ],
            stop_losses=[
                {"price": "90", "volume": "1.0"},
            ],
        )
        
        position = builder.build(signal, mock_bar)
        
        # Должен быть 1 ENTRY + 1 TP + 1 SL = 3 ордера
        assert len(position.orders) == 3
        assert any(o.type == OrderType.ENTRY for o in position.orders)
        assert any(o.type == OrderType.TAKE_PROFIT for o in position.orders)
        assert any(o.type == OrderType.STOP_LOSS for o in position.orders)
    
    def test_build_handles_tp_to_break_metadata(
        self, mock_position_manager, mock_coin, mock_bar
    ):
        """Тест: обработка метаданных tp_to_break в тейк-профитах"""
        builder = PositionBuilder(mock_position_manager, mock_coin)
        
        signal = Signal.entry(
            source="strategy",
            direction=Direction.LONG,
            entry_price=Decimal("100"),
            volume=Decimal("10"),
            take_profits=[
                {"price": "110", "volume": "0.5", "tp_to_break": True},
            ],
            stop_losses=[],
        )
        
        position = builder.build(signal, mock_bar)
        
        tp_orders = [o for o in position.orders if o.type == OrderType.TAKE_PROFIT]
        assert len(tp_orders) == 1
        assert tp_orders[0].meta.get("tp_to_break") is True
    
    def test_build_adjusts_tp_volume_to_match_total(
        self, mock_position_manager, mock_coin, mock_bar
    ):
        """Тест: корректировка объема TP для соответствия общему объему"""
        builder = PositionBuilder(mock_position_manager, mock_coin)
        
        signal = Signal.entry(
            source="strategy",
            direction=Direction.LONG,
            entry_price=Decimal("100"),
            volume=Decimal("10"),
            take_profits=[
                {"price": "110", "volume": 0.5},
                {"price": "120", "volume": 0.5},
            ],
            stop_losses=[],
        )
        
        position = builder.build(signal, mock_bar)
        
        # Объем должен быть скорректирован так, чтобы сумма TP = общему объему
        entry_order = next(o for o in position.orders if o.type == OrderType.ENTRY)
        total_volume = entry_order.volume
        
        tp_orders = [o for o in position.orders if o.type == OrderType.TAKE_PROFIT]
        sum_tp_volume = sum(o.volume for o in tp_orders)
        
        # Сумма объемов TP должна равняться общему объему (с учетом округления)
        assert abs(sum_tp_volume - total_volume) < Decimal("0.001")
    
    def test_build_adjusts_sl_volume_to_match_total(
        self, mock_position_manager, mock_coin, mock_bar
    ):
        """Тест: корректировка объема SL для соответствия общему объему"""
        builder = PositionBuilder(mock_position_manager, mock_coin)
        
        signal = Signal.entry(
            source="strategy",
            direction=Direction.LONG,
            entry_price=Decimal("100"),
            volume=Decimal("10"),
            take_profits=[],
            stop_losses=[
                {"price": "90", "volume": "0.8"},
            ],
        )
        
        position = builder.build(signal, mock_bar)
        
        entry_order = next(o for o in position.orders if o.type == OrderType.ENTRY)
        total_volume = entry_order.volume
        
        sl_orders = [o for o in position.orders if o.type == OrderType.STOP_LOSS]
        sum_sl_volume = sum(o.volume for o in sl_orders)
        
        # Сумма объемов SL должна равняться общему объему (с учетом округления)
        assert abs(sum_sl_volume - total_volume) < Decimal("0.001")
    
    def test_build_raises_error_when_signal_is_none(
        self, mock_position_manager, mock_coin, mock_bar
    ):
        """Тест: ошибка при отсутствии сигнала"""
        builder = PositionBuilder(mock_position_manager, mock_coin)
        
        with pytest.raises(ValueError, match="Необходимо указать сигнал"):
            builder.build(None, mock_bar)
    
    def test_build_raises_error_when_direction_is_none(
        self, mock_position_manager, mock_coin, mock_bar
    ):
        """Тест: ошибка при отсутствии направления в сигнале"""
        builder = PositionBuilder(mock_position_manager, mock_coin)
        
        signal = Signal(
            signal_type=SignalType.ENTRY,
            source="strategy",
            direction=None,
            price=Decimal("100"),
            take_profits=[],
            stop_losses=[],
        )
        
        with pytest.raises(ValueError, match="Необходимо указать направление в сигнале"):
            builder.build(signal, mock_bar)
    
    def test_build_rounds_price_to_tick_size(
        self, mock_position_manager, mock_coin, mock_bar
    ):
        """Тест: округление цены до размера тика"""
        builder = PositionBuilder(mock_position_manager, mock_coin)
        
        # Цена 100.123 должна округлиться до 100.12 (tick_size = 0.01)
        signal = Signal.entry(
            source="strategy",
            direction=Direction.LONG,
            entry_price=Decimal("100.123"),
            volume=Decimal("10"),
            take_profits=[],
            stop_losses=[],
        )
        
        position = builder.build(signal, mock_bar)
        
        entry_order = next(o for o in position.orders if o.type == OrderType.ENTRY)
        # Проверяем, что цена округлена до 0.01
        assert entry_order.price == Decimal("100.12")
    
    def test_build_works_with_short_direction(
        self, mock_position_manager, mock_coin, mock_bar
    ):
        """Тест: создание позиции для SHORT направления"""
        builder = PositionBuilder(mock_position_manager, mock_coin)
        
        signal = Signal.entry(
            source="strategy",
            direction=Direction.SHORT,
            entry_price=Decimal("100"),
            volume=Decimal("10"),
            take_profits=[],
            stop_losses=[],
        )
        
        position = builder.build(signal, mock_bar)
        
        assert position.direction == Direction.SHORT
        entry_order = next(o for o in position.orders if o.type == OrderType.ENTRY)
        assert entry_order.direction == Direction.SHORT
    
    @patch('src.backtester.trading.position_builder.RiskManager')
    def test_build_uses_risk_manager_for_volume_calculation(
        self, mock_risk_manager_class, mock_position_manager, mock_coin, mock_bar
    ):
        """Тест: использование RiskManager для расчета объема"""
        mock_rm = MagicMock()
        mock_rm.calculate_position_size.return_value = Decimal("1.5")
        mock_risk_manager_class.return_value = mock_rm
        
        builder = PositionBuilder(mock_position_manager, mock_coin)
        
        signal = Signal.entry(
            source="strategy",
            direction=Direction.LONG,
            entry_price=Decimal("100"),
            volume=Decimal("10"),
            take_profits=[],
            stop_losses=[],
        )
        
        position = builder.build(signal, mock_bar)
        
        # Проверяем, что RiskManager был вызван с правильной ценой
        mock_rm.calculate_position_size.assert_called_once()
        call_args = mock_rm.calculate_position_size.call_args[0][0]
        assert call_args == Decimal("100")  # Округленная цена входа
        
        # Проверяем, что объем из RiskManager использован
        entry_order = next(o for o in position.orders if o.type == OrderType.ENTRY)
        assert entry_order.volume == Decimal("1.5")
    
    def test_build_sets_open_bar_correctly(
        self, mock_position_manager, mock_coin, mock_bar
    ):
        """Тест: установка времени открытия позиции из бара"""
        builder = PositionBuilder(mock_position_manager, mock_coin)
        
        signal = Signal.entry(
            source="strategy",
            direction=Direction.LONG,
            entry_price=Decimal("100"),
            volume=Decimal("10"),
            take_profits=[],
            stop_losses=[],
        )
        
        position = builder.build(signal, mock_bar)
        
        # Проверяем, что bar_opened установлен из bar[4]
        assert position.bar_opened == mock_bar[4]
        
        # Проверяем, что все ордера созданы с правильным created_bar
        for order in position.orders:
            assert order.created_bar == mock_bar[4]
