from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import uuid4

from src.trading_engine.core.enums import Direction, OrderType
from src.trading_engine.core.order import Order

# -------------------------
# Создание ордеров
# -------------------------
def make_order(order_type: OrderType, price: Optional[Decimal], volume: Decimal, direction: Direction, created_bar: Optional[datetime] = None, meta: Optional[Dict[str, Any]] = None) -> Order:
    """
    Создать ордер на основе параметров.

    :param order_type: тип ордера (MARKET, TAKE_PROFIT, STOP_LOSS, LIMIT, ENTRY)
    :param price: цена ордера (если достигнута)
    :param volume: объем ордера
    :param direction: направление ордера (LONG, SHORT)
    :param created_at: метка создания ордера (если не указана, то текущая метка)
    :param meta: мета-информация ордера (необязательный параметр)
    :return: созданный ордер
    """
    return Order(
        id=uuid4().hex,
        type=order_type,
        price=price if price is not None else None,
        volume=volume,
        direction=direction,
        created_bar=created_bar,
        meta=meta or {}
    )