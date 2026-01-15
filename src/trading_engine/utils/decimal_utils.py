from decimal import Decimal
from typing import Any

# -------------------------
# перевод в Decimal
# -------------------------
def to_decimal(v: Any) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))