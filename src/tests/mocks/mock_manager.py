class MockPositionManager:
    def __init__(self):
        self.closed = []
        self.canceled = []

    def cancel_active_orders(self, position_id, bar):
        self.canceled.append(position_id)

    def close_position_at_market(self, position_id, price, bar):
        self.closed.append(position_id)
