from datetime import datetime
from bs4 import BeautifulSoup
from .base_adapter import BaseAdapter
from config import CATEGORIES

class SozcuAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(
            source_id="sozcu",
            source_name="Sözcü",
            category=CATEGORIES["MUHALIF"]
        )

    def fetch_latest_news(self) -> list:
        rss_urls = [
            "https://www.sozcu.com.tr/feeds-rss-category-gundem",
            "https://www.sozcu.com.tr/feeds-rss-category-dunya",
            "https://www.sozcu.com.tr/rss/gundem.xml"
        ]
        items = []
        for url in rss_urls:
            rss_items = self.parse_rss_feed(url)
            items.extend(rss_items)

        if items:
            return items

        # Fallback Scraper
        scrape_urls = ["https://www.sozcu.com.tr/gundem", "https://www.sozcu.com.tr/dunya"]
        for url in scrape_urls:
            html = self.fetch_url(url)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select(".news-card, article, a[href*='sozcu.com.tr/']")
            for card in cards[:20]:
                link_tag = card if card.name == "a" else card.find("a")
                if not link_tag or not link_tag.get("href"):
                    continue
                link = link_tag.get("href")
                if not link.startswith("http"):
                    link = "https://www.sozcu.com.tr" + link

                if not any(k in link for k in ["/gundem/", "/dunya/", "-p", "-wp"]):
                    continue

                title_tag = card.find(["h2", "h3", "h4", "span", "strong"]) or link_tag
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
                        "author": "Sözcü",
                        "publish_date": self.extract_date_from_card(card),
                        "link": link,
                        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
        return items
