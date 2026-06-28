import json
import logging
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class PostgresLoader:
    def __init__(self):
        # Конфигурация подключения совпадает с docker-compose.yml
        self.conn_params = {
            "host": "localhost",
            "port": 5432,
            "dbname": "leads_db",
            "user": "admin",
            "password": "admin_password"
        }

    def setup_database(self):
        """Создает схему таблицы, если она не существует."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS industrial_leads (
            id BIGINT PRIMARY KEY,
            name VARCHAR(255),
            lead_type VARCHAR(100),
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            phone VARCHAR(100),
            website TEXT,
            address TEXT,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute(create_table_query)
                conn.commit()
            logger.info("Database schema validated/created successfully.")
        except Exception as e:
            logger.error(f"Failed to setup database: {e}")
            raise

    def load_data(self, jsonl_path: Path):
        """Читает JSONL и загружает данные в PostgreSQL."""
        if not jsonl_path.exists():
            logger.error(f"File not found: {jsonl_path}")
            return

        records = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                records.append(json.loads(line))

        if not records:
            logger.warning("No records found in JSONL to load.")
            return

        # Идемпотентный запрос: обновляет данные при совпадении ID (ON CONFLICT)
        insert_query = """
        INSERT INTO industrial_leads (id, name, lead_type, latitude, longitude, phone, website, address)
        VALUES (%(id)s, %(name)s, %(lead_type)s, %(latitude)s, %(longitude)s, %(phone)s, %(website)s, %(address)s)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            phone = EXCLUDED.phone,
            website = EXCLUDED.website,
            address = EXCLUDED.address;
        """

        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    execute_batch(cur, insert_query, records)
                conn.commit()
            logger.info(f"Successfully loaded {len(records)} records into PostgreSQL.")
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            raise

if __name__ == "__main__":
    loader = PostgresLoader()
    data_file = Path("data/raw_leads.jsonl")
    
    loader.setup_database()
    loader.load_data(data_file)