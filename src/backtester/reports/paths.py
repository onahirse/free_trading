# src/backtester/reports/paths.py
from pathlib import Path
from datetime import datetime

BASE_REPORT_DIR = Path("reports")

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def build_test_report_path(symbol: str, timeframe: str) -> Path:
    ensure_dir(BASE_REPORT_DIR / "tests")
    return BASE_REPORT_DIR / "tests" / f"{symbol}_TF-{timeframe}.html"

def build_summary_report_path() -> Path:
    ensure_dir(BASE_REPORT_DIR)
    return BASE_REPORT_DIR / "summary.html"
