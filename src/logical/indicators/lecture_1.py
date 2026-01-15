"""
Данный модуль предназначен для определения тренда 
используя первую лекцию 7 потока трейдера и блогера Mr Mozart
"""

# Логирование 
import logging
# Создание логгера
logger = logging.getLogger(__name__)


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
"""
Функция проверки на экстремум 
Верхний экстремум "+"   :           1_high < 2_high > 3_high 
Нижний экстремум "-"    :           1_low > 2_low < 3_low 
"""
def checking_for_an_extreme(one, two, three):
    # Свеча 1
    one_high = float(one['high'])
    one_low = float(one['low'])
    # Свеча 2
    two_high = float(two['high'])
    two_low = float(two['low'])
    # Свеча 3
    three_high = float(three['high'])
    three_low = float(three['low'])

    #  Находим точки "+" Экстремумы 
    if one_high <= two_high >= three_high:
        return 1 
            
    #находим точки "-"
    if one_low >= two_low <= three_low: 
        return -1
    
    
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
"""
Проверяем экстремум на пробитие 
    если лой 2 свечи больше лоя  следующих свечей то экстремум не является трендовыи
        True
    если хай 2 свечи меньше хая следующих свечей то экстремум не является трендовыи
        False
"""
def _confirmation_extremum(high, low, data, start_index):
    # Перебираем все свечи 
    for i in range(start_index+1, len(data)-1):
        current_high = float(data['high'].iloc[i])
        current_low = float(data['low'].iloc[i])
        # если лой 2 свечи больше лоя  следующих свечей то экстремум не является трендовыи         
        if low > current_low:
            return True    
        
        # если хай 2 свечи меньше хая следующих свечей то экстремум не является трендовыи
        if high < current_high:
            return False   
    return None         


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
"""
Чистим значение после перелома тренда 
"""
def _clear_extremum(data, start_point, end_point, colum):
    # Удалям значения в периоде 
    for i in range(start_point+1, end_point):
        data.loc[i, colum] = None

    
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
"""
Функция поиска экстремумов с подтверждением
"""
def _search_extremes_1(data):
    
    extremum = 0

    data['extremum'] = None
    
    data.reset_index(inplace=True)
    
    i = 1
    while i < len(data) - 1:
        if extremum == 0 or extremum == -1:
            # Проверяем является верхним экстремумом по 3м свечам
            # Проверяем пробивает хай свечи или лой
            if (checking_for_an_extreme(data.iloc[i-1], data.iloc[i], data.iloc[i+1]) == 1 and
                _confirmation_extremum(data['high'].iloc[i], data['low'].iloc[i], data, i)):
                # Подтвержденный Экстремум ВВЕРХ по 3 свечам с подтверждением
                data.loc[i,'extremum'] = 1 
                extremum = 1
            
        elif extremum == 0 or extremum == 1:
            # Проверяем является нижним экстремумом по 3м свечам
            # Проверяем пробивает хай свечи 
            if (checking_for_an_extreme(data.iloc[i-1], data.iloc[i], data.iloc[i+1]) == -1 and
                not _confirmation_extremum(data['high'].iloc[i], data['low'].iloc[i], data, i)):
                # Подтвержденный Экстремум ВНИЗ V по 3 свечам с подтверждением 
                data.loc[i, 'extremum'] = -1 # Да это просто экстремум c подтверждением  
                extremum = -1          
            
        i += 1  # Переход к следующему значению, если нет изменения
    
    data.set_index('timestamp', inplace=True)  # Восстановите индекс, если это нужно
    return data    
    
