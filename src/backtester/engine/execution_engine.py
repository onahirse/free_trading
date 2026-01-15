from src.trading_engine.core.order import Order
from src.trading_engine.core.enums import OrderType, Position_Status, Direction
from src.trading_engine.utils.decimal_utils import to_decimal
from src.trading_engine.managers.position_manager import PositionManager
from datetime import datetime

from decimal import Decimal

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

# -------------------------------------------------
# Класс ExecutionEngine - движок исполнения ордеров
# -------------------------------------------------
class ExecutionEngine:
    """
    Упрощенный движок исполнения, который обрабатывает бар по бару и заполняет активные ордера.
    Правила (упрощенные):
        - MARKET-ордеры: заполняются немедленно при закрытии бара
        - ОРДЕРЫ ЛИМИТ на вход (для LONG): заполняются, если низкая цена бара <= цены лимита <= высокая цена бара
        (аналогично для SHORT: если низкая цена бара <= цены лимита <= высокая цена бара)
    - ОРДЕРЫ СТОП-ЛОСС:
        - для LONG стоп-лосс (продажа для закрытия): запускается, если низкая цена бара <= цены стопа
        - для SHORT стоп-лосс (покупка для закрытия): запускается, если высокая цена бара >= цены стопа
    - ОРДЕРЫ ТЕЙК-ПРОФИТ:
        - для LONG: запускается, если высокая цена бара >= цены тейка
        - для SHORT: запускается, если низкая цена бара <= цены тейка
    Частичные заполнения не моделируются (полное заполнение).
    """
    
    def __init__(self, position_manager: PositionManager, on_execution=None):
        
        self.position_manager = position_manager # менеджер позиций
        self.on_execution = on_execution # коллбек после исполнения ордера (если нужен)

    def process_bar(self, bar: list[float], bar_index: datetime):
        """
        bar: dict with keys: 'time' (optional), 'open', 'high', 'low', 'close'
        bar_index: integer index of the bar
        """
        # перебераем все позиции и их активные ордера
        for pos in list(self.position_manager.positions.values()):
            # из позиции получаем активные ордера
            active_orders = pos.get_active_orders()
            if not active_orders:
                # если активных ордеров нет, переходим к следующей позиции
                continue
            
            # перебираем все активные ордера позиции
            for order in active_orders:
                # проверяем, следует ли исполнить ордер на этом баре
                if self.should_execute(order, bar):
                    
                    # определяем цену исполнения и объем
                    exec_price = self.get_execution_price(order, bar)
                    exec_volume = order.remaining()
                    
                    # убедиться, что мы не закрываем больше, чем осталось (для ордеров на выход)
                    if order.type in {OrderType.TAKE_PROFIT, OrderType.CLOSE, OrderType.STOP_LOSS}:
                        exec_volume = min(exec_volume, pos.remaining_volume)

                    if exec_volume <= Decimal("0"):
                        continue

                    # ! регистрируем исполнение ордера в позиции
                    pos.record_execution(order, exec_price, pos.round_to_tick(exec_volume), bar_index)

                    # действия после выполнения: если запись заполнена, могут быть ордера в скобках (их может установить пользователь)
                    # здесь мы могли бы реализовать логику OCO, трейлинг-стопы и т. д. 
                    # На данный момент мы оставляем расширения на усмотрение пользователя.
            
            # Сделать универсальную проверку по переводу SL в безубыточность
            # Пока проверяем только для активных позиций
            # проверяем исполнен ли TP после которого переводим SL в без убыточность
            if pos.status == Position_Status.ACTIVE and pos.check_stop_break():
                # если закрыт хотя бы один TP, двигаем стоп в безубыточность
                pos.move_stop_to_break_even()


    # ------------------------
    # Проверка условий исполнения
    # ------------------------  
    def should_execute(self, order: Order, bar: list[float]) -> bool:
        """
        Проверка условий исполнения ордера на текущем баре.
        Если ордер может быть заполнен на этом баре, то возвращает True, иначе False.
        """
        low = to_decimal(bar[2])
        high = to_decimal(bar[1])
        close = to_decimal(bar[3])

        # MARKET
        if order.type in {OrderType.MARKET, OrderType.CLOSE}:
            return True

        # проверка ЛИМИТ и Вход
        if order.type in {OrderType.LIMIT, OrderType.ENTRY} and order.price is not None:
            # A limit buy executes when price <= limit (we assume liquidity, so check if limit within bar)
            # For simplicity: if the bar's range touches the limit -> execute
            return (low <= order.price <= high)

        # STOP_LOSS
        if order.type == OrderType.STOP_LOSS and order.price is not None:
            if order.direction == Direction.LONG:
                return low <= order.price
            else:
                return high >= order.price

        # TAKE_PROFIT
        if order.type == OrderType.TAKE_PROFIT and order.price is not None:
            if order.direction == Direction.LONG:
                return high >= order.price
            else:
                return low <= order.price

        return False

    # ------------------------
    # ? Получить цену исполнения
    # ------------------------
    def get_execution_price(self, order: Order, bar: list[float]) -> Decimal:
        """
        Определить цену исполнения. Для упрощения:
            - MARKET -> цена закрытия
            - TP -> цена тейка
            - SL -> цена стопа
            - LIMIT/ENTRY -> цена ордера (если достигнута)
        Вы можете улучшить метод, моделируя слэп, заполнение при открытии, VWAP и т.д.
        """
        
        close = to_decimal(bar[3]) # * берем цену закрытия бара
        if order.type == OrderType.MARKET:
            return close
        if order.type in {OrderType.TAKE_PROFIT, OrderType.STOP_LOSS, OrderType.LIMIT, OrderType.ENTRY} and order.price is not None:
            return order.price
        return close
