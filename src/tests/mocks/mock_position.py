import uuid
from decimal import Decimal

class MockPosition:
    def __init__(
        self,
        direction,
        source,
        is_hedge=False,
        price=Decimal("100"),
        volume=Decimal("10"),
    ):
        self.id = str(uuid.uuid4())
        self.direction = direction
        self.source = source
        self.is_hedge = is_hedge
        self.last_price: Decimal = price
        self.volume = volume
