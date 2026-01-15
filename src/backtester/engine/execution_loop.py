# исполнение по lower TF

# src/backtester/engine/execution_loop.py
class ExecutionLoop:
    def __init__(self, engine):
        self.engine = engine

    # Перебор минутных баров и передача их в движок исполнения
    def run(self, bars_1m):
        # Итерация по минутным барам
        for bar in bars_1m:
            self.engine.process_bar(bar, bar[4])
