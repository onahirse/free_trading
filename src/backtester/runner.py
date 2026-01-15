# src/backtester/runner.py
from src.backtester.engine.backtest_engine import BacktestEngine
from src.backtester.engine.execution_loop import ExecutionLoop
from src.backtester.trading.position_builder import PositionBuilder
from src.backtester.trading.signal_handler import SignalHandler
from src.backtester.portfolio.portfolio import Portfolio
from src.backtester.portfolio.metrics import MetricsCalculator


# Запуск бэктеста
def run_backtest(data, data_1m, coin, strategy, position_manager, engine, logger):
    """
    Запускает бэктест. Возвращает результаты бэктеста.
    :param data: исторические данные для бэктеста (DataFrame)
    :param data_1m: исторические данные 1м для бэктеста (DataFrame)
    :param coin: информация о монете (из конфига) (dict)
    :param strategy: объект стратегии (из конфига) (Strategy)
    :param manager: менеджер позиций (из конфига) (PositionManager)
    :param engine: объект исполнителя (из конфига) (ExecutionEngine)    
    :param logger: объект логирования (из конфига) (Logger)
    :return: результаты бэктеста (dict)
    """
    # хранит информацию о PnL, балансе и т.д.
    portfolio = Portfolio(coin["START_DEPOSIT_USDT"])
    # инициализация билдера позиций
    builder = PositionBuilder(position_manager, coin)
    # исполнение сигналов стратегии
    signal_handler = SignalHandler(position_manager, builder, logger)
    # исполнение ордеров по минутным барам
    exec_loop = ExecutionLoop(engine)

    bt = BacktestEngine(
        strategy,
        position_manager,
        exec_loop,
        signal_handler,
        portfolio,
        logger
    )

    bt.run(data, data_1m, coin["TIMEFRAME"])

    return {
        "test_id": position_manager.id,
        "positions": position_manager.positions,
        "portfolio": portfolio,
        "metrics": MetricsCalculator.from_positions(position_manager.positions)
    }
