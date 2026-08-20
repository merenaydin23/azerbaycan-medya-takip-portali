Aşağıdaki projeyi baştan sona kur. Local ortamda (benim makinemde) çalışacak bir Python projesi olsun.

## PROJE
Azerbaycan Büyükelçiliği için Türkiye medya takip sistemi. Sistem her gün Türkiye'deki haber kaynaklarını tarayıp Azerbaycan ile ilgili haberleri toplayacak, kaynakları karşılaştırıp tutarsızlıkları işaretleyecek ve büyükelçinin göreceği sade bir web arayüzünde gösterecek. Nihai kullanıcı (büyükelçi) teknik bilgiye sahip değil, arayüz çok sade ve az tıklamalı olmalı.

## KAYNAKLAR (3 kategori, toplam 14 kaynak)
Her kaynak için önce RSS beslemesi dene, yoksa basit bir scraper (requests + BeautifulSoup) yaz. Her kaynak ayrı bir "adapter" modülü olsun (bir kaynak bozulursa diğerleri etkilenmesin).

**Resmi / Ana Akım:** AA, TRT Haber, İHA, Milliyet, Hürriyet
**İktidar Yanlısı:** A Haber, Yeni Şafak, Sabah, Türkiye Gazetesi
**Muhalif:** Sözcü, Cumhuriyet, Halk TV, T24, BirGün

Şu an hiçbir resmi/ücretli API kullanma (AA API dahil değil) — sadece RSS ve web taraması.

## HABER SINIFLANDIRMA (2 aşamalı — çok önemli)
**Aşama 1 (local, ücretsiz, hızlı):** Genişletilmiş bir anahtar kelime/varlık listesiyle (Azerbaycan, Bakü, Aliyev, Nahçıvan, Karabağ, Şuşa, Hankendi, Zangezur koridoru, Ermenistan-Azerbaycan, Türk Devletleri Teşkilatı, TANAP, Güney Kafkasya, Dağlık Karabağ vb.) her taranan haberin başlık ve metnini tara. Bu liste ayrı bir config dosyasında (kolayca genişletilebilir) tutulsun.

**Aşama 2 (Qwen API ile):** Aşama 1'de doğrudan eşleşme çıkmayan ama dış politika/Kafkasya/enerji/savunma gibi ilgili kategorilerde yayınlanan haberleri Anthropic Qwen API'sine gönder ve şunu sor: "Bu haber Azerbaycan ile doğrudan veya dolaylı ilgili mi? İlgiliyse hangi açıdan (siyasi/ekonomik/güvenlik/kültürel/enerji)? Kısa gerekçe ver." API anahtarını ortam değişkeninden (.env, ANTHROPIC_API_KEY) oku, koda gömme.

## ÇAPRAZ KARŞILAŞTIRMA VE TUTARSIZLIK TESPİTİ
Aynı gün toplanan, aynı konudaki haberleri grupla (konu benzerliğine göre). Bu grubu Qwen API'ye vererek kaynaklar arasında çelişki/farklılık var mı (farklı rakamlar, çelişkili ifadeler, biri veriyor biri vermiyor) diye sor. Varsa haberi "Tutarsızlık var" etiketiyle işaretle ve kısa bir açıklama notu ekle. Sistem kesin doğru/yanlış hükmü vermiyor, sadece farkı özetleyip insan incelemesine işaret ediyor — bunu arayüzde de böyle ifade et.

## OTOMASYON
- Sistem her gün saat 07:30'da otomatik olarak tüm kaynakları tarasın (local scheduled task/cron mantığıyla, Python `schedule` kütüphanesi veya benzeri).
- Kullanıcı ekranı hiç açmasa bile bu tarama gerçekleşsin.
- Ayrıca arayüzde bir "Yenile" butonu olsun, kullanıcı istediği an manuel tetikleyebilsin.

## VERİ SAKLAMA
SQLite kullan. Her haber kaydında: kaynak adı, kategori (Resmi/İktidar/Muhalif), başlık, özet, yazar, yayın tarihi-saati, orijinal link, ilgi durumu (Aşama 1'de mi Aşama 2'de mi yakalandı), LLM ilgi gerekçesi, ilgi açısı, tutarsızlık durumu, tutarsızlık notu, ilişkili haber grubu ID'si. Geçmiş günler arşivlensin, tarihe göre geriye dönük sorgulanabilsin.

## ARAYÜZ (çok önemli — kullanıcı teknik değil)
- Tek sayfa, sekme/link geçişi yok — üç kategori (Resmi/Ana Akım, İktidar Yanlısı, Muhalif) aynı sayfada kaydırmalı bloklar halinde.
- Her haber bir kart: başlık, kısa özet, kaynak adı, yazar, saat, "Orijinali gör" linki.
- Tutarsızlık etiketli haberler görsel olarak belirgin şekilde öne çıksın (renk/ikon).
- Üstte küçük bir Azerbaycan bayrağı/amblemi (mavi-kırmızı-yeşil, ay-yıldız). Genel tasarım beyaz/gri sade zemin, vurgu renkleri bayrağın mavi-kırmızı-yeşil tonları. Büyük okunaklı yazı tipi, gereksiz animasyon yok.
- Üstte "Yenile" butonu ve tarih seçici (geçmiş günlere bakmak için).
- Basit bir Flask veya FastAPI backend + sade HTML/CSS (mümkünse ekstra frontend framework olmadan, kolay çalıştırılabilir olsun) tercih et.

## TESLİM
- README.md yaz: kurulum adımları, .env dosyasına ANTHROPIC_API_KEY nasıl eklenir, nasıl çalıştırılır (`python app.py` gibi), zamanlanmış görevin nasıl aktif edileceği.
- RSS bulunamayan/scraping'i şu an güvenilir çalışmayan kaynaklar için kodu yine de yaz ama README'de "bu kaynağın scraping mantığı test edilmeli, site yapısı değişirse adapter güncellenmeli" notu bırak.
- Kodun genelini modüler tut: `adapters/` (her kaynak için ayrı dosya), `classifier/` (aşama 1 + aşama 2), `db/`, `scheduler/`, `web/` şeklinde klasörle.

Şimdi bu projeyi eksiksiz şekilde, çalışır durumda kur.
