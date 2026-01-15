# src/backtester/result/test_result.py
from uuid import uuid4
from decimal import Decimal

class TestResult:
    def __init__(self, symbol, timeframe, start_deposit):
        self.id = uuid4().hex
        self.symbol = symbol
        self.timeframe = timeframe

        self.positions = {}
        self.equity_curve = []
        self.drawdown_curve = []

        self.start_deposit = Decimal(start_deposit)
        self.balance = Decimal(start_deposit)
        self.equity = Decimal(start_deposit)

        self.metrics = None
