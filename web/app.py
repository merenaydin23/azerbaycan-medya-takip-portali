import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from config import BASE_DIR, PORT, HOST, DEBUG, CATEGORIES, LLM_MODEL, SCHEDULE_TIME, SOURCES_CONFIG
from db import init_db, get_news_by_date, get_available_dates, get_daily_summary, update_news_summary, get_connection
from scheduler import start_background_scheduler, trigger_manual_refresh, get_pipeline_status
from classifier import generate_qwen_summary

TRANSLATIONS = {
    "tr": {
        "title": "Azerbaycan Büyükelçiliği",
        "subtitle": "Türkiye Basını Canlı Medya Takip ve Tutarsızlık Analiz Portalı",
        "all_news": "Tüm Haberler (Filtresiz)",
        "az_oriented": "🇦🇿 Azerbaycan Odaklı",
        "date_label": "Tarih:",
        "refresh_btn": "Kaynakları Yeniden Tara",
        "refresh_btn_scanning": "Taranıyor...",
        "scanning_banner": "Medya Tarama ve Yapay Zeka Analizi Devam Ediyor...",
        "scanning_banner_sub": "Tüm medya kaynaklarından ve Google News üzerinden veriler toplanıyor ve Qwen LLM ile analiz ediliyor. Tamamlandığında sayfa otomatik güncellenecektir.",
        "displayed_total": "Görüntülenen Toplam Haber",
        "az_related_total": "Azerbaycan İlgili Haber",
        "resmi": "Resmi / Ana Akım",
        "iktidar": "İktidar Yanlısı",
        "muhalif": "Muhalif Basın",
        "inconsistencies": "Tutarsızlık / Fark İşareti",
        "disclaimer_title": "Filtre Durumu:",
        "disclaimer_all": "Şu anda tüm haberler filtresiz olarak listelenmektedir. Yalnızca Azerbaycan ile ilgili haberleri görmek için üstteki '🇦🇿 Azerbaycan Odaklı' butonuna basabilirsiniz.",
        "disclaimer_az": "Şu anda sadece Azerbaycan ile doğrudan veya dolaylı ilgili haberler gösterilmektedir.",
        "empty_state": "Bu kategoride haber bulunamadı.",
        "footer_embassy": "Azerbaycan Cumhuriyeti Türkiye Büyükelçiliği Basın & İletişim Birimi",
        "footer_schedule": "Otomatik Tarama:",
        "footer_ai": "Yapay Zeka:",
        "footer_sources": "Geniş Kapsamlı Canlı Medya Takibi",
        "inconsistency_found": "TUTARSIZLIK / ÇELİŞKİ TESPİT EDİLDİ",
        "original_link": "Orijinali Gör",
        "keyword_badge": "🔍 Anahtar Kelime",
        "llm_badge": "🤖 Yapay Zeka (Qwen)",
        "genel_badge": "📰 Genel Akış",
        "aspect_label": "📌 İlgi Açısı:",
        "all_sources": "Hepsi",
        "sources_title": "Haber Kaynakları",
        "all_sources_sidebar": "Tüm Kaynaklar",
        "generate_ai_summary": "✨ Yapay Zeka Özeti Oluştur",
        "generating_ai_summary": "⏳ Özetleniyor...",
        "other_sources": "Diğer Kaynaklar",
        "search_placeholder": "Haber başlığı veya anahtar kelime ara...",
        "search_btn": "Ara",
        "tab_all_media": "📰 Tüm Medya Akışı",
        "tab_az_agenda": "🇦🇿 Azerbaycan Gündemi",
        "az_filter_all": "Tümü",
        "az_filter_ermenistan": "Ermenistan Hattı",
        "az_filter_diplomasi": "Diplomasi & Siyaset",
        "az_filter_turk_devletleri": "Türk Devletleri / Bölgesel",
        "az_filter_enerji": "Enerji / Ekonomi",
        "az_filter_guvenlik": "Güvenlik / Savunma",
        "az_empty_state": "Bu kategoride Azerbaycan ile ilgili haber bulunamadı."
    },
    "az": {
        "title": "Azərbaycan Səfirliyi",
        "subtitle": "Türkiyə Mətbuatı Canlı Media Təqib və Ziddiyyət Təhlili Portalı",
        "all_news": "Bütün Xəbərlər (Filtrsiz)",
        "az_oriented": "🇦🇿 Azərbaycan Yönümlü",
        "date_label": "Tarix:",
        "refresh_btn": "Mənbələri Yenidən Tara",
        "refresh_btn_scanning": "Tarama gedir...",
        "scanning_banner": "Media Tarama və Süni İntellekt Təhlili Davam Edir...",
        "scanning_banner_sub": "Bütün media mənbələrindən və Google News üzərindən məlumatlar toplanır və Qwen LLM ilə təhlil edilir. Tamamlandıqda səhifə avtomatik yenilənəcəkdir.",
        "displayed_total": "Göstərilən Ümumi Xəbər",
        "az_related_total": "Azərbaycanla Bağlı Xəbər",
        "resmi": "Rəsmi / Əsas Medya",
        "iktidar": "İqtidaryönlü Medya",
        "muhalif": "Müxalif Mətbuat",
        "inconsistencies": "Ziddiyyət / Fərq İşarəsi",
        "disclaimer_title": "Filtr Statusu:",
        "disclaimer_all": "Hazırda bütün xəbərlər filtrsiz olaraq siyahıya alınır. Yalnız Azərbaycanla bağlı xəbərləri görmək üçün yuxarıdakı '🇦🇿 Azərbaycan Yönümlü' düyməsinə basa bilərsiniz.",
        "disclaimer_az": "Hazırda yalnız Azərbaycanla birbaşa və ya dolayısı ilə bağlı xəbərlər göstərilir.",
        "empty_state": "Bu kateqoriyada xəbər tapılmadı.",
        "footer_embassy": "Azərbaycan Respublikasının Türkiyə Səfirliyinin Mətbuat və İctimaiyyətlə Əlaqələr Şöbəsi",
        "footer_schedule": "Avtomatik Tarama:",
        "footer_ai": "Süni İntellekt:",
        "footer_sources": "Geniş Əhatəli Canlı Media Təqibi",
        "inconsistency_found": "ZİDDİYYƏT / FƏRQ TƏSPİT EDİLDİ",
        "original_link": "Orijinalı Gör",
        "keyword_badge": "🔍 Açar Söz",
        "llm_badge": "🤖 Süni İntellekt (Qwen)",
        "genel_badge": "📰 Ümumi Axın",
        "aspect_label": "📌 Mövzu:",
        "all_sources": "Hamısı",
        "sources_title": "Xəbər Mənbələri",
        "all_sources_sidebar": "Bütün Mənbələr",
        "generate_ai_summary": "✨ Süni İntellekt Xülasəsi Yarat",
        "generating_ai_summary": "⏳ Xülasə edilir...",
        "other_sources": "Digər Mənbələr",
        "search_placeholder": "Xəbər başlığı və ya açar söz axtar...",
        "search_btn": "Axtar",
        "tab_all_media": "📰 Bütün Media Axını",
        "tab_az_agenda": "🇦🇿 Azərbaycan Gündəmi",
        "az_filter_all": "Hamısı",
        "az_filter_ermenistan": "Ermənistan Xətti",
        "az_filter_diplomasi": "Diplomatiya və Siyasət",
        "az_filter_turk_devletleri": "Türk Dövlətləri / Regional",
        "az_filter_enerji": "Enerji / İqtisadiyyat",
        "az_filter_guvenlik": "Təhlükəsizlik / Müdafiə",
        "az_empty_state": "Bu kateqoriyada Azərbaycanla bağlı xəbər tapılmadı."
    }
}

def create_app():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "web" / "templates"),
        static_folder=str(BASE_DIR / "web" / "static")
    )

    # Initialize database
    init_db()

    @app.route("/")
    def index():
        selected_date = request.args.get("date")
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        if not selected_date:
            selected_date = today_str

        # Show all news by default as requested (or allow filter via ?filter=azerbaijan)
        filter_mode = request.args.get("filter", "all")  # 'all' or 'azerbaijan'
        only_relevant = (filter_mode == "azerbaijan")

        # Get language selection (TR or AZ)
        lang = request.args.get("lang", "tr").lower()
        if lang not in TRANSLATIONS:
            lang = "tr"
        
        t = TRANSLATIONS[lang]

        # Get news for selected date
        all_news = get_news_by_date(selected_date, only_relevant=only_relevant)
        
        # Calculate counts per source and other sources
        source_counts = {}
        for s in SOURCES_CONFIG:
            source_counts[s["name"]] = 0
            
        other_count = 0
        az_gundemi_count = 0
        for n in all_news:
            if n.get("category") == CATEGORIES["OTHER"]:
                other_count += 1
            else:
                source_counts[n["source_name"]] = source_counts.get(n["source_name"], 0) + 1
            
            if n.get("ilgili_mi") in (1, True, "1"):
                az_gundemi_count += 1

        summary = get_daily_summary(selected_date)
        available_dates = get_available_dates()
        if today_str not in available_dates:
            available_dates.insert(0, today_str)

        pipeline_status = get_pipeline_status()

        return render_template(
            "index.html",
            selected_date=selected_date,
            today_str=today_str,
            available_dates=available_dates,
            filter_mode=filter_mode,
            news_items=all_news,
            sources=SOURCES_CONFIG,
            source_counts=source_counts,
            other_count=other_count,
            az_gundemi_count=az_gundemi_count,
            total_displayed=len(all_news),
            summary=summary,
            pipeline_status=pipeline_status,
            llm_model=LLM_MODEL,
            schedule_time=SCHEDULE_TIME,
            lang=lang,
            t=t
        )

    @app.route("/api/refresh", methods=["POST"])
    def refresh_news():
        status = get_pipeline_status()
        if status.get("is_running"):
            return jsonify({"status": "already_running", "message": "Tarama işlemi zaten devam ediyor."})
        
        trigger_manual_refresh()
        return jsonify({"status": "started", "message": "14 haber kaynağından tarama başlatıldı."})

    @app.route("/api/status", methods=["GET"])
    def pipeline_status_api():
        return jsonify(get_pipeline_status())

    @app.route("/api/summary", methods=["GET"])
    def daily_summary_api():
        date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
        return jsonify(get_daily_summary(date_str))

    @app.route("/api/summarize-article/<int:item_id>", methods=["POST"])
    def summarize_article(item_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, summary, link FROM news WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({"status": "error", "message": "Haber bulunamadı."}), 404
            
        title = row["title"]
        summary = row["summary"]
        
        # Fallback to title if summary is placeholder/empty
        content_to_summarize = summary
        if not summary or len(summary.strip()) < 10 or summary == "..." or summary == "` and `":
            content_to_summarize = title
        
        # Call Qwen
        qwen_summary = generate_qwen_summary(title, content_to_summarize)
        
        if qwen_summary:
            update_news_summary(item_id, qwen_summary)
            return jsonify({"status": "success", "summary": qwen_summary})
        else:
            return jsonify({"status": "error", "message": "Yapay zeka özeti oluşturulamadı."})

    return app

if __name__ == "__main__":
    app = create_app()
    start_background_scheduler()
    app.run(host=HOST, port=PORT, debug=DEBUG)
