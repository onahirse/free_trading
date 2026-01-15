from uuid import uuid4
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import uuid4

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.trading_engine.core.enums import Direction, OrderType, OrderStatus
from src.trading_engine.core.position import Position
from src.trading_engine.orders.order_factory import Order

# -------------------------
# Manager & Executor
# -------------------------
class PositionManager:
    """
    Управление позициями: открытие, закрытие, получение списка позиций.
    Поддерживает множественные позиции на один и тот же символ (хеджирование).
    """
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.id = uuid4().hex
    # ------------------------
    # открытие 
    # ------------------------
    def open_position(self, 
                    symbol: str, 
                    source: str, 
                    direction: Direction, 
                    tick_size: Optional[Decimal], 
                    open_bar: Optional[datetime],
                    meta: Dict[str, Any]
                ) -> Position:

        pos = Position(
            symbol=symbol, 
            direction=direction, 
            tick_size=tick_size, 
            source=source,
            meta=meta
            )
        self.positions[pos.id] = pos
        self.positions[pos.id].bar_opened = open_bar
        logger.debug(f"[{symbol}] 📚 Создана новая позиция  {direction.value} id: {pos.id} ")
        return pos

    # ------------------------
    # закрытие по ID
    # ------------------------
    def cancel_active_orders(self, position_id: str, close_bar: Optional[datetime] = None):
        pos = self.positions.get(position_id)
        if not pos:
            return
        # cancel active orders
        for o in pos.get_active_orders():
            o.status = OrderStatus.CANCELLED
        
        logger.debug(f"📚По позиции {position_id[:6]} Все активные ордера отменены на баре {pos.bar_closed}")

    # ------------------------
    # Закрытие позиции по текущей цене
    # ------------------------
    def close_position_at_market(self, position_id: str, current_price: Decimal, close_bar: Optional[datetime] = None):
        """
        Закрыть позицию полностью по текущей рыночной цене.
        Устанавливает статус CANCELLED для всех активных ордеров.
        """
        pos = self.positions.get(position_id)
        if not pos:
            logger.warning(f"Позиция {position_id} не найдена")
            return
        
        remaining_vol = pos.remaining_volume
        if remaining_vol > 0:
            # Создаем закрывающий маркет ордер для закрытия всей позиции
            market_order = Order(
                id=uuid4().hex,
                type=OrderType.CLOSE,
                price=current_price,
                volume=remaining_vol,
                direction=pos.direction,
                status=OrderStatus.ACTIVE
            )
            pos.add_order(market_order)
            logger.info(f"Создан ордер на закрытие по текущей рыночной цене: {current_price}")
        

    # ------------------------
    # Получить позиции по символу и/или направлению 
    # ------------------------
    def get_positions(self, symbol: Optional[str] = None, direction: Optional[Direction] = None) -> List[Position]:
        res = list(self.positions.values())
        if symbol:
            res = [p for p in res if p.symbol == symbol]
        if direction:
            res = [p for p in res if p.direction == direction]
        return res
