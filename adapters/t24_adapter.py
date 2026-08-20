from datetime import datetime
from bs4 import BeautifulSoup
from .base_adapter import BaseAdapter
from config import CATEGORIES

class T24Adapter(BaseAdapter):
    def __init__(self):
        super().__init__(
            source_id="t24",
            source_name="T24",
            category=CATEGORIES["MUHALIF"]
        )

    def fetch_latest_news(self) -> list:
        rss_urls = [
            "https://news.google.com/rss/search?q=site:t24.com.tr&hl=tr&gl=TR&ceid=TR:tr",
            "https://t24.com.tr/rss"
        ]
        items = []
        for url in rss_urls:
            rss_items = self.parse_rss_feed(url, max_items=40)
            items.extend(rss_items)

        if items:
            return items[:50]
            
            # Find all article links
            for a_tag in soup.find_all("a", href=True):
                href = a_tag.get("href")
                if not href:
                    continue
                if href.startswith("/"):
                    href = "https://t24.com.tr" + href

                if "/haber/" in href and href not in seen_links:
                    seen_links.add(href)
                    title = self.clean_text(a_tag.get_text())
                    # Look for parent/sibling summary
                    parent = a_tag.parent
                    summary = ""
                    p_tag = parent.find("p") if parent else None
                    if p_tag:
                        summary = self.clean_text(p_tag.get_text())

                    if title and len(title) > 15 and not title.lower().startswith("t24"):
                        items.append({
                            "source_id": self.source_id,
                            "source_name": self.source_name,
                            "category": self.category,
                            "title": title,
                            "summary": summary,
                            "author": "T24",
                            "publish_date": self.extract_date_from_card(parent or a_tag),
                            "link": href,
                            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
        return items[:30]
