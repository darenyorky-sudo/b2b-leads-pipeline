import logging
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class DataQualityChecker:
    def __init__(self):
        self.conn_params = {
            "host": "localhost",
            "port": 5432,
            "dbname": "leads_db",
            "user": "admin",
            "password": "admin_password"
        }

    def run_checks(self):
        """Выполняет серию проверок качества данных."""
        # Убедись, что отступы здесь ровно 8 пробелов от начала строки
        checks = {
            "No empty names": "SELECT COUNT(*) FROM industrial_leads WHERE name = 'NO_NAME_PROVIDED'",
            "No duplicates": "SELECT COUNT(*) FROM (SELECT name, COUNT(*) FROM industrial_leads GROUP BY name HAVING COUNT(*) > 1) AS dups",
            "Geodata present": "SELECT COUNT(*) FROM industrial_leads WHERE latitude IS NULL OR longitude IS NULL"
        }

        logger.info("Starting Data Quality Checks...")
        
        with psycopg2.connect(**self.conn_params) as conn:
            with conn.cursor() as cur:
                for check_name, query in checks.items():
                    cur.execute(query)
                    count = cur.fetchone()[0]
                    if count > 0:
                        logger.error(f"FAIL: {check_name} - Found {count} invalid records!")
                        raise ValueError(f"Data Quality Check Failed: {check_name}")
                    else:
                        logger.info(f"PASS: {check_name}")
        
        logger.info("All Data Quality Checks passed successfully.")

if __name__ == "__main__":
    checker = DataQualityChecker()
    checker.run_checks()