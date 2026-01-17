"""Простой тест для проверки RSI Scale-In стратегии."""

import pandas as pd
import numpy as np
from decimal import Decimal

from src.logical.strategy.rsi_scale_in.rsi_scale_in_strategy import RSIScaleInStrategy
from src.trading_engine.core.enums import Direction


def create_test_data():
    """Создать тестовые данные с определенным поведением RSI."""
    
    # Создаем синтетические данные с трендом вниз (для LONG сигнала)
    dates = pd.date_range('2025-01-01', periods=200, freq='1h')
    
    # Начальная цена
    base_price = 100.0
    
    # Создаем цены с нисходящим трендом и небольшой волатильностью
    prices = []
    for i in range(200):
        # Тренд вниз с волатильностью
        if i < 100:
            # Плавное снижение
            price = base_price - (i * 0.3) + np.random.normal(0, 1)
        else:
            # Разворот и рост
            price = base_price - 30 + ((i - 100) * 0.4) + np.random.normal(0, 1)
        prices.append(price)
    
    # Создаем OHLC данные
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        high = close + abs(np.random.normal(0, 0.5))
        low = close - abs(np.random.normal(0, 0.5))
        open_price = close + np.random.normal(0, 0.3)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close
        })
    
    df = pd.DataFrame(data, index=dates)
    return df


def test_rsi_calculation():
    """Тест расчета RSI."""
    print("=" * 60)
    print("Тест 1: Расчет RSI индикатора")
    print("=" * 60)
    
    coin = {
        "SYMBOL": "ETH",
        "TIMEFRAME": "1h",
        "START_DEPOSIT_USDT": 1000,
        "MINIMAL_TICK_SIZE": 0.01,
        "LEVERAGE": 1,
        "VOLUME_SIZE": 100
    }
    
    strategy = RSIScaleInStrategy(coin)
    data = create_test_data()
    
    # Расчет RSI
    rsi = strategy.calculate_rsi(data, period=6)
    
    print(f"Всего баров: {len(data)}")
    print(f"RSI рассчитан для: {len(rsi)} баров")
    print(f"\nПоследние 10 значений RSI:")
    print(rsi.tail(10))
    print(f"\nСтатистика RSI:")
    print(f"  Минимум: {rsi.min():.2f}")
    print(f"  Максимум: {rsi.max():.2f}")
    print(f"  Среднее: {rsi.mean():.2f}")
    
    assert len(rsi) == len(data), "RSI должен быть рассчитан для всех баров"
    assert rsi.min() >= 0 and rsi.max() <= 100, "RSI должен быть в диапазоне 0-100"
    
    print("\n✅ Тест пройден!")
    return strategy, data


def test_signal_generation():
    """Тест генерации сигналов."""
    print("\n" + "=" * 60)
    print("Тест 2: Генерация торговых сигналов")
    print("=" * 60)
    
    strategy, data = test_rsi_calculation()
    
    positions = []
    signals_count = 0
    long_signals = 0
    short_signals = 0
    
    # Прогон по барам
    for i in range(strategy.allowed_min_bars, len(data)):
        current_data = data.iloc[:i+1]
        signal = strategy.run(current_data, positions, None)
        
        if not signal.is_no_signal():
            signals_count += 1
            rsi_value = signal.metadata.get('rsi', 0)
            entry_type = signal.metadata.get('entry_type', 'unknown')
            
            if signal.direction == Direction.LONG:
                long_signals += 1
                print(f"\n📈 LONG сигнал на баре {i}:")
            elif signal.direction == Direction.SHORT:
                short_signals += 1
                print(f"\n📉 SHORT сигнал на баре {i}:")
            
            print(f"   Тип: {entry_type}")
            print(f"   RSI: {rsi_value:.2f}")
            print(f"   Цена: {signal.price}")
            print(f"   Объем: {signal.volume}")
            
            if entry_type == 'scale_in':
                scale_count = signal.metadata.get('scale_count', 0)
                multiplier = signal.metadata.get('multiplier', 1)
                print(f"   Докупка №: {scale_count}")
                print(f"   Мультипликатор: {multiplier}x")
    
    print(f"\n{'=' * 60}")
    print(f"Итого сигналов: {signals_count}")
    print(f"  LONG: {long_signals}")
    print(f"  SHORT: {short_signals}")
    
    assert signals_count > 0, "Должны быть сгенерированы сигналы"
    
    print("\n✅ Тест пройден!")


def test_cross_detection():
    """Тест определения пересечений."""
    print("\n" + "=" * 60)
    print("Тест 3: Определение пересечений RSI")
    print("=" * 60)
    
    coin = {
        "SYMBOL": "ETH",
        "TIMEFRAME": "1h",
        "START_DEPOSIT_USDT": 1000,
        "MINIMAL_TICK_SIZE": 0.01,
        "LEVERAGE": 1,
        "VOLUME_SIZE": 100
    }
    
    strategy = RSIScaleInStrategy(coin)
    
    # Тест пересечения сверху вниз (предыдущее значение > уровень, текущее <= уровень)
    rsi_down = pd.Series([40, 38, 36, 34])  # 36 -> 34 это пересечение уровня 35
    cross_down = strategy.detect_rsi_cross(rsi_down, 35, 'down')
    print(f"Пересечение 35 сверху вниз (36→34): {cross_down}")
    assert cross_down == True, f"Должно быть обнаружено пересечение вниз, но получили {cross_down}. Последние значения: {rsi_down.iloc[-2]:.2f} -> {rsi_down.iloc[-1]:.2f}"
    
    # Тест пересечения снизу вверх
    rsi_up = pd.Series([60, 62, 64, 66])  # 64 -> 66 это пересечение уровня 65
    cross_up = strategy.detect_rsi_cross(rsi_up, 65, 'up')
    print(f"Пересечение 65 снизу вверх (64→66): {cross_up}")
    assert cross_up == True, f"Должно быть обнаружено пересечение вверх, но получили {cross_up}. Последние значения: {rsi_up.iloc[-2]:.2f} -> {rsi_up.iloc[-1]:.2f}"
    
    # Тест отсутствия пересечения
    rsi_no_cross = pd.Series([40, 41, 42, 43, 44])
    no_cross = strategy.detect_rsi_cross(rsi_no_cross, 35, 'down')
    print(f"Нет пересечения 35 (44): {no_cross}")
    assert no_cross == False, "Не должно быть пересечения"
    
    print("\n✅ Тест пройден!")


def run_all_tests():
    """Запустить все тесты."""
    print("\n" + "🚀" * 30)
    print("ЗАПУСК ТЕСТОВ RSI SCALE-IN STRATEGY")
    print("🚀" * 30 + "\n")
    
    try:
        test_rsi_calculation()
        test_cross_detection()
        test_signal_generation()
        
        print("\n" + "✅" * 30)
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅" * 30 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ Тест провален: {e}")
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении тестов: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
