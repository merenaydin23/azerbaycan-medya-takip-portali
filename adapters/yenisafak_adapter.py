from datetime import datetime
from bs4 import BeautifulSoup
from .base_adapter import BaseAdapter
from config import CATEGORIES

class YeniSafakAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(
            source_id="yenisafak",
            source_name="Yeni Şafak",
            category=CATEGORIES["IKTIDAR"]
        )

    def fetch_latest_news(self) -> list:
        # We try standard RSS first, then use Google News verified live mirror
        rss_urls = [
            "https://news.google.com/rss/search?q=site:yenisafak.com&hl=tr&gl=TR&ceid=TR:tr",
            "https://www.yenisafak.com/rss?xml=gundem",
            "https://www.yenisafak.com/rss?xml=dunya"
        ]
        items = []
        for url in rss_urls:
            rss_items = self.parse_rss_feed(url, max_items=40)
            if rss_items:
                # Clean up title suffix like ' - Yeni Şafak'
                for item in rss_items:
                    if " - Yeni Şafak" in item["title"]:
                        item["title"] = item["title"].replace(" - Yeni Şafak", "").strip()
                    item["author"] = "Yeni Şafak"
                    items.append(item)
                break

        return items[:40]
