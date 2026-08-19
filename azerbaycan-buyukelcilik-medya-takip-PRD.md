# PRD — Azerbaycan Büyükelçiliği Türkiye Medya Takip Sistemi

**Versiyon:** 0.1 (Taslak)
**Tarih:** 19 Ağustos 2026
**Hazırlayan:** [proje sahibi]
**Ortam:** Local (sunucu barındırma sonraki fazda değerlendirilecek)

---

## 1. Özet ve Amaç

Azerbaycan Büyükelçisi, her sabah Türkiye basınında Azerbaycan ile ilgili çıkan haberleri takip etmek, bu haberlerin doğruluğunu/tutarlılığını değerlendirmek ve yanlış ya da çelişkili bilgi içeren haberleri hızlıca tespit etmek istiyor. Bu ihtiyacı karşılamak üzere, Türkiye'deki farklı siyasi/editoryal çizgideki haber kaynaklarını otomatik olarak tarayan, Azerbaycan ile ilgili haberleri filtreleyen, kaynakları karşılaştırarak tutarsızlıkları işaretleyen ve büyükelçiye sade bir arayüzde sunan bir sistem geliştirilecektir.

**Birincil kullanıcı:** Büyükelçi (teknik bilgisi yok, sade ve az tıklamalı bir deneyim bekliyor).
**İkincil kullanıcı:** Büyükelçilik personeli / sistemi yöneten teknik ekip.

---

## 2. Hedefler

- Büyükelçinin her sabah tek bir ekranda, Türkiye medyasındaki Azerbaycan haberlerinin tam görünümünü elde etmesi.
- Haberlerin hangi kaynaktan, hangi yazardan, ne zaman yayınlandığının net şekilde görülmesi.
- Farklı kaynaklar arasındaki çelişkili/tutarsız bilgilerin otomatik olarak işaretlenmesi.
- Sistemin manuel müdahale gerektirmeden, her gün kendiliğinden çalışması.
- Arayüzün teknik bilgi gerektirmeden, tek bakışta anlaşılır olması.

### Kapsam Dışı (bu faz için)
- Kesin/otoriter "doğru-yanlış" hakemliği yapmak (yazılım nihai karar vermez, karşılaştırma ve işaretleme yapar).
- Ücretli/resmi kurumsal API entegrasyonları (AA API dahil) — bu faz yalnızca RSS ve web taraması (scraping) ile çalışacak. API entegrasyonu ileride ayrı bir faz olarak değerlendirilebilir.
- Kürt/bölgesel basın kaynakları (Mezopotamya Ajansı, Rûdaw Türkçe vb.) — kullanıcı talebiyle kapsam dışı bırakılmıştır.
- Bulut sunucu / hosting kurulumu — sistem local ortamda çalışacaktır.

---

## 3. Kaynaklar

Sistem, üç ayrı editoryal kategori altında toplam 14 kaynağı tarayacaktır. Tüm kaynaklar **RSS beslemesi** (varsa) veya **web taraması (scraping)** ile çekilecektir; resmi API kullanılmayacaktır.

### 3.1 Resmi / Ana Akım
| Kaynak | Veri çekme yöntemi |
|---|---|
| AA (Anadolu Ajansı) | Scraping (resmi API bu fazda kullanılmıyor) |
| TRT Haber | Scraping |
| İHA (İhlas Haber Ajansı) | Scraping |
| Milliyet | RSS (mevcut, doğrulanacak) |
| Hürriyet | RSS/Scraping (RSS durumu doğrulanacak) |

### 3.2 İktidar Yanlısı
| Kaynak | Veri çekme yöntemi |
|---|---|
| A Haber | Scraping |
| Yeni Şafak | Scraping |
| Sabah | RSS (mevcut, doğrulanacak) |
| Türkiye Gazetesi | RSS/Scraping (doğrulanacak) |

