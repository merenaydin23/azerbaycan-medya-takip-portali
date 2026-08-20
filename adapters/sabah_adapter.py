from datetime import datetime
from bs4 import BeautifulSoup
from .base_adapter import BaseAdapter
from config import CATEGORIES

class SabahAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(
            source_id="sabah",
            source_name="Sabah",
            category=CATEGORIES["IKTIDAR"]
        )

    def fetch_latest_news(self) -> list:
        rss_urls = [
            "https://www.sabah.com.tr/rss/gundem.xml",
            "https://www.sabah.com.tr/rss/dunya.xml",
            "https://www.sabah.com.tr/rss/anasayfa.xml"
        ]
        items = []
        for url in rss_urls:
            rss_items = self.parse_rss_feed(url)
            items.extend(rss_items)

        if items:
            return items

        # Fallback Scraper
        scrape_urls = ["https://www.sabah.com.tr/gundem", "https://www.sabah.com.tr/dunya"]
        for url in scrape_urls:
            html = self.fetch_url(url)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select(".card, .news-item, a[href*='sabah.com.tr/gundem/'], a[href*='sabah.com.tr/dunya/']")
            for card in cards[:20]:
                link_tag = card if card.name == "a" else card.find("a")
                if not link_tag or not link_tag.get("href"):
                    continue
                link = link_tag.get("href")
                if not link.startswith("http"):
                    link = "https://www.sabah.com.tr" + link

                title_tag = card.find(["h2", "h3", "h4", "strong", "span"]) or link_tag
                title = self.clean_text(title_tag.get_text()) if title_tag else ""

                desc_tag = card.find("p") or card.find(".desc")
                summary = self.clean_text(desc_tag.get_text()) if desc_tag else ""

                if title and len(title) > 10 and "-" in link:
                    items.append({
                        "source_id": self.source_id,
                        "source_name": self.source_name,
                        "category": self.category,
                        "title": title,
                        "summary": summary,
                        "author": "Sabah",
                        "publish_date": self.extract_date_from_card(card),
                        "link": link,
                        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
        return items
