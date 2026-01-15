# src/backtester/reports/serializers.py
def serialize_meta(meta):
    if not isinstance(meta, dict) or not meta:
        return ""
    return " ".join(f"{k}={v}" for k, v in meta.items())

def serialize_order(order):
    return {
        "id": order.id,
        "order_type": order.type.name,
        "status": order.status.name,
        "price": float(order.price),
        "volume": float(order.volume),
        "profit": float(order.profit),
        "direction": getattr(order.direction, "name", order.direction),
        "filled": getattr(order, "filled", None),
        "created_bar": order.created_bar,
        "close_bar": order.close_bar,
        "meta":  serialize_meta(getattr(order, "meta", {})),  # на случай использования оригинального объекта
    }

def serialize_position(position):
    return {
        "id": position.id,
        "symbol": position.symbol,
        "direction": position.direction.name,
        "status": position.status.name,
        "opened_volume": getattr(position, "opened_volume", None),
        "closed_volume": getattr(position, "closed_volume", None),
        "bar_opened": position.bar_opened,
        "bar_closed": position.bar_closed,
        "avg_entry_price": float(position.avg_entry_price) if position.avg_entry_price else None,
        "profit": getattr(position, "realized_pnl", None),
        "realized_pnl": float(position.realized_pnl),
        "orders": [serialize_order(o) for o in position.orders],
        "meta": getattr(position, "meta", None),
    }

def serialize_positions(positions: dict):
    return [serialize_position(p) for p in positions.values()]
