from datetime import datetime
from bs4 import BeautifulSoup
from .base_adapter import BaseAdapter
from config import CATEGORIES

class IHAAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(
            source_id="iha",
            source_name="İhlas Haber Ajansı (İHA)",
            category=CATEGORIES["RESMI"]
        )

    def fetch_latest_news(self) -> list:
        rss_urls = [
            "https://news.google.com/rss/search?q=site:iha.com.tr&hl=tr&gl=TR&ceid=TR:tr"
        ]
        items = []
        for url in rss_urls:
            rss_items = self.parse_rss_feed(url, max_items=40)
            items.extend(rss_items)

        if items:
            return items[:50]

        for url in urls:
            html = self.fetch_url(url)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            
            for a_tag in soup.find_all("a", href=True):
                link = a_tag.get("href", "").strip()
                if not link or link in seen_links:
                    continue

                if link.startswith("/"):
                    link = "https://www.iha.com.tr" + link

                # Filter IHA article patterns
                if any(k in link for k in ["/haber-", "-haberleri/", "-haberi-", "/gundem/", "/dunya/", "/politika/"]) and not link.endswith(("/gundem", "/dunya", "/politika", ".jpg", ".png")):
                    seen_links.add(link)
                    title = self.clean_text(a_tag.get_text())
                    
                    # Try to get parent summary if title is too short or inside a card
                    summary = ""
                    parent = a_tag.parent
                    if parent:
                        p_tag = parent.find("p") or parent.find_next_sibling("p")
                        if p_tag:
                            summary = self.clean_text(p_tag.get_text())

                    if title and len(title) > 15 and not title.lower().startswith("tüm haberler"):
                        items.append({
                            "source_id": self.source_id,
                            "source_name": self.source_name,
                            "category": self.category,
                            "title": title,
                            "summary": summary,
                            "author": "İHA",
                            "publish_date": self.extract_date_from_card(parent or a_tag),
                            "link": link,
                            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })

        return items[:40]
