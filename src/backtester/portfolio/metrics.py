
# * sharpe, drawdown, winrate
# src/backtester/portfolio/metrics.py


class MetricsCalculator:
    @staticmethod
    def from_positions(positions: dict) -> dict:
        total_pnl = sum(p.realized_pnl for p in positions.values())
        wins = [p for p in positions.values() if p.realized_pnl > 0]
        losses = [p for p in positions.values() if p.realized_pnl < 0]
        total_win = sum(p.realized_pnl for p in positions.values() if p.realized_pnl > 0)
        total_loss = sum(p.realized_pnl for p in positions.values() if p.realized_pnl < 0)

        return {
            "total_pnl": total_pnl,
            "winrate": len(wins) / len(positions) * 100 if positions else 0,
            "wins": len(wins),
            "losses": len(losses),
            "count": len(positions),
            "total_win": total_win,
            "total_loss": total_loss,
            
        }
