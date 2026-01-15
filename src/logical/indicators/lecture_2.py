import numpy as np
import pandas as pd
# Библиотека для вывода в консоль форматированного DataFrame 
from tabulate import tabulate

# from scipy.signal import find_peaks
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples, silhouette_score


"""
По лекции # 2 модуль 
Временные метки по лекции 2
настройки индикатора VPVR
Какие за что отвечают и добавить их в config.py
Сила уровня 32 минута
47 минута Ценность уровней. Какой период брать для индикатора VPVR
"""



# VPVR_data столбцы Price_levels, Volumes, max_volume, min_volume
 
 
def all_lecture_2(data, config, tickSize):
    # Строим сам индикаор VPVR
    vpvr_data = calculate_vpvr(data, config, tickSize)
    # print(tabulate(vpvr_data, headers='keys', tablefmt='grid'))
    
    
    # Высчитываем колличество максимумов и минимумов
    search_high_low_volumes(vpvr_data, config)
    # print(tabulate(vpvr_data, headers='keys', tablefmt='grid'))
    
    
    # Находим уровни в низких объемах
    search_vpvr_levels(vpvr_data, config)
    print(tabulate(vpvr_data, headers='keys', tablefmt='grid'))

    return vpvr_data
    
   
# вычисление самого индикатора VPVR
def calculate_vpvr(data, config, tickSize):
    """
    Рассчитывает объемный профиль (VPVR) для заданного диапазона данных.

    Parameters:
        data (DataFrame): Данные OHLCV (с колонками 'High', 'Low', 'Volume').
        price_bins (int): Количество бинов (уровней цены) для расчета VPVR. Задается с файле config

    Returns:
        price_levels (array): Уровни цен.
        volumes (array): Объемы на каждом уровне цен.
        poc_price (float): Точка контроля (Point of Control).
    """
    # Определение диапазона цен
    price_min = data['Low'].min()
    price_max = data['High'].max()


    # Расчет тиков на строку
    ticks_per_row = (price_max - price_min) / config.ROW_SIZE / tickSize
    ticks_per_row = round(ticks_per_row)  # Округляем до ближайшего целого числа  
    
    # Рассчитываем шаг для каждой строки (ценовой диапазон для строки)
    row_height = ticks_per_row * tickSize
    row_height = round(row_height)
    # price_bins = np.arange(price_min, price_max, row_height)  


    # Создание бинов цен
    price_levels = np.linspace(price_min, price_max, config.ROW_SIZE)
    volumes = np.zeros(config.ROW_SIZE)

    # Заполнение объемов для каждого ценового уровня
    for i, row in data.iterrows():
        price_range = np.linspace(row['Low'], row['High'], row_height)  # Подразделение свечи на 10 частей
        price_volume = row['Volume'] / row_height  # Объем на каждую часть

        for price in price_range:
            # Определение ближайшего ценового уровня (бина)
            idx = np.searchsorted(price_levels, price) - 1
            volumes[idx] += price_volume

    # Определение уровня Point of Control (POC) — уровня с наибольшим объемом
    poc_idx = np.argmax(volumes)
    poc_price = price_levels[poc_idx]

    vpvr_data = pd.DataFrame({
        'Price_levels': price_levels,
        'Volumes': volumes, 
        'Poc_price': None
        })
    vpvr_data.loc[poc_idx, 'Poc_price'] = 'poc'
    
    return vpvr_data


"""
Функция поиска максимальных и минимальных обьемов полученных из индикатора VPVR
"""
def search_high_low_volumes(vpvr_data, config):
    max_volume_temp = 0
    min_volume_temp = vpvr_data['Volumes'].max()
    number_bars_check = config.NUMBER_BARS_CHECK
    
    search_extremum = 1
    vpvr_data['Max_volume'] = None
    vpvr_data['Min_volume'] = None
    
    for i in range(0, len(vpvr_data)):
        if search_extremum == 1:
            # Ищем максимум
            if vpvr_data['Volumes'].iloc[i] > max_volume_temp:
                # если объем больше предыдущего максимума
                max_volume_temp = vpvr_data['Volumes'].iloc[i]
            else:
                # Если объем текущего бара меньше предыдущего максимума
                # Проверяем еще config.NUMBER_BARS_CHECK количество свечей дальше для подтверждения экстремума
                if i - 1 + config.NUMBER_BARS_CHECK > len(vpvr_data):
                    number_bars_check = len(vpvr_data) - i-1
                    
                if all(max_volume_temp > vpvr_data['Volumes'].iloc[i-1 + j] for j in range(1, number_bars_check)):                  
                    vpvr_data.loc[i-1, 'Max_volume'] = 'max'
                    max_volume_temp = 0
                    search_extremum = -1


        elif search_extremum == -1:
            # ищем минимумы
            if vpvr_data['Volumes'].iloc[i] < min_volume_temp:
                min_volume_temp = vpvr_data['Volumes'].iloc[i]
            else:
                # проверяем что бы не уходил за пределы массива
                if i - 1 + config.NUMBER_BARS_CHECK > len(vpvr_data):
                    number_bars_check = len(vpvr_data) - i-1
                # Проверяем еще config.NUMBER_BARS_CHECK количество свечей дальше для подтверждения экстремума
                if all(min_volume_temp < vpvr_data['Volumes'].iloc[i-1 + j] for j in range(1, number_bars_check)):
                    
                    vpvr_data.loc[i-1,'Min_volume'] = 'min'
                    min_volume_temp = vpvr_data['Volumes'].max()
                    search_extremum = 1

    


def search_vpvr_levels(vpvr_data, config):
    """
    Функция для поиска уровней VPVR (Volume Profile Visible Range).
    Она находит первую строку с минимальным значением в столбце 'Min_volume',
    ближайшее значение максимума в столбце 'Max_volume',
    а также строки, где значения 'Volumes' меньше найденного минимума.

    Аргументы:
    vpvr_data -- DataFrame с колонками, такими как 'Min_volume', 'Max_volume', 'Volumes'.
    config -- конфигурация для возможных дополнительных параметров (не используется в этой реализации).

    Возвращает:
    Ничего не возвращает, но выводит результаты в консоль.
    """

    # 1. Находим строки, где в 'Min_volume' указано значение 'min'
    min_rows = vpvr_data[vpvr_data['Min_volume'] == 'min']

    vpvr_data['Level'] = None    
    # Если такие строки есть (DataFrame не пустой)
    if not min_rows.empty:
        
        for ind_min, row in min_rows.iterrows():
            # ==========================================
            # Находим ближайшие максимумы 
            j=1
            ind_max_high    = None

            while ind_max_high is None and ind_min+j < len(vpvr_data):
                if vpvr_data['Max_volume'].iloc[ind_min+j]=='max':
                    ind_max_high = ind_min+j
                j += 1
            
            j=1
            ind_max_low     = None

            while ind_max_low is None and ind_min-j >= 0:
                if vpvr_data['Max_volume'].iloc[ind_min-j]=='max':
                    ind_max_low = ind_min-j
                j += 1
            
            
            min_volumes =    vpvr_data['Volumes'].iloc[ind_min]
            
           
            if ind_max_low is not None:
                max_low_volume = vpvr_data['Volumes'].iloc[ind_max_low]
            else:
                max_low_volume = None
                
            if ind_max_high is not None:
                max_high_volume = vpvr_data['Volumes'].iloc[ind_max_high]
            else:
                max_high_volume = None
                
            if max_low_volume is None and max_high_volume is None:
                print("Обе переменные равны None")
            elif max_low_volume is None:
                min_max_value = max_high_volume
            elif max_high_volume is None:
                min_max_value = max_low_volume
            else:
                min_max_value = min(max_low_volume, max_high_volume)
                max_max_value = max(max_low_volume, max_high_volume)

            
            
            print(f"{ind_min} *******************************************************")
            print(f"min_volums = {min_volumes}")
            print(f"max_low_volume = {max_low_volume}")
            print(f"max_high_volume = {max_high_volume}")
            
            percentage = (max_max_value - min_volumes) * config.PERCENTAGE
            print(f"Процент от минимального объема для вхождения в уровень = {max_high_volume}")
            
            
            percentage_decrease = int(
                (((min_max_value - min_volumes) / min_max_value) * 100 + int(((max_max_value - min_volumes) / max_max_value) * 100))/2
                )
            print(f"Глубина в % {percentage_decrease} ")
            
            
            # находим сильные уровни
            for i, row in vpvr_data.iloc[ind_max_low:ind_max_high].iterrows():
                # print(percentage_decrease)
                if min_volumes+percentage > vpvr_data['Volumes'].iloc[i]:
                    
                    if percentage_decrease > config.LEVELS_PARAM[0] and percentage_decrease < config.LEVELS_PARAM[1]:
                        vpvr_data.loc[i, 'Level'] = config.LEVELS_PARAM[0]
                        
                    elif percentage_decrease > config.LEVELS_PARAM[1] and percentage_decrease < config.LEVELS_PARAM[2]:
                        vpvr_data.loc[i, 'Level'] = config.LEVELS_PARAM[1]
                        
                    elif percentage_decrease > config.LEVELS_PARAM[2]:
                        vpvr_data.loc[i, 'Level'] = config.LEVELS_PARAM[2]
        
    else:
        # Если в 'Min_volume' нет значений 'min', выводим сообщение
        print("В столбце Min_volume нет значений 'min'")


    






# def analyze_vpvr_clusters(vpvr_data, config):
#     """
#     Выполняет кластеризацию уровней VPVR и анализирует зоны с низкими объемами
#     относительно высоких объемов рядом.

#     Аргументы:
#     - price_levels: Уровни цен (массив numpy).
#     - volumes: Объемы на каждом уровне (массив numpy).
#     - n_clusters: Количество кластеров для KMeans.
#     - low_volume_threshold: Порог для определения низкого объема.

#     Возвращает:
#     - метки кластеров, средний силуэтный коэффициент, уровни с низким объемом
#     """
#     price_levels, volumes, poc_price = vpvr_data
#     n_clusters = len(min_volume)
#     # Нормализация объемов
#     normalized_volumes = volumes / np.max(volumes)
    
#     # Подготовка данных для кластеризации (цена и нормализованный объем)
#     X = np.column_stack((price_levels, normalized_volumes))
    
#     # Кластеризация с помощью KMeans
#     kmeans  = KMeans(n_clusters=n_clusters, init=min_volume, random_state=0, tol=1e-5)
#     kmeans.fit(X)
#     cluster_labels = kmeans.labels_
    
#     # Вычисление среднего силуэтного коэффициента для оценки качества кластеров
#     silhouette_avg = silhouette_score(X, cluster_labels)
#     print(f"Средний силуэтный коэффициент для {n_clusters} кластеров: {silhouette_avg}")
    
#     # Получаем силуэтные коэффициенты для каждого уровня
#     sample_silhouette_values = silhouette_samples(X, cluster_labels)
    
#     # Определяем уровни с низким объемом
#     low_volume_levels = []
#     for i, label in enumerate(cluster_labels):
#         # Если объем на уровне значительно ниже соседних, помечаем его как "низкий"
#         if normalized_volumes[i] < low_volume_threshold:
#             low_volume_levels.append(price_levels[i])

#     return cluster_labels, silhouette_avg, low_volume_levels


# def find_low_volume_levels_with_clusters(price_levels, volumes, count_min, volume_difference_threshold=0.7):
#     # Нормализуем объемы
#     normalized_volumes = volumes / np.max(volumes)
    
#     # Объединяем данные ценовых уровней и нормализованных объемов для кластеризации
#     data = np.column_stack((price_levels, normalized_volumes))
    
#     # Применяем KMeans для кластеризации по объемам
#     # kmeans = KMeans(n_clusters=n_clusters, random_state=3).fit(data)
#     kmeans = KMeans(n_clusters=count_min, algorithm='lloyd').fit(data)
#     labels = kmeans.labels_
    
#     # Находим центры кластеров для анализа
#     cluster_centers = kmeans.cluster_centers_
    
#     # Отделяем кластеры низкого и высокого объема
#     cluster_volumes = cluster_centers[:, 1]  # Центры кластеров по объемам
#     low_volume_clusters = np.where(cluster_volumes < volume_difference_threshold)[0]
    
#     # Список для хранения ценовых уровней с минимальными объемами, которые соответствуют условию разницы
#     low_volume_levels = []
#     low_volume_prices = []
    
#     for idx, label in enumerate(labels):
#         if label in low_volume_clusters:
#             # Проверка разницы в объемах для соседних уровней
#             adjacent_volumes = volumes[max(0, idx - 1):min(len(volumes), idx + 2)]
#             max_adjacent_volume = np.max(adjacent_volumes)
            
#             if volumes[idx] < (1 - volume_difference_threshold) * max_adjacent_volume:
#                 # Добавляем, если объем на текущем уровне на 70% меньше соседнего
#                 low_volume_levels.append(volumes[idx])
#                 low_volume_prices.append(price_levels[idx])
    
#     return low_volume_levels, low_volume_prices


    
# # Функция для кластерного анализа и нахождения уровней с низким объемом
# def apply_kmeans_and_low_volume_levels(vpvr_data, n_clusters, low_volume_ratio=0.2):
    
#     price_levels, volumes, poc_price = vpvr_data
    
#     normalized_volumes = volumes / np.max(volumes)
#     X = np.column_stack((price_levels, normalized_volumes))

#     # Инициализация и обучение модели KMeans
#     # kmeans = KMeans(n_clusters=n_clusters, random_state=4).fit(X)
#     kmeans = KMeans(n_clusters=n_clusters, algorithm = 'lloyd').fit(X)
    
#     labels = kmeans.labels_
#     cluster_centers = kmeans.cluster_centers_

#     cluster_levels = cluster_centers[:, 0]
#     cluster_volumes = cluster_centers[:, 1] * np.max(volumes)

#     low_volume_levels = []
#     low_volumes = []

#     for cluster_label in range(n_clusters):
#         # Определяем уровни, принадлежащие текущему кластеру
#         cluster_indices = np.where(labels == cluster_label)[0]
#         cluster_volume_values = volumes[cluster_indices]
#         cluster_price_values = price_levels[cluster_indices]

#         # Средний объем в кластере
#         avg_volume_in_cluster = np.mean(cluster_volume_values)

#         # Определяем уровни, объем которых меньше 20% от среднего
#         low_volume_mask = cluster_volume_values < (low_volume_ratio * avg_volume_in_cluster)
#         low_volume_levels.extend(cluster_price_values[low_volume_mask])
#         low_volumes.extend(cluster_volume_values[low_volume_mask])

#     low_volumes, low_volume_levels = find_low_volume_levels_with_clusters(price_levels, volumes, n_clusters=30, volume_difference_threshold=0.5)
    
#     return labels, cluster_levels, cluster_volumes, low_volumes, low_volume_levels




