import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from . import ALL_ADAPTER_CLASSES

logger = logging.getLogger("AdaptersRunner")

def run_all_adapters(max_workers: int = 20) -> list:
    """
    Executes all 14 news adapters concurrently.
    Any single adapter failure is caught and logged, without affecting others.
    """
    all_articles = []
    logger.info(f"Starting news gathering from {len(ALL_ADAPTER_CLASSES)} adapters...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_adapter = {
            executor.submit(adapter_cls().fetch_latest_news): adapter_cls.__name__
            for adapter_cls in ALL_ADAPTER_CLASSES
        }

        for future in as_completed(future_to_adapter):
            adapter_name = future_to_adapter[future]
            try:
                items = future.result()
                logger.info(f"[{adapter_name}] successfully fetched {len(items)} items.")
                all_articles.extend(items)
            except Exception as e:
                logger.error(f"[{adapter_name}] failed with error: {e}", exc_info=False)

    logger.info(f"Total fetched articles across all adapters: {len(all_articles)}")
    return all_articles
