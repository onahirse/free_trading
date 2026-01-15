from decimal import Decimal
from typing import Optional
from datetime import datetime
from dataclasses import dataclass   

# ? класс исполнения ордера
@dataclass
class Execution:
    price: Decimal
    volume: Decimal
    bar_index: Optional[datetime]  # индекс бара исполнения
    order_id: str
    realized_pnl: Decimal = Decimal("0")