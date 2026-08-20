import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

class BaseAdapter:
    def __init__(self, source_id: str, source_name: str, category: str):
        self.source_id = source_id
        self.source_name = source_name
        self.category = category
        self.logger = logging.getLogger(f"Adapter.{source_id}")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/"
        }

    def fetch_url(self, url: str, timeout: int = 6) -> str:
        try:
            response = requests.get(url, headers=self.headers, timeout=timeout)
            if response.status_code == 200:
                response.encoding = response.apparent_encoding or "utf-8"
                return response.text
            else:
                self.logger.warning(f"Failed to fetch {url}, status code: {response.status_code}")
                return ""
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return ""

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        # Remove HTML tags if present
        text = re.sub(r'<[^>]+>', ' ', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def extract_date_from_card(self, card) -> str:
        """Extracts publication date/time from HTML card elements or fallback to current date."""
        if not card:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Check time/meta tags
        time_tag = card.find("time") or card.find("span", class_=re.compile(r"date|time|saat|tarih", re.I))
        if time_tag:
            dt_attr = time_tag.get("datetime") or time_tag.get("content") or time_tag.get_text()
            if dt_attr:
                dt_str = self.clean_text(dt_attr)
                m_time = re.search(r"\b([0-2]?\d[:.][0-5]\d)\b", dt_str)
                if m_time:
                    time_part = m_time.group(1).replace(".", ":")
                    if len(time_part.split(":")[0]) == 1:
                        time_part = "0" + time_part
                    today = datetime.now().strftime("%Y-%m-%d")
                    return f"{today} {time_part}:00"

        # Search anywhere in card text for HH:MM time pattern
        card_text = card.get_text()
        m_time = re.search(r"\b([0-2]?\d[:.][0-5]\d)\b", card_text)
        if m_time:
            time_part = m_time.group(1).replace(".", ":")
            if len(time_part.split(":")[0]) == 1:
                time_part = "0" + time_part
            today = datetime.now().strftime("%Y-%m-%d")
            return f"{today} {time_part}:00"

    def canonicalize_url(self, url: str) -> str:
        if not url:
            return ""
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            clean_query = []
            if parsed.query:
                for pair in parsed.query.split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        if not any(t in k.lower() for t in ("utm", "amp", "ref", "rss", "fbclid", "gclid")):
                            clean_query.append(pair)
            new_query = "&".join(clean_query)
            path = parsed.path.rstrip("/")
            clean_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc.lower(), path, parsed.params, new_query, ""))
            return clean_url
        except:
            return url

    def is_junk_title(self, title: str) -> bool:
        if not title:
            return True
        title_clean = self.clean_text(title)
        title_clean = re.sub(r'^\d{1,2}\s+[A-ZÇĞİÖŞÜa-zçğıöşü]+\s+\d{4}\s*\d{0,2}[:.]?\d{0,2}\s*[-–—]?\s*', '', title_clean)
        title_clean = re.sub(r'^\d{1,2}[:.]\d{2}(:\d{2})?\s*[-–—]?\s*', '', title_clean).strip()
        if len(title_clean) < 12:
            return True
        title_lower = title_clean.lower()
        spam_kw = [
            "sayısal loto", "süper loto", "on numara", "şans topu", "milli piyango",
            "çekiliş sonuçları", "bilet sorgulama", "günlük burç", "burç yorumları",
            "nöbetçi eczane", "çerez politikası", "gizlilik politikası", "künye",
            "kurumsal satış", "bize ulaşın", "site haritası"
        ]
        if any(sk in title_lower for sk in spam_kw):
            return True
        if re.match(r'^(\d+\s+[A-Za-zÇĞİÖŞÜçğıöşü]+\s+\d{4}|\d+[\s.-]+\d+[\s.-]+\d+|\d{1,2}[:.]\d{2})+$', title.strip()):
            return True
        return False

    def extract_explicit_date_from_title(self, title: str) -> str:
        if not title:
            return None
        import html
        t_clean = html.unescape(title)
        month_map = {
            "ocak": "01", "şubat": "02", "mart": "03", "nisan": "04", "mayıs": "05", "haziran": "06",
            "temmuz": "07", "ağustos": "08", "agustos": "08", "eylül": "09", "ekim": "10", "kasım": "11", "aralık": "12"
        }
        m = re.search(r'\b([0-3]?\d)\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Agustos|Eylül|Ekim|Kasım|Aralık)\s*(\d{4})?\b', t_clean, re.I)
        if m:
            day = int(m.group(1))
            month_str = m.group(2).lower()
            year = m.group(3) or datetime.now().strftime("%Y")
            month = month_map.get(month_str, "08")
            if 1 <= day <= 31:
                dt_str = f"{year}-{month}-{day:02d} 12:00:00"
                try:
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                    if dt <= datetime.now():
                        return dt_str
                except:
                    pass
        return None

    def parse_rss_feed(self, rss_url: str, max_items: int = 100) -> list:
        items = []
        xml_content = self.fetch_url(rss_url)
        if not xml_content:
            return items

        try:
            soup = BeautifulSoup(xml_content, "xml")
            entries = soup.find_all("item") or soup.find_all("entry")
            
            for entry in entries[:max_items]:
                title = ""
                link = ""
                summary = ""
                pub_date = ""
                author = ""

                # Title
                title_tag = entry.find("title")
                if title_tag:
                    title = self.clean_text(title_tag.get_text())
                    if " - " in title and len(title.rsplit(" - ", 1)[0].strip()) > 10:
                        title = title.rsplit(" - ", 1)[0].strip()

                # Link
                link_tag = entry.find("link")
                if link_tag:
                    link = link_tag.get_text() if link_tag.get_text() else link_tag.get("href", "")
                    link = link.strip()

                # Summary / Description
                desc_tag = entry.find("description") or entry.find("summary") or entry.find("content:encoded")
                if desc_tag:
                    summary = self.clean_text(desc_tag.get_text())

                # Author
                author_tag = entry.find("author") or entry.find("dc:creator")
                if author_tag:
                    author = self.clean_text(author_tag.get_text())

                # Pub Date (Parses RFC 822, ISO 8601, Atom, and custom formats)
                import email.utils
                pub_date_tag = entry.find("pubDate") or entry.find("published") or entry.find("dc:date") or entry.find("updated")
                if pub_date_tag:
                    raw_pub_date = self.clean_text(pub_date_tag.get_text())
                    dt_obj = None
                    try:
                        parsed_tuple = email.utils.parsedate_tz(raw_pub_date)
                        if parsed_tuple:
                            dt_obj = datetime.fromtimestamp(email.utils.mktime_tz(parsed_tuple))
                    except:
                        pass

                    if not dt_obj:
                        try:
                            clean_iso = raw_pub_date.split(".")[0].replace("Z", "")
                            dt_obj = datetime.fromisoformat(clean_iso)
                        except:
                            pass

                    if not dt_obj:
                        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"):
                            try:
                                dt_obj = datetime.strptime(raw_pub_date, fmt)
                                break
                            except:
                                pass

                explicit_date = self.extract_explicit_date_from_title(title)
                if explicit_date:
                    pub_date = explicit_date
                elif dt_obj:
                    pub_date = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    pub_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if title and link and not self.is_junk_title(title):
                    items.append({
                        "source_id": self.source_id,
                        "source_name": self.source_name,
                        "category": self.category,
                        "title": title,
                        "summary": summary,
                        "author": author,
                        "publish_date": pub_date,
                        "link": self.canonicalize_url(link),
                        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
        except Exception as e:
            self.logger.error(f"Error parsing RSS feed from {rss_url}: {e}")

        return items

    def fetch_latest_news(self) -> list:
        """Subclasses should implement this method."""
        raise NotImplementedError("Each adapter must implement fetch_latest_news()")
