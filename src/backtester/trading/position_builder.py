# создание позиции + ордера

# src/backtester/trading/position_builder.py
from decimal import Decimal
from src.trading_engine.orders.order_factory import make_order
from src.trading_engine.core.enums import OrderType
from src.risk_manager.risk_manager import RiskManager
from src.trading_engine.core.signal import Signal
from src.trading_engine.core.position import Position

# ==========================
# ? Класс PositionBuilder отвечает за создание новых позиций
# ? на основе полученных торговых сигналов.
# ==========================
class PositionBuilder:
    def __init__(self, manager, coin):
        self.manager = manager
        self.coin = coin

    def build(self, signal: Signal, bar) -> Position:
        if not signal:
            raise ValueError("Необходимо указать сигнал")   
    
        direction = signal.direction
        if direction is None:
            raise ValueError("Необходимо указать направление в сигнале")

        symbol = self.coin["SYMBOL"] + "/USDT"
        tick_size = Decimal(str(self.coin["MINIMAL_TICK_SIZE"]))

        position = self.manager.open_position(
            symbol=symbol,
            source=signal.source,
            direction=direction,
            tick_size=tick_size,
            open_bar=bar[4], # время открытия бара
            meta=signal.metadata
        )

        entry_price = position.round_to_tick(signal.price)
        rm = RiskManager(self.coin)
        volume = rm.calculate_position_size(entry_price)

        position.add_order(
            make_order(OrderType.ENTRY, entry_price, volume, direction, bar[4])
        )
        sum_tp_volume: Decimal = Decimal('0')
        
        for tp in signal.take_profits:
            tp_volume = position.round_to_tick(volume*Decimal(str(tp["volume"])))
            tp_price = position.round_to_tick(Decimal(str(tp["price"])))
            
            if tp.get('tp_to_break', False):
                meta={"tp_to_break": True}
            else:
                meta={}
                
            position.add_order(
                make_order(
                    OrderType.TAKE_PROFIT,
                    tp_price,
                    tp_volume,
                    direction,
                    bar[4],
                    meta=meta
                )
            )
            sum_tp_volume += tp_volume
            
        if sum_tp_volume != volume:
            volume_diff = volume - sum_tp_volume
            if position.orders[-1].type == OrderType.TAKE_PROFIT:
                position.orders[-1].volume += volume_diff  # добавляем недостающий объем к последнему TP


        sum_sl_volume: Decimal = Decimal('0')
        for sl in signal.stop_losses:
            sl_volume = position.round_to_tick(volume*Decimal(str(sl["volume"])))
            sl_price = position.round_to_tick(Decimal(str(sl["price"])))
            
            position.add_order(
                make_order(
                    OrderType.STOP_LOSS,
                    sl_price,
                    sl_volume,
                    direction,
                    created_bar=bar[4]
                )
            )
            sum_sl_volume += sl_volume
        if sum_sl_volume != volume:
            volume_diff = volume - sum_sl_volume
            if position.orders[-1].type == OrderType.STOP_LOSS:
                position.orders[-1].volume += volume_diff  # добавляем недостающий объем к последнему SL


        return position
