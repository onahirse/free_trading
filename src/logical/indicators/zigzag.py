import pandas as pd
import numpy as np

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)
# конфигурация приложения
from src.config.config import config



class ZigZag:
    def __init__(self, coin):
        # Получение настроек индикатора
    #   ZIGZAG_DEPTH: 12
    #   ZIGZAG_DEVIATION: 5
    #   ZIGZAG_BACKTEP: 2
        try:
            self.depth = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEPTH")
            self.deviation = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEVIATION")   
            self.backstep = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_BACKTEP") 
            self.mintick = coin.get("MINIMAL_TICK_SIZE", 0.01)
        except Exception as e:
            logger.error(f"Ошибка при получении настроек индикатора ZigZag: {e}")
            self.depth = 12
            self.deviation = 5
            self.backstep = 2
        
    
    # === Методы класса ===
    
    # ----------------------
    # Расчет индикатора ZigZag
    # ----------------------
    def calculate_zigzag(self, df_data):
        """
        Вычисляет ZigZag индикатор и добавляет его в DataFrame.
        hr = ta.barssince(not (_high[-ta.highestbars(depth)] - _high > deviation*syminfo.mintick)[1])
        
        Оптимизация: работаем с исходным DataFrame, создаем копию только если нужно
        сохранить исходные данные (но в бэктесте это не требуется).
        """
        # Оптимизация: не копируем DataFrame, работаем напрямую
        # В бэктесте df_data создается специально для этого расчета, копия не нужна
        df = df_data
        
        # Расчёт
        df['hr'] = self._calc_hr(df, self.depth, self.deviation, self.mintick)
        df['lr'] = self._calc_lr(df, self.depth, self.deviation, self.mintick)
        
        df['direction'] = self._calc_direction(df['hr'], df['lr'], self.backstep)
       
        direction = df["direction"].to_numpy()
        _high = df["high"].to_numpy()
        _low = df["low"].to_numpy()

            
        # Инициализация z, z1, z2 значениями цен
        z  = df['low'].iloc[-1]
        z_index = df.index[-1]
        
        z1 = df['low'].iloc[-1]
        z1_index = df.index[-1]
        
        z2 = df['high'].iloc[-1]
        z2_index = df.index[-1]
        
        bars = []       
        for i in range(1, len(df)):
            dir_prev = direction[i-1]
            dir_curr = direction[i]
    
            if dir_prev != dir_curr:
                z1 = z2
                z2 = z
                z2_index = z_index
        # === направление вверх ===
            if dir_curr > 0:
                if _high[i] > z2:
                    z2 = _high[i]
                    z2_index = df.index[i]
                    z = _low[i]
                    z_index = df.index[i]
                if _low[i] < z:
                    z = _low[i]
                    z_index = df.index[i]

            # === направление вниз ===
            elif dir_curr < 0:
                if _low[i] < z2:
                    z2 = _low[i]
                    z2_index = df.index[i]
                    z = _high[i]
                    z_index = df.index[i]
                if _high[i] > z:
                    z = _high[i]
                    z_index = df.index[i]

            bars.append({
                    "bar_index": i,
                    "direction": dir_curr,
                    "z": z,
                    "z1": z1,
                    "z2": z2,
                    "z2_index": z2_index
                })

        last_values = {
            'z1': bars[-1]['z1'],
            'z2': bars[-1]['z2'],
            'direction': bars[-1]['direction'],
            'z2_index': bars[-1]['z2_index']
        }
        
        return  last_values  #z1, z2, zz['direction'].iloc[-1], z2_index
    
    # ----------------------
    # Вспомогательные методы для работы с точками ZigZag
    # ----------------------
    
    # === Аналог ta.highestbars() ===
    def _highestbars(self, series: pd.Series, length: int) -> pd.Series:
        """
        Возвращает количество баров назад до максимума за последние length баров.
        Для баров, где недостаточно данных — NaN.
        Устойчиво к nullable dtypes (конвертируем в numpy).
        """
        offsets = []
        n = len(series)
        for i in range(n):
            if i < length - 1:
                offsets.append(np.nan)
            else:
                # окно от i-length+1 до i включительно
                window = series.iloc[i - length + 1 : i + 1]

                # безопасно конвертируем в numpy-массив float (чтобы избежать ExtensionArray проблем)
                arr = window.to_numpy(dtype=float)

                # если все значения nan — возвращаем nan
                if np.all(np.isnan(arr)):
                    offsets.append(np.nan)
                else:
                    # nanargmax вернёт индекс максимального элемента в arr (0..length-1)
                    idx_max = int(np.nanargmax(arr))
                    offsets.append(length - 1 - idx_max)
        return pd.Series(offsets, index=series.index)

    # === Аналог ta.lowestbars() ===
    def _lowestbars(self,series: pd.Series, length: int) -> pd.Series:
        """
        Возвращает количество баров назад до минимума за последние length баров.
        """
        offsets = []
        n = len(series)
        for i in range(n):
            if i < length - 1:
                offsets.append(np.nan)
            else:
                window = series.iloc[i - length + 1 : i + 1]
                arr = window.to_numpy(dtype=float)
                if np.all(np.isnan(arr)):
                    offsets.append(np.nan)
                else:
                    idx_min = int(np.nanargmin(arr))
                    offsets.append(length - 1 - idx_min)
        return pd.Series(offsets, index=series.index)

    # === Аналог ta.barssince() ===
    def _barssince(self, condition: pd.Series) -> pd.Series:
        """
        Возвращает количество баров, прошедших с последнего True.
        Если True ещё не было — NaN.
        """
        result = []
        count = np.nan
        for val in condition:
            if val:
                count = 0
            elif np.isnan(count):
                count = np.nan
            else:
                count += 1
            result.append(count)
        return pd.Series(result, index=condition.index)


    # === hr ===
    def _calc_hr(self,df: pd.DataFrame, depth: int, deviation: float, syminfo_mintick: float) -> pd.Series:
        """
        Аналог PineScript выражения:
        hr = ta.barssince(not (_high[-ta.highestbars(depth)] - _high > deviation * syminfo.mintick)[1])
        """
        _high = df['high']

        # 1. Смещения до максимумов
        offsets = self._highestbars(_high, depth)

        # 2. Значения high на тех барах, где был максимум
        _highest = [
            np.nan if np.isnan(offsets.iloc[i]) or i - int(offsets.iloc[i]) < 0 else _high.iloc[i - int(offsets.iloc[i])]
            for i in range(len(_high))
        ]
        _highest = pd.Series(_highest, index=_high.index)

        # 3. Условие (high[-highestbars] - high) > deviation * mintick
        cond = (_highest - _high) > (deviation * syminfo_mintick)

        # 4. Смещаем на 1 бар назад
        cond_prev = cond.shift(1)

        # 5) привести к булевому типу: NaN -> False (или можно выбрать другое поведение)
        #    затем инвертировать
        cond_prev_bool = cond_prev.astype(bool).fillna(False)
        cond_inv = ~cond_prev_bool

        # 6) barssince
        hr = self._barssince(cond_inv)

        return hr

    # === lr ===
    def _calc_lr(self, df: pd.DataFrame, depth: int, deviation: float, syminfo_mintick: float) -> pd.Series:
        """
        Аналог:
        lr = ta.barssince(not (_low - _low[-ta.lowestbars(depth)] > deviation*syminfo.mintick)[1])
        """
        _low = df['low'].astype(float)
        offsets = self._lowestbars(_low, depth)

        _lowest = []
        for i in range(len(_low)):
            off = offsets.iat[i]
            if pd.isna(off):
                _lowest.append(np.nan)
            else:
                idx = i - int(off)
                _lowest.append(np.nan if idx < 0 else float(_low.iat[idx]))
        _lowest = pd.Series(_lowest, index=_low.index)

        cond = (_low - _lowest) > (deviation * syminfo_mintick)
        cond_prev = cond.shift(1)
        cond_prev_bool = cond_prev.astype(bool).fillna(False)
        cond_inv = ~cond_prev_bool

        return self._barssince(cond_inv)

    # === direction ===
    def _calc_direction(self, hr: pd.Series, lr: pd.Series, backstep: int) -> pd.Series:
        """
        Аналог строки:
        direction = ta.barssince(not (hr > lr)) >= backstep ? -1 : 1
        """
        # 1️⃣ Сравнение hr и lr
        cond = hr > lr

        # 2️⃣ Сдвиг, чтобы условие было как [1] в Pine (если нужно точно 1 бар назад)
        # Если не нужно — можно убрать.
        # cond = cond.shift(1)

        # 3️⃣ Преобразуем NaN → False и делаем инверсию
        cond_bool = cond.fillna(False).astype(bool)
        cond_inv = ~cond_bool

        # 4️⃣ ta.barssince(not (hr > lr))
        bars_since = self._barssince(cond_inv)

        # 5️⃣ Проверяем, >= backstep ?
        direction = np.where(bars_since >= backstep, -1, 1)

        return pd.Series(direction, index=hr.index)
