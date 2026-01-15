# src/backtester/reports/summary/summary_report_generator.py
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from src.utils.logger import get_logger

logger = get_logger(__name__)

class SummaryReportGenerator:
    def __init__(self, template_dir: str, settings_test: dict):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.settings_test = settings_test

    def generate(self, summary_data: dict, output_path: Path):
        template = self.env.get_template("v2/report_summary.html")

        html = template.render(
            coins=summary_data,
            settings=self.settings_test,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        output_path.write_text(html, encoding="utf-8")
        logger.info(f"✅ Summary report saved: {output_path}")
