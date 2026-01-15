# цикл по барам

# src/backtester/engine/backtest_engine.py
import numpy as np
import pandas as pd
from decimal import Decimal
# from src.data_fetcher.utils import shift_timestamp
# from src.logical.hedging.als.als_engine import ALSEngine
from src.backtester.engine.fast_1m_selector import Fast1mBarSelector

# Engine выполнения бэктеста по барам.
# Отвечает за обход баров, вызов стратегии, обработку сигналов,
# запуск исполняющего цикла по минутным барам и учет PnL в портфеле.
class BacktestEngine:
    def __init__(self, strategy, manager, execution_loop, signal_handler, portfolio, logger):
        # strategy: объект стратегии с методом find_entry_point и параметром allowed_min_bars
        # manager: менеджер позиций, содержит словарь positions
        # execution_loop: объект, который симулирует исполнение ордеров по 1m барам
        # signal_handler: обработчик сигналов, возвращает/обновляет позицию
        # portfolio: учетная логика портфеля (расчёт floating, on_bar и т.д.)
        # logger: объект логирования
        self.strategy = strategy
        self.manager = manager
        self.execution_loop = execution_loop
        self.signal_handler = signal_handler
        self.portfolio = portfolio
        self.logger = logger

    # ===================================================
    # ? Запуск бэктеста
    # ===================================================
    def run(self, ohlcv, ohlcv_1m, timeframe):
        positions = {}

        # Оптимизация: конвертируем в numpy один раз без лишних копий
        # Используем view где возможно, чтобы избежать копирования данных
        data_cols = ohlcv[['open','high','low','close']].values  # numpy массив напрямую
        timestamps = ohlcv.index.values  # numpy массив timestamps (datetime64[ns])
        
        # Создаем массив с object dtype для последнего столбца, чтобы хранить timestamps
        # Это позволяет объединить float данные с datetime объектами
        n_bars = len(data_cols)
        arr = np.empty((n_bars, 5), dtype=object)
        arr[:, :4] = data_cols  # open, high, low, close
        arr[:, 4] = pd.to_datetime(timestamps)  # timestamps как pd.Timestamp объекты

        # ! Инициализация оптимизированного селектора 1m баров
        # Это делается один раз вместо вызова select_range на каждом баре
        fast_selector = Fast1mBarSelector(ohlcv_1m)

        # ! Итерация по барам торгового таймфрейма
        for i in range(self.strategy.allowed_min_bars, len(arr)):
            bar = arr[i]
            bar_time = bar[4]  # pd.Timestamp объект из массива

            # ! запуск стратегии, генерирует сигнал
            # передаем нужное число баров на заданном таймфрейме.
            signal = self.strategy.find_entry_point(arr[i-self.strategy.allowed_min_bars:i])

            # ! Обработка сигнала и Создание / обновление позиции ордеров через SignalHandler
            # Сюда можно подовать сигналы из других стратегий и она будет работать
            positions = self.signal_handler.handle(signal, positions, bar)

            # ! Запуск исполнения по минутным барам, если есть открытые позиции
            # Позиций может быть несколько, основная и хеджирующие
            if len(positions) > 0:
                # Используем оптимизированный селектор вместо select_range
                arr_1m = fast_selector.get_bars_for_htf_bar(bar_time, timeframe)
                
                if arr_1m is not None and len(arr_1m) > 0:
                    self.execution_loop.run(arr_1m)

            # ! Учет PnL в портфеле по окончании бара
            realized = Decimal("0")
            for p in self.manager.positions.values():
                for e in p.executions:
                    if e.bar_index == bar_time:
                        realized += e.realized_pnl
            
            # ! расчет floating  
            floating = self.portfolio.calculate_floating(
                self.manager,
                Decimal(str(bar[1])),
                Decimal(str(bar[2]))
            )
            # self.logger.debug(f"Осуществленный PnL на баре {bar_time}: {realized}, Плавающий PnL: {floating}")
            # ! обновление портфеля по бару
            self.portfolio.on_bar(bar_time, realized, floating)
