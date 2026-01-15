from pandas import Timedelta, DateOffset
import pandas as pd
from typing import Optional

from src.utils.logger import get_logger 

logger = get_logger(__name__)

# ====================================================
# Выбор диапазона дат для бэктеста
# ==================================================== 
def select_range_backtest(
    data_df: pd.DataFrame,
    full_datafile: bool,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    offset_bars: int = 0
) -> pd.DataFrame:
    """
    Фильтрация DataFrame по заданному диапазону дат.
    Если full_datafile = True, возвращается исходный DataFrame без изменений.
    
    :param data_df: Исходный DataFrame с колонкой 'timestamp' или индексом datetime
    :param timeframe: Таймфрейм данных (например, '1h', '4h') — используется только если full_datafile=False
    :param full_datafile: Если True — игнорировать даты и вернуть весь data_df
    :param allowed_min_bars: Минимальное количество баров (используется только в оригинальной логике, но здесь не применяется при отключённом смещении)
    :param start_date: Начальная дата в формате, понятном pd.to_datetime (например, '2023-01-01')
    :param end_date: Конечная дата в том же формате
    :return: Отфильтрованный DataFrame
    :raises ValueError: При недопустимых входных данных
    """
    if not isinstance(data_df, pd.DataFrame):
        raise ValueError("data_df должен быть pandas DataFrame")

    if not isinstance(full_datafile, bool):
        raise ValueError("full_datafile должен быть булевым значением")

    if full_datafile:
        return data_df.copy()

    # Проверки на даты
    if start_date is None or end_date is None:
        raise ValueError("При full_datafile=False необходимо указать обе даты: start_date и end_date")

    try:
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)
    except Exception as e:
        raise ValueError(f"Некорректный формат даты: {e}")

    if start_ts > end_ts:
        raise ValueError("start_date не может быть позже end_date")

    # Убедимся, что DataFrame имеет datetime-совместимый индекс или колонку 'timestamp'
    df = data_df.copy()
    if isinstance(df.index, pd.DatetimeIndex):
        time_series = df.index
    elif 'timestamp' in df.columns and pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        time_series = df['timestamp']
    else:
        raise ValueError("DataFrame должен иметь DatetimeIndex или колонку 'timestamp' с datetime типом")

    # ==============================
    # 1. Ищем ближайший индекс >= start_ts
    # ==============================
    try:
        start_idx = time_series.get_indexer([start_ts], method="bfill")[0]
    except:
        start_idx = 0  # безопасный fallback
    # ==============================
    # 2. Отнимаем offset_bars
    # ==============================
    shifted_start_idx = max(0, start_idx - offset_bars)

    # Новый start_ts для фильтрации
    shifted_start_ts = time_series[shifted_start_idx]

    # Фильтрация без смещения
    mask = (time_series >= shifted_start_ts) & (time_series <= end_ts)
    filtered_df = df[mask]

    if filtered_df.empty:
        logger.warning("Выделенный диапазон дат не содержит данных.")

    logger.info(f"📅 Период тестирования: {shifted_start_ts} ↔️  {end_ts}")
    return filtered_df

# def select_range_backtest(data_df, timeframe, full_datafile, allowed_min_bars, start_date = None, end_date = None)  -> pd.DataFrame:
#     """
#     Фильтрация DataFrame по заданному диапазону дат.
#     Если full_datafile = True, то возвращаем исходный DataFrame
    
#     :param data_df: pd.DataFrame — исходный DataFrame с данными
#     :return: pd.DataFrame — отфильтрованный DataFrame
#     """
    

#     if full_datafile:
#         logger.info("Используется полный исторический диапазон. full_datafile = True")
#         return data_df
#     else:
#         start_date = shift_timestamp(start_date, allowed_min_bars, timeframe, direction=-1)
#         logger.info(f"📅 Период тестированияыы: {start_date} ↔️   {end_date}")
#         return select_range(data_df, start_date, end_date)
    
def select_range(data_df, start_date, end_date):
    # Преобразование строковых дат в datetime объекты
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)

    
    # Фильтрация DataFrame по диапазону дат
    filtered_df = data_df[(data_df.index >= start_dt) & (data_df.index <= end_dt)].copy()
    
    return filtered_df

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