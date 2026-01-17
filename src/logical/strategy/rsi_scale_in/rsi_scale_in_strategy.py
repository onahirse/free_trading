"""RSI Scale-In Strategy with multiple entry levels and position averaging.

Стратегия использует RSI для определения точек входа и выхода:
- LONG: открытие при пересечении RSI уровня снизу вверх
- SHORT: открытие при пересечении RSI уровня сверху вниз
- Поддержка до 4 докупок с удвоением объема
- Закрытие позиции по обратному сигналу

Особенности:
- Настраиваемый период RSI
- Отдельные уровни для каждой докупки
- Удвоение объема при каждой докупке (2x, 4x, 8x, 16x от базового)
- Торговля в обе стороны (LONG и SHORT)
"""

from typing import List, Any, Optional, Dict
from decimal import Decimal
import pandas as pd
import numpy as np

from src.trading_engine.core.signal import Signal
from src.trading_engine.core.enums import Direction, SignalType
from src.trading_engine.core.position import Position
from src.utils.logger.logger import get_logger
from src.config.config import config
from src.logical.strategy.base import BaseStrategy
from src.logical.strategy.risk_manager.risk_manager import RiskManager

logger = get_logger(__name__)


class RSIScaleInStrategy(BaseStrategy):
    """RSI Scale-In стратегия с усреднением позиции."""

    def __init__(self, coin: dict):
        super().__init__(name=config.get_setting("STRATEGY_SETTINGS", "STRATEGY_NAME") or "rsi_scale_in")
        self.coin = coin
        self.symbol = (coin.get("SYMBOL") or "").upper() + "/USDT"
        self.timeframe = coin.get("TIMEFRAME") or "1"
        
        # Загрузка параметров RSI из конфига
        self.rsi_period = config.get_setting("STRATEGY_SETTINGS", "RSI_PERIOD") or 6
        
        # Уровни для LONG
        self.long_entry_level = config.get_setting("STRATEGY_SETTINGS", "LONG_ENTRY_LEVEL") or 35
        self.long_scale_levels = config.get_setting("STRATEGY_SETTINGS", "LONG_SCALE_LEVELS") or [30, 25, 20, 15]
        
        # Уровни для SHORT
        self.short_entry_level = config.get_setting("STRATEGY_SETTINGS", "SHORT_ENTRY_LEVEL") or 65
        self.short_scale_levels = config.get_setting("STRATEGY_SETTINGS", "SHORT_SCALE_LEVELS") or [70, 75, 80, 85]
        
        # Максимальное количество докупок
        self.max_scale_ins = config.get_setting("STRATEGY_SETTINGS", "MAX_SCALE_INS") or 4
        
        # Минимальное количество баров для расчета
        self.allowed_min_bars = config.get_setting("STRATEGY_SETTINGS", "MINIMUM_BARS_FOR_STRATEGY_CALCULATION") or 100
        
        # Risk manager для расчета объема
        self.risk_manager = RiskManager(coin)
        
        logger.info(f"RSI Scale-In Strategy initialized: RSI({self.rsi_period}), "
                f"LONG levels: {self.long_entry_level}/{self.long_scale_levels}, "
                f"SHORT levels: {self.short_entry_level}/{self.short_scale_levels}")

    def calculate_rsi(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Расчет RSI индикатора.
        
        Args:
            data: DataFrame с OHLCV данными
            period: период для расчета RSI
            
        Returns:
            Series с значениями RSI
        """
        close = data['close'].copy()
        
        # Расчет изменений цены
        delta = close.diff()
        
        # Разделение на прибыли и убытки
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Экспоненциальное скользящее среднее
        avg_gains = gains.ewm(span=period, adjust=False).mean()
        avg_losses = losses.ewm(span=period, adjust=False).mean()
        
        # Расчет RS и RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    def detect_rsi_cross(self, rsi: pd.Series, level: float, direction: str) -> bool:
        """Определение пересечения RSI уровня.
        
        Args:
            rsi: Series с значениями RSI
            level: уровень для проверки пересечения
            direction: направление пересечения ('down' для сверху вниз, 'up' для снизу вверх)
            
        Returns:
            True если произошло пересечение в указанном направлении
        """
        if len(rsi) < 2:
            return False
            
        current_rsi = rsi.iloc[-1]
        previous_rsi = rsi.iloc[-2]
        
        if direction == 'down':
            # Пересечение сверху вниз (для LONG)
            return previous_rsi > level and current_rsi <= level
        elif direction == 'up':
            # Пересечение снизу вверх (для SHORT)
            return previous_rsi < level and current_rsi >= level
            
        return False

    def get_position_scale_count(self, positions: List[Position]) -> int:
        """Получить количество докупок в текущей позиции.
        
        Args:
            positions: список открытых позиций
            
        Returns:
            Количество докупок (0 = первичная позиция)
        """
        if not positions:
            return 0
            
        # Предполагаем, что у нас одна позиция от этой стратегии
        for pos in positions:
            if pos.source == self.name:
                # Считаем количество entry ордеров
                scale_count = sum(1 for order in pos.orders if order.type.name == 'ENTRY') - 1
                return max(0, scale_count)
        
        return 0

    def should_close_position(self, positions: List[Position], rsi: pd.Series) -> bool:
        """Проверить, нужно ли закрыть позицию по обратному сигналу.
        
        Args:
            positions: список открытых позиций
            rsi: Series с значениями RSI
            
        Returns:
            True если нужно закрыть позицию
        """
        if not positions:
            return False
        
        if len(rsi) < 2:
            logger.debug("should_close_position: недостаточно данных RSI")
            return False
            
        for pos in positions:
            if pos.source != self.name:
                continue
                
            # Если есть LONG позиция, проверяем пересечение SHORT уровня
            if pos.direction == Direction.LONG:
                cross_detected = self.detect_rsi_cross(rsi, self.short_entry_level, 'up')
                logger.debug(f"Checking LONG close: RSI={rsi.iloc[-1]:.2f}, prev={rsi.iloc[-2]:.2f}, "
                           f"level={self.short_entry_level}, cross={cross_detected}")
                if cross_detected:
                    logger.info(f"RSI crossed {self.short_entry_level} upward - closing LONG position")
                    return True
                    
            # Если есть SHORT позиция, проверяем пересечение LONG уровня
            elif pos.direction == Direction.SHORT:
                cross_detected = self.detect_rsi_cross(rsi, self.long_entry_level, 'down')
                logger.debug(f"Checking SHORT close: RSI={rsi.iloc[-1]:.2f}, prev={rsi.iloc[-2]:.2f}, "
                           f"level={self.long_entry_level}, cross={cross_detected}")
                if cross_detected:
                    logger.info(f"RSI crossed {self.long_entry_level} downward - closing SHORT position")
                    return True
        
        return False

    def run(self, data: Any, positions: List[Position], trading_context: Optional[Dict[str, Any]] = None) -> Signal:
        """Запуск стратегии RSI Scale-In.
        
        Args:
            data: исторические данные (numpy array или DataFrame)
            positions: список открытых позиций
            trading_context: дополнительный контекст торговли
            
        Returns:
            Signal объект с торговым сигналом
        """
        # Приведение к DataFrame
        if isinstance(data, pd.DataFrame):
            data_df = data.copy()
        else:
            try:
                data_values = data[:, :-1]
                timestamps = data[:, -1]
                data_df = pd.DataFrame(data_values, columns=["open", "high", "low", "close"])
                data_df.index = pd.to_datetime(timestamps)
            except Exception as e:
                logger.error(f"RSIScaleIn: невозможно привести data к DataFrame: {e}")
                return Signal.no_signal(source=self.name)

        # Проверка минимального количества баров
        if len(data_df) < self.allowed_min_bars:
            logger.debug(f"Недостаточно баров для расчета RSI: {len(data_df)} < {self.allowed_min_bars}")
            return Signal.no_signal(source=self.name)

        # Расчет RSI
        try:
            rsi = self.calculate_rsi(data_df, self.rsi_period)
            current_rsi = rsi.iloc[-1]
            
            if pd.isna(current_rsi):
                logger.debug("RSI значение не рассчитано (NaN)")
                return Signal.no_signal(source=self.name)
                
        except Exception as e:
            logger.error(f"Ошибка при расчете RSI: {e}")
            return Signal.no_signal(source=self.name)

        logger.debug(f"Current RSI: {current_rsi:.2f}")

        # Получаем текущую цену
        try:
            entry_price = Decimal(str(data_df['close'].iloc[-1]))
        except Exception:
            logger.error("Не удалось получить цену закрытия")
            return Signal.no_signal(source=self.name)

        # ========================================
        # Проверка закрытия существующих позиций
        # ========================================
        if positions and self.should_close_position(positions, rsi):
            return Signal.close(source=self.name, metadata={'rsi': float(current_rsi)})

        # ========================================
        # Проверка открытия новой позиции или докупки
        # ========================================
        
        # Получаем количество докупок
        scale_count = self.get_position_scale_count(positions)
        
        # Если позиций нет - проверяем сигнал на открытие
        if not positions or scale_count == 0:
            # LONG сигнал: RSI пересекает entry level сверху вниз
            if self.detect_rsi_cross(rsi, self.long_entry_level, 'down'):
                volume = self.risk_manager.calculate_position_size(entry_price)
                logger.info(f"LONG ENTRY signal: RSI crossed {self.long_entry_level} downward, RSI={current_rsi:.2f}")
                
                return Signal.entry(
                    direction=Direction.LONG,
                    entry_price=entry_price,
                    volume=volume,
                    take_profits=[],  # TP/SL только по обратному сигналу
                    stop_losses=[],
                    source=self.name,
                    metadata={
                        'rsi': float(current_rsi),
                        'scale_count': 0,
                        'entry_type': 'initial'
                    }
                )
            
            # SHORT сигнал: RSI пересекает entry level снизу вверх
            if self.detect_rsi_cross(rsi, self.short_entry_level, 'up'):
                volume = self.risk_manager.calculate_position_size(entry_price)
                logger.info(f"SHORT ENTRY signal: RSI crossed {self.short_entry_level} upward, RSI={current_rsi:.2f}")
                
                return Signal.entry(
                    direction=Direction.SHORT,
                    entry_price=entry_price,
                    volume=volume,
                    take_profits=[],  # TP/SL только по обратному сигналу
                    stop_losses=[],
                    source=self.name,
                    metadata={
                        'rsi': float(current_rsi),
                        'scale_count': 0,
                        'entry_type': 'initial'
                    }
                )
        
        # ========================================
        # Проверка докупок (scale-in)
        # ========================================
        if positions and scale_count < self.max_scale_ins:
            for pos in positions:
                if pos.source != self.name:
                    continue
                
                # Проверяем докупки для LONG позиции
                if pos.direction == Direction.LONG and scale_count < len(self.long_scale_levels):
                    scale_level = self.long_scale_levels[scale_count]
                    
                    if self.detect_rsi_cross(rsi, scale_level, 'down'):
                        # Объем удваивается с каждой докупкой (2x, 4x, 8x, 16x)
                        base_volume = self.risk_manager.calculate_position_size(entry_price)
                        multiplier = 2 ** (scale_count + 1)
                        volume = base_volume * Decimal(str(multiplier))
                        
                        logger.info(f"LONG SCALE-IN #{scale_count + 1}: RSI crossed {scale_level} downward, "
                                  f"RSI={current_rsi:.2f}, volume_multiplier={multiplier}x")
                        
                        return Signal.entry(
                            direction=Direction.LONG,
                            entry_price=entry_price,
                            volume=volume,
                            take_profits=[],
                            stop_losses=[],
                            source=self.name,
                            metadata={
                                'rsi': float(current_rsi),
                                'scale_count': scale_count + 1,
                                'entry_type': 'scale_in',
                                'multiplier': multiplier
                            }
                        )
                
                # Проверяем докупки для SHORT позиции
                elif pos.direction == Direction.SHORT and scale_count < len(self.short_scale_levels):
                    scale_level = self.short_scale_levels[scale_count]
                    
                    if self.detect_rsi_cross(rsi, scale_level, 'up'):
                        # Объем удваивается с каждой докупкой
                        base_volume = self.risk_manager.calculate_position_size(entry_price)
                        multiplier = 2 ** (scale_count + 1)
                        volume = base_volume * Decimal(str(multiplier))
                        
                        logger.info(f"SHORT SCALE-IN #{scale_count + 1}: RSI crossed {scale_level} upward, "
                                  f"RSI={current_rsi:.2f}, volume_multiplier={multiplier}x")
                        
                        return Signal.entry(
                            direction=Direction.SHORT,
                            entry_price=entry_price,
                            volume=volume,
                            take_profits=[],
                            stop_losses=[],
                            source=self.name,
                            metadata={
                                'rsi': float(current_rsi),
                                'scale_count': scale_count + 1,
                                'entry_type': 'scale_in',
                                'multiplier': multiplier
                            }
                        )

        return Signal.no_signal(source=self.name)

    def find_entry_point(self, data: Any, positions: Optional[List[Position]] = None) -> Signal:
        """Compatibility метод для старого API движка.
        
        Args:
            data: исторические данные
            positions: список открытых позиций (опционально для совместимости)
            
        Returns:
            Signal объект
        """
        # Используем переданные позиции или пустой список
        if positions is None:
            positions = []
        return self.run(data, positions, None)


__all__ = ['RSIScaleInStrategy']
