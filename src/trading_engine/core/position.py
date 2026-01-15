from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

# Core enums
from src.trading_engine.core.execution import Execution
from src.trading_engine.core.enums import Direction, OrderType, Position_Status, OrderStatus, PositionType
from src.trading_engine.orders.order_factory import Order
from src.trading_engine.utils.decimal_utils import to_decimal



class Position:
    """
    Позиция объединяет ордера и исполнения.
    Он НЕ сам принимает решения о выполнении — это делает ExecutionEngine.
    """
    def __init__(self, symbol: str, direction: Direction, tick_size: Optional[Decimal], source: str, meta={}):
        self.id = uuid4().hex # уникальный идентификатор позиции
        self.source = source # источник позиции
        self.type = PositionType.MAIN # тип позиции (основная/хеджирующая)
        self.symbol = symbol # торговый символ / инструмент
        self.direction = direction # направление позицией (long/short)
        self.status = Position_Status.CREATED
        self.orders: List[Order] = []        # все связанные заказы (entry, tp, sl, ...)
        self.executions: List[Execution] = []  # все исполнения, связанные с этой позицией
        self.opened_volume: Decimal = Decimal("0") # общий открытый объем
        self.closed_volume: Decimal = Decimal("0") # общий закрытый объем
        self.bar_opened: Optional[datetime] = None  # индекс бара, в котором была открыта позиция
        self.bar_closed: Optional[datetime] = None  # индекс бара, в котором была закрыта позиция
        self.avg_entry_price: Decimal = Decimal("0") # средняя цена входа
        self.realized_pnl: Decimal = Decimal("0")      # накопленная прибыль / убыток по позиции
        self.tick_size = tick_size if tick_size is not None else None # размер тика для округления цен
        
        self.filled_tp_volume: Decimal = Decimal("0") # объем исполненных ордеров TP
        self.filled_sl_volume: Decimal = Decimal("0") # объем исполненных ордеров SL
        self.filled_close_volume: Decimal = Decimal("0") # объем исполненных ордеров закрытия
        
        self.meta: Dict[str, Any] = meta  # дополнительная информация о позиции  без убытка moved_to_break=true

    # ------------------------
    # Order management
    # ------------------------
    def add_order(self, order: Order):
        logger.debug(f"[{self.symbol}] Позиция {self.id[:6]}: ордер {order.id[:6]} {order.type} /price = {order.price} /volume = {order.volume} /status = {order.status}")
        self.orders.append(order)

    # Отмена ордера по ID
    def __cancel_order(self, order_id: str):
        for o in self.orders:
            if o.id == order_id and o.status == OrderStatus.ACTIVE:
                o.status = OrderStatus.CANCELLED
                logger.debug(f"[{self.symbol}] Order {order_id} cancelled")
    
    # Установка типа позиции
    def setPositionType(self, ptype: PositionType):
        self.type = ptype
        logger.debug(f"[{self.symbol}] Позиция {self.id[:6]} установлена как тип {ptype.value}")

    # Отмена ордера по типу
    def cancel_orders_by_type(self, otype: OrderType):
        for o in self.orders:
            if o.type == otype and o.status == OrderStatus.ACTIVE:
                o.status = OrderStatus.CANCELLED
                logger.debug(f"[{self.symbol}] Order {o.id} of type {otype} cancelled")
    
    # проверка по переводу стопа в безубыточность
    def check_stop_break(self) -> bool:
        if self.opened_volume >= self.closed_volume and self.realized_pnl > Decimal("0"):
            checked = False
            for o in self.orders:
                if o.type == OrderType.TAKE_PROFIT and o.meta.get("tp_to_break") and o.status == OrderStatus.FILLED:
                    checked = True
                    continue
                
                if checked and o.type == OrderType.STOP_LOSS and not o.meta.get("moved_to_break") and o.status == OrderStatus.ACTIVE:
                    return True
        return False
    
    def is_hedge(self) -> bool:
        return self.type == PositionType.HEDGE
    

    # ------------------------
    # Управление исполнением
    # ------------------------
    def record_execution(self, order: Order, price: Decimal, volume: Decimal, bar_index: datetime):
        """
        Применить исполнение к позиции и обновить состояние.
        1. Записать исполнение
        2. Обновить состояние позиции
        """
        # по объему пометить ордер как заполненный (полностью или частично)
        # ! поменяет статус ордера соответственно
        order.mark_filled(volume, bar_index)

        # ! управление объемами и средней ценой для входов/закрытий
        if order.type == OrderType.ENTRY:
            prev_total = self.opened_volume * self.avg_entry_price
            
            self.opened_volume += to_decimal(volume)
            
            if self.avg_entry_price == 0:
                self.avg_entry_price = to_decimal(price)
            else:
                # пересчитать среднюю цену входа
                self.avg_entry_price = (prev_total + to_decimal(price) * to_decimal(volume)) / self.opened_volume

            # mark active if at least some opened
            self.status = Position_Status.ACTIVE
            logger.info(f"[{self.symbol}] ☑️ Ордер {order.id[:6]} Тип: {order.type.value} Исполнен.  Объем: {order.volume}, Средняя цена входа: {self.avg_entry_price}")  

        # если это закрывающий ордер (TP/SL/CLOSE)
        elif order.type in {OrderType.TAKE_PROFIT, OrderType.CLOSE, OrderType.STOP_LOSS}:
            # обновить закрытый объем
            self.closed_volume += to_decimal(volume)
            # рассчитать PnL для закрытого объема
            if self.avg_entry_price is not None:
                if self.direction == Direction.LONG:
                    pnl = (price - self.avg_entry_price) * volume
                else:
                    pnl = (self.avg_entry_price - price) * volume
                self.realized_pnl += pnl
                order.profit = pnl
                
                if order.status in (OrderStatus.FILLED, OrderStatus.PARTIAL):
                    if order.type == OrderType.TAKE_PROFIT:
                        self.filled_tp_volume += volume
                    elif order.type == OrderType.STOP_LOSS:
                        self.filled_sl_volume += volume
                    elif order.type == OrderType.CLOSE:
                        self.filled_close_volume += volume
                        
                logger.info(f"☑️ Ордер {order.id[:6]} [bool cyan] Тип:{order.type.value}[/bool cyan] Исполнен. Объем: {order.volume} profit: {order.profit}")

        # обновить статус позиции
        if  self.opened_volume > Decimal("0") and self.closed_volume >=  self.opened_volume:
            # закрыт весь объем позиции
            # Меняет Статус на закрывающий. Может быть TAKEN_FULL, STOPPED, TAKEN_PART
            self.setStatus()
            self.bar_closed = bar_index


        elif self.closed_volume > Decimal("0") and self.closed_volume  < self.opened_volume:
            # закрыта частично
            logger.info(f"[symbol]🟢 Позиция {self.id[:6]} частично закрыта. Статус: {self.status.value}")
            
        # записываем исполнение
        ex = Execution(price=price, volume=volume, bar_index=bar_index, realized_pnl=(order.profit or Decimal("0")), order_id=order.id) 
        self.executions.append(ex)

    # ------------------------
    # Позиционные утилиты
    # ------------------------

    # Расчет плавающего PnL
    def calc_worst_unrealized_pnl(self, high_price: Decimal, low_price: Decimal) -> Decimal:
        """
        Расчет плавающего PnL для активной позиции
        """
        if self.opened_volume <= Decimal("0") or self.status is not Position_Status.ACTIVE:
            return Decimal("0")
        
        remaining_volume = self.opened_volume - self.closed_volume
        
        if remaining_volume <= Decimal("0"):
            return Decimal("0")
        
        if self.direction == Direction.LONG:
            # Для лонга: profit = (текущая цена - средняя цена входа) * оставшийся объем
            return (low_price - self.avg_entry_price) * remaining_volume
        else:
            # Для шорта: profit = (средняя цена входа - текущая цена) * оставшийся объем
            return (self.avg_entry_price - high_price) * remaining_volume
        
    
    
    # Устанавливает статус позиции
    def setStatus(self):
        if self.status != Position_Status.ACTIVE:
            return

        total_filled = self.filled_tp_volume + self.filled_sl_volume + self.filled_close_volume
        if total_filled < self.opened_volume:
            return  # ещё не вся позиция закрыта            
    
        # Определяем финальный статус:
        if self.filled_close_volume > Decimal("0"):
            self.status = Position_Status.CANCELED
        elif self.filled_sl_volume >= self.opened_volume:
            self.status = Position_Status.STOPPED
        elif self.filled_tp_volume >= self.opened_volume:
            self.status = Position_Status.TAKEN_FULL
        else:
            self.status = Position_Status.TAKEN_PART

        logger.info(f"✅ Позиция {self.id[:6]} закрыта. Статус: {self.status.value}")
                
                
    @property            
    # Оставшийся объем для закрытия
    def remaining_volume(self) -> Decimal:
        return max(Decimal("0"), self.opened_volume - self.closed_volume)
    
    # Получить активные заказы 
    def get_active_orders(self) -> List[Order]:
        return [o for o in self.orders if o.status == OrderStatus.ACTIVE]

    # Получить ордера по типу только активные
    def get_orders_by_type(self, otype: OrderType, active_only: bool = True) -> List[Order]:
        if active_only:
            return [o for o in self.orders if o.type == otype and o.status == OrderStatus.ACTIVE]
        else:
            return [o for o in self.orders if o.type == otype]

    # Округление цены до размера тика
    def round_to_tick(self, price: Decimal) -> Decimal:
        if not self.tick_size:
            return price
        if self.tick_size <= 0:
            return price
        q = (to_decimal(price) / self.tick_size).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return q * self.tick_size

    # Переместить стоп-лосс к безубыточности
    def move_stop_to_break_even(self):
        if self.avg_entry_price is None:
            logger.warning("Невозможно переместить стоп в безубыток: записей пока нет.")
            return None
        be_price = self.avg_entry_price # Средняя цена входа
        # отменить существующие активные стопы и добавить новый стоп по цене входа
        self.cancel_orders_by_type(OrderType.STOP_LOSS)
        new_stop = Order(
            id=uuid4().hex,
            type=OrderType.STOP_LOSS,
            price=self.round_to_tick(be_price),
            volume=self.remaining_volume,
            direction=self.direction,
            meta={"moved_to_break": True}
        )
        self.add_order(new_stop)
        logger.info(f"Позиция {self.id[:6]}: стоп перенесен в точку безубыточности цена: {new_stop.price}, volume={new_stop.volume}")
        return new_stop



    def __repr__(self):
        return f"<Position id={self.id[:6]} sym={self.symbol} dir={self.direction.value} status={self.status.value} opened={self.opened_volume} closed={self.closed_volume} avg_entry={self.avg_entry_price} pnl={self.realized_pnl}>"
