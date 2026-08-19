# 🇦🇿 Azerbaycan Büyükelçiliği - Türkiye Medya Takip ve Analiz Portalı

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Web%20Framework-green.svg)](https://flask.palletsprojects.com/)
[![Qwen LLM](https://img.shields.io/badge/AI-Qwen--397B-orange.svg)](https://llmstat.iletisim.gov.tr/)
[![SerpApi](https://img.shields.io/badge/SerpApi-Google%20News-red.svg)](https://serpapi.com/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

Azerbaycan Cumhuriyeti Türkiye Büyükelçiliği Basın ve Halkla İlişkiler Şubesi için geliştirilmiş, Türkiye medyasını (ulusal gazeteler, haber ajansları ve dijital medya kanalları) 7/24 canlı tarayan, yapay zeka (Qwen LLM) ile otomatik analiz edip 2 cümlelik özetler çıkaran ve Azerbaycan odaklı haberleri 5 ana stratejik kategoride sınıflandıran kurumsal medya takip ve tutarsızlık analiz portalıdır.

---

## 🌟 Temel Özellikler

### 1. 📰 Çok Katmanlı Geniş Medya Taraması (RSS + Scraping + SerpApi)
* **14 Ulusal Ana Medya Kaynağı:**
  * **Resmi / Ana Akım:** Anadolu Ajansı (AA), TRT Haber, İhlas Haber Ajansı (İHA), Milliyet, Hürriyet
  * **İktidar Yanlısı:** A Haber, Yeni Şafak, Sabah, Türkiye Gazetesi
  * **Muhalif:** Sözcü, Cumhuriyet, Halk TV, T24, BirGün
* **Google News & SerpApi Katmanı:**
  * NTV, Habertürk, CNN Türk, Demirören Haber Ajansı (DHA), Karar, Akşam, Star, Aydınlık, Gazete Duvar, Ekonomim/Dünya Gazetesi vb. 35'in üzerinde gazete ve haber kaynağı otomatik taranır.
  * Mükerrer haber tespiti (Deduplication) ile aynı haberin tekrar eklenmesi engellenir.

### 2. 🇦🇿 "Azerbaycan Gündemi" Sekmesi ve 5 Stratejik Kategori
Tüm haber akışı içinden Azerbaycan'ı doğrudan veya dolaylı ilgilendiren gelişmeler Qwen LLM ile tespit edilerek 5 odaklı kategoride sunulur:
1. **🇦🇿 Ermenistan Hattı:** Ermenistan-Azerbaycan barış süreci, Zengezur koridoru, sınır görüşmeleri, Karabağ, Şuşa, Hankendi ve Paşinyan'ın açıklamaları.
2. **🤝 Diplomasi & Siyaset:** Türkiye-Azerbaycan ikili resmi ilişkileri, Cumhurbaşkanı İlham Aliyev, Dışişleri Bakanlığı, Büyükelçilik faaliyetleri ve üst düzey heyet temasları.
3. **🌐 Türk Devletleri / Bölgesel:** Türk Devletleri Teşkilatı (TDT), Orta Koridor, Nahçıvan ve Hazar bölgesi projeleri.
4. **⚡ Enerji & Ekonomi:** SOCAR, TANAP/TAP boru hatları, doğalgaz/petrol sevkiyatları ve stratejik yatırım anlaşmaları.
5. **🛡️ Güvenlik & Savunma:** Türkiye-Azerbaycan ortak askeri tatbikatları, savunma sanayii, ordu ve sınır güvenliği.

### 3. 🤖 Yapay Zeka Destekli 2 Cümlelik Otomatik Özetleme
* Taranan her haber için **Qwen LLM** tarafından diplomatik ve profesyonel üslupla 2 cümlelik net özetler arka planda paralel olarak (`max_workers=20`) üretilir.
* Kullanıcı karta tıkladığında özet halihazırda hazır olduğu için bekleme yaşanmaz.

### 4. 🏷️ İnteraktif Rozetler (Badges) ve Gerekçe Açıklamaları
* Azerbaycan ile ilgili haber kartlarında **`🇦🇿 Azerbaycan Gündemi`** rozeti belirir.
* Rozetin üzerine gelindiğinde (hover) yapay zekanın belirlediği **kategori, güven skoru (%95+) ve tek cümlelik gerekçe açıklaması** açılır bir tooltip kutusunda gösterilir.

### 5. 🔍 Anlık Başlık ve Anahtar Kelime Arama Motoru
* Üst bardaki arama kutusuna yazıldığı anda başlık, özet, yazar veya kaynak bazında filtreleme yapılır.

### 6. ⚠️ Çelişki ve Tutarsızlık Tespiti (Cross-Comparison)
* Farklı yayın organlarının aynı konuyu aktarırken kullandığı çelişkili rakamlar veya iddialar yapay zeka tarafından tespit edilerek kırmızı uyarı kutusu ile vurgulanır.

### 7. 🌐 İki Dilli Arayüz (TR / AZ)
* Türkçe ve Azerbaycan Türkçesi arasında tek tıkla dil değişimi yapılabilir.

---

## 🏗️ Proje Mimarisi

```text
├── adapters/                  # 14 Bağımsız Kaynak Adaptörü & SerpApi Entegrasyonu
│   ├── base_adapter.py        # Temel HTTP/RSS okuyucu
│   ├── serpapi_adapter.py     # Google News / SerpApi çoklu gazete tarayıcı
│   ├── aa_adapter.py          # Anadolu Ajansı
│   ├── trt_adapter.py         # TRT Haber
│   ├── iha_adapter.py         # İHA (Scraper)
│   ├── sozcu_adapter.py       # Sözcü
│   ├── yenisafak_adapter.py   # Yeni Şafak
│   └── runner.py              # Paralel adaptör yürütücüsü
├── classifier/                # Yapay Zeka & NLP Sınıflandırma Katmanı
│   ├── azerbaijan_relevance_prompt.py # Qwen LLM 5 kategorili sistem promptu
│   ├── stage1.py              # Aşama 1: Yerel anahtar kelime kuralları
│   ├── stage2.py              # Aşama 2: Qwen LLM API & Özetleme Motoru
│   └── cross_comparison.py    # Çapraz Karşılaştırma & Tutarsızlık Tespiti
├── db/                        # SQLite Veritabanı Katmanı
│   └── database.py            # Şema yönetimi, migration ve CRUD işlemleri
├── scheduler/                 # Otomasyon ve Zamanlayıcı
│   └── scheduler.py           # Günlük 07:30 cron, tarih filtreleme ve paralel özetleyici
├── web/                       # Web Sunucusu ve Kullanıcı Arayüzü
│   ├── app.py                 # Flask REST API ve yönlendirmeler
│   ├── templates/             # Jinja2 HTML şablonları (index.html, news_card.html)
│   └── static/                # Vanilla CSS ve reaktif JavaScript varlıkları
├── config.py                  # Kaynak ayarları, kategoriler ve ortam değişkenleri
├── run.py                     # Ana başlatıcı script
├── requirements.txt           # Python bağımlılıkları
├── .env.example               # Örnek ortam değişkenleri şablonu
└── README.md                  # Dokümantasyon
```

---

## 🚀 Kurulum ve Çalıştırma

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/merenaydin23/azerbaycan-medya-takip-portali.git
cd azerbaycan-medya-takip-portali
```

### 2. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 3. Ortam Değişkenlerini (.env) Yapılandırın
`.env.example` dosyasını `.env` olarak kopyalayın:
```bash
cp .env.example .env
```
`.env` dosyasını açarak API anahtarlarınızı girin:
```env
# Qwen LLM API Yapılandırması
LLM_BASE_URL=https://llmstat.iletisim.gov.tr/v1
LLM_API_KEY=buraya_llm_api_anahtarinizi_girin
LLM_MODEL=qwen-397b

# SerpApi (Google News API) Anahtarı
SERPAPI_KEY=buraya_serpapi_anahtarinizi_girin

# Web Sunucu Portu
PORT=5000
HOST=127.0.0.1

# Günlük Otomatik Tarama Saati
SCHEDULE_TIME=07:30
```

### 4. Portalı Başlatın
```bash
python run.py
```

Tarayıcınızda açın:
👉 **`http://127.0.0.1:5000`**

---

## ⚙️ Günlük Çalışma Mantığı ve Arşiv
* **Sıfır Geçmiş Sınırı:** Sistem `16.08.2026` tarihinden itibaren arşiv tutmaktadır.
* **Gece Devri (00:00):** Her gece saat `00:00`'da sistem otomatik olarak yeni güne geçer ve filtreleri günceller.
* **Sabah Taraması (07:30):** Sabah saat `07:30`'da tüm ulusal medya ve Google News taranarak güncel haberler işlenir.
* **Manuel Tarama:** İstenildiği zaman arayüzdeki *"Mənbələri Yenidən Tara"* butonuna basılarak anlık tarama tetiklenebilir.

---

## 🔒 Güvenlik & Gizlilik
* API anahtarları `.env` dosyasında tutulur ve `.gitignore` ile korunur. Depoya kesinlikle gerçek anahtarlar gönderilmez.
* Veritabanı yerel SQLite (`db/media_monitor.db`) üzerinde çalışır, dışarıya veri sızdırılmaz.

---

## 📄 Lisans
Bu proje [MIT Lisansı](LICENSE) kapsamında lisanslanmıştır.
