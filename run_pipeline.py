import logging
import sys
from src.extractor import OverpassExtractor, ExtractorConfig
from src.loader import PostgresLoader
from src.transformer import DataTransformer
from src.dq_checks import DataQualityChecker
from src.reporter import ReportGenerator

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info(">>> Starting Data Pipeline Execution <<<")

        # 1. Extract
        logger.info("Step 1: Extracting data...")
        # Запускаем асинхронно
        import asyncio
        asyncio.run(extractor_task())

        # 2. Load
        logger.info("Step 2: Loading data to PostgreSQL...")
        loader = PostgresLoader()
        loader.setup_database()
        loader.load_data(Path("data/raw_leads.jsonl"))

        # 3. Transform
        logger.info("Step 3: Transforming data...")
        transformer = DataTransformer()
        transformer.transform()

        # 4. Quality Check
        logger.info("Step 4: Running Data Quality Checks...")
        checker = DataQualityChecker()
        checker.run_checks()

        # 5. Report
        logger.info("Step 5: Generating final report...")
        reporter = ReportGenerator()
        reporter.generate_csv()

        logger.info(">>> Pipeline completed successfully! <<<")

    except Exception as e:
        logger.critical(f"Pipeline crashed: {e}")
        sys.exit(1)

async def extractor_task():
    from pathlib import Path
    config = ExtractorConfig()
    config.timeout = 120  # Даем API целых 2 минуты на обработку нашего запроса
    config.max_retries = 5 # Даем больше шансов на успех
    extractor = OverpassExtractor(config)
    raw_data = await extractor.fetch_raw_data()
    validated_leads = extractor.parse_and_validate(raw_data)
    extractor.save_to_jsonl(validated_leads, Path("data/raw_leads.jsonl"))

if __name__ == "__main__":
    from pathlib import Path
    main()