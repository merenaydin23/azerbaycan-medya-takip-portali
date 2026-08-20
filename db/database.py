import sqlite3
import os
from datetime import datetime
from pathlib import Path
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=10000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA cache_size=-128000;")
        conn.execute("PRAGMA mmap_size=268435456;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA threads=4;")
    except:
        pass
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id TEXT,
        source_name TEXT NOT NULL,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT,
        author TEXT,
        publish_date TEXT,
        link TEXT UNIQUE NOT NULL,
        relevance_status TEXT,
        llm_relevance_explanation TEXT,
        relevance_aspect TEXT,
        inconsistency_status INTEGER DEFAULT 0,
        inconsistency_note TEXT,
        group_id TEXT,
        scraped_at TEXT,
        veri_kaynagi TEXT DEFAULT 'Scraping',
        ilgili_mi INTEGER DEFAULT 0,
        ilgi_kategorisi TEXT DEFAULT 'İlgisiz',
        guven_skoru REAL DEFAULT 0.0,
        gerekce TEXT DEFAULT ''
    )
    """)
    # Migration helper for existing DBs
    for col, ctype, cdefault in [
        ("veri_kaynagi", "TEXT", "'Scraping'"),
        ("ilgili_mi", "INTEGER", "0"),
        ("ilgi_kategorisi", "TEXT", "'İlgisiz'"),
        ("guven_skoru", "REAL", "0.0"),
        ("gerekce", "TEXT", "''")
    ]:
        try:
            cursor.execute(f"ALTER TABLE news ADD COLUMN {col} {ctype} DEFAULT {cdefault}")
        except sqlite3.OperationalError:
            pass
        
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_publish_date ON news(publish_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON news(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_relevance ON news(relevance_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ilgili_mi ON news(ilgili_mi)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ilgi_kategorisi ON news(ilgi_kategorisi)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_id ON news(group_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_name ON news(source_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_link ON news(link)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_title ON news(title)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_date_rel ON news(publish_date, relevance_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_date_ilgili ON news(publish_date, ilgili_mi)")
    conn.commit()
    conn.close()

def clean_leading_time(text: str) -> str:
    import re
    import html
    if not text:
        return ""
    # Unescape HTML entities (&nbsp;, &amp;, &quot; etc.)
    text = html.unescape(text)
    # Strip leading timestamps "14:24 ", "14.24 - " etc.
    text = re.sub(r'^\d{1,2}[:.]\d{2}(:\d{2})?\s*[-–—]?\s*', '', text)
    # Strip leading clickbait prefixes "SON DAKİKA:", "CANLI YAYIN:"
    text = re.sub(r'^(SON DAKİKA|CANLI|FLASH|ÖZEL HABER)\s*[:|-]?\s*', '', text, flags=re.IGNORECASE)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def save_news_item(item: dict) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    scraped_at = item.get("scraped_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    publish_date = item.get("publish_date") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    veri_kaynagi = item.get("veri_kaynagi", "Scraping")
    
    title = clean_leading_time(item.get("title", ""))
    summary = clean_leading_time(item.get("summary", ""))

    ilgili_mi = 1 if item.get("ilgili_mi") in (True, 1, "1") else 0
    ilgi_kategorisi = item.get("ilgi_kategorisi") or ("Doğrudan" if ilgili_mi else "İlgisiz")
    guven_skoru = float(item.get("guven_skoru") or (1.0 if ilgili_mi else 0.0))
    gerekce = item.get("gerekce") or item.get("llm_relevance_explanation") or ""

    try:
        cursor.execute("""
        INSERT INTO news (
            source_id, source_name, category, title, summary, author,
            publish_date, link, relevance_status, llm_relevance_explanation,
            relevance_aspect, inconsistency_status, inconsistency_note, group_id, scraped_at, veri_kaynagi,
            ilgili_mi, ilgi_kategorisi, guven_skoru, gerekce
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(link) DO UPDATE SET
            title=excluded.title,
            summary=CASE
                WHEN news.ilgili_mi = 1
                     AND length(ifnull(news.summary, '')) >= 60
                     AND substr(trim(news.summary), -3) != '...'
                THEN news.summary
                ELSE COALESCE(NULLIF(excluded.summary, ''), news.summary)
            END,
            author=COALESCE(excluded.author, news.author),
            publish_date=COALESCE(NULLIF(excluded.publish_date, ''), news.publish_date),
            relevance_status=COALESCE(excluded.relevance_status, news.relevance_status),
            llm_relevance_explanation=COALESCE(excluded.llm_relevance_explanation, news.llm_relevance_explanation),
            relevance_aspect=COALESCE(excluded.relevance_aspect, news.relevance_aspect),
            inconsistency_status=COALESCE(excluded.inconsistency_status, news.inconsistency_status),
            inconsistency_note=COALESCE(excluded.inconsistency_note, news.inconsistency_note),
            group_id=COALESCE(excluded.group_id, news.group_id),
            veri_kaynagi=COALESCE(excluded.veri_kaynagi, news.veri_kaynagi),
            ilgili_mi=COALESCE(excluded.ilgili_mi, news.ilgili_mi),
            ilgi_kategorisi=COALESCE(excluded.ilgi_kategorisi, news.ilgi_kategorisi),
            guven_skoru=COALESCE(excluded.guven_skoru, news.guven_skoru),
            gerekce=COALESCE(excluded.gerekce, news.gerekce)
        """, (
            item.get("source_id", ""),
            item.get("source_name", "Bilinmeyen"),
            item.get("category", "Resmi / Ana Akım"),
            title,
            summary,
            item.get("author", ""),
            publish_date,
            item.get("link", ""),
            item.get("relevance_status", ""),
            item.get("llm_relevance_explanation", ""),
            item.get("relevance_aspect", ""),
            item.get("inconsistency_status", 0),
            item.get("inconsistency_note", ""),
            item.get("group_id", ""),
            scraped_at,
            veri_kaynagi,
            ilgili_mi,
            ilgi_kategorisi,
            guven_skoru,
            gerekce
        ))
        conn.commit()
        last_id = cursor.lastrowid
        if not last_id or last_id == 0:
            cursor.execute("SELECT id FROM news WHERE link = ?", (item.get("link"),))
            row = cursor.fetchone()
            last_id = row["id"] if row else None
        return last_id
    finally:
        conn.close()

def update_news_relevance_classification(news_id: int, ilgili_mi: bool, ilgi_kategorisi: str, guven_skoru: float, gerekce: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE news 
        SET ilgili_mi = ?, 
            ilgi_kategorisi = ?, 
            guven_skoru = ?, 
            gerekce = ?,
            relevance_status = ?,
            relevance_aspect = ?,
            llm_relevance_explanation = ?
        WHERE id = ?
    """, (
        1 if ilgili_mi else 0,
        ilgi_kategorisi,
        guven_skoru,
        gerekce,
        "Stage 2 (LLM)" if ilgili_mi else "Genel (Filtresiz)",
        ilgi_kategorisi if ilgili_mi else "Genel",
        gerekce,
        news_id
    ))
    conn.commit()
    conn.close()

def update_news_summary(news_id: int, summary: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE news SET summary = ? WHERE id = ?", (summary, news_id))
    conn.commit()
    conn.close()

def get_news_by_date(date_str: str, only_relevant: bool = True) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    start_dt = f"{date_str} 00:00:00"
    end_dt = f"{date_str} 23:59:59"
    
    if only_relevant:
        query = """
        SELECT * FROM news 
        WHERE publish_date >= ? AND publish_date <= ?
          AND (relevance_status LIKE 'Stage 1%' OR relevance_status LIKE 'Stage 2%' OR relevance_status = 'İlgili' OR ilgili_mi = 1)
        ORDER BY publish_date DESC, id DESC
        """
    else:
        query = """
        SELECT * FROM news 
        WHERE publish_date >= ? AND publish_date <= ?
        ORDER BY publish_date DESC, id DESC
        """

    cursor.execute(query, (start_dt, end_dt))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_available_dates() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT SUBSTR(publish_date, 1, 10) as dt 
        FROM news 
        WHERE publish_date IS NOT NULL AND publish_date != ''
        ORDER BY dt DESC
        LIMIT 30
    """)
    rows = cursor.fetchall()
    conn.close()
    return [row["dt"] for row in rows if row["dt"]]

def update_llm_analysis(news_id: int, relevance_status: str, explanation: str, aspect: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE news SET
        relevance_status = ?,
        llm_relevance_explanation = ?,
        relevance_aspect = ?
    WHERE id = ?
    """, (relevance_status, explanation, aspect, news_id))
    conn.commit()
    conn.close()

def get_daily_summary(date_str: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    start_dt = f"{date_str} 00:00:00"
    end_dt = f"{date_str} 23:59:59"
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN ilgili_mi = 1 THEN 1 ELSE 0 END) as az_related,
            SUM(CASE WHEN category = 'Resmi / Ana Akım' THEN 1 ELSE 0 END) as resmi,
            SUM(CASE WHEN category = 'İktidar Yanlısı' THEN 1 ELSE 0 END) as iktidar,
            SUM(CASE WHEN category = 'Muhalif' THEN 1 ELSE 0 END) as muhalif
        FROM news
        WHERE publish_date >= ? AND publish_date <= ?
    """, (start_dt, end_dt))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {"total": 0, "az_related": 0, "by_category": {"Resmi / Ana Akım": 0, "İktidar Yanlısı": 0, "Muhalif": 0}}
    return {
        "total": row["total"] or 0,
        "az_related": row["az_related"] or 0,
        "by_category": {
            "Resmi / Ana Akım": row["resmi"] or 0,
            "İktidar Yanlısı": row["iktidar"] or 0,
            "Muhalif": row["muhalif"] or 0
        }
    }
