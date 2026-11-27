# Instagram Ajan Sistemi

Claude ile çalışan, GitHub Actions üzerinde kendi kendine dönen 9 ajanlı bir Instagram ekibi.
Sunucu gerekmez; resmi Instagram API'sini kullanır (hesabın kapanma riski olan bot hilesi yok).

## Ekip

```
 05:00  1. ARAŞTIRMACI ──── büyük sayfaların en iyi gönderileri + hashtag'ler + web trendleri
          │                  → "ne tutuyor, neden tutuyor" raporu
 06:00  2. FİKİR AJANI ──── günün içerik fikirleri (tekrar yok, öğrenilenlere göre)
          │
        3. HOOK YAZARI ──── 8 farklı teknikle açılış cümlesi, en güçlüsünü seçer
          │
        4. İÇERİK ÜRETİCİ ─ carousel slaytları, açıklama, hashtag, reel senaryosu
          │       ▲
        5. TASARIMCI ────── markana uygun 1080x1350 görseller (ya da senin görselin)
          │       │ REVİZYON (geri bildirimle, en fazla 2 kez)
        6. MÜDÜR ─┴──────── 100 puan üzerinden değerlendirir: TUTAR MI?
          │                  ONAY → yayın kuyruğu   RED → arşiv
          ▼
 */30dk 7. YAYINCI ──────── saati gelen gönderiyi Instagram'a yükler
 */2sa  8. TOPLULUK ─────── yorumlara (ve izinliyse DM'lere) yanıt verir
 Pzt    9. ANALİST ──────── haftalık rapor (GitHub issue) + "öğrenilenler"
                              ↳ tüm ajanlar bir sonraki hafta bunları okur
```

Müdürün puanlama tablosu: hook gücü 25 · değer 25 · trend uyumu 15 · özgünlük 15 · marka/doğruluk 10 · görsel okunurluk 10.
Onay eşiği `config.yaml` içinde (varsayılan 75).

## Kurulum (yaklaşık 45 dakika, bir kez)

### 1. Instagram hesabı
1. Yeni Instagram hesabını aç.
2. **Ayarlar → Hesap türü ve araçlar → Profesyonel hesaba geç → İşletme**. Creator da olur; ancak İşletme hesabı API ile en sorunsuz çalışan seçenek.
3. Bir **Facebook Sayfası** oluştur ve Instagram ayarlarından bu sayfaya bağla. Bu adım zorunlu: büyük sayfaları inceleme ve hashtag araştırması yalnızca Facebook sayfasına bağlı hesaplarda çalışıyor.

### 2. Meta geliştirici uygulaması ve token
1. [developers.facebook.com](https://developers.facebook.com) adresinde **Uygulama oluştur** de ve tür olarak **İşletme** seç.
2. Uygulamaya **Instagram Graph API** (Facebook Girişi ile) ürününü ekle.
3. **Graph API Explorer**'da kendi uygulamanı seç ve şu izinlerle bir kullanıcı tokeni oluştur:
   `instagram_basic, instagram_content_publish, instagram_manage_comments, instagram_manage_insights, pages_show_list, pages_read_engagement, business_management`
4. Bu tokeni **uzun ömürlü** yap (Access Token Debugger → *Extend*).
5. Explorer'da `me/accounts` sorgusunu çalıştır. Sayfanın `access_token` değeri süresi dolmayan sayfa tokenidir: bu **IG_ACCESS_TOKEN** olacak. Aynı satırdaki `id` değeri **FB_PAGE_ID** olacak.
6. `{FB_PAGE_ID}?fields=instagram_business_account` sorgusunu çalıştır. Dönen `id` değeri **IG_USER_ID** olacak.

> Daha sağlam bir yol: Business Manager'da bir **Sistem Kullanıcısı** oluşturup ona token verirsen, bu token hiç süresi dolmadan çalışır.

### 3. Claude API anahtarı
[console.anthropic.com](https://console.anthropic.com) → API Keys → yeni anahtar oluştur. Bu **ANTHROPIC_API_KEY** olacak.

### 4. GitHub reposu
1. Bu klasörü yeni bir GitHub reposuna yükle. Repo **Public** olmalı, çünkü Instagram görselleri herkese açık bir adresten çekiyor. Sırların hiçbiri kodda değil; hepsi Secrets'ta duruyor.
   - Repo gizli kalsın istiyorsan görselleri başka bir yerde barındırıp adresini `MEDIA_BASE_URL` değişkenine yaz.
2. **Settings → Secrets and variables → Actions → New repository secret** yolundan şunları ekle:
   | Secret | Değer |
   |---|---|
   | `ANTHROPIC_API_KEY` | Claude API anahtarın |
   | `IG_USER_ID` | 2.6. adımdaki ID |
   | `IG_ACCESS_TOKEN` | 2.5. adımdaki sayfa tokeni |
   | `FB_PAGE_ID` | 2.5. adımdaki sayfa ID'si (sadece DM için) |
3. **Settings → Actions → General → Workflow permissions** altında **Read and write** seç ve **Allow GitHub Actions to create and approve pull requests** kutusunu işaretle.

### 5. Ayarlar
`config.yaml` hazır gelir: niş **yapay zeka araçları ve pratik kullanım**, hesap adı `yapayzeka.pratik`, ton, renkler, hashtag'ler ve paylaşım saati belirlenmiş durumda. Profil fotoğrafı `assets/profil.png` içinde.
İncelenecek büyük sayfaları araştırmacı kendisi bulur ve Instagram API ile doğrular (`buyuk_sayfalar: []` + `otomatik_sayfa_bulma: true`). İstersen listeye kendi seçtiğin hesapları da ekleyebilirsin.

### 6. İlk çalıştırma (deneme)
Reponun **Actions** sekmesinde sırayla şunları yap:
1. **1 · Araştırmacı** → *Run workflow*.
2. **2 · İçerik Üretimi** → *Run workflow*. İlk seferde `dry_run` kutusunu işaretlersen hiçbir şey kaydedilmez, sadece log'lara bakarsın.
3. Logları ve `data/queue/` klasörüne düşen içeriği kontrol et.
4. **3 · Yayıncı** → *Run workflow* (dry_run seçili). Paylaşılacak görsel adreslerini ve açıklamayı gösterir.

Her şey doğru görünüyorsa başka bir şey yapmana gerek yok. Zamanlanmış çalışmalar her gün kendiliğinden başlar.

## Günlük kullanım

| İstediğin | Yapman gereken |
|---|---|
| Kendi görselini paylaştırmak | Görseli `media/inbox/` klasörüne yükle. Fikir ajanı bir sonraki üretimde tek görsellik gönderi planlar, açıklamayı görsele bakarak yazar. |
| Her içeriği önce görmek | `config.yaml` içinde `insan_onayi: true` yap. Onaylanan içerikler sana Pull Request olarak gelir. **Merge** dersen yayın kuyruğuna girer, **Close** dersen iptal olur. |
| Reel çekmek | Müdürün onayladığı reel senaryoları `data/reels/` klasörüne düşer. Çekip kendin paylaşırsın. |
| Raporları görmek | Her pazartesi **Issues** sekmesinde yeni bir rapor açılır (GitHub mobil uygulamasına bildirim gelir). |
| Kuyruğu görmek | `data/queue/` klasörü. Bir gönderiyi iptal etmek için dosyasını sil. |
| Neden reddedildi? | `data/rejected/` klasöründe müdürün gerekçesi yazıyor. |
| Maliyeti düşürmek | `config.yaml` → `modeller.varsayilan: "claude-sonnet-5-5"` |

## Bilmen gerekenler

- **Tahmini maliyet:** Claude Opus 5.5 ile günde 1 gönderi için ayda yaklaşık 20-40 $. Sonnet ile bunun kabaca yarısı. GitHub Actions, public repolarda ücretsiz.
- **DM yanıtı:** Instagram mesajlaşma API'si, uygulamada rolü olmayan kişilerle yazışmak için Meta'nın **uygulama incelemesinden** (App Review) geçmeyi istiyor. Ayrıca `instagram_manage_messages` izni gerekiyor. Bunlar tamamlanmadan `dm_yaniti: false` kalsın. Yorum yanıtı ise inceleme olmadan çalışıyor.
- **Büyük sayfa analizi** yalnızca Business/Creator hesaplarda çalışıyor. Kişisel hesap girersen araştırmacı o hesabı atlıyor ve log'a yazıyor.
- **Hashtag araştırması:** Instagram haftada en fazla 30 farklı hashtag aramaya izin veriyor.
- **Yeni hesap tavsiyesi:** İlk 2 hafta günde 1 gönderiyi geçme. Ara sıra hesaba girip elle etkileşim de yap; tamamen otomatik görünen yeni hesapların erişimi düşük kalabiliyor.
- **GitHub zamanlaması** yoğun saatlerde 5-15 dakika gecikebiliyor. Bu yüzden gönderi, planlanan saatten biraz sonra çıkabilir.
- Meta, API sürümlerini ve metrik adlarını zaman zaman değiştiriyor. Bir şey bozulursa repo **Variables** bölümüne `GRAPH_API_VERSION` ekleyerek sürümü güncelleyebilirsin.

## Yerelde çalıştırma (isteğe bağlı)

```powershell
pip install -r requirements.txt
$env:ANTHROPIC_API_KEY="..."; $env:IG_USER_ID="..."; $env:IG_ACCESS_TOKEN="..."; $env:DRY_RUN="1"
python pipeline.py arastir
python pipeline.py uret
python pipeline.py durum
```

## Dosya yapısı

```
config.yaml                 ← tek ayar dosyası
pipeline.py                 ← komut satırı (arastir | uret | yayinla | topluluk | analiz | durum)
agents/
  researcher.py  strategist.py  hook_writer.py  creator.py  designer.py
  manager.py     publisher.py   community.py    analyst.py
  producer.py    (ajanları sırayla çalıştıran üretim hattı)
  llm.py         (Claude bağlantısı)   instagram.py (Instagram API)
data/
  research/  queue/  published/  rejected/  reels/  reports/  learnings.md
media/
  inbox/ (senin görsellerin)  generated/ (ajanın görselleri)  used/
.github/workflows/          ← 5 zamanlanmış görev
```
