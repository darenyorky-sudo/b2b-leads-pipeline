import logging
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class DataTransformer:
    def __init__(self):
        self.conn_params = {
            "host": "localhost",
            "port": 5432,
            "dbname": "leads_db",
            "user": "admin",
            "password": "admin_password"
        }

    def transform(self):
        """Выполняет ультра-очистку и дедупликацию."""
        transform_query = """
        -- 1. Агрессивная нормализация (удаляем всё лишнее)
        UPDATE industrial_leads SET 
            name = UPPER(REGEXP_REPLACE(TRIM(name), '\s+', ' ', 'g')), 
            address = REGEXP_REPLACE(TRIM(address), '\s+', ' ', 'g');
        
        UPDATE industrial_leads SET website = 'N/A' WHERE website IS NULL;
        DELETE FROM industrial_leads WHERE name IN ('UNKNOWN ENTERPRISE', '', 'NO_NAME_PROVIDED') OR name IS NULL;

        -- 2. Дедупликация на основе очищенных данных
        CREATE TEMP TABLE temp_leads AS 
        SELECT DISTINCT ON (name, address) * FROM industrial_leads 
        ORDER BY name, address, id;

        TRUNCATE TABLE industrial_leads;
        INSERT INTO industrial_leads SELECT * FROM temp_leads;
        DROP TABLE temp_leads;
        """
        
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute(transform_query)
                conn.commit()
            logger.info("Data fully deduplicated and normalized.")
        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            raise

if __name__ == "__main__":
    transformer = DataTransformer()
    transformer.transform()