# ZigZag + Fibonacci strategy adapter

Описание
--------
Этот модуль предоставляет адаптацию оригинальной стратегии `zigzag_and_fibo.py` к новому
шаблону стратегий. Теперь стратегия совместима с `BaseStrategy` и с инфраструктурой
валидации/исполнения (validators, trading_context).

Файлы
-----
- `zigzag_fibo_strategy.py` — класс `ZigZagFiboStrategy`, реализует `run(data, positions, trading_context)`
  и возвращает объект `Signal`.
- `zigzag_and_fibo.py` — оригинальная реализация (не трогается).

Как это работает
----------------
1. `ZigZagFiboStrategy` создаётся с объектом `coin` (словарь с настройками монеты).
2. При вызове `run` данные приводятся к pandas.DataFrame (или принимаются как DataFrame).
3. Вычисляются ZigZag и уровни Фибоначчи через существующие функции `calculate_indicators`.
4. Применяются те же правила, что в оригинальной стратегии:
   - проверяется, что ближайшая z2-точка находится в текущем баре или в допустимом смещении;
   - сравнивается текущая цена с уровнем 78.6 для определения направления;
   - формируются TP/SL по рассчитанным уровням;
   - объём считается с помощью `RiskManager` (как в оригинале).
5. Возвращается `Signal.entry` или `Signal.no_signal`.

Параметры и безопасность
-------------------------
- `allowed_min_bars`, `ALLOWED_Z2_OFFSET` и имя стратегии читаются из `configs` через `config.get_setting(...)` —
  это сохраняет совместимость с существующими настройками.
- Для live-исполнения стратегия поддерживает флаги `live_enabled` и `dry_run` (унаследованы от `BaseStrategy`).

Пример использования
--------------------
```python
from decimal import Decimal
import pandas as pd
from src.logical.strategy.zigzag_fibo.zigzag_fibo_strategy import ZigZagFiboStrategy

# coin — словарь с параметрами монеты (используется в RiskManager и для symbol/timeframe)
coin = {
    'SYMBOL': 'ETH',
    'TIMEFRAME': '1',
    # другие параметры, необходимые RiskManager
}

strategy = ZigZagFiboStrategy(coin)

# В тестах/бэктесте передаём DataFrame или numpy массив с колонками [open, high, low, close, timestamp]
df = pd.read_csv('DATA_OHLCV/csv_files/ETH_USDT_1_bybit_OHLCV.csv')
df.columns = [c.lower() for c in df.columns]

signal = strategy.run(df, positions=[], trading_context={'available_balance': Decimal('1000'), 'symbol': 'ETH/USDT'})
print(signal)

# Перед исполнением в live используйте validators.can_execute(strategy, signal, positions, trading_context)
```

# TODO Дополнения и расширения
-----------------------
- Можно унаследовать `ZigZagFiboStrategy` и переопределить методы (например, `calculate_volume`),
  или добавить дополнительные условия через `BaseStrategy` (путём добавления `conditions`).
- Рекомендуется дополнить `validators` более жёсткими проверками для реальной торговли: учёт плеча,
  требования маржи, частота ордеров, проверка открытых позиций на совместимость.

Если нужно, добавлю пример интеграции с исполнителем (order manager) и покажу,
какие поля `trading_context` передавать для корректной проверки (balance, leverage, free_margin и т.д.).
