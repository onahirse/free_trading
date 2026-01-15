import types

import pytest

from src.utils.strategy_loader import (
    ensure_find_entry_point,
    function_to_class_adapter,
    load_strategy_class,
    resolve_strategy_class,
)


def test_load_strategy_class_colon_path_loads_symbol():
    # built-in symbol: types:FunctionType
    obj = load_strategy_class("types:FunctionType")
    assert obj is types.FunctionType


def test_load_strategy_class_dot_path_loads_symbol():
    # built-in symbol: types.FunctionType
    obj = load_strategy_class("types.FunctionType")
    assert obj is types.FunctionType


@pytest.mark.parametrize("bad", [None, "", 123])
def test_load_strategy_class_rejects_invalid_path(bad):
    with pytest.raises(ValueError):
        load_strategy_class(bad)  # type: ignore[arg-type]


def test_function_to_class_adapter_calls_wrapped_function_data_only():
    calls = {"n": 0, "last": None}

    def f(data):
        calls["n"] += 1
        calls["last"] = data
        return {"ok": True, "data": data}

    Strategy = function_to_class_adapter(f)
    s = Strategy(coin={"symbol": "ETH/USDT"}, allowed_min_bars=10, foo="bar")

    assert s.coin["symbol"] == "ETH/USDT"
    assert s.allowed_min_bars == 10
    assert s._params["foo"] == "bar"

    out = s.find_entry_point([1, 2, 3])
    assert out == {"ok": True, "data": [1, 2, 3]}
    assert calls["n"] == 1


def test_function_to_class_adapter_calls_wrapped_function_three_args_then_fallback():
    calls = {"n": 0, "args_len": None}

    def f(data, positions, trading_context):
        calls["n"] += 1
        calls["args_len"] = 3
        return (data, positions, trading_context)

    Strategy = function_to_class_adapter(f)
    s = Strategy()

    out = s.find_entry_point("X")
    assert out == ("X", [], None)
    assert calls["n"] == 1
    assert calls["args_len"] == 3


def test_ensure_find_entry_point_adds_wrapper_when_only_run_present():
    class S:
        def run(self, data, positions=None, trading_context=None):
            return ("ok", data)

    s = ensure_find_entry_point(S())
    assert hasattr(s, "find_entry_point")
    assert s.find_entry_point(123) == ("ok", 123)


def _data_only_func(data):
    return {"data": data}


def test_resolve_strategy_class_wraps_function():
    StrategyClass = resolve_strategy_class(
        "src.utils.tests.test_strategy_loader:_data_only_func"
    )
    assert isinstance(StrategyClass, type)
    s = StrategyClass()
    assert s.find_entry_point([1, 2, 3]) == {"data": [1, 2, 3]}
