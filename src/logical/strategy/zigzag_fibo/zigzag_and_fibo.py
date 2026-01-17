
import pandas as pd
from pandas import Timedelta, DateOffset
from typing import List
from decimal import Decimal

# ====================================================
# Логирование и конфигурация
# ====================================================
from src.utils.logger.logger import get_logger
logger = get_logger(__name__)
from src.config.config import config
# ====================================================
# Индикаторы
# ====================================================
from src.logical.indicators.fibonacci import fibonacci_levels
from src.logical.indicators.zigzag import ZigZag
# ====================================================
# Торговые сущности
# ====================================================
from src.trading_engine.core.enums import  Direction, PositionType  # статусы
from src.trading_engine.core.position import Position
from src.trading_engine.core.signal import Signal
# ====================================================
# Risk Manager
# ====================================================
from src.logical.strategy.risk_manager.risk_manager import RiskManager

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Класс стратегии
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
class ZigZagAndFibo:
    def __init__(self, coin):
        
        self.coin = coin
        self.symbol = coin.get("SYMBOL")+"/USDT"
        # tick_size = coin.get("MINIMAL_TICK_SIZE")
        self.timeframe = coin.get("TIMEFRAME")
        self.allowed_min_bars = config.get_setting("STRATEGY_SETTINGS", "MINIMUM_BARS_FOR_STRATEGY_CALCULATION")
        self.ALLOWED_Z2_OFFSET = config.get_setting("STRATEGY_SETTINGS", "Z2_INDEX_OFFSET")
        self.source = config.get_setting("STRATEGY_SETTINGS", "STRATEGY_NAME")
        self.risk_manager = RiskManager(coin)
        
    # ===================================================
    # ? Запуск стратегии на выходе Signal
    # ? params: data - массив исторических данных
    # ?         positions - список открытых позиций
    # ===================================================
    def run_strategy(self, data, positions: List[Position]) -> Signal:
        if len(positions) > 0:
            logger.debug(f"Есть открытые позиции, по стратегии ZigZag и Фибоначчи ")
            
            for position in positions:
                if position.type == PositionType.HEDGE:
                    logger.debug(f"Есть хеджирующая позиция {position.direction} {position.symbol}, стратегия не будет входить в позицию.")
                    # Обрабатываем наличие хеджирующей позиции
                    # TODO: возможно нужно добавить логику выхода из хеджирующей позиции
                    # пока ставим нет сигнала
                    return Signal.no_signal(source=self.source)
            logger.debug(f"Есть открытые позиции, стратегия ZigZag и Фибоначчи не будет искать точку входа.")
            return Signal.no_signal(source=self.source)
        else:
            logger.debug(f"Открытых позиций нет, стратегия ZigZag и Фибоначчи может искать точку входа.")
            return self.find_entry_point(data)

    # Ищем точку входа по стратегии
    def find_entry_point(self, data, positions=None) -> Signal:
        """
        Запуск стратегии ZigZag и уровней Фибоначчи на переданных данных.
        Определяем есть ли сигнал и если есть создаем позицию
        
        :param data: numpy массив формы (N, 5) где последний столбец - timestamps
        :param positions: список открытых позиций (для совместимости с новым API)
        """
        # Если переданы позиции, используем их для проверки
        if positions is not None and len(positions) > 0:
            logger.debug(f"Есть открытые позиции, стратегия ZigZag и Фибоначчи не будет искать точку входа.")
            return Signal.no_signal(source=self.source)
            
        # Оптимизация: создаем DataFrame один раз, но только если нужен для индикаторов
        # Разделяем данные и timestamps
        data_values = data[:, :-1]  # open, high, low, close
        timestamps = data[:, -1]   # timestamps
        
        # Создаем DataFrame только для индикаторов (они требуют pandas)
        # Но делаем это один раз, а не на каждом баре в цикле
        data_df = pd.DataFrame(data_values, columns=["open","high","low","close"])
        data_df.index = pd.to_datetime(timestamps)
        
        # Расчет индикаторов
        zigzag, fiboLev = calculate_indicators(data_df, self.coin)
        
        # Проверка корректности результата
        if zigzag is None or fiboLev is None:
            logger.error(f"Стратегия не вернула корректные результаты.")
            return Signal.no_signal(source=self.source)

        logger.debug(f"ZigZag / z1 =: {zigzag["z1"]}, z2 =: {zigzag["z2"]}, z2_index: {zigzag['z2_index'].strftime("%d.%m.%Y %H:%M")} direction: {zigzag['direction']}")        
        
        direction_zigzag = zigzag["direction"] # направление позиции -1 long, 1 short
        z2_index = zigzag["z2_index"] # индекс ближайшей точки z2 
        # Оптимизация: используем numpy напрямую вместо iloc
        entry_price = data_values[-1, 3]  # close - последний элемент, столбец 3
        volume = self.calculate_position_size(entry_price)  # размер позиции
        current_index = pd.Timestamp(timestamps[-1])  # текущий бар

        direction = None
        
                    
        # 2) z2_index должен быть текущим баром или не более чем на ALLOWED_Z2_OFFSET баров раньше
        allowed_shifted = shift_timestamp(current_index, self.ALLOWED_Z2_OFFSET, self.timeframe, direction=-1)
        if not (z2_index == current_index or z2_index == allowed_shifted):
            logger.debug(f"Пропускаем сигнал: z2_index={z2_index} не в допустимом окне (текущий={current_index})")
            return Signal.no_signal(source=self.source)
                            
        
        if direction_zigzag == -1: #индикатор zigzag показывает что нужно входить в long
            # проверяем цену входа в позицию с первым тейком 1 уровня фибоначчи цена входа должна быть меньше уровня 1
            if entry_price < fiboLev[78.6]['level_price']:
                logger.debug(f"Цена входа {entry_price} [bold green] < [/bold green] {fiboLev[78.6]['level_price']} [bold green]long[/bold green]")
                direction = Direction.LONG # направление позиции -1 long, 1 short
            else :
                logger.debug(f"Цена входа {entry_price} [bold red] > [/bold red] {fiboLev[78.6]['level_price']}")
                logger.debug(f"Пропускаем сигнал на LONG")
                return Signal.no_signal(source=self.source)

        if direction_zigzag == 1: #индикатор zigzag показывает что нужно входить в long
            logger.debug(f"Индикатор zigzag показывает что нужно входить в long {direction_zigzag}")
            # проверяем цену входа в позицию с первым тейком 1 уровня фибоначчи цена входа должна быть меньше уровня 1
            if entry_price > fiboLev[78.6]['level_price']:
                logger.debug(f"Цена входа {entry_price} [bold green] > [/bold green] {fiboLev[78.6]['level_price']}")
                direction = Direction.SHORT # направление позиции -1 long, 1 short
            else :
                logger.debug(f"Цена входа {entry_price} [bold red] < [/bold red] {fiboLev[78.6]['level_price']}")
                logger.debug(f"Пропускаем сигнал на SHORT")
                return Signal.no_signal(source=self.source)
            
                    
        if direction is None:
            logger.debug(f"Нет сигнала на вход в позицию")
            return Signal.no_signal(source=self.source)
        # Создание сделки
        tps= []
        sls=[]
        info = {}
        # перебираем все уровни и находим тейки и стопы
        for value in fiboLev.values():
            info = {"price": value['level_price'], "volume": value['volume']}
            if value.get('tp') is True:
                if value.get('tp_to_break') is True:
                    info["tp_to_break"] = True
                tps.append(info)
            if value.get('sl') is True:
                sls.append(info)
        
        signal = Signal.entry(
            
            direction=direction,
            entry_price=entry_price,
            volume=volume,
            take_profits=tps,
            stop_losses=sls,
            source=self.source,
            metadata = {"z2_index":z2_index}
        )
        return signal
    
    def calculate_position_size(self, entry_price): 
        """Расчет размера позиции на основе цены входа"""
        entry_price = Decimal(str(entry_price))
        return self.risk_manager.calculate_position_size(entry_price)

