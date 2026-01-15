# src/backtester/reports/collector.py
class SummaryCollector:
    def __init__(self):
        self.data = {}

    def add(
        self,
        *,
        symbol: str,
        coin: str,
        timeframe: str,
        metrics: dict,
        test_id: str,
        portfolio: dict,
        report_path: str
    ):
        self.data.setdefault(symbol, [])
        self.data[symbol].append({
            "coin": coin,
            "timeframe": timeframe,
            "metrics": metrics,
            "portfolio": portfolio,
            "report_path": report_path,
            "test_id": test_id,
        })
