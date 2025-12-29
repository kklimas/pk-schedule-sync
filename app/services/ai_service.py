import httpx
import json
import logging
from app.config import config

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, model_name: str = "pk-llama", base_url: str = None):
        self.model_name = model_name
        # Use the provided base_url, or fall back to the config value
        target_url = base_url or config.AI_SERVICE_URL
        if target_url:
            self.base_url = f"{target_url.rstrip('/')}/api/generate"
        else:
            self.base_url = None

    def _enrich_single_lecture(self, lecture_data: dict) -> dict:
        """
        Shortcuts enrichment for single lecture.
        """
        for key, value in lecture_data.items():
            if value in config.LECTURE_SHORTCUTS:
                lecture_data[key] = config.LECTURE_SHORTCUTS[value]
        return lecture_data

    async def enrich_lectures(self, lectures_data: list[dict]) -> list[dict]:
        """
        Sends raw lecture data to local Ollama instance for structured parsing in batches.
        """
        if not lectures_data:
            return []

        batch_size = 3
        all_enriched_data = []

        async with httpx.AsyncClient(timeout=120.0) as client:
            for i in range(0, len(lectures_data), batch_size):
                batch = lectures_data[i : i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} lectures...")
                
                prompt = json.dumps(batch, ensure_ascii=False)
                
                try:
                    response = await client.post(
                        self.base_url,
                        json={
                            "model": self.model_name,
                            "prompt": prompt,
                            "stream": False
                        }
                    )
                    response.raise_for_status()
                    
                    result_json = response.json().get('response', '{}')
                
                    try:
                        batch_result = json.loads(result_json)
                        logger.info(f"Batch {i//batch_size + 1} raw result: {batch_result}")
                        
                        # Handle different model output styles
                        if isinstance(batch_result, list):
                            items = batch_result
                        elif isinstance(batch_result, dict):
                            # Try to find a list inside (common if model wraps in "data" or "result")
                            items = next((v for v in batch_result.values() if isinstance(v, list)), None)
                            if items is None:
                                # If no list found, maybe it returned a single object as requested but it's one of the items?
                                items = [batch_result]
                        else:
                            items = []

                        if isinstance(items, list):
                            if len(items) != len(batch):
                                logger.warning(f"Batch {i//batch_size + 1} size mismatch: expected {len(batch)}, got {len(items)}")
                            
                            all_enriched_data.extend(items)
                            logger.info(f"Batch {i//batch_size + 1} processed. Added {len(items)} items.")
                        else:
                            logger.error(f"Batch {i//batch_size + 1} failed to yield a valid list of results.")
                            
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse Ollama response for batch {i//batch_size + 1}.")

                
                except Exception as e:
                    logger.error(f"Failed to enrich batch {i//batch_size + 1}: {str(e)}")
                    # Continue with other batches even if one fails
                    continue

        logger.info(f"AI enrichment complete. Total items enriched: {len(all_enriched_data)}.")
        return list(map(self._enrich_single_lecture, all_enriched_data)) 

ai_service = AIService()
