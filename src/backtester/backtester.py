# backtest	Тестирование стратегии на исторических данных.	
# Симуляция выполнения сделок. 
# Расчет метрик производительности (прибыльность, просадка, Sharpe Ratio).
import concurrent.futures
from threading import Lock


# Логирование
# ====================================================
from src.utils.logger.logger import get_logger
logger = get_logger(__name__)
from src.utils.logger.logger_time import LoggingTimer
from src.config.config import config

# Подключение модуля с загрузчиком данных
from src.data_fetcher.data_fetcher import DataFetcher
from src.data_fetcher.utils import select_range_backtest
import pandas as pd

from src.backtester.reports.collector import SummaryCollector
from src.backtester.reports.single_test.test_report_generator import TestReportGenerator
from src.backtester.reports.summary.summary_report_generator import SummaryReportGenerator
from src.backtester.reports.paths import (
    build_test_report_path,
    build_summary_report_path,
)


    
# -------------------------
# Manager & Executor
# -------------------------
class TestManager:
    """
    Управление тестами: запуск, получение списка позиций, подсчет статистики.
    Проведение паралельное тестирования 
    """
    def __init__(self):
        # Параметры биржи
        self.exchange = config.get_section("EXCHANGE_SETTINGS")
        # Получение массива монет из конфигурации
        self.coins_list = config.get_section("COINS")
        # Параметры бэктеста
        self.settings_test = config.get_section("BACKTEST_SETTINGS")
        self.settings_strategy = config.get_section("STRATEGY_SETTINGS")
        
        self.collector = SummaryCollector()
        self.collector_lock = Lock()
        logger.info(f"Загружено {len(self.coins_list)} монет из конфигурации.")

    # ====================================================
    # ? Выполнение одного теста бэктеста
    # ? Подготовка данных, инициализация компонентов и запуск бэктеста
    # ====================================================
    def _execute_single_backtest(self, coin, timeframe): # Dict[str, Any]:
        # * Выполняет один бэктест для конкретной монеты и таймфрейма.
        # * Возвращает все позиции которые были за указанный период
        
        symbol = f"{coin['SYMBOL']}/USDT"
        coin = coin.copy()  # Создаем копию чтобы избежать изменений оригинала
        coin["TIMEFRAME"] = timeframe
        
        # Замер времени выполнения одного теста Название задачи
        task_name = f"[{symbol}, {timeframe}] Backtest"
        
        try:
            with LoggingTimer(task_name):

                # ! -------- 1. Загрузка данных --------
                fetcher = DataFetcher(
                    coin=coin, 
                    exchange=self.exchange, 
                    directory=self.settings_test.get("DATA_DIR", "")
                    )

                data_1m  = fetcher.load_from_csv(file_type="csv")
                data_htf  = fetcher.load_from_csv(file_type="csv", timeframe=timeframe)
                if data_1m is None or data_htf is None:
                    raise RuntimeError("Данные не загружены")

                # ! -------- 2. Выбор периода --------
                data_htf = select_range_backtest(
                    data_df=data_htf,  
                    full_datafile=self.settings_test.get("FULL_DATAFILE", ""),
                    start_date=self.settings_test.get("START_DATE"),
                    end_date=self.settings_test.get("END_DATE"),
                    offset_bars=self.settings_strategy.get("MINIMUM_BARS_FOR_STRATEGY_CALCULATION", 0)
                )
                data_1m = select_range_backtest(
                    data_df=data_1m,  
                    full_datafile=self.settings_test.get("FULL_DATAFILE", ""),  
                    start_date=self.settings_test.get("START_DATE"), 
                    end_date=self.settings_test.get("END_DATE"),
                    offset_bars=0
                )

                if data_htf is None or len(data_htf) == 0:
                        raise RuntimeError("Недостаточно данных")

                # !-------- 3. Инициализация --------
                # импортируем здесь чтобы избежать циклических импортов
                from src.backtester.runner import run_backtest
                from src.backtester.engine.execution_engine import ExecutionEngine
                from src.trading_engine.managers.position_manager import PositionManager
                # загрузка стратегии динамически (path в configs STRATEGY_SETTINGS.PATH)
                from src.utils.strategy_loader import load_strategy_class, function_to_class_adapter
                import types
                import numpy as np

                strategy_path = self.settings_strategy.get("PATH")
                if not strategy_path:
                    raise RuntimeError("Strategy path not configured in STRATEGY_SETTINGS.PATH")

                StrategyObj = load_strategy_class(strategy_path)
                # если функция — оборачиваем в класс-адаптер
                if not isinstance(StrategyObj, type) and callable(StrategyObj):
                    StrategyClass = function_to_class_adapter(StrategyObj)
                else:
                    StrategyClass = StrategyObj

                # инстанцируем стратегию
                strategy = StrategyClass(coin)

                # compatibility: если у стратегии нет find_entry_point, но есть run — привяжем адаптер
                if not hasattr(strategy, 'find_entry_point'):
                    if hasattr(strategy, 'run'):
                        def _find_entry(self, data_slice):
                            # run может ожидать data как np.array или pd.DataFrame
                            try:
                                return self.run(data_slice, positions=[], trading_context=None)
                            except TypeError:
                                return self.run(data_slice, [])

                        strategy.find_entry_point = types.MethodType(_find_entry, strategy)
                    else:
                        raise RuntimeError(f"Loaded strategy {strategy_path} has neither find_entry_point nor run method")

                # Простая валидация стратегии — smoke run на небольшом фрагменте данных
                try:
                    # подготовим массив похожий на тот, который используется в BacktestEngine
                    data_cols = data_htf[['open','high','low','close']].values
                    timestamps = data_htf.index.values
                    n = min(len(data_cols), max(1, int(getattr(strategy, 'allowed_min_bars', 1))))
                    arr_small = np.empty((n, 5), dtype=object)
                    arr_small[:, :4] = data_cols[:n]
                    arr_small[:, 4] = pd.to_datetime(timestamps[:n])
                    # вызов
                    smoke_sig = strategy.find_entry_point(arr_small)
                    if smoke_sig is None or not (hasattr(smoke_sig, 'is_no_signal') or hasattr(smoke_sig, 'is_entry')):
                        raise RuntimeError("Strategy smoke run returned unexpected result")
                except Exception as e:
                    logger.exception(f"Strategy validation failed for {strategy_path}: {e}")
                    raise
                # инициализация менеджера позиций
                position_manager = PositionManager()
                # инициализация движка исполнения
                engine = ExecutionEngine(position_manager)
                # инициализация модуля хеджирования (если нужен)
                
                
                # ! -------- 4. Backtest --------
                result = run_backtest(
                        data = data_htf,  #  исторические данные для бэктеста
                        data_1m = data_1m, #  исторические данные 1м для бэктеста
                        coin = coin, # информация о монете (из конфига)
                        strategy = strategy, # стратегия
                        position_manager = position_manager, # менеджер позиций
                        engine = engine, # движок исполнения
                        logger = logger # логгер
                    )
                
                # ! -------- 5. Test report --------
                test_report_path = build_test_report_path(
                    coin["SYMBOL"], timeframe
                )

                TestReportGenerator(
                    template_dir=self.settings_test.get("TEMPLATE_DIRECTORY", ""),
                    settings_test=self.settings_test,
                ).generate(
                    
                    symbol=coin["SYMBOL"],
                    timeframe=timeframe,
                    coin=coin,
                    test_id=result["test_id"],
                    metrics=result["metrics"],
                    portfolio=result["portfolio"],
                    positions=result["positions"],
                    output_path=test_report_path,
                )

                # ! -------- 6. Collect summary (THREAD SAFE) --------
                with self.collector_lock:
                    self.collector.add(
                        symbol=coin["SYMBOL"],
                        coin=coin,
                        timeframe=timeframe,
                        test_id=result["test_id"],
                        metrics=result["metrics"],
                        portfolio=result["portfolio"],
                        report_path=str(test_report_path),
                    )
                
                logger.warning(f"[{symbol}, {timeframe}] ✅ Обработка завершена.")
        
        except Exception as e:
            logger.exception(f"[{symbol}, {timeframe}] ❌ FAILED: {e}")

    # ====================================================
    # ? Точка входа для параллельного бэктеста
    # ====================================================
    def run_parallel_backtest(self, max_workers: int = 4):
        """Основной конвейер для параллельного бэктеста."""

        tasks = [
            (coin.copy(), tf)
            for coin in self.coins_list
            for tf in self.settings_test.get("TIMEFRAME_LIST", [])
        ]

        logger.info(f"📊 Всего задач бэктеста: {len(tasks)}")
        
        # Словарь для структурирования результатов: {"BTC": {"1h": Test_obj, "4h": Test_obj}, ...}

        # ! Запуск параллельного выполнения
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

            futures = [
                executor.submit(self._execute_single_backtest, coin, tf)
                for coin, tf in tasks
            ]
            
            # запускаем задачи строго в том порядке как идут в tasks
            for future in concurrent.futures.as_completed(futures):
                future.result()  # ошибки уже залогированы

        # ! -------- Summary report --------
        SummaryReportGenerator(
            template_dir=self.settings_test.get("TEMPLATE_DIRECTORY", ""),
            settings_test=self.settings_test,
        ).generate(
            summary_data=self.collector.data,
            output_path=build_summary_report_path(),
        )

        logger.info("============================================================================")
        logger.info("📈 Все бэктесты завершены!")
        logger.info("============================================================================")