# ==========================================================
# основная функция по определению тренда
# ==========================================================
def strategy_extremes(data):
    
    _search_extremes_1(data)
    
    trend = 1
    
    point_index_max = 0
    point_index_min = 0
    point_intermediate_max = 0
    point_intermediate_min = 0
    start_trend = 0


    data['extremum_trend'] = None
    data['false_breakout'] = None
    data['start_trend'] = None
    data['false_breakout'] = None
    
    # Сбрасываем индекс
    data.reset_index(inplace=True)
    
    i = 1
    while i < len(data) - 1:
        if trend == 1:
            if data['extremum'].iloc[i] == 1:
                # Если тренд восходящий  
                if data['high'].iloc[point_index_max] < data['high'].iloc[i] or point_index_min == point_intermediate_min:
                    # если обновляем верхний экстремум 
                    data.loc[i, 'extremum_trend']   = 2
                    if point_intermediate_min < point_index_max:
                        data.loc[point_index_max, 'extremum_trend']   = None
                    else:
                        point_index_min                 = point_intermediate_min
                        data.loc[point_intermediate_min, 'extremum_trend']   = -2
                    point_index_max                 = i
                    
            elif data['extremum'].iloc[i] == -1:
                # Происходит смена тренда
                if data['low'].iloc[point_intermediate_min] > data['close'].iloc[i]:
                    # закрепились ниже меняем тренд
                    # Происходит смена тренда
                    trend = -1
                    start_trend = point_index_max
                    _clear_extremum(data, start_trend, i,  'extremum_trend')
                    data.loc[start_trend, 'start_trend'] = trend
                    point_index_min = start_trend
                    i = start_trend
                    point_intermediate_max = start_trend
                    point_intermediate_min = start_trend
                # ложный пробой
                elif data['low'].iloc[point_index_min] < data['close'].iloc[i] and data['low'].iloc[point_index_min] > data['low'].iloc[i]:
                    # ложный пробой
                    data.loc[i, 'false_breakout'] = -3
                    point_intermediate_min = i
                # если  экстремум в расширении
                elif data['low'].iloc[point_index_min] < data['low'].iloc[i] and data['high'].iloc[point_index_max] > data['low'].iloc[i]:
                    # если  экстремум в расширении
                    if point_intermediate_min == point_index_min:
                        point_intermediate_min = i
                    elif data['low'].iloc[point_intermediate_min] > data['low'].iloc[i]:
                        point_intermediate_min = i    
            
        elif trend == -1:  
            # Если тренд нисходящий
            if data['extremum'].iloc[i] == -1:
                # Обновляем лой
                if data['low'].iloc[point_index_min] > data['low'].iloc[i] or point_index_min == point_intermediate_min:
                    # если обновляем Low 
                    data.loc[i, 'extremum_trend'] = -2
                    if point_intermediate_max < point_index_min:
                        data.loc[point_index_min, 'extremum_trend'] = None
                    else:
                        point_index_max                 = point_intermediate_max
                        data.loc[point_intermediate_max, 'extremum_trend'] = 2
                    point_index_min                 = i
            
            elif data['extremum'].iloc[i] == 1:  # Если тренд нисходящий 
                # Происходит смена тренда               
                if data['high'].iloc[point_intermediate_max] < data['close'].iloc[i]:
                    # Если свеча закрылась выше предыдущего максимума
                    trend = 1
                    start_trend = point_index_min
                    _clear_extremum(data, start_trend, i,  'extremum_trend')
                    data.loc[start_trend, 'start_trend'] = trend
                    point_index_max = start_trend
                    i = start_trend                                        
                    point_intermediate_max = start_trend
                    point_intermediate_min = start_trend
                # ложный пробой
                elif data['high'].iloc[point_index_max] > data['close'].iloc[i] and data['high'].iloc[point_index_max] < data['high'].iloc[i]: 
                    data.loc[i, 'false_breakout'] = 3
                    point_intermediate_max = i
                # если  экстремум в расширении
                elif data['high'].iloc[point_index_max] > data['high'].iloc[i] and data['low'].iloc[point_index_min] < data['high'].iloc[i]: 
                    
                    if point_intermediate_max == point_index_max:
                        point_intermediate_max = i
                    elif data['high'].iloc[point_intermediate_max] < data['high'].iloc[i]:
                        point_intermediate_max = i
        
        i += 1  # Переход к следующему значению, если нет изменения
    
    data.set_index('timestamp', inplace=True)  # Восстановите индекс, если это нужно
    return data

