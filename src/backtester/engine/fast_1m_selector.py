# Оптимизированный селектор 1-минутных баров для бэктеста
# src/backtester/engine/fast_1m_selector.py

import numpy as np
import pandas as pd
from typing import Optional
from src.data_fetcher.utils import shift_timestamp


class Fast1mBarSelector:
    """
    Оптимизированный класс для быстрого выбора 1-минутных баров по диапазону времени.
    
    Вместо сканирования всего DataFrame на каждом HTF-баре, использует:
    - Предварительно подготовленные numpy массивы
    - Бинарный поиск для нахождения индексов
    - Прямое срезание массивов без создания промежуточных DataFrame
    
    Это дает значительное ускорение (10-100x) при большом количестве HTF-баров.
    """
    
    def __init__(self, ohlcv_1m: pd.DataFrame):
        """
        Инициализация селектора.
        
        :param ohlcv_1m: DataFrame с 1-минутными данными, должен иметь DatetimeIndex
        и колонки ['open', 'high', 'low', 'close', 'volume']
        """
        if not isinstance(ohlcv_1m.index, pd.DatetimeIndex):
            raise ValueError("ohlcv_1m должен иметь DatetimeIndex")
        
        # Проверка наличия необходимых колонок
        required_cols = ['open', 'high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in ohlcv_1m.columns]
        if missing_cols:
            raise ValueError(f"Отсутствуют необходимые колонки: {missing_cols}")
        
        # Сохраняем исходный DataFrame для совместимости (если понадобится)
        self._df = ohlcv_1m
        
        # Конвертируем в numpy массивы один раз при инициализации
        # Это намного быстрее, чем делать это на каждом баре
        self._timestamps = ohlcv_1m.index.values.astype('datetime64[ns]')
        self._data = ohlcv_1m[['open', 'high', 'low', 'close']].values
        
        # Проверяем, что данные отсортированы по времени (должно быть так после загрузки)
        if len(self._timestamps) > 1:
            if not np.all(self._timestamps[:-1] <= self._timestamps[1:]):
                raise ValueError("Данные должны быть отсортированы по времени")
        
        self._len = len(self._timestamps)
    
    def get_bars(self, start_time: pd.Timestamp, end_time: pd.Timestamp) -> Optional[np.ndarray]:
        """
        Получить 1-минутные бары для заданного диапазона времени.
        
        :param start_time: Начальное время (включительно)
        :param end_time: Конечное время (ИСКЛЮЧИТЕЛЬНО - не включается)
                         Это нужно для корректной работы с HTF интервалами
                         где end_time указывает на начало СЛЕДУЮЩЕГО бара
        :return: numpy массив формы (N, 5) где:
                 - столбцы 0-3: open, high, low, close
                 - столбец 4: timestamp (datetime64[ns])
                 Если баров нет, возвращает None
        """
        # Конвертируем входные времена в datetime64[ns] для сравнения
        start_ts = np.datetime64(start_time, 'ns')
        end_ts = np.datetime64(end_time, 'ns')
        
        # Быстрая проверка границ
        if self._len == 0:
            return None
        
        if start_ts > self._timestamps[-1] or end_ts < self._timestamps[0]:
            # Диапазон полностью вне данных
            return None
        
        # Бинарный поиск начального индекса (первый >= start_ts)
        start_idx = np.searchsorted(self._timestamps, start_ts, side='left')
        
        # Бинарный поиск конечного индекса (первый >= end_ts)
        # Это исключает бары в момент end_ts, что корректно для HTF интервалов
        # где end_ts указывает на начало СЛЕДУЮЩЕГО бара
        end_idx = np.searchsorted(self._timestamps, end_ts, side='left')
        
        # Проверка, что есть хотя бы один бар в диапазоне
        if start_idx >= end_idx:
            return None
        
        # Срезаем массивы
        data_slice = self._data[start_idx:end_idx]
        timestamps_slice = self._timestamps[start_idx:end_idx]
        
        # Конвертируем timestamps в pd.Timestamp для совместимости с существующим кодом
        # Это необходимо, так как ExecutionEngine ожидает datetime объекты
        timestamps_pd = pd.to_datetime(timestamps_slice)
        
        # Объединяем в один массив: [open, high, low, close, dt]
        # Используем object dtype для последнего столбца, чтобы хранить pd.Timestamp
        result = np.empty((len(data_slice), 5), dtype=object)
        result[:, :4] = data_slice
        result[:, 4] = timestamps_pd
        
        return result
    
    def get_bars_for_htf_bar(self, htf_bar_time: pd.Timestamp, timeframe: str) -> Optional[np.ndarray]:
        """
        Удобный метод для получения 1m баров, соответствующих одному HTF-бару.
        
        :param htf_bar_time: Время HTF-бара (начало диапазона)
        :param timeframe: Таймфрейм HTF (например, '1h', '4h', 'D')
        :return: numpy массив с 1m барами или None
        """
        start_time = pd.Timestamp(htf_bar_time)
        end_time = shift_timestamp(htf_bar_time, 1, timeframe, direction=+1)
        
        # Для корректного включения всех минутных баров в HTF-бар,
        # нужно немного скорректировать end_time (включить его полностью)
        # Но shift_timestamp уже возвращает начало следующего бара, что нам и нужно
        return self.get_bars(start_time, end_time)
    
    def __len__(self) -> int:
        """Возвращает количество 1-минутных баров."""
        return self._len