### 3.3 Muhalif
| Kaynak | Veri çekme yöntemi |
|---|---|
| Sözcü | Scraping |
| Cumhuriyet | RSS (mevcut, doğrulanacak) |
| Halk TV | Scraping |
| T24 | RSS (mevcut, doğrulanacak) |
| BirGün | Scraping |

> **Not:** Her kaynak için ayrı bir "adapter" (veri çekme modülü) yazılacaktır. Bir kaynağın sitesi değişip veri çekme bozulursa, yalnızca o adapter güncellenecek; sistemin geneli etkilenmeyecektir.

---

## 4. Temel Özellikler

### 4.1 Otomatik Günlük Tarama
- Sistem, **her gün saat 07:30**'da otomatik olarak tüm kaynakları tarar ve Azerbaycan ile ilgili haberleri toplar.
- Kullanıcı ekranı açmasa bile tarama gerçekleşir; büyükelçi ekranı açtığında güncel liste hazır bulunur.
- Otomasyon local ortamda zamanlanmış görev (scheduled task / cron) ile sağlanacaktır.

### 4.2 Manuel Yenileme
- Ekranda bir **"Yenile"** butonu bulunur; kullanıcı istediği an tıklayarak o günün haberlerini tekrar taratabilir.

### 4.3 Konu Filtreleme (Hibrit Sınıflandırma: Anahtar Kelime + LLM)

Basit anahtar kelime taraması, "Azerbaycan" kelimesi doğrudan geçmeyen ama konuyla dolaylı ilgili haberleri (ör. "Zangezur koridoru", "Aliyev-Erdoğan görüşmesi" başlıklı ama metinde "Azerbaycan" geçmeyen bir haber) kaçırabilir. Bu riski azaltmak için iki aşamalı bir sınıflandırma uygulanacaktır:

**Aşama 1 — Anahtar Kelime Ön Filtresi (Güçlü/Geniş Liste)**
Sistem, her taranan haberi geniş ve düzenli olarak güncellenebilir bir anahtar kelime/varlık listesiyle tarar. Liste yalnızca "Azerbaycan" ile sınırlı kalmaz, dolaylı ilişkili özel isim ve kavramları da kapsar:
- Ülke/yer adları: Azerbaycan, Bakü, Nahçıvan, Karabağ, Şuşa, Hankendi
- Kişi/kurum adları: Aliyev, Paşinyan (Ermenistan bağlamında), Türk Devletleri Teşkilatı
- Konu/kavram: Zangezur koridoru, Ermenistan-Azerbaycan, TANAP, Güney Kafkasya, Dağlık Karabağ
- Bu liste yapılandırılabilir bir dosyada tutulur, ihtiyaç halinde kolayca genişletilir.

Bu aşamadan **doğrudan eşleşenler** otomatik olarak "Azerbaycan ile ilgili" kabul edilir ve sisteme dahil edilir.

**Aşama 2 — LLM ile İkincil Sınıflandırma (Şüpheli/Sınırda Haberler)**
Aşama 1'de doğrudan eşleşme çıkmayan ama ilgili kategori/bölümde (ör. dış politika, Kafkasya, enerji, savunma) yayınlanan haberler otomatik elenmez; bunun yerine **Claude API'sine** (Anthropic) gönderilerek şu değerlendirme yaptırılır:
- Haber Azerbaycan ile doğrudan veya dolaylı olarak ilgili mi?
- İlgiliyse hangi açıdan ilgili (siyasi, ekonomik, güvenlik, kültürel, enerji vb.)?
- Kısa bir gerekçe (neden ilgili bulundu) döndürülür — bu gerekçe, büyükelçinin haberi neden gördüğünü anlamasına yardımcı olur.

