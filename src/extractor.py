import asyncio
import logging
import json
from pathlib import Path
import aiohttp
from src.models import IndustrialLead, ExtractorConfig

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class OverpassExtractor:
    def __init__(self, config: ExtractorConfig):
        self.config = config
        self.api_url = "https://overpass-api.de/api/interpreter"

    def _build_query(self, region_name: str) -> str:
        """
        Формирует отказоустойчивый запрос к Overpass API.
        Ищет конкретные предприятия (works) и коммерческие офисы.
        """
        return f"""
        [out:json][timeout:{self.config.timeout}];
        area["name"="{region_name}"]->.searchArea;
        (
          node["man_made"="works"](area.searchArea);
          way["man_made"="works"](area.searchArea);
          node["office"="energy"](area.searchArea);
          way["office"="energy"](area.searchArea);
          node["office"="company"](area.searchArea);
          way["office"="company"](area.searchArea);
        );
        out center;
        """

    async def fetch_raw_data(self, region_name: str) -> dict:
        """Выполняет асинхронный запрос к API с логикой повторных попыток."""
        query = self._build_query(region_name)
        async with aiohttp.ClientSession() as session:
            delay = 1.0
            for attempt in range(1, self.config.max_retries + 1):
                try:
                    logger.info(f"Sending request to Overpass API (Attempt {attempt}/{self.config.max_retries})...")
                    async with session.post(self.api_url, data={"data": query}, timeout=self.config.timeout) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            logger.warning(f"Rate limit hit (429). Retrying in {delay} seconds...")
                        else:
                            logger.error(f"API returned status code {response.status}")
                except Exception as e:
                    logger.error(f"Network error during extraction: {str(e)}")
                
                if attempt < self.config.max_retries:
                    await asyncio.sleep(delay)
                    delay *= self.config.backoff_factor
            
            raise RuntimeError("Failed to fetch data from Overpass API after maximum retries.")

    def parse_and_validate(self, raw_data: dict) -> list[IndustrialLead]:
        """Парсит сырой JSON и валидирует его через Pydantic-модели."""
        elements = raw_data.get("elements", [])
        validated_leads = []

        for elem in elements:
            try:
                tags = elem.get("tags", {})
                
                # Извлекаем координаты
                lat = elem.get("lat") or elem.get("center", {}).get("lat")
                lon = elem.get("lon") or elem.get("center", {}).get("lon")
                
                if not lat or not lon:
                    continue

                # Формируем плоскую структуру для Pydantic
                lead_data = {
                    "id": elem["id"],
                    "name": tags.get("name") or tags.get("operator"),
                    "amenity": tags.get("man_made") or tags.get("office") or "industrial_zone",
                    "latitude": lat,
                    "longitude": lon,
                    "phone": tags.get("phone") or tags.get("contact:phone"),
                    "website": tags.get("website") or tags.get("contact:website"),
                    "address": tags.get("addr:street")
                }

                lead = IndustrialLead(**lead_data)
                validated_leads.append(lead)
            except Exception as e:
                logger.debug(f"Skipping element {elem.get('id')} due to validation error: {str(e)}")
                continue

        logger.info(f"Successfully validated {len(validated_leads)} leads out of {len(elements)} raw elements.")
        return validated_leads

    def save_to_jsonl(self, leads: list[IndustrialLead], output_path: Path):
        """Сохраняет валидированные данные в файлы формата JSONLines."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for lead in leads:
                f.write(lead.model_dump_json() + "\n")
        logger.info(f"Data successfully saved to Data Lake: {output_path}")

async def main():
    config = ExtractorConfig()
    extractor = OverpassExtractor(config)
    
    # Город вшит жестко
    target_region = "Атырау"
    output_file = Path("data/raw_leads.jsonl")

    try:
        raw_data = await extractor.fetch_raw_data(target_region)
        validated_leads = extractor.parse_and_validate(raw_data)
        extractor.save_to_jsonl(validated_leads, output_file)
    except Exception as e:
        logger.critical(f"Pipeline extraction failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())