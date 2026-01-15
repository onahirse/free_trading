# главный orchestrator
# src/als/als_engine.py

from decimal import Decimal
from src.logical.hedging.als.calculator import calculate_roi


class ALSEngine:

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        # self.state = ALSState(set(), [])
        # self.hedge_manager = HedgeManager()
        # self.stop_manager = StopManager()
        # self.close_manager = CloseManager()

    def on_bar(self, *, base_position, current_price, position_manager):

        if not self.config.enabled or not base_position.is_open:
            return

        roi = calculate_roi(
            base_position.entry_price,
            current_price,
            base_position.direction
        )

        # 1️⃣ Emergency close
        if roi <= Decimal(str(self.config.emergency_close_roi)):
            self.logger.debug(f"Срочное закрытие : {roi}%" )
            return

        # 2️⃣ Open hedges
        # 
        
        
        # 3️⃣ Total ROI close
        