Bu iki aşamalı yapı sayesinde:
- Açık/doğrudan haberler hızlı ve maliyetsiz şekilde yakalanır (Aşama 1).
- Kelimeyle yakalanamayan dolaylı/örtük haberler LLM değerlendirmesiyle kaçırılmaz (Aşama 2).
- LLM yalnızca "şüpheli" haberlere uygulandığından maliyet ve işlem süresi kontrol altında tutulur (tüm haber trafiği değil, filtrelenmiş bir alt küme LLM'e gönderilir).

**Kullanılacak API:** Sınıflandırma ve ilişkilendirme için **Claude API (Anthropic)** kullanılacaktır. Bu, sistemin geri kalanı (veri çekme, veritabanı, arayüz) local çalışırken, yalnızca sınıflandırma adımında dışarıya (Anthropic API'sine) bir çağrı yapılması anlamına gelir. API anahtarının güvenli şekilde saklanması (ortam değişkeni / .env, koda gömülmemesi) gerekir.

### 4.4 Kaynak Bilgisi Çıkarımı
Her haber için sistem şu bilgileri otomatik olarak çıkarır ve gösterir:
- Haberin başlığı ve kısa özeti
- Kaynak kuruluş adı
- Yazar adı (varsa)
- Yayınlanma tarihi ve saati
- Orijinal habere giden link

### 4.5 Çapraz Kaynak Karşılaştırma ve Tutarsızlık Tespiti
- Sistem, aynı konuyu farklı kaynakların nasıl işlediğini karşılaştırır.
- Kaynaklar arasında belirgin farklılık (ör. farklı rakamlar, çelişkili ifadeler, bir kaynağın verdiği bilgiyi diğerinin vermemesi) tespit edilirse bu haber **"Tutarsızlık var"** etiketiyle işaretlenir.
- Bu karşılaştırma da 4.3'te tanımlanan **Claude API** üzerinden yapılır: aynı gün/konu etrafında toplanan haberler gruplandırılır, LLM'e birlikte verilerek farklılıkların özetlenmesi istenir. LLM, farklılığı kısa bir notla (ör. "Kaynak A 500 kişi diyor, Kaynak B 300 kişi diyor") açıklar.
- **Önemli sınırlama:** Sistem nihai bir "doğru/yanlış" hükmü vermez; yalnızca çapraz karşılaştırma yaparak insan incelemesine dikkat çeker. Bu, PRD genelinde "doğrulama" değil "tutarsızlık tespiti" olarak konumlandırılmıştır.

### 4.6 Arşiv ve Geçmişe Dönük Arama
- Geçmiş günlere ait taramalar saklanır, kullanıcı tarih seçerek geçmiş haberlere ulaşabilir.

---

## 5. Arayüz (UI/UX) Gereksinimleri

Büyükelçi teknik bilgiye sahip olmadığından arayüz tasarımı şu ilkelere göre kurgulanacaktır:

- **Tek ekran, sade tasarım:** Kullanıcının farklı sayfalar arasında gezinmesi gerekmeyecek şekilde, üç kategori (Resmi/Ana Akım, İktidar Yanlısı, Muhalif) tek sayfa üzerinde bloklar/bölümler halinde gösterilecektir. Sekme (tab) geçişi yerine kaydırmalı (scroll) tek sayfa tercih edilecektir.
- **Az tıklama:** Haberi görmek için ekstra sayfa açmaya gerek kalmadan, kart üzerinde başlık + özet + kaynak bilgisi doğrudan görünür olacaktır. Orijinal habere gitmek isteyenler için link sağlanacaktır.
- **Yorucu olmayan görsel dil:** Büyük, okunaklı yazı tipleri; sade renk paleti; gereksiz animasyon/karmaşadan kaçınılacaktır.
- **Azerbaycan kimliği:** Sayfanın üst kısmında Azerbaycan bayrağı (mavi–kırmızı–yeşil, ay-yıldız) küçük bir şerit/amblem olarak yer alacak. Genel renk paleti ağırlıklı beyaz/gri zemin üzerine, vurgu renkleri olarak Azerbaycan bayrağının mavi, kırmızı ve yeşil tonları kullanılacaktır.
- **Tutarsızlık uyarısı görünürlüğü:** "Tutarsızlık var" etiketli haberler, kullanıcının gözünden kaçmayacak şekilde görsel olarak (ör. bir renk/ikon ile) öne çıkarılacaktır.

---

## 6. Teknik Mimari (Yüksek Seviye)

- **Ortam:** Local (kullanıcı/geliştirici makinesinde çalışacak; sunucu/hosting bu fazda konu dışı).
- **Backend:**
  - Her kaynak için ayrı adapter modülü (RSS parse veya scraping).
  - Zamanlanmış görev (cron/scheduled task) ile her gün 07:30'da otomatik tarama.
  - **Sınıflandırma katmanı:** Aşama 1 (anahtar kelime ön filtresi, local) → Aşama 2 (Claude API ile ilgi/kapsam ve tutarsızlık değerlendirmesi, dışa API çağrısı).
  - Basit bir yerel veritabanı (ör. SQLite) ile günlük haberlerin, LLM değerlendirme sonuçlarının ve geçmiş arşivin saklanması.
- **Frontend:**
  - Tek sayfa, sade arayüz (yenile butonu, kategori blokları, tutarsızlık etiketleri, tarih/arşiv seçici).
- **Veri modeli (taslak):** Her haber kaydı şu alanları içerir: kaynak adı, kategori (Resmi/İktidar/Muhalif), başlık, özet, yazar, yayın tarihi-saati, link, ilgi durumu (Aşama 1'de mi Aşama 2'de mi yakalandığı), LLM ilgi gerekçesi, ilgi açısı (siyasi/ekonomik/güvenlik/kültürel vb.), tutarsızlık durumu (var/yok), tutarsızlık notu (LLM tarafından üretilen kısa açıklama), ilişkili haber grubu (aynı konudaki diğer kaynak haberleriyle eşleştirme için).

---

## 7. Açık Konular / Karar Bekleyenler

- RSS beslemesi bulunmayan kaynaklar (TRT Haber, İHA, A Haber, Yeni Şafak, Halk TV, BirGün vb.) için scraping mantığının kaynak bazında ayrı ayrı doğrulanması gerekiyor.
- Milliyet, Hürriyet, Sabah, Türkiye Gazetesi, Cumhuriyet, T24 için RSS linklerinin güncel/çalışır durumda olup olmadığının teyidi gerekiyor.
- Tutarsızlık tespiti için kullanılacak yöntemin (basit anahtar kelime/rakam karşılaştırması mı, daha gelişmiş bir metin analizi mi) detaylandırılması gerekiyor.
- Anında bildirim (ör. kritik haber çıktığında büyükelçiye e-posta/mesaj) bu fazda kapsam dahilinde değil; ihtiyaç görülürse sonraki fazda değerlendirilecek.
- Aşama 1 anahtar kelime listesinin ilk versiyonunun netleştirilmesi ve onaylanması gerekiyor.
- Aşama 2'de LLM'e hangi haberlerin gönderileceğine dair kriterin (ör. hangi kategori/bölüm başlıkları "şüpheli" sayılacak) netleştirilmesi gerekiyor.
- Claude API kullanım maliyetinin (günlük ortalama haber hacmine göre) kabaca tahmin edilmesi ve bütçe onayı alınması gerekiyor.
- API anahtarının güvenli saklanması için ortam değişkeni (.env) yönteminin uygulanması gerekiyor.

---

## 8. Sonraki Adımlar

1. Kaynak bazında RSS/scraping fizibilite testi.
2. Veri modeli ve local veritabanı şemasının netleştirilmesi.
3. Backend adapter'larının geliştirilmesi (kaynak başına bir modül).
4. Zamanlanmış görev (07:30 otomatik tarama) kurulumu.
5. Frontend arayüzünün (tek sayfa, sade, bayrak temalı) geliştirilmesi.
6. Tutarsızlık tespiti mantığının ilk versiyonunun uygulanması.
7. Büyükelçiye demo ve geri bildirim toplama.
