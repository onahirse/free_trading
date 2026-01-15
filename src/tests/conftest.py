import pytest
import sys
import os
from unittest.mock import MagicMock

# #region agent log
log_path = r"e:\Developmen\Trading\algo_traid\.cursor\debug.log"
try:
    with open(log_path, "a", encoding="utf-8") as f:
        import json
        log_entry = {
            "sessionId": "debug-session",
            "runId": "import-check",
            "hypothesisId": "A",
            "location": "conftest.py:7",
            "message": "Checking sys.path and import paths",
            "data": {
                "sys_path": sys.path[:5],
                "cwd": os.getcwd(),
                "workspace_root": os.path.abspath(".") if os.path.exists(".") else None
            },
            "timestamp": __import__("time").time() * 1000
        }
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
except Exception:
    pass
# #endregion

# Попытка импорта с разными путями
try:
    from src.tests.mocks.mock_builder import MockPositionBuilder
    from src.tests.mocks.mock_manager import MockPositionManager
    import_style = "src.tests.mocks"
except ImportError as e1:
    try:
        # Попытка добавить корневую директорию в путь
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
        from src.tests.mocks.mock_builder import MockPositionBuilder
        from src.tests.mocks.mock_manager import MockPositionManager
        import_style = "src.tests.mocks (after path fix)"
    except ImportError as e2:
        try:
            from tests.mocks.mock_builder import MockPositionBuilder
            from tests.mocks.mock_manager import MockPositionManager
            import_style = "tests.mocks"
        except ImportError as e3:
            # #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    log_entry = {
                        "sessionId": "debug-session",
                        "runId": "import-check",
                        "hypothesisId": "A,B,C,D",
                        "location": "conftest.py:30",
                        "message": "All import attempts failed",
                        "data": {
                            "error1": str(e1),
                            "error2": str(e2),
                            "error3": str(e3),
                            "sys_path": sys.path
                        },
                        "timestamp": __import__("time").time() * 1000
                    }
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            raise

# #region agent log
try:
    with open(log_path, "a", encoding="utf-8") as f:
        log_entry = {
            "sessionId": "debug-session",
            "runId": "import-check",
            "hypothesisId": "A",
            "location": "conftest.py:45",
            "message": "Import successful",
            "data": {"import_style": import_style},
            "timestamp": __import__("time").time() * 1000
        }
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
except Exception:
    pass
# #endregion


@pytest.fixture
def mock_logger():
    """Фикстура для мок-логгера"""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def mock_manager():
    """Фикстура для мок-менеджера позиций"""
    return MockPositionManager()


@pytest.fixture
def mock_builder():
    """Фикстура для мок-билдера позиций"""
    return MockPositionBuilder()


@pytest.fixture
def mock_coin():
    """Фикстура для мок-конфигурации монеты"""
    return {
        "SYMBOL": "BTC",
        "MINIMAL_TICK_SIZE": "0.01",
        "LEVERAGE": "10",
        "START_DEPOSIT_USDT": "10000",
        "VOLUME_SIZE": "100"
    }


@pytest.fixture
def mock_bar():
    """Фикстура для мок-бара OHLCV"""
    from datetime import datetime, UTC
    return [0, 0, 0, 100, datetime.now(UTC)]
