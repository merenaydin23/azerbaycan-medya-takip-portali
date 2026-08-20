import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# LLM Configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://llmstat.iletisim.gov.tr/v1").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-397b")

# SerpApi Configuration
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# Web Server Configuration
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "127.0.0.1")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

# Database Configuration
DB_PATH = BASE_DIR / "db" / "media_monitor.db"

# Schedule Configuration
SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "07:30")

# Stage 1: Extended Keywords List (Case-insensitive matching)
KEYWORDS_STAGE_1 = [
    # Ülke ve Şehir İsimleri
    "azerbaycan", "azerbaycan'ın", "azerbaycan'a", "azerbaycan'da", "azerbaycanlı", "azerbaycanlılar",
    "bakü", "bakü'de", "bakü'ye", "bakü'nün",
    "nahçıvan", "nahçivan", "nahcivan", "nahçıvan'a", "nahçıvan'da",
    "karabağ", "dağlık karabağ", "karabağ'da", "karabağ'ın", "karabağ'a",
    "şuşa", "şuşa'da", "şuşa'ya", "şuşa beyannamesi",
    "hankendi", "hocalı", "kelbecer", "laçın", "ağdam", "cebrayıl", "fuzuli", "zengilan", "gubadlı",

    # Kişi ve Lider İsimleri
    "ilham aliyev", "aliyev", "aliyev'in", "aliyev'den", "mehriban aliyeva",
    "haydar aliyev", "heydar aliyev",
    "paşinyan", "ermenistan-azerbaycan", "azerbaycan-ermenistan",

    # Kurum, İttifak ve Projeler
    "türk devletleri teşkilatı", "tdt", "türk konseyi",
    "zangezur", "zengezur", "zangezur koridoru", "zengezur koridoru",
    "tanap", "trans anadolu", "şahdeniz", "şah deniz", "socar", "petkim",
    "güney kafkasya", "kafkasya barış", "3+3 formatı",
    "bakü-tiflis-ceyhan", "btc boru hattı", "bakü-tiflis-kars", "btk demiryolu",
    "bir millet iki devlet", "can azerbaycan",
    # Kısa kodlar — Stage1 kelime sınırlı; tek başlarına zayıf sayılır
    "tap", "tdt", "btc",
]

# Stage 2: Relevant Context Topics (for fallback to LLM classification)
STAGE2_CONTEXT_TOPICS = [
    "dış politika", "dışişleri", "diplomasi", "savunma", "enerji", "doğalgaz", "boru hattı",
    "kafkasya", "orta asya", "türk dünyası", "ermenistan", "gürcistan", "iran", "hazar denizi"
]

# Source Categories
CATEGORIES = {
    "RESMI": "Resmi / Ana Akım",
    "IKTIDAR": "İktidar Yanlısı",
    "MUHALIF": "Muhalif",
    "OTHER": "Diğer / Sınıflandırılmamış"
}

# 14 News Sources Metadata
SOURCES_CONFIG = [
    # 1. Resmi / Ana Akım
    {"id": "aa", "name": "Anadolu Ajansı (AA)", "category": CATEGORIES["RESMI"], "type": "scrape", "domain": "aa.com.tr"},
    {"id": "trt", "name": "TRT Haber", "category": CATEGORIES["RESMI"], "type": "rss/scrape", "domain": "trthaber.com"},
    {"id": "iha", "name": "İhlas Haber Ajansı (İHA)", "category": CATEGORIES["RESMI"], "type": "scrape", "domain": "iha.com.tr"},
    {"id": "milliyet", "name": "Milliyet", "category": CATEGORIES["RESMI"], "type": "rss", "domain": "milliyet.com.tr"},
    {"id": "hurriyet", "name": "Hürriyet", "category": CATEGORIES["RESMI"], "type": "rss/scrape", "domain": "hurriyet.com.tr"},

    # 2. İktidar Yanlısı
    {"id": "ahaber", "name": "A Haber", "category": CATEGORIES["IKTIDAR"], "type": "rss/scrape", "domain": "ahaber.com.tr"},
    {"id": "yenisafak", "name": "Yeni Şafak", "category": CATEGORIES["IKTIDAR"], "type": "rss/scrape", "domain": "yenisafak.com"},
    {"id": "sabah", "name": "Sabah", "category": CATEGORIES["IKTIDAR"], "type": "rss", "domain": "sabah.com.tr"},
    {"id": "turkiyegazetesi", "name": "Türkiye Gazetesi", "category": CATEGORIES["IKTIDAR"], "type": "rss/scrape", "domain": "turkiyegazetesi.com.tr"},

    # 3. Muhalif
    {"id": "sozcu", "name": "Sözcü", "category": CATEGORIES["MUHALIF"], "type": "rss/scrape", "domain": "sozcu.com.tr"},
    {"id": "cumhuriyet", "name": "Cumhuriyet", "category": CATEGORIES["MUHALIF"], "type": "rss", "domain": "cumhuriyet.com.tr"},
    {"id": "halktv", "name": "Halk TV", "category": CATEGORIES["MUHALIF"], "type": "rss/scrape", "domain": "halktv.com.tr"},
    {"id": "t24", "name": "T24", "category": CATEGORIES["MUHALIF"], "type": "rss", "domain": "t24.com.tr"},
    {"id": "birgun", "name": "BirGün", "category": CATEGORIES["MUHALIF"], "type": "rss/scrape", "domain": "birgun.net"}
]
