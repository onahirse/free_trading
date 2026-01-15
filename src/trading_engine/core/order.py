from decimal import Decimal
from typing import  Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

# Логирование
# ====================================================
from src.utils.logger.logger import get_logger
logger = get_logger(__name__)

from src.trading_engine.core.enums import Direction, OrderType, OrderStatus

@dataclass
class Order:
    id: str
    type: OrderType
    price: Optional[Decimal]  # Нет для рыночных ордеров
    volume: Decimal           # абсолютный объем в нативных единицах (не дробях)
    direction: Direction      #направление: ДЛИННОЕ или КОРОТКОЕ (влияет на интерпретацию стопов)
    profit: Optional[Decimal] = Decimal("0")  # результат исполнения ордера
    status: OrderStatus = OrderStatus.ACTIVE
    filled: Decimal = field(default_factory=lambda: Decimal("0"))
    created_bar: Optional[datetime] = None  # optional bar index when created
    close_bar: Optional[datetime] = None  # optional bar index when closed
    meta: Dict[str, Any] = field(default_factory=dict)

    # ------------------------
    # Метод управления остатком объема ордера
    # ------------------------
    def remaining(self) -> Decimal:
        return max(Decimal("0"), self.volume - self.filled)

    # ------------------------
    # Метод управления заполнением ордера
    # ------------------------
    def mark_filled(self, amount: Decimal, close_bar: datetime):
        self.filled += amount
        if self.filled >= self.volume:
            # полный объем ордера заполнен
            self.status = OrderStatus.FILLED
            self.close_bar = close_bar
        else:
            # частичное заполнение ордера
            # self.status = OrderStatus.FILLED
            self.status = OrderStatus.PARTIAL
            self.close_bar = close_bar
    
    # Расчет профита
    def calculate_profit(self, current_price: Decimal):
        if self.type in {OrderType.TAKE_PROFIT, OrderType.STOP_LOSS, OrderType.CLOSE} and self.price and self.volume:
            if self.direction == Direction.LONG:
                self.profit = (current_price - self.price) * self.volume
            else:
                self.profit = (self.price - current_price) * self.volume

