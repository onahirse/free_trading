# tests/test_data_fetcher.py
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest
from src.data_fetcher.data_fetcher import DataFetcher


@pytest.fixture
def mock_coin():
    return {
        "SYMBOL": "BTC",
        "TIMEFRAME": "1h",
        "MIN_TIMEFRAME": "1"
    }

@pytest.fixture
def mock_exchange():
    return {
        "EXCHANGE_ID": "binance",
        "LIMIT": 500
    }

@pytest.fixture
def data_fetcher(mock_coin, mock_exchange):
    tmpdir = tempfile.mkdtemp()
    try:
        df = DataFetcher(coin=mock_coin, exchange=mock_exchange, directory=tmpdir + os.sep)
        yield df
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ===== ИНИЦИАЛИЗАЦИЯ =====

def test_init_sets_attributes_correctly(data_fetcher):
    assert data_fetcher.symbol == "BTC/USDT"
    assert data_fetcher.timeframe == "1h"
    assert data_fetcher.min_timeframe == "1"
    assert data_fetcher.exchange_id == "binance"
    assert data_fetcher.limit == 500


# ===== ДАТЫ =====

def test_convert_date_to_ms_start(data_fetcher):
    ms = data_fetcher._convert_date_to_ms("2023-01-01", is_end_date=False)
    expected = pd.Timestamp("2023-01-01 00:00:00").value // 1_000_000  # nanos → ms
    assert ms == expected

def test_convert_date_to_ms_end(data_fetcher):
    ms = data_fetcher._convert_date_to_ms("2023-01-01", is_end_date=True)
    expected = pd.Timestamp("2023-01-01 23:59:59.999").value // 1_000_000
    assert ms == expected

def test_convert_date_invalid_format(data_fetcher):
    with pytest.raises(ValueError):
        data_fetcher._convert_date_to_ms("01-01-2023")


# ===== ПУТИ ЭКСПОРТА =====

def test_get_export_path_csv(data_fetcher):
    path = data_fetcher._get_export_path("15m", "csv")
    assert "csv_files" in path
    assert "BTC_USDT_15m_binance_OHLCV.csv" in path
    assert os.path.dirname(path).endswith("csv_files")

def test_get_export_path_xlsx(data_fetcher):
    path = data_fetcher._get_export_path("1h", "xlsx")
    assert "excel" in path
    assert "BTC_USDT_1h_binance_OHLCV.xlsx" in path


# ===== ЗАГРУЗКА ДАННЫХ (МОКИ) =====

@patch("src.data_fetcher.data_fetcher.ccxt")
def test_generic_fetcher_successful(mock_ccxt, data_fetcher):
    # Мок биржи
    mock_exchange = MagicMock()
    mock_ccxt.binance.return_value = mock_exchange

    # Данные: 2 свечи (timestamp в ms)
    ohlcv_data = [
        [1672531200000, 20000, 21000, 19000, 20500, 100],
        [1672534800000, 20500, 21500, 20000, 21000, 120]
    ]
    mock_exchange.fetch_ohlcv.return_value = ohlcv_data
    mock_exchange.rateLimit = 100

    data_fetcher._set_exchange()

    # Мок time.time()
    with patch("src.data_fetcher.data_fetcher.time.time", return_value=1672534800.0):  # соответствует 2-й свече
        df = data_fetcher._generic_fetcher("1h", start_date_ms=1672531200000 - 1, end_date_ms=1672534800000)

    assert df is not None
    assert len(df) == 2
    assert df.index[0] == pd.to_datetime("2023-01-01 00:00:00")
    assert df["close"].iloc[0] == 20500


@patch("src.data_fetcher.data_fetcher.ccxt")
def test_generic_fetcher_empty_response(mock_ccxt, data_fetcher):
    mock_exchange = MagicMock()
    mock_ccxt.binance.return_value = mock_exchange
    mock_exchange.fetch_ohlcv.return_value = []

    data_fetcher._set_exchange()
    with patch("src.data_fetcher.data_fetcher.time.time", return_value=1672534800.0):
        df = data_fetcher._generic_fetcher("1h")

    assert df is None


# ===== ЭКСПОРТ И ИМПОРТ =====

def test_export_to_csv(data_fetcher):
    df = pd.DataFrame({
        'open': [100],
        'high': [110],
        'low': [90],
        'close': [105],
        'volume': [10]
    }, index=[pd.to_datetime("2023-01-01")] )
    df.index.name = 'timestamp'

    path = data_fetcher.export_to_csv(df, "1h")
    assert path is not None
    assert os.path.exists(path)

    # Проверка чтения обратно
    df_loaded = pd.read_csv(path, index_col=0, parse_dates=True)
    pd.testing.assert_frame_equal(df, df_loaded)


def test_load_from_csv(data_fetcher):
    # Сначала создадим файл
    df_orig = pd.DataFrame({
        'open': [200.0, 205.0],
        'high': [210.0, 215.0],
        'low': [195.0, 200.0],
        'close': [205.0, 210.0],
        'volume': [50.0, 60.0]
    }, index=pd.to_datetime(["2023-01-01", "2023-01-02"]))
    df_orig.index.name = 'timestamp'

    path = data_fetcher.export_to_csv(df_orig, "1h")
    assert path is not None

    # Теперь загрузим
    df_loaded = data_fetcher.load_from_csv("csv", "1h")
    assert df_loaded is not None
    pd.testing.assert_frame_equal(df_orig, df_loaded)


def test_load_from_csv_file_not_found(data_fetcher):
    df = data_fetcher.load_from_csv("csv", "1h")
    assert df is None  # файл не создавался → вернёт None


# ===== ОШИБКИ =====

def test_fetch_history_range_invalid_dates(data_fetcher):
    with patch.object(data_fetcher, '_convert_date_to_ms', side_effect=[1672534800000, 1672531200000]):  # end < start
        df = data_fetcher.fetch_history_range("1h", "2023-01-02", "2023-01-01")
        assert df is None