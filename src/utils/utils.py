import datetime

def get_previous_interval(intervals, target):
    try:
        # Найти индекс заданного значения
        index = intervals.index(target)
        # Вернуть предыдущее значение, если оно существует
        return intervals[index - 1] if index > 0 else target
    except ValueError:
        # Если значение не найдено в массиве, вернуть None
        return target
    
# # Перевод времени из миллисекунд в часы, минуты, секунды
# # Время в миллисекундах
# def DataTimeToUnix(timestamp_ms):

#     # Преобразование в datetime
#     dt = datetime.datetime.fromtimestamp(timestamp_ms / 1000.0)

#     # Читаемый формат
#     return(dt.strftime("%d.%m.%Y %H:%M:%S"))
#     # print(dt.strftime("%d.%m.%Y %H:%M:%S"))  # 31.10.2023 14:37:12