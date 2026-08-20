import os
import re
import html
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

            # Parse publish date (supports iso_date and relative text like '2 saat önce', '15 dak önce')
            pub_date_str = res.get("iso_date")
            raw_date_str = res.get("date", "")
            publish_date = None

            if pub_date_str:
                try:
                    clean_iso = pub_date_str.split(".")[0].replace("Z", "")
                    dt = datetime.datetime.fromisoformat(clean_iso)
                    publish_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass

            if not publish_date and raw_date_str:
                import re
                now = datetime.datetime.now()
                raw_lower = raw_date_str.lower()
                m_min = re.search(r"(\d+)\s*(?:dak|min)", raw_lower)
                m_hr = re.search(r"(\d+)\s*(?:saat|hour|hr)", raw_lower)
                m_day = re.search(r"(\d+)\s*(?:gün|day)", raw_lower)
                if m_min:
                    publish_date = (now - datetime.timedelta(minutes=int(m_min.group(1)))).strftime("%Y-%m-%d %H:%M:%S")
                elif m_hr:
                    publish_date = (now - datetime.timedelta(hours=int(m_hr.group(1)))).strftime("%Y-%m-%d %H:%M:%S")
                elif m_day:
                    publish_date = (now - datetime.timedelta(days=int(m_day.group(1)))).strftime("%Y-%m-%d %H:%M:%S")

            # Check if title has explicit date
            import html
            t_clean = html.unescape(title)
            month_map = {
                "ocak": "01", "şubat": "02", "mart": "03", "nisan": "04", "mayıs": "05", "haziran": "06",
                "temmuz": "07", "ağustos": "08", "agustos": "08", "eylül": "09", "ekim": "10", "kasım": "11", "aralık": "12"
            }
            m_tdate = re.search(r'\b([0-3]?\d)\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Agustos|Eylül|Ekim|Kasım|Aralık)\s*(\d{4})?\b', t_clean, re.I)
            if m_tdate:
                t_day = int(m_tdate.group(1))
                t_mon = month_map.get(m_tdate.group(2).lower(), "08")
                t_yr = m_tdate.group(3) or datetime.datetime.now().strftime("%Y")
                if 1 <= t_day <= 31:
                    dt_str = f"{t_yr}-{t_mon}-{t_day:02d} 12:00:00"
                    try:
                        dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                        if dt <= datetime.datetime.now():
                            publish_date = dt_str
                    except:
                        pass

            if not publish_date:
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
