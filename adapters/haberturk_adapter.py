from datetime import datetime
from bs4 import BeautifulSoup
from .base_adapter import BaseAdapter
from config import CATEGORIES

class HaberturkAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(
            source_id="haberturk",
            source_name="Habertürk",
            category=CATEGORIES["RESMI"]
        )

    def fetch_latest_news(self) -> list:
        rss_urls = [
            "https://news.google.com/rss/search?q=site:haberturk.com&hl=tr&gl=TR&ceid=TR:tr",
            "https://www.haberturk.com/rss/gundem.xml"
        ]
        items = []
        for url in rss_urls:
            rss_items = self.parse_rss_feed(url, max_items=50)
            for item in rss_items:
                item["source_id"] = self.source_id
                item["source_name"] = self.source_name
                item["category"] = self.category
                items.append(item)

        if items:
            return items[:60]
        return []
