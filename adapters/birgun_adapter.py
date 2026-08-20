from datetime import datetime
from bs4 import BeautifulSoup
from .base_adapter import BaseAdapter
from config import CATEGORIES

class BirgunAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(
            source_id="birgun",
            source_name="BirGün",
            category=CATEGORIES["MUHALIF"]
        )

    def fetch_latest_news(self) -> list:
        rss_urls = [
            "https://news.google.com/rss/search?q=site:birgun.net&hl=tr&gl=TR&ceid=TR:tr",
            "https://www.birgun.net/xml/rss.xml"
        ]
        items = []
        for url in rss_urls:
            rss_items = self.parse_rss_feed(url, max_items=40)
            items.extend(rss_items)

        if items:
            return items[:50]
            
            for a_tag in soup.find_all("a", href=True):
                href = a_tag.get("href")
                if not href:
                    continue
                if href.startswith("/"):
                    href = "https://www.birgun.net" + href

                if "-haber-" in href or "/haber/" in href or (len(href.split("-")) > 3 and "birgun.net" in href):
                    if href not in seen_links and not href.endswith(".jpg") and not href.endswith(".png"):
                        seen_links.add(href)
                        title = self.clean_text(a_tag.get_text())
                        parent = a_tag.parent
                        summary = ""
                        p_tag = parent.find("p") if parent else None
                        if p_tag:
                            summary = self.clean_text(p_tag.get_text())

                        if title and len(title) > 15:
                            items.append({
                                "source_id": self.source_id,
                                "source_name": self.source_name,
                                "category": self.category,
                                "title": title,
                                "summary": summary,
                                "author": "BirGün",
                                "publish_date": self.extract_date_from_card(parent),
                                "link": href,
                                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
        return items[:30]