# ------------------------------------------
# Расчет индикаторов
# ------------------------------------------
def calculate_indicators(data_df, coin):
    try:
        
        zigzag_indicator = ZigZag(coin)
        # z1, z2, direction, z2_index = zigzag_indicator.calculate_zigzag(data_df)
        zigzag = zigzag_indicator.calculate_zigzag(data_df)
        
        # Расчет уровней Фибоначчи
        fiboLev = fibonacci_levels(zigzag["z1"], zigzag["z2"], zigzag["direction"]) # fiboLev = fibonacci_levels(z1, z2, direction)

        return zigzag, fiboLev
    except Exception as e:
        logger.error(f"Ошибка при запуске стратегии ZigZag и Фибоначчи: {e}")
        return None, None


# сдвиг метки времени
def shift_timestamp(index, bars: int, timeframe: str, direction: int = -1):
    """
    Сдвигает метку времени на заданное количество баров для заданного таймфрейма.

    index: pandas.Timestamp или числовой индекс (int)
    bars: число баров (int, >=0)
    timeframe: строка таймфрейма, поддерживает: числовые минуты ('1','3','5','15',...),
               единицы 'D','W','M' или форматы с суффиксом ('15m','1h').
    direction: -1 для сдвига назад (index - bars*tf), +1 для вперёд.

    Возвращает новый индекс того же типа, что и входной (Timestamp или int).
    """
    index = pd.Timestamp(index)
    # если индекс не временной (например, целочисленный индекс), просто сдвигаем по числу баров
    if not isinstance(index, (pd.Timestamp, pd.DatetimeIndex)):
        try:
            # предполагаем, что index — целое число (позиция/номер строки)
            return index + direction * bars
        except Exception:
            return index

    tf = str(timeframe).strip()
    # normalize
    tf_upper = tf.upper()

    # минутные значения — либо чисто число ("15"), либо с суффиксом m ("15m")
    try:
        if tf_upper.endswith('M') and not tf_upper.isdigit():
            # could be '15M' meaning minutes or 'M' meaning month -> distinguish
            # if single 'M' treat as month
            if tf_upper == 'M':
                delta = DateOffset(months=bars)
            else:
                # numeric part
                num = int(tf_upper[:-1])
                delta = Timedelta(minutes=num * bars)
        elif tf_upper.endswith('H'):
            num = int(tf_upper[:-1])
            delta = Timedelta(minutes=60 * num * bars)
        elif tf_upper in ('D', 'W', 'M'):
            if tf_upper == 'D':
                delta = DateOffset(days=bars)
            elif tf_upper == 'W':
                delta = DateOffset(weeks=bars)
            else:  # 'M'
                delta = DateOffset(months=bars)
        else:
            # try parse as integer minutes
            num = int(tf_upper)
            delta = Timedelta(minutes=num * bars)
    except Exception:
        # fallback: try parsing common patterns like '15m', '1h'
        s = tf_upper
        if s.endswith('M') and len(s) > 1:
            num = int(s[:-1])
            delta = Timedelta(minutes=num * bars)
        elif s.endswith('H'):
            num = int(s[:-1])
            delta = Timedelta(minutes=60 * num * bars)
        else:
            # as last resort — treat timeframe as minutes if numeric part exists
            digits = ''.join(ch for ch in s if ch.isdigit())
            if digits:
                delta = Timedelta(minutes=int(digits) * bars)
            else:
                # Unknown timeframe — возврат оригинального индекса
                return index

    if direction < 0:
        return index - delta
    return index + delta
