import argparse
import os


# ====================================================
# Основная функция
# ====================================================
def main():
    # Загружаем и валидируем конфигурацию
    # ====================================================
    from src.config.config import config
    # ------------------------------------------
    # аргументы командной строки
    parser = argparse.ArgumentParser(description='Программа алготрейдинга с бэктестером и загрузкой данных.')
    
    # Добавляем параметр --ldata загрузка данных с биржи
    parser.add_argument(
        '--ldata',
        action='store_true',  # Флаг (без значения)
        help='Загрузить или обновить исторические данные c биржи'
    )
    parser.add_argument(
        '--ld_min',
        action='store_true',  # Флаг (без значения)
        help='Загрузить или обновить исторические данные c биржи минутный график'
    )
    # Добавляем параметр --debug
    parser.add_argument(
        '--debug',
        action='store_true',  # Флаг (без значения)
        help='запуск отладки стратегии на локальных данных'
    )
    # Добавляем параметр --btest
    data_dir = config.get_setting("BACKTEST_SETTINGS", "DATA_DIR")
    parser.add_argument(
        '--btest',
        action='store_true',  # Флаг (без значения)
        help=f'Запустить бэктестер с локальными данными из директории {data_dir}'
    )
    
    args = parser.parse_args()

    # Логирование
    # ====================================================
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
    
    # Проверяем параметры
    # Загрузка исторических данных с биржи
    if args.ldata:
        logger.info("Загрузка и обновление исторических данных...")
        from src.data_fetcher.get_data_from_exchange import run_data_update_pipeline
        if args.ld_min:
            run_data_update_pipeline(loading_min=True)
        else:
            run_data_update_pipeline()
            
        logger.info("Загрузка исторических данных завершена.")
        
    
    # Отладка стратегии 
    if args.debug:
        logger.info("Запуск отладки стратегии...")
        from src.debugger.debugger import debugger_strategy
        debugger_strategy()
        logger.info("Отладка стратегии завершена.")
    
    # бектестинг стратегии на исторических данных
    if args.btest:
        logger.info("Запуск бэктестера...")
        max_workers = config.get_setting("BACKTEST_SETTINGS", "MAX_WORKERS")
        
        from src.backtester.backtester import TestManager
        test_manager = TestManager()
        test_manager.run_parallel_backtest(max_workers=max_workers)
        
        logger.info("Бэктестер завершил работу.")
    

# Точка входа
if __name__ == "__main__":
    main()    