
# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.config.config import config

# точка входа для бектеста
# ====================================================
def debugger_strategy():
    """Отладка стратегии"""

    from src.backtester.backtester import TestManager
    
    test_manager = TestManager()
    # ! Берем первую монету из списка для отладки
    coin = test_manager.coins_list[0]
    test_manager._execute_single_backtest(coin, coin.get("TIMEFRAME")) # test_manager._execute_single_backtest(coin, timeframe)
    
    logger.info("Debugging completed.")
        
        
        