import os
import logging
import requests
import datetime
import email.utils
from pathlib import Path
from config import SERPAPI_KEY, SOURCES_CONFIG, CATEGORIES, BASE_DIR

logger = logging.getLogger("Adapter.SerpApi")

class SerpApiAdapter:
    def __init__(self):
        self.api_key = SERPAPI_KEY
        self.url = "https://serpapi.com/search.json"
        self.log_file = BASE_DIR / "logs" / "serpapi_usage.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _log_usage(self, query_count: int):
        """Logs SerpApi usage count and estimated cost to logs/serpapi_usage.log."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            estimated_cost = query_count * 0.01 # $0.01 per request estimation
            
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] Queries Run: {query_count} | Estimated Cost: ${estimated_cost:.2f}\n")
        except Exception as e:
            logger.error(f"Failed to write SerpApi usage logs: {e}")

    def fetch_source_backup(self, source_name: str, domain: str, category: str) -> list:
        """Fetches news specifically from a configured site domain using google_news engine."""
        if not self.api_key:
            logger.warning("SERPAPI_KEY is not set. Skipping SerpApi search.")
            return []

        params = {
            "engine": "google_news",
            "q": f"site:{domain} Azerbaycan",
            "api_key": self.api_key,
            "gl": "tr",
            "hl": "tr"
        }

        try:
            logger.info(f"Querying SerpApi for source '{source_name}' ({domain})...")
            response = requests.get(self.url, params=params, timeout=6)
            self._log_usage(1)

            if response.status_code != 200:
                logger.error(f"SerpApi returned status code {response.status_code}: {response.text}")
                return []

            data = response.json()
            results = data.get("news_results", [])
            return self._parse_results(results, source_name, category)
        except Exception as e:
            logger.error(f"Error querying SerpApi for {domain}: {e}")
            return []

    def fetch_general_news(self) -> list:
        """Runs multiple wider search queries concurrently to catch articles across all Turkish media."""
        if not self.api_key:
            logger.warning("SERPAPI_KEY is not set. Skipping SerpApi search.")
            return []

        search_queries = [
            "Türkiye gündem son dakika haberleri",
            "Türkiye siyaset ekonomi diplomasi dış politika",
            "Azerbaycan Kafkasya Türk Dünyası haberleri",
            "Türkiye güncel gelişmeler",
            "site:ntv.com.tr",
            "site:haberturk.com",
            "site:cnnturk.com",
            "site:dha.com.tr",
            "site:ekonomim.com",
            "site:gazeteduvar.com.tr",
            "site:karar.com",
            "site:aksam.com.tr",
            "site:star.com.tr",
            "site:yenicaggazetesi.com.tr",
            "site:odatv.com",
            "site:aydinlik.com.tr"
        ]

        all_results = []
        from concurrent.futures import ThreadPoolExecutor

        def _fetch_query(q):
            params = {
                "engine": "google_news",
                "q": q,
                "api_key": self.api_key,
                "gl": "tr",
                "hl": "tr"
            }
            try:
                response = requests.get(self.url, params=params, timeout=6)
                self._log_usage(1)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("news_results", [])
                    return self._parse_results(results, None, None)
            except Exception as e:
                logger.error(f"Error querying SerpApi for query '{q}': {e}")
            return []

        with ThreadPoolExecutor(max_workers=8) as executor:
            res_lists = executor.map(_fetch_query, search_queries)
            for res in res_lists:
                all_results.extend(res)

        return all_results

    def _parse_results(self, news_results: list, default_source_name: str = None, default_category: str = None) -> list:
        """Parses SerpApi raw news items list into standardized news dictionary structure."""
        items = []
        for res in news_results:
            title = res.get("title", "").strip()
            link = res.get("link", "").strip()
            
            if not title or not link:
                continue

            # Parse publish date
            pub_date_str = res.get("iso_date")
            if pub_date_str:
                try:
                    dt = datetime.datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                    publish_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    publish_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                publish_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Determine source name and category
            res_source = res.get("source", {})
            raw_source_name = res_source.get("name", "Bilinmeyen").strip()
            
            source_name = default_source_name
            category = default_category

            if not source_name:
                # If doing a general query, check if this source fits one of our 14 sources
                matched_source = None
                for config in SOURCES_CONFIG:
                    if config["name"].lower() in raw_source_name.lower() or raw_source_name.lower() in config["name"].lower():
                        matched_source = config
                        break
                
                if matched_source:
                    source_name = matched_source["name"]
                    category = matched_source["category"]
                else:
                    source_name = raw_source_name
                    category = CATEGORIES["OTHER"]

            items.append({
                "source_id": "serpapi",
                "source_name": source_name,
                "category": category,
                "title": title,
                "summary": "",  # Google News API doesn't provide body summary snippets
                "author": "",
                "publish_date": publish_date,
                "link": link,
                "veri_kaynagi": "SerpApi",
                "scraped_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        return items
