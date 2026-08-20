import logging
import threading
import time
from datetime import datetime, timedelta
import schedule

from concurrent.futures import ThreadPoolExecutor
from config import SCHEDULE_TIME, SOURCES_CONFIG, CATEGORIES, SERPAPI_KEY
from db import init_db, save_news_item, get_connection, clean_leading_time, update_news_relevance_classification, update_news_summary
from adapters.runner import run_all_adapters
from adapters.serpapi_adapter import SerpApiAdapter
from classifier import (
    check_stage1_relevance,
    check_stage2_llm_relevance,
    generate_az_agenda_brief,
)

logger = logging.getLogger("MediaPipeline")

_is_running_lock = threading.Lock()
_pipeline_status = {
    "is_running": False,
    "last_run": None,
    "last_count": 0,
    "last_error": None
}
_global_existing_links = None
_global_existing_titles = None
_last_general_serp_run = None

def _get_global_dedup_sets():
    global _global_existing_links, _global_existing_titles
    if _global_existing_links is None or _global_existing_titles is None:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT link, title FROM news")
        db_rows = cursor.fetchall()
        conn.close()
        _global_existing_links = {row["link"] for row in db_rows if row["link"]}
        _global_existing_titles = {"".join(ch for ch in row["title"].lower() if ch.isalnum()) for row in db_rows if row["title"]}
    return _global_existing_links, _global_existing_titles

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
                # Run source-specific search concurrently
                sources_with_domain = [src for src in SOURCES_CONFIG if src.get("domain")]
                def _fetch_src(src):
                    return serp_adapter.fetch_source_backup(src["name"], src["domain"], src["category"])

                with ThreadPoolExecutor(max_workers=8) as executor:
                    for items in executor.map(_fetch_src, sources_with_domain):
                        raw_articles.extend(items)
                
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

        # Step 2: Instant RAM deduplication
        existing_links, existing_titles = _get_global_dedup_sets()

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

        # Retain articles from the last 3 days to account for timezone offsets and late night releases
        cutoff_date = datetime.now() - timedelta(days=3)
        relevant_articles_saved = []

        # Prepare deduplicated list for Stage 1 & Stage 2 processing
        items_to_process = []
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

            items_to_process.append(item)

        # Stage 1 keyword matching
        stage2_candidates = []
        for item in items_to_process:
            title = clean_leading_time(item.get("title", ""))
            summary = item.get("summary", "")
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
            elif s1_result.get("is_candidate_for_stage2"):
                stage2_candidates.append(item)
            else:
                item["ilgili_mi"] = 0
                item["ilgi_kategorisi"] = "İlgisiz"
                item["guven_skoru"] = 0.0
                item["gerekce"] = ""
                item["relevance_status"] = "Genel (Filtresiz)"
                item["relevance_aspect"] = "Genel"
                item["llm_relevance_explanation"] = ""

        # Run Stage 2 LLM relevance concurrently for stage2_candidates
        if stage2_candidates:
            logger.info(f"Running Stage 2 LLM evaluation concurrently for {len(stage2_candidates)} candidates...")
            def _eval_stage2(item):
                title = clean_leading_time(item.get("title", ""))
                summary = item.get("summary", "")
                s2 = check_stage2_llm_relevance(
                    title,
                    summary,
                    source_name=item.get("source_name", ""),
                    category=item.get("category", "Genel"),
                )
                if s2.get("is_relevant") or s2.get("ilgili_mi"):
                    item["ilgili_mi"] = 1
                    item["ilgi_kategorisi"] = s2.get("ilgi_kategorisi") or s2.get("aspect") or "Doğrudan"
                    item["guven_skoru"] = float(s2.get("guven_skoru") or 0.7)
                    item["gerekce"] = s2.get("gerekce") or s2.get("explanation") or ""
                    item["relevance_status"] = "Stage 2 (LLM)"
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

            with ThreadPoolExecutor(max_workers=4) as executor:
                list(executor.map(_eval_stage2, stage2_candidates))

        # Save processed items to DB
        for item in items_to_process:
            news_id = save_news_item(item)
            item["id"] = news_id
            relevant_articles_saved.append(item)

        logger.info(f"Step 2 Complete: Saved and categorized {len(relevant_articles_saved)} new articles.")

        az_for_brief = [a for a in relevant_articles_saved if a.get("ilgili_mi") in (1, True, "1")]

        # Step 3: Azerbaycan gündemi içerik özetleri (arka plan)
        def run_background_ai_tasks():
            try:
                summarize_azerbaijan_agenda(az_for_brief)
                backfill_azerbaijan_briefs()
            except Exception as e:
                logger.error(f"Error summarizing Azerbaijan agenda briefs: {e}")

        threading.Thread(target=run_background_ai_tasks, daemon=True, name="BackgroundAITasks").start()

        duration = (datetime.now() - start_time).total_seconds()
        _pipeline_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _pipeline_status["last_count"] = len(relevant_articles_saved)
        logger.info(f"=== Pipeline Completed in {duration:.1f}s. Relevant articles saved: {len(relevant_articles_saved)} (AI tasks running in background) ===")

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


def _needs_az_brief(summary: str) -> bool:
    s = (summary or "").strip()
    if len(s) < 60:
        return True
    if s in ("...", "` and `"):
        return True
    if s.endswith("...") or s.endswith("…"):
        return True
    return False


def summarize_azerbaijan_agenda(articles: list, max_workers: int = 4):
    """Yalnızca Azerbaycan Gündemi haberleri için genel içerik açıklama özeti üretir (paralel)."""
    if not articles:
        return

    logger.info(f"Generating content briefs concurrently (workers={max_workers}) for {len(articles)} Azerbaijan agenda articles...")
    
    def _process_single(item):
        try:
            news_id = item.get("id")
            if not news_id:
                return
            title = item.get("title") or ""
            raw = item.get("summary") or ""
            content = title if _needs_az_brief(raw) else raw
            brief = generate_az_agenda_brief(
                title,
                content,
                item.get("ilgi_kategorisi") or "",
            )
            if brief:
                update_news_summary(news_id, brief)
                item["summary"] = brief
                logger.info(f"AZ brief saved for article ID {news_id}")
        except Exception as e:
            logger.error(f"Error creating AZ brief for {item.get('id')}: {e}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(_process_single, articles))

    logger.info("Azerbaijan agenda briefing complete.")


def backfill_azerbaijan_briefs():
    """Eksik özeti olan mevcut Azerbaycan gündemi haberlerini tamamlar."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, summary, ilgi_kategorisi FROM news
        WHERE ilgili_mi = 1
          AND (
            summary IS NULL OR summary = '' OR summary = '...' OR summary = '` and `'
            OR summary LIKE '%...'
            OR length(summary) < 60
          )
        ORDER BY publish_date DESC
        LIMIT 40
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    if not rows:
        return
    logger.info(f"Backfilling {len(rows)} existing Azerbaijan agenda briefs...")
    summarize_azerbaijan_agenda(rows)


def trigger_manual_refresh():
    """Triggers manual pipeline execution in background thread."""
    thread = threading.Thread(target=run_media_monitoring_pipeline, daemon=True)
    thread.start()
    return thread

def _scheduler_loop():
    logger.info("Background scheduler initiated. Auto-scanning sources every 1 minute.")
    # Run immediate scan on startup, then every 1 minute
    schedule.every(1).minutes.do(run_media_monitoring_pipeline)

    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            logger.error(f"Scheduler exception: {e}")
        time.sleep(5)

def start_background_scheduler():
    """Starts the daily cron scheduler. Keep python run.py running for scans to continue."""
    scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True, name="MediaSchedulerThread")
    scheduler_thread.start()
    # Mevcut AZ gündemi haberleri için özetleri arka planda tamamla
    threading.Thread(target=backfill_azerbaijan_briefs, daemon=True, name="AZBriefBackfill").start()
    return scheduler_thread
