# Простой тест для проверки Fast1mBarSelector
# src/backtester/engine/test_fast_selector.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.backtester.engine.fast_1m_selector import Fast1mBarSelector


def test_fast_selector():
    """Тест для проверки корректности работы Fast1mBarSelector"""
    
    # Создаем тестовые данные: 1000 минутных баров
    start = datetime(2024, 1, 1, 0, 0, 0)
    timestamps = [start + timedelta(minutes=i) for i in range(1000)]
    
    # Создаем случайные OHLC данные
    np.random.seed(42)
    data = {
        'open': 100 + np.random.randn(1000).cumsum(),
        'high': 100 + np.random.randn(1000).cumsum() + 0.5,
        'low': 100 + np.random.randn(1000).cumsum() - 0.5,
        'close': 100 + np.random.randn(1000).cumsum(),
        'volume': np.random.randint(100, 1000, 1000)
    }
    
    df = pd.DataFrame(data, index=timestamps)
    
    # Инициализируем селектор
    selector = Fast1mBarSelector(df)
    
    # Тест 1: Получение баров для одного часа (60 минут)
    # get_bars_for_htf_bar() передает end_time = начало СЛЕДУЮЩЕГО часа
    # Например для часа 0:00-1:00 она передает (0:00, 1:00)
    # get_bars() с side='left' исключит бар в 1:00
    # Результат: бары 0:00, 0:01, ..., 0:59 = 60 баров (ПРАВИЛЬНО!)
    htf_bar_time = pd.Timestamp(start + timedelta(hours=5))
    bars_1m = selector.get_bars_for_htf_bar(htf_bar_time, '1h')
    
    assert bars_1m is not None, "Должны быть получены бары"
    assert len(bars_1m) == 60, f"Ожидалось 60 баров для 1h, получено {len(bars_1m)}"
    assert bars_1m.shape[1] == 5, "Массив должен иметь 5 столбцов"
    
    # Проверяем, что это именно барыот 5:00 до 5:59
    first_bar_time = bars_1m[0, 4]
    last_bar_time = bars_1m[-1, 4]
    assert first_bar_time == pd.Timestamp(start + timedelta(hours=5)), \
        f"Первый бар должен быть в 5:00, получено {first_bar_time}"
    assert last_bar_time == pd.Timestamp(start + timedelta(hours=5, minutes=59)), \
        f"Последний бар должен быть в 5:59, получено {last_bar_time}"
    
    # Проверяем формат данных
    assert isinstance(bars_1m[0, 4], pd.Timestamp), "Последний столбец должен содержать pd.Timestamp"
    
    # Тест 2: Получение баров для диапазона (явный вызов get_bars())
    # ВАЖНО: end_time теперь исключительно (не включается в результат)
    start_time = pd.Timestamp(start + timedelta(hours=2))
    end_time = pd.Timestamp(start + timedelta(hours=3))  # НЕ включается
    bars_range = selector.get_bars(start_time, end_time)
    
    assert bars_range is not None, "Должны быть получены бары для диапазона"
    assert len(bars_range) == 60, f"Ожидалось 60 баров, получено {len(bars_range)}"
    # Проверяем границы
    assert bars_range[0, 4] == start_time, "Первый бар должен быть в start_time"
    assert bars_range[-1, 4] < end_time, "Последний бар должен быть ДО end_time"
    
    # Тест 3: Пустой диапазон (вне данных)
    future_start = pd.Timestamp(start + timedelta(days=10))
    future_end = pd.Timestamp(start + timedelta(days=11))
    empty_bars = selector.get_bars(future_start, future_end)
    
    assert empty_bars is None, "Для будущего диапазона должен вернуться None"
    
    # Тест 4: Проверка совместимости с ExecutionLoop
    # ExecutionLoop ожидает массив, где можно обратиться к bar[0], bar[1], bar[2], bar[3], bar[4]
    test_bar = bars_1m[0]
    assert len(test_bar) == 5, "Бар должен иметь 5 элементов"
    assert isinstance(test_bar[0], (int, float, np.number)), "bar[0] должен быть числом (open)"
    assert isinstance(test_bar[1], (int, float, np.number)), "bar[1] должен быть числом (high)"
    assert isinstance(test_bar[2], (int, float, np.number)), "bar[2] должен быть числом (low)"
    assert isinstance(test_bar[3], (int, float, np.number)), "bar[3] должен быть числом (close)"
    assert isinstance(test_bar[4], pd.Timestamp), "bar[4] должен быть pd.Timestamp"
    
    # Тест 5: Дополнительная проверка - разные таймфреймы
    print("\nПроверка разных таймфреймов:")
    
    # 4h бар должен содержать 240 минут
    htf_4h = pd.Timestamp(start + timedelta(hours=8))
    bars_4h = selector.get_bars_for_htf_bar(htf_4h, '4h')
    assert bars_4h is not None, "Должны быть получены бары для 4h"
    assert len(bars_4h) == 240, f"Ожидалось 240 баров для 4h, получено {len(bars_4h)}"
    print(f"  4h: получено {len(bars_4h)} баров (корректно)")
    
    # Дневной бар должен содержать 1440 минут (но у нас только 1000)
    # поэтому вернется None или меньше
    htf_d = pd.Timestamp(start)
    bars_d = selector.get_bars_for_htf_bar(htf_d, 'D')
    if bars_d is not None:
        # Дневной бар 2024-01-01 длится до 2024-01-02 00:00
        # В наших данных есть все минуты с 2024-01-01 00:00 до 2024-01-01 16:39
        # Так что получим 1000 баров
        assert len(bars_d) > 0, f"Для дневного бара должны быть бары, получено {len(bars_d)}"
        print(f"  D: получено {len(bars_d)} баров")
    
    print("\nВсе тесты пройдены успешно!")
    print(f"✓ Получено {len(bars_1m)} баров для 1h таймфрейма (60 - ПРАВИЛЬНО!)")
    print(f"✓ Формат данных корректен")
    print(f"✓ Совместимость с ExecutionLoop подтверждена")


if __name__ == "__main__":
    test_fast_selector()
