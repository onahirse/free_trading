# logger.py
import logging
import logging.handlers
import os


from rich.logging import RichHandler
from src.config.config import config # Импортируем наш модуль конфигурации

class LoggerManager:
    """
    Класс для настройки и получения централизованного Logger.
    Использует RotatingFileHandler для управления размером и количеством файлов.
    """
    
    def __init__(self):
        # 1. Получение настроек логирования
        log_settings = config.get_section("LOGGING_SETTINGS")
        
        self.log_level = log_settings["LEVEL"].upper()
        self.log_dir = log_settings["LOG_DIR"]
        self.log_file = os.path.join(self.log_dir, log_settings["FILENAME"])
        self.max_bytes = log_settings["MAX_BYTES"]
        self.backup_count = log_settings["BACKUP_COUNT"]
        
        # Убедимся, что директория для логов существует
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # 2. Форматтер
        # Добавляем %(name)s (имя Logger, т.е. модуля) для поддержки модульности
        self.formatter = logging.Formatter(
            '%(message)s'
        )
        self.formatter_files = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )   

        # 3. Базовая настройка
        # Устанавливаем корневой уровень для всего приложения
        logging.getLogger().setLevel(self.log_level)
        
        # Настройка файлового обработчика
        self._setup_file_handler()
        
        # Настройка консольного обработчика
        self._setup_console_handler()
        
        # Выводим информацию об успешной настройке
        self.get_logger(__name__).info("Система логирования инициализирована.")


    def _setup_file_handler(self):
        """Настраивает обработчик для записи в файл с ротацией."""
        # 'a' - режим добавления (append)
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(self.formatter_files)
        logging.getLogger().addHandler(file_handler)
        
        self.get_logger(__name__).info(
            f"Логирование в файл: {self.log_file} (Max size: {self.max_bytes / 1024**2:.2f} MB, Backups: {self.backup_count})"
        )

    def _setup_console_handler(self):
        """Настраивает обработчик для вывода в консоль."""
        # console_handler = logging.StreamHandler()
        console_handler = RichHandler(
            markup=True,
            rich_tracebacks=True,
            show_time=True,
            show_level=True,
            show_path=True,
            enable_link_path = True
        )
        console_handler.setFormatter(self.formatter)
        logging.getLogger().addHandler(console_handler)

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Статический метод для получения Logger в любом модуле.
        Имя Logger должно соответствовать имени модуля (используйте __name__).
        """
        return logging.getLogger(name)

# Инициализируем систему логирования один раз при запуске приложения
log_manager = LoggerManager()

# Статический метод для простого импорта в других модулях
get_logger = LoggerManager.get_logger

from src.utils.logger_time import LoggingTimer  as LoggingTimer # Импортируем LoggingTimer для использования в других модулях 

