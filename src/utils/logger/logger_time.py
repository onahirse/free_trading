import time
from datetime import datetime
import math

# Логирование
# ====================================================
from src.utils.logger.logger import get_logger
logger = get_logger(__name__)


class LoggingTimer:
    """
    Менеджер контекста для логирования времени выполнения задачи.
    Записывает время начала, конца и общее затраченное время.
    """
    def __init__(self, task_name="Задача"):
        self.task_name = task_name

    def __enter__(self):
        # 1. Фиксация и запись времени НАЧАЛА
        self.start_time_raw = time.time()
        self.start_datetime = datetime.now()

        logger.warning(f"[🟢🟢🟢] {self.task_name} / {self.start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 2. Фиксация и запись времени КОНЦА
        self.end_time_raw = time.time()
        self.end_datetime = datetime.now()

        # 3. Расчет и запись ЗАТРАЧЕННОГО ВРЕМЕНИ
        execution_time = self.end_time_raw - self.start_time_raw

        logger.warning(f"[🔴🔴🔴] {self.task_name} / Затрачено времени: {format_time(execution_time)} / {self.end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        
        # Возвращает False, чтобы не подавлять возможные исключения
        return False
    
def format_time(seconds):
    """
    Преобразует общее количество секунд в строку формата ЧЧ:ММ:СС.СССС.
    :param seconds: Время в секундах (может быть float).
    :return: Строка с отформатированным временем.
    """
    if seconds is None:
        return "N/A"
    
    # Гарантируем, что число положительное для корректного расчета
    abs_seconds = abs(seconds)

    # 1. Рассчитываем часы (целое число)
    hours = math.floor(abs_seconds / 3600)
    
    # 2. Рассчитываем минуты (целое число)
    # Остаток от часов (сколько секунд осталось)
    seconds_remaining_after_hours = abs_seconds % 3600
    minutes = math.floor(seconds_remaining_after_hours / 60)
    
    # 3. Рассчитываем секунды (с плавающей точкой)
    # Остаток от минут
    final_seconds = abs_seconds % 60
    
    # Форматирование вывода: 
    # {}:02d для часов и минут (целое число, минимум 2 цифры, с ведущим нулем)
    # {:.4f} для секунд (4 знака после запятой)
    formatted_time = (
        f"{hours:02d} часов, "
        f"{minutes:02d} минут, "
        f"{final_seconds:.4f} секунд"
    )
    
    return formatted_time