import yaml
import os
from typing import Any, Dict, Tuple
from pathlib import Path
from datetime import datetime

# Путь к файлу конфигурации по умолчанию (предпочтительно относительный к корню проекта)
# Если файл не найден по этому пути, будет использован cwd (как раньше).
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "config.yaml"
CONFIG_FILE_PATH = str(DEFAULT_CONFIG_PATH) if DEFAULT_CONFIG_PATH.exists() else os.path.join(os.getcwd(), "configs", 'config.yaml')


# Определение ожидаемых параметров и их типов
REQUIRED_SETTINGS: Dict[str, Dict[str, Any]] = {
    "EXCHANGE_SETTINGS": {
        "EXCHANGE_ID": str,
        "API_KEY": str,
        "API_SECRET": str,
        "CATEGORY": str,
        "LIMIT": int,
    },
    "STRATEGY_SETTINGS": {
        "MINIMUM_BARS_FOR_STRATEGY_CALCULATION": int,
        "ZIGZAG_DEPTH": (int, float),
        "ZIGZAG_DEVIATION": (int, float),
        "ZIGZAG_BACKTEP": (int, float),
        "FIBONACCI_LEVELS": list,
    },
    "RISK_SETTINGS": {
        "STOP_LOSS_PERCENT": (int, float),
        "TAKE_PROFIT_PERCENT": (int, float),
        "MAX_POSITIONS": int,
    },
    "BACKTEST_SETTINGS": {
        "DATA_DIR": str,
        "REPORT_DIRECTORY": str,
        "TEMPLATE_DIRECTORY": str,
        "FULL_DATAFILE": bool
    },
    "LOGGING_SETTINGS": {
        "LEVEL": str,
        "LOG_DIR": str,
        "FILENAME": str,
        "MAX_BYTES": int,
        "BACKUP_COUNT": int
    },
    "TELEGRAM_SETTINGS": {
        "TOKEN": str,
        "ADMIN_ID": int,
        "CHANNEL_ID": int
    },
    "SCHEDULER_SETTINGS": {
        "ENABLED": bool,
        "TIMEZONE": str
    }
}


# Определение ожидаемых параметров и их типов для каждого элемента в массиве COINS
REQUIRED_COIN_FIELDS: Dict[str, Any] = {
    "SYMBOL": str,
    "TIMEFRAME": str,
    "AUTO_TRADING": bool,
    "START_DEPOSIT_USDT": (int, float),
    "LEVERAGE": (int, float),
    "MINIMAL_TICK_SIZE": (int, float), # Минимальный размер шага цены
    "VOLUME_SIZE": (int, float)
}

class ConfigValidationError(Exception):
    """Кастомное исключение для ошибок валидации конфигурации."""
    pass

