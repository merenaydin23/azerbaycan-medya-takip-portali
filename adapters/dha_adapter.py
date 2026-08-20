from datetime import datetime
from bs4 import BeautifulSoup
from .base_adapter import BaseAdapter
from config import CATEGORIES

class DHAAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(
            source_id="dha",
            source_name="DHA | Demirören Haber Ajansı",
            category=CATEGORIES["RESMI"]
        )

    def fetch_latest_news(self) -> list:
        rss_urls = [
            "https://news.google.com/rss/search?q=site:dha.com.tr&hl=tr&gl=TR&ceid=TR:tr",
            "https://www.dha.com.tr/rss/gundem.xml",
            "https://www.dha.com.tr/rss/dunya.xml"
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

        # Fallback Scraper
        scrape_urls = ["https://www.dha.com.tr/gundem", "https://www.dha.com.tr/dunya"]
        for url in scrape_urls:
            html = self.fetch_url(url)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select(".card, article, a[href*='dha.com.tr/']")
            for card in cards[:25]:
                link_tag = card if card.name == "a" else card.find("a")
                if not link_tag or not link_tag.get("href"):
                    continue
                link = link_tag.get("href")
                if not link.startswith("http"):
                    link = "https://www.dha.com.tr" + link

                title_tag = card.find(["h2", "h3", "h4", "strong"]) or link_tag
                title = self.clean_text(title_tag.get_text()) if title_tag else ""

                desc_tag = card.find("p")
                summary = self.clean_text(desc_tag.get_text()) if desc_tag else ""

                if title and len(title) > 10:
                    items.append({
                        "source_id": self.source_id,
                        "source_name": self.source_name,
                        "category": self.category,
                        "title": title,
                        "summary": summary,
                        "author": "DHA",
                        "publish_date": self.extract_date_from_card(card),
                        "link": link,
                        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
        return items[:60]
