"""Тест закрытия позиций RSI Scale-In стратегии."""

import pandas as pd
import numpy as np
from decimal import Decimal

from src.logical.strategy.rsi_scale_in.rsi_scale_in_strategy import RSIScaleInStrategy
from src.trading_engine.core.enums import Direction, Position_Status, SignalType
from src.trading_engine.core.position import Position


def test_position_closing():
    """Тест закрытия позиций по обратному сигналу."""
    print("\n" + "=" * 60)
    print("ТЕСТ ЗАКРЫТИЯ ПОЗИЦИЙ")
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
    
    # Создаем тестовые данные с четким паттерном
    # RSI идет от 40 -> 30 (LONG вход) -> 20 -> 40 -> 70 (закрытие LONG)
    dates = pd.date_range('2025-01-01', periods=150, freq='1h')
    
    # Генерируем цены, чтобы получить нужный паттерн RSI
    prices = []
    for i in range(150):
        if i < 40:
            # Падение - RSI снижается к 30
            price = 100 - (i * 1.2) + np.random.normal(0, 0.3)
        elif i < 70:
            # Боковик на низком уровне - RSI около 30-40
            price = 52 + np.random.normal(0, 1.5)
        elif i < 100:
            # Резкий рост - RSI растет к 70
            price = 52 + ((i - 70) * 1.0) + np.random.normal(0, 0.5)
        elif i < 130:
            # Боковик на высоком уровне - RSI около 60-70
            price = 82 + np.random.normal(0, 1.5)
        else:
            # Падение - RSI снижается обратно к 30
            price = 82 - ((i - 130) * 1.5) + np.random.normal(0, 0.5)
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
    
    # Рассчитываем RSI
    rsi = strategy.calculate_rsi(df, period=6)
    
    print(f"Всего баров: {len(df)}")
    print(f"\nСтатистика RSI:")
    print(f"  Минимум: {rsi.min():.2f}")
    print(f"  Максимум: {rsi.max():.2f}")
    print(f"  Среднее: {rsi.mean():.2f}")
    
    # Симулируем торговлю
    positions = []
    signals_log = []
    
    print(f"\n{'='*60}")
    print("СИМУЛЯЦИЯ ТОРГОВЛИ")
    print(f"{'='*60}\n")
    
    for i in range(strategy.allowed_min_bars, len(df)):
        current_data = df.iloc[:i+1]
        current_rsi = rsi.iloc[i]
        current_price = df.iloc[i]['close']
        
        # Получаем сигнал
        signal = strategy.run(current_data, positions, None)
        
        # Дебаг логирование
        if len(positions) > 0 and i % 10 == 0:
            pos_directions = [p.direction.value for p in positions]
            should_close = strategy.should_close_position(positions, rsi.iloc[:i+1])
            print(f"   [Дебаг] Бар {i}: RSI={current_rsi:.2f}, Позиций={len(positions)} ({pos_directions}), "
                  f"Should Close={should_close}, Сигнал={signal.signal_type.value}")
        
        if not signal.is_no_signal():
            signal_info = {
                'bar': i,
                'rsi': current_rsi,
                'price': current_price,
                'type': signal.signal_type.value,
                'direction': signal.direction.value if signal.direction else None
            }
            signals_log.append(signal_info)
            
            # Обработка сигнала
            if signal.is_entry() and signal.direction:
                # Создаем mock позицию
                mock_position = Position(
                    symbol="ETH/USDT",
                    direction=signal.direction,
                    tick_size=Decimal("0.01"),
                    source=strategy.name
                )
                mock_position.status = Position_Status.ACTIVE
                positions.append(mock_position)
                
                print(f"📊 Бар {i} | RSI: {current_rsi:.2f} | Цена: {current_price:.2f}")
                print(f"   ✅ {signal.direction.value} ENTRY")
                print(f"   Открытых позиций: {len(positions)}\n")
                
            elif signal.signal_type == SignalType.CLOSE:
                # Закрываем позицию
                if positions:
                    positions = []
                    print(f"📊 Бар {i} | RSI: {current_rsi:.2f} | Цена: {current_price:.2f}")
                    print(f"   ❌ CLOSE POSITION")
                    print(f"   Открытых позиций: {len(positions)}\n")
    
    # Анализ результатов
    print(f"{'='*60}")
    print("РЕЗУЛЬТАТЫ")
    print(f"{'='*60}\n")
    
    entry_signals = [s for s in signals_log if s['type'] == 'ENTRY']
    close_signals = [s for s in signals_log if s['type'] == 'CLOSE']
    
    print(f"Всего сигналов: {len(signals_log)}")
    print(f"  ENTRY сигналов: {len(entry_signals)}")
    print(f"  CLOSE сигналов: {len(close_signals)}")
    
    # Проверка LONG циклов
    long_entries = [s for s in entry_signals if s['direction'] == 'LONG']
    print(f"\nLONG позиции: {len(long_entries)}")
    for entry in long_entries:
        print(f"  Открытие на баре {entry['bar']}: RSI={entry['rsi']:.2f}, Цена={entry['price']:.2f}")
    
    # Проверка SHORT циклов
    short_entries = [s for s in entry_signals if s['direction'] == 'SHORT']
    print(f"\nSHORT позиции: {len(short_entries)}")
    for entry in short_entries:
        print(f"  Открытие на баре {entry['bar']}: RSI={entry['rsi']:.2f}, Цена={entry['price']:.2f}")
    
    print(f"\nЗакрытие позиций:")
    for close in close_signals:
        print(f"  Закрытие на баре {close['bar']}: RSI={close['rsi']:.2f}, Цена={close['price']:.2f}")
    
    # Проверки
    print(f"\n{'='*60}")
    print("ПРОВЕРКИ")
    print(f"{'='*60}\n")
    
    if len(close_signals) > 0:
        print("✅ ТЕСТ ПРОЙДЕН: Сигналы на закрытие генерируются!")
        print(f"   Обнаружено {len(close_signals)} сигналов на закрытие")
    else:
        print("❌ ТЕСТ ПРОВАЛЕН: Нет сигналов на закрытие позиций!")
        print("   Проверьте логику should_close_position()")
    
    # Проверка на незакрытые позиции
    if len(positions) > 0:
        print(f"\n⚠️  ВНИМАНИЕ: Остались открытые позиции: {len(positions)}")
    else:
        print(f"\n✅ Все позиции закрыты")
    
    return len(close_signals) > 0


if __name__ == "__main__":
    print("\n" + "🔍" * 30)
    print("ТЕСТ ЗАКРЫТИЯ ПОЗИЦИЙ RSI SCALE-IN STRATEGY")
    print("🔍" * 30)
    
    try:
        success = test_position_closing()
        
        if success:
            print("\n" + "✅" * 30)
            print("ТЕСТ УСПЕШНО ПРОЙДЕН!")
            print("✅" * 30 + "\n")
        else:
            print("\n" + "❌" * 30)
            print("ТЕСТ ПРОВАЛЕН!")
            print("❌" * 30 + "\n")
            
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении теста: {e}")
        import traceback
        traceback.print_exc()