class ConfigManager:
    """
    Класс для загрузки, парсинга и предоставления доступа к настройкам из config.yml.
    """
    def __init__(self, config_path: str = CONFIG_FILE_PATH):
        self.config_path = config_path
        self._config = self._load_config()
        # Вызов функции валидации сразу после загрузки
        self._validate_config()
        

    def _load_config(self) -> dict:
        """Загружает и возвращает данные из YAML-файла."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
            # Не выводим содержимое или секреты — только путь
            print(f"✅ Конфигурация успешно загружена из: {self.config_path}")
            return config_data
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Файл конфигурации не найден по пути: {self.config_path}")
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"❌ Ошибка парсинга YAML-файла: {e}")
        
    def _validate_config(self):
        """Проверяет наличие и тип всех обязательных параметров."""
        print("🔍 Запуск валидации конфигурации...")
        errors = []
        warnings = []

        def _type_name(expected: Any) -> str:
            """Возвращает читаемое имя для expected type (поддерживает кортежы)."""
            if isinstance(expected, tuple):
                return " or ".join([t.__name__ for t in expected])
            try:
                return expected.__name__
            except Exception:
                return str(expected)

        def _is_instance_of_expected(value: Any, expected: Any) -> bool:
            # None is considered invalid by default (explicit checks may allow None)
            try:
                return isinstance(value, expected)
            except TypeError:
                # If expected is something else, fall back to simple comparison
                return False
        
        # 1. Проверка наличия и типа основных параметров
        for section, settings in REQUIRED_SETTINGS.items():
            if section not in self._config:
                errors.append(f"Отсутствует обязательная секция: {section}")
                continue

            for key, expected_type in settings.items():
                if key not in self._config[section]:
                    errors.append(f"Отсутствует обязательный параметр: [{section}][{key}]")
                    continue

                value = self._config[section][key]
                if value is None:
                    errors.append(f"Некорректный тип для [{section}][{key}]. Ожидается {_type_name(expected_type)}, но получено None.")
                    continue

                if not _is_instance_of_expected(value, expected_type):
                    errors.append(
                        f"Некорректный тип для [{section}][{key}]. Ожидается {_type_name(expected_type)}, но получено {type(value).__name__}."
                    )

        # 2. **НОВАЯ ПРОВЕРКА**: Проверка массива COINS
        if 'COINS' not in self._config:
            errors.append("Отсутствует обязательный массив: [COINS]")
        else:
            coins_list = self._config['COINS']
            if not isinstance(coins_list, list):
                errors.append(f"[COINS] должен быть списком (массивом). Получено: {type(coins_list).__name__}")
            elif not coins_list:
                errors.append("Массив [COINS] не должен быть пустым.")
            else:
                # Перебор каждой монеты в массиве
                for i, coin in enumerate(coins_list):
                    if not isinstance(coin, dict):
                        errors.append(f"[COINS][{i}]: Элемент должен быть объектом (словарем). Получено: {type(coin).__name__}")
                        continue

                    for key, expected_type in REQUIRED_COIN_FIELDS.items():
                        if key not in coin:
                            errors.append(f"[COINS][{i}] ({coin.get('SYMBOL', 'UNKNOWN')}): Отсутствует обязательный параметр: {key}")
                            continue

                        value = coin[key]
                        # Проверка типа
                        if value is None:
                            errors.append(
                                f"[COINS][{i}] ({coin.get('SYMBOL', 'UNKNOWN')}): Некорректный тип для '{key}'. Ожидается {_type_name(expected_type)}, но получено None."
                            )
                            continue

                        if not _is_instance_of_expected(value, expected_type):
                            errors.append(
                                f"[COINS][{i}] ({coin.get('SYMBOL', 'UNKNOWN')}): Некорректный тип для '{key}'. Ожидается {_type_name(expected_type)}, но получено {type(value).__name__}."
                            )
                            continue

                        # Дополнительные семантические проверки
                        if key in ("START_DEPOSIT_USDT", "LEVERAGE", "MINIMAL_TICK_SIZE", "VOLUME_SIZE"):
                            try:
                                numeric = float(value)
                                if numeric <= 0 and key != "VOLUME_SIZE":
                                    errors.append(f"[COINS][{i}] ({coin.get('SYMBOL','UNKNOWN')}): '{key}' должен быть > 0.")
                                if key == "VOLUME_SIZE" and numeric < 0:
                                    errors.append(f"[COINS][{i}] ({coin.get('SYMBOL','UNKNOWN')}): '{key}' не может быть отрицательным.")
                            except Exception:
                                errors.append(f"[COINS][{i}] ({coin.get('SYMBOL','UNKNOWN')}): '{key}' должен быть числом.")
                        if key == "TIMEFRAME" and (not isinstance(value, str) or not value.strip()):
                            errors.append(f"[COINS][{i}] ({coin.get('SYMBOL','UNKNOWN')}): 'TIMEFRAME' должен быть непустой строкой.")
            
        
        
        # Базовые проверки и дополнительные семантические проверки

        # Проверка FIBONACCI_LEVELS
        try:
            fib = self._config.get("STRATEGY_SETTINGS", {}).get("FIBONACCI_LEVELS")
            if fib is None:
                errors.append("[STRATEGY_SETTINGS][FIBONACCI_LEVELS] отсутствует или имеет значение None.")
            elif not isinstance(fib, list):
                errors.append("[STRATEGY_SETTINGS][FIBONACCI_LEVELS] должен быть списком.")
            elif not fib:
                errors.append("[STRATEGY_SETTINGS][FIBONACCI_LEVELS] не должен быть пустым.")
            else:
                for j, lvl in enumerate(fib):
                    if not isinstance(lvl, dict):
                        errors.append(f"[STRATEGY_SETTINGS][FIBONACCI_LEVELS][{j}] должен быть объектом (dict). Получено: {type(lvl).__name__}")
                        continue
                    if 'level' not in lvl:
                        errors.append(f"[STRATEGY_SETTINGS][FIBONACCI_LEVELS][{j}]: отсутствует ключ 'level'.")
                        continue
                    try:
                        lvl_val = float(lvl['level'])
                        if lvl_val <= 0:
                            errors.append(f"[STRATEGY_SETTINGS][FIBONACCI_LEVELS][{j}]: 'level' должно быть > 0.")
                    except Exception:
                        errors.append(f"[STRATEGY_SETTINGS][FIBONACCI_LEVELS][{j}]: 'level' должно быть числом.")
                    if 'volume' in lvl:
                        try:
                            vol = float(lvl['volume'])
                            if vol < 0 or vol > 1:
                                warnings.append(f"[STRATEGY_SETTINGS][FIBONACCI_LEVELS][{j}]: 'volume' обычно в диапазоне [0,1]. Текущее значение: {vol}")
                        except Exception:
                            errors.append(f"[STRATEGY_SETTINGS][FIBONACCI_LEVELS][{j}]: 'volume' должно быть числом.")
        except Exception:
            # defensive
            errors.append("Ошибка при проверке FIBONACCI_LEVELS.")

        # Проверки BACKTEST_SETTINGS: даты
        try:
            bt = self._config.get('BACKTEST_SETTINGS', {})
            full = bt.get('FULL_DATAFILE')
            start = bt.get('START_DATE')
            end = bt.get('END_DATE')
            if full is False:
                if not start or not end:
                    errors.append("Если BACKTEST_SETTINGS.FULL_DATAFILE = False, то нужны START_DATE и END_DATE.")
                else:
                    try:
                        sd = datetime.strptime(start, '%Y-%m-%d')
                        ed = datetime.strptime(end, '%Y-%m-%d')
                        if sd >= ed:
                            errors.append("BACKTEST_SETTINGS: START_DATE должен быть раньше END_DATE.")
                    except Exception:
                        errors.append("BACKTEST_SETTINGS: START_DATE и END_DATE должны быть в формате YYYY-MM-DD.")
        except Exception:
            errors.append("Ошибка при проверке BACKTEST_SETTINGS.")

        # Логирование: LEVEL
        try:
            log_level = self._config.get('LOGGING_SETTINGS', {}).get('LEVEL')
            if log_level and isinstance(log_level, str):
                allowed = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
                if str(log_level).upper() not in allowed:
                    warnings.append(f"LOGGING_SETTINGS.LEVEL '{log_level}' не в списке {allowed}. Рекомендуется: {allowed}.")
        except Exception:
            warnings.append("Ошибка при проверке LOGGING_SETTINGS.LEVEL.")

        # EXCHANGE_SETTINGS: если не demo, требуем ключи
        try:
            exch = self._config.get('EXCHANGE_SETTINGS', {})
            demo = exch.get('DEMO') if isinstance(exch, dict) else True
            testnet = exch.get('TESTNET') if isinstance(exch, dict) else False
            api_key = exch.get('API_KEY') if isinstance(exch, dict) else None
            api_secret = exch.get('API_SECRET') if isinstance(exch, dict) else None
            if not demo and not testnet:
                if not api_key or not str(api_key).strip():
                    errors.append("EXCHANGE_SETTINGS: API_KEY обязателен для режима не-DEMO и не-TESTNET.")
                if not api_secret or not str(api_secret).strip():
                    errors.append("EXCHANGE_SETTINGS: API_SECRET обязателен для режима не-DEMO и не-TESTNET.")
        except Exception:
            errors.append("Ошибка при проверке EXCHANGE_SETTINGS.")

        # Вывод результатов валидации
        if warnings:
            print("⚠️ Предупреждения конфигурации:")
            for w in warnings:
                print(f"- {w}")

        if errors:
            error_message = "\n\n❌ ОШИБКА ВАЛИДАЦИИ КОНФИГУРАЦИИ (config.yml):\n"
            error_message += "\n".join([f"- {err}" for err in errors])
            error_message += "\n\nПожалуйста, исправьте файл config.yml и перезапустите."
            raise ConfigValidationError(error_message)

        print("✅ Валидация конфигурации успешно пройдена.")
    
    def get_setting(self, section: str, key: str, logger=None):
        """Возвращает конкретную настройку по секции и ключу."""
        # ... (Код без изменений)
        if section in self._config and key in self._config[section]:
            return self._config[section][key]
        else:
            # Во время runtime мы предполагаем, что _validate_config уже нашел все критические ошибки,
            # но для безопасности можно оставить эту проверку.
            if logger:
                logger.error(f"❌ Настройка '{key}' не найдена в секции '{section}'.")
            # return None 
            raise KeyError(f"Настройка '{key}' не найдена в секции '{section}'.")

    def get_section(self, section: str, logger=None) -> dict:
        """Возвращает всю секцию настроек."""
        if section in self._config:
            return self._config[section]
        else:
            
            if logger:
                logger.error(f"❌ Секция '{section}' не найдена в файле конфигурации.")

            raise KeyError(f"❌ Секция '{section}' не найдена в файле конфигурации.")

try:
    config = ConfigManager()
except (FileNotFoundError, yaml.YAMLError, ConfigValidationError) as e:
    # Важно: При ошибке валидации или загрузки, программа должна быть остановлена
    print(f"\nFATAL ERROR: {e}")
    # Вы можете добавить здесь os._exit(1) для принудительной остановки, 
    # если это главный скрипт
    raise SystemExit(1)

# # Создание синглтона для доступа к конфигурации
# config = ConfigManager()