import pandas as pd


# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)
   

def run_strategy(data_df): 
    logger.info("Запуск стратегии Mozart.")
    
    from src.logical.indicators.lecture_1 import strategy_extremes
    df = strategy_extremes(data_df)
    
                # Используем ExcelWriter, чтобы избежать предупреждений
    writer = pd.ExcelWriter("m_extremum.xlsx", engine='openpyxl')
    df.to_excel(writer, sheet_name='OHLCV Data', index=True)
    writer.close()
    
    
  