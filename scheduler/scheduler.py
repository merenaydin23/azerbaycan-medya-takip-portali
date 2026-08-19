import logging
import threading
import time
from datetime import datetime, timedelta
import schedule

from concurrent.futures import ThreadPoolExecutor
from config import SCHEDULE_TIME, SOURCES_CONFIG, CATEGORIES, SERPAPI_KEY
from db import init_db, save_news_item, get_all_news_for_grouping, get_connection, update_news_summary, clean_leading_time, update_news_relevance_classification
from adapters.runner import run_all_adapters
from adapters.serpapi_adapter import SerpApiAdapter
from classifier import (
    check_stage1_relevance,
    check_stage2_llm_relevance,
    run_cross_comparison_for_articles,
    generate_qwen_summary
)

logger = logging.getLogger("MediaPipeline")

_is_running_lock = threading.Lock()
_pipeline_status = {
    "is_running": False,
    "last_run": None,
    "last_count": 0,
    "last_error": None
}
_last_general_serp_run = None

def get_pipeline_status() -> dict:
    return _pipeline_status

def run_media_monitoring_pipeline() -> dict:
    """
    Full pipeline execution:
    1. Fetch news from 14 sources
    2. Stage 1 Keyword Classification
    3. Stage 2 LLM Relevance Classification (for candidate articles)
    4. Save to DB
    5. Run Cross-Comparison & Inconsistency Detection with LLM
    """
    global _pipeline_status

    if not _is_running_lock.acquire(blocking=False):
        logger.warning("Pipeline is already running! Skipping duplicate trigger.")
        return {"status": "already_running"}

    try:
        _pipeline_status["is_running"] = True
        _pipeline_status["last_error"] = None
        start_time = datetime.now()
        logger.info(f"=== Starting Media Monitoring Pipeline at {start_time} ===")

        # Ensure DB is initialized
        # Step 1: Scrape all 14 sources
        raw_articles = run_all_adapters()
        
        # Tag native sources with 'RSS' / 'Scraping'
        for item in raw_articles:
            matched_config = next((c for c in SOURCES_CONFIG if c["name"] == item.get("source_name")), None)
            if matched_config:
                item["veri_kaynagi"] = "RSS" if "rss" in matched_config.get("type", "") else "Scraping"
            else:
                item["veri_kaynagi"] = "Scraping"
                
        # Step 1.5: Run SerpApi backup search if key is set
        if SERPAPI_KEY:
            try:
                serp_adapter = SerpApiAdapter()
                # Run source-specific search
                for src in SOURCES_CONFIG:
                    if src.get("domain"):
                        serp_items = serp_adapter.fetch_source_backup(src["name"], src["domain"], src["category"])
                        raw_articles.extend(serp_items)
                
                # Run general search once per day
                global _last_general_serp_run
                today_date = datetime.now().date()
                if _last_general_serp_run != today_date:
                    general_items = serp_adapter.fetch_general_news()
                    raw_articles.extend(general_items)
                    _last_general_serp_run = today_date
            except Exception as serp_err:
                logger.error(f"SerpApi backup crawling failed: {serp_err}")

        logger.info(f"Step 1 Complete: Fetched {len(raw_articles)} total articles (including SerpApi).")

        # Step 2: Filter by date range (today 00:00 and last 3 days) and save without duplicates
        # Load existing articles to memory for fast deduplication
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT link, title FROM news WHERE publish_date >= date('now', '-3 days')")
        db_rows = cursor.fetchall()
        conn.close()
        
        existing_links = {row["link"] for row in db_rows}
        existing_titles = {"".join(ch for ch in row["title"].lower() if ch.isalnum()) for row in db_rows if row["title"]}

        import email.utils
        def parse_publish_date(date_str: str) -> datetime:
            if not date_str:
                return datetime.now()
            try:
                parsed_tuple = email.utils.parsedate_tz(date_str)
                if parsed_tuple:
                    return datetime.fromtimestamp(email.utils.mktime_tz(parsed_tuple))
            except:
                pass
            try:
                return datetime.fromisoformat(date_str.split(".")[0].replace("Z", ""))
            except:
                pass
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M"):
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    pass
            return datetime.now()

        # Filter strictly for today (starting at 00:00:00)
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = today_start
        relevant_articles_saved = []

        for item in raw_articles:
            pub_date_str = item.get("publish_date", "")
            pub_dt = parse_publish_date(pub_date_str)
            
            # Skip if older than today 00:00:00
            if pub_dt.replace(tzinfo=None) < cutoff_date.replace(tzinfo=None):
                continue

            # Standardize date format in DB
            item["publish_date"] = pub_dt.strftime("%Y-%m-%d %H:%M:%S")

            # Deduplication checks
            link = item.get("link", "")
            title = clean_leading_time(item.get("title", ""))
            clean_title_str = "".join(ch for ch in title.lower() if ch.isalnum())
            
            if link in existing_links or clean_title_str in existing_titles:
                continue
                
            existing_links.add(link)
            if clean_title_str:
                existing_titles.add(clean_title_str)

            summary = item.get("summary", "")

            # Run Stage 1 keyword filter for candidate screening
            s1_result = check_stage1_relevance(title, summary)
            is_candidate = s1_result.get("is_relevant", False)
            
            if is_candidate:
                item["ilgili_mi"] = 1
                item["ilgi_kategorisi"] = s1_result.get("aspect") or "Doğrudan"
                item["guven_skoru"] = 0.95
                item["gerekce"] = s1_result.get("explanation") or "Anahtar kelime eşleşmesi."
                item["relevance_status"] = s1_result["stage"]
                item["relevance_aspect"] = item["ilgi_kategorisi"]
                item["llm_relevance_explanation"] = item["gerekce"]
            else:
                item["ilgili_mi"] = 0
                item["ilgi_kategorisi"] = "İlgisiz"
                item["guven_skoru"] = 0.0
                item["gerekce"] = ""
                item["relevance_status"] = "Genel (Filtresiz)"
                item["relevance_aspect"] = "Genel"
                item["llm_relevance_explanation"] = ""

            news_id = save_news_item(item)
            item["id"] = news_id
            relevant_articles_saved.append(item)

        logger.info(f"Step 2 Complete: Saved and categorized {len(relevant_articles_saved)} new articles.")

        # Step 3: Cross Comparison & Inconsistency Detection
        today_str = datetime.now().strftime("%Y-%m-%d")
        all_today_relevant = get_all_news_for_grouping(today_str)
        if all_today_relevant:
            run_cross_comparison_for_articles(all_today_relevant)
        logger.info("Step 3 Complete: Cross comparison analysis finished.")

        duration = (datetime.now() - start_time).total_seconds()
        _pipeline_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _pipeline_status["last_count"] = len(relevant_articles_saved)
        logger.info(f"=== Pipeline Completed in {duration:.1f}s. Relevant articles saved: {len(relevant_articles_saved)} ===")

        return {
            "status": "success",
            "relevant_count": len(relevant_articles_saved),
            "total_fetched": len(raw_articles),
            "duration_seconds": duration
        }

    except Exception as e:
        logger.error(f"Error during pipeline execution: {e}", exc_info=True)
        _pipeline_status["last_error"] = str(e)
        return {"status": "error", "message": str(e)}
    finally:
        _pipeline_status["is_running"] = False
        _is_running_lock.release()

def summarize_missing_history():
    """Finds all news items from 2026-08-16 onwards that lack a valid Qwen summary,
    and summarizes them in the background to pre-populate the database.
    """
    logger.info("Background job started: Summarizing existing articles in database...")
    
    conn = get_connection()
    cursor = conn.cursor()
    # Find articles that need a summary (where summary is empty, None, '...', or similar placeholders)
    cursor.execute("""
        SELECT id, title, summary FROM news 
        WHERE publish_date >= '2026-08-16' 
          AND (summary IS NULL OR summary = '' OR summary = '...' OR summary = '` and `')
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if not rows:
        logger.info("No historical articles need summarization.")
        return

    logger.info(f"Found {len(rows)} historical articles needing Qwen summaries. Processing in parallel...")

    def process_row(row):
        try:
            title = row["title"]
            summary = row["summary"]
            content_to_summarize = summary
            if not summary or len(summary.strip()) < 10 or summary == "..." or summary == "` and `":
                content_to_summarize = title
                
            q_sum = generate_qwen_summary(title, content_to_summarize)
            if q_sum:
                update_news_summary(row["id"], q_sum)
        except Exception as e:
            logger.error(f"Error summarizing historical article {row['id']}: {e}")

    with ThreadPoolExecutor(max_workers=20) as executor:
        list(executor.map(process_row, rows))

    logger.info("Background historical summarization complete.")

def trigger_manual_refresh():
    """Triggers manual pipeline execution in background thread."""
    thread = threading.Thread(target=run_media_monitoring_pipeline, daemon=True)
    thread.start()
    return thread

def _scheduler_loop():
    logger.info(f"Background scheduler initiated. Daily scheduled time: {SCHEDULE_TIME}")
    schedule.every().day.at(SCHEDULE_TIME).do(run_media_monitoring_pipeline)

    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            logger.error(f"Scheduler exception: {e}")
        time.sleep(30)

def start_background_scheduler():
    """Starts the daily 07:30 cron scheduler and historical summarizer on daemon threads."""
    scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True, name="MediaSchedulerThread")
    scheduler_thread.start()
    
    # Run the historical summarizer in a separate background thread
    history_thread = threading.Thread(target=summarize_missing_history, daemon=True, name="HistoricalSummarizerThread")
    history_thread.start()
    
    return scheduler_thread
