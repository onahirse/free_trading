from src.config.config import config
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# расчет уровней Фибоначчи
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
def fibonacci_levels(z1: float, z2: float, direction: int) -> dict:
    """
    Рассчитывает уровни коррекции Фибоначчи.

    :param z1: float — начальная точка (например, минимум)
    :param z2: float — конечная точка (например, максимум)
    :param direction: int — направление движения (1 — вверх, -1 — вниз)
    :return: dict — уровни коррекции в формате {уровень: значение}
    """
    fib_ratios = config.get_setting("STRATEGY_SETTINGS", "FIBONACCI_LEVELS")
    levels = {}

    for r in fib_ratios:
    
        if direction == 1:
            # коррекция вниз
            level = z1 + (z2 - z1) * r['level']
        elif direction == -1:
        # коррекция вверх
            level = z1 - (z1 - z2) * r['level']
        else:
            raise ValueError("direction должен быть 'up' или 'down'")
        

        order_info = {'level_price': level, 'volume': r['volume']}
        if r.get('SL', False):
            order_info['sl'] = True
        if r.get('TP', False):
            order_info['tp'] = True
        if r.get('TP_TO_BREAK', False):
            order_info['tp_to_break'] = True

        levels[round(r['level'] * 100, 1)] = order_info 

    return dict(list(levels.items())[::-1])
