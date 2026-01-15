"""
Основной конвейер для получения и сохранения исторических данных по монетам из конфигурации.
Загрузка данных осуществляется через DataFetcher.

"""
import time

# Логирование
# ====================================================
from src.utils.logger import get_logger, LoggingTimer
logger = get_logger(__name__)

from src.config.config import config


# ====================================================
# Основной конвейер для получения и сохранения исторических данных
# ====================================================
def run_data_update_pipeline(loading_min=True):
    """Основной конвейер для получения и сохранения исторических данных по монетам из конфигурации."""
    
    
    # Получение настроек Биржи
    exchange = config.get_section("EXCHANGE_SETTINGS")
    data_dir = config.get_setting("BACKTEST_SETTINGS", "DATA_DIR")
    loading_update_min = False
    
    # 1. Получение массива монет
    try:
        coins_list = config.get_section("COINS")
        timeframe_list = config.get_setting("BACKTEST_SETTINGS", "TIMEFRAME_LIST")
        logger.info(f"Загружено {len(coins_list)} монет из конфигурации.")
    except KeyError as e:
        # Хотя валидация должна была поймать это, это хорошая защита
        logger.error(f"Критическая ошибка: {e}")
        coins_list = [] # Устанавливаем пустой список для безопасной работы
        timeframe_list = [] # Устанавливаем пустой список для безопасной работы
        
    # Подключение к Бирже
    from src.data_fetcher.data_fetcher import DataFetcher
    # 2. Обработка каждой монеты   
    for coin in coins_list:
        logger.info("============================================================================")
        symbol = coin.get("SYMBOL")+"/USDT"
        timeframe = coin.get("TIMEFRAME")
        min_timeframe = coin.get("MIN_TIMEFRAME", "")
        market_type = coin.get("MARKET_TYPE", "spot")  # Добавлено получение категории рынка
        logger.info(f"[bold yellow]{symbol}[/bold yellow], Маркет: [bold green]{market_type}[/bold green], Таймфрейм: [bold yellow]{timeframe}[/bold yellow], Минимальный таймфрейм: [bold yellow]{min_timeframe}[/bold yellow]")

        fetcher = DataFetcher( coin,
            exchange=exchange, 
            directory=data_dir,
            )
        for timeframe in timeframe_list:
            # coin["TIMEFRAME"] = tf
            logger.info(f"[{symbol}] 🪙, 🕒 Таймфрейм: [bold yellow]{timeframe}[/bold yellow]")
            # проверка на существование данных 
            if fetcher.check_file_exists(timeframe) and loading_min:
                logger.info(f"[{symbol}] 🪙, 🕒 Таймфрейм: [bold yellow]{timeframe}[/bold yellow] уже существует пропускаем")
                continue
            
            # Загрузка данных
            with LoggingTimer(f"[bold yellow]{symbol}[/bold yellow] load timeframe.....: {timeframe}"):
                data_df = fetcher.fetch_entire_history(timeframe)
                # Сохранение данных
                if data_df is not None:
                    # Сохранить в под папку 'csv_files'
                    fetcher.export_to_csv(data_df, timeframe) 
                        
                        # Сохранить в под папку 'excel_files'
                    fetcher.export_to_excel(data_df, timeframe)
                    
                    loading_update_min = True
            
        logger.info(f"[{symbol}] 🪙, 🕒 Таймфрейм: [bold yellow]{min_timeframe}[/bold yellow] pause..........")
        time.sleep(100) # Пауза в 100 секунд
        if loading_min or loading_update_min:
            if min_timeframe != "":
                with LoggingTimer(f"[bold yellow]{symbol}[/bold yellow] load timeframe.....: {timeframe}"):
                    data_df_min = fetcher.fetch_entire_history(min_timeframe)
                
                    # Сохранение данных
                    if data_df_min is not None:
                        # Сохранить в под папку 'csv_files'
                        fetcher.export_to_csv(data_df_min, timeframe=min_timeframe) 
                    