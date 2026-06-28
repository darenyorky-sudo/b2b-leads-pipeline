import csv
import logging
import psycopg2
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        self.conn_params = {
            "host": "localhost",
            "port": 5432,
            "dbname": "leads_db",
            "user": "admin",
            "password": "admin_password"
        }

    def generate_csv(self):
        """Выгружает чистые данные в CSV-отчет."""
        report_dir = Path("reports")
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = report_dir / f"industrial_leads_report_{timestamp}.csv"

        query = "SELECT id, name, lead_type, latitude, longitude, phone, website, address FROM industrial_leads"

        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    rows = cur.fetchall()
                    colnames = [desc[0] for desc in cur.description]

                    with open(file_path, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(colnames)
                        writer.writerows(rows)
            
            logger.info(f"Report generated successfully: {file_path}")
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            raise

if __name__ == "__main__":
    reporter = ReportGenerator()
    reporter.generate_csv()