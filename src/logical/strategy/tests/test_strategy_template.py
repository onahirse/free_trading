import sys
import os

# ensure repo root is on sys.path so imports like `from src...` work when pytest is run
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pandas as pd
import numpy as np
from decimal import Decimal

from src.logical.strategy.base import BaseStrategy
from src.logical.strategy.conditions import (
    min_bars_condition,
    close_above_ma_condition,
    example_set_volume,
)
from src.logical.strategy.validators import can_execute


def make_df(n=30, start=1.0, step=1.0):
    closes = [start + i * step for i in range(n)]
    data = {
        'open': closes,
        'high': [c + 0.5 for c in closes],
        'low': [c - 0.5 for c in closes],
        'close': closes,
    }
    idx = pd.date_range(end=pd.Timestamp('2026-01-01'), periods=n, freq='T')
    df = pd.DataFrame(data, index=idx)
    return df


def test_min_bars_blocks():
    df = make_df(n=10)
    strategy = BaseStrategy(name='t1')
    strategy.add_condition(min_bars_condition(20))

    signal = strategy.run(df, positions=[])
    assert signal.is_no_signal(), "Strategy should return no_signal when not enough bars"


def test_close_above_ma_allows_and_sets_volume():
    df = make_df(n=30, start=100.0, step=1.0)
    strategy = BaseStrategy(name='t2')
    strategy.add_condition(min_bars_condition(20))
    strategy.add_condition(close_above_ma_condition(20))
    strategy.add_condition(example_set_volume(Decimal('0.5')))

    signal = strategy.run(df, positions=[])
    assert signal.is_entry(), "Expected entry signal when conditions pass"
    assert Decimal(str(df['close'].iloc[-1])) == signal.price
    assert signal.volume == Decimal('0.5')


def test_numpy_input_works():
    df = make_df(n=30, start=10.0)
    # build numpy array: open, high, low, close, timestamp
    cols = [
        df['open'].values.astype(object),
        df['high'].values.astype(object),
        df['low'].values.astype(object),
        df['close'].values.astype(object),
        df.index.astype('datetime64[ns]').astype(str).astype(object),
    ]
    arr = np.column_stack(cols)

    strategy = BaseStrategy(name='t3')
    strategy.add_condition(min_bars_condition(20))
    strategy.add_condition(close_above_ma_condition(10))
    strategy.add_condition(example_set_volume(Decimal('0.1')))

    signal = strategy.run(arr, positions=[])
    assert signal.is_entry()


def test_can_execute_checks():
    df = make_df(n=30, start=50.0)
    strategy = BaseStrategy(name='t4')
    strategy.add_condition(min_bars_condition(20))
    strategy.add_condition(close_above_ma_condition(10))
    strategy.add_condition(example_set_volume(Decimal('1')))

    # by default dry_run True and live_enabled False -> run returns signal but can_execute should block
    strategy.live_enabled = True
    strategy.dry_run = True

    signal = strategy.run(df, positions=[])
    ok, reason = can_execute(strategy, signal, positions=[], trading_context={'available_balance': Decimal('1000'), 'symbol': 'ETH/USDT'})
    assert not ok and reason == 'dry_run_enabled'

    # disable dry_run -> basic risk check will reject because default max_risk_fraction is small
    strategy.dry_run = False
    ok, reason = can_execute(strategy, signal, positions=[], trading_context={'available_balance': Decimal('1000'), 'symbol': 'ETH/USDT'})
    assert not ok and reason == 'notional_exceeds_max_risk_fraction'

    # increase allowed risk fraction so the check passes
    strategy.max_risk_fraction = 0.2
    ok, reason = can_execute(strategy, signal, positions=[], trading_context={'available_balance': Decimal('1000'), 'symbol': 'ETH/USDT'})
    assert ok

    # set max_notional small to force rejection by absolute notional
    strategy.max_notional = Decimal('1')
    ok, reason = can_execute(strategy, signal, positions=[], trading_context={'available_balance': Decimal('1000'), 'symbol': 'ETH/USDT'})
    assert not ok and reason == 'notional_exceeds_max_notional'
