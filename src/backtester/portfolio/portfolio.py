# /* Портфель /portfolio/portfolio.py
# * Деньги, прибыль, максимальная прибыль,  
# * Кривая прибыли, кривая убытков

from decimal import Decimal
from src.trading_engine.core.enums import Position_Status

class Portfolio:
    def __init__(self, start_balance: Decimal):
        self.balance = start_balance
        self.equity = start_balance
        self.max_equity = start_balance

        self.equity_curve = []
        self.drawdown_curve = []

    def on_bar(self, timestamp, realized_pnl: Decimal, floating_pnl: Decimal):
        self.balance += realized_pnl
        self.equity = self.balance + floating_pnl

        self.max_equity = max(self.max_equity, self.equity)
        drawdown = (self.equity - self.max_equity) / self.max_equity if self.max_equity > 0 else Decimal("0")

        self.equity_curve.append({
            "timestamp": timestamp,
            "balance": self.balance,
            "equity": self.equity
        })

        self.drawdown_curve.append(drawdown)

    @staticmethod
    def calculate_floating(manager, high, low) -> Decimal:
        floating = Decimal("0")
        for pos in manager.positions.values():
            if pos.status == Position_Status.ACTIVE:
                floating += pos.calc_worst_unrealized_pnl(high, low)
        return floating
