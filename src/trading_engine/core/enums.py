from enum import Enum

class Position_Status(Enum):
    ACTIVE = "active"           #активная позиция
    TAKEN_PART = "part_taken"   #финальный статус, когда позиция была исполнена частично
    TAKEN_FULL = "taken_full"   #финальный статус, когда позиция была исполнена полностью
    STOPPED = "stopped"         #финальный статус, когда позиция была остановлена по стоп-лоссу в минусе
    CANCELED = "cancelled"      #финальный статус, когда позиция была отменена (профит может быть как положительный так и отрицательный)
    NONE = "none"               #начальный статус, когда позиция не создана
    CREATED = "created"         #начальный статус, когда позиция создана
    
class PositionType(Enum):
    MAIN = "main"               # Основная позиция
    HEDGE = "hedge"             # хеджирующая позиция


class OrderType(Enum):
    ENTRY           = "entry"     # вход в позицию
    TAKE_PROFIT     = "tp"  # тейк-профит
    STOP_LOSS       = "sl"    # стоп-лосс
    CLOSE           = "close"     # закрытие позиции
    TRAILING_STOP   = "trailing_stop" # трейлинг-стоп
    LIMIT           = "limit"   # лимитный ордер
    MARKET          = "market"  # рыночный ордер


class OrderStatus(Enum):
    ACTIVE = "active"
    FILLED = "filled"
    CANCELLED = "cancelled"
    PARTIAL = "partial"

# направление позиции
class Direction(Enum):
    LONG = "long"
    SHORT = "short"
    
    

# ==========================
# Signal Type Enum
# ==========================
class SignalType(Enum):
    ENTRY           = "entry" # сигнал на Открытие позиции Может бы limit или market, может содержать параметры SL[], TP[]
    CLOSE           = "close"   # сигнал на Закрытие позиции по рынку, Должны содержать ID позиции (Обязательно)
    CLOSE_ALL       = "close_all" # сигнал на Закрытие всех позиций по указанной монете
    HEDGE_ENTRY     = "hedge_open" # сигнал на Открытие хедж-позиции работает только через entry
    HEDGE_CLOSE     = "hedge_close" # сигнал на Закрытие хедж-позиции работает только через close
    UPDATE          = "update" # изменить ордера в позиции Limit, SL, TP  (Обязательно ID позиции) Работает через отмену старых ордеров и создание новых если указаны
    NO_SIGNAL       = "no_signal" # отсутствие сигнала
