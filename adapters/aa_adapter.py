from datetime import datetime
from bs4 import BeautifulSoup
from .base_adapter import BaseAdapter
from config import CATEGORIES

class AAAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(
            source_id="aa",
            source_name="Anadolu Ajansı (AA)",
            category=CATEGORIES["RESMI"]
        )

    def fetch_latest_news(self) -> list:
        # AA provides RSS feeds for general and world categories, fallback to HTML scraping if RSS fails
        rss_urls = [
            "https://www.aa.com.tr/tr/rss/default?cat=guncel",
            "https://www.aa.com.tr/tr/rss/default?cat=dunya"
        ]
        items = []
        for url in rss_urls:
            rss_items = self.parse_rss_feed(url)
            items.extend(rss_items)

        if items:
            return items

        # Fallback scraping: AA Gündem & Dünya
        scrape_urls = [
            "https://www.aa.com.tr/tr/gundem",
            "https://www.aa.com.tr/tr/dunya"
        ]
        for url in scrape_urls:
            html = self.fetch_url(url)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            # Find news card elements
            articles = soup.select("article, .item-card, .list-item, a[href*='/tr/']")
            for art in articles[:20]:
                link_tag = art if art.name == "a" else art.find("a")
                if not link_tag or not link_tag.get("href"):
                    continue
                link = link_tag.get("href")
                if not link.startswith("http"):
                    link = "https://www.aa.com.tr" + link

                # Filter valid article URLs
                if not any(cat in link for cat in ["/gundem/", "/dunya/", "/politika/", "/turkiye/"]):
                    continue

                title = ""
                title_tag = art.find(["h2", "h3", "h4", "span", "div"]) or link_tag
                if title_tag:
                    title = self.clean_text(title_tag.get_text())

                summary = ""
                p_tag = art.find("p")
                if p_tag:
                    summary = self.clean_text(p_tag.get_text())

                if title and len(title) > 10:
                    items.append({
                        "source_id": self.source_id,
                        "source_name": self.source_name,
                        "category": self.category,
                        "title": title,
                        "summary": summary,
                        "author": "Anadolu Ajansı",
                        "publish_date": self.extract_date_from_card(art),
                        "link": link,
                        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

        return items
