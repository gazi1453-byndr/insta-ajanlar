# Gerçek Maliyet: Instagram Ajan Sistemi

"Bu kaça mal oluyor?" sorusunu güncel Türkiye fiyatlarıyla, kalem kalem ve kaynaklı yanıtlayan
45 saniyelik Reels ve carousel içerikleri üreten, Claude ile çalışan otomatik bir ekip.
GitHub Actions üzerinde kendi kendine çalışır; sunucu gerekmez; resmi Instagram API'sini kullanır.

Yapay zeka arka planda gizli bir araştırma ekibi gibi çalışır. İzleyici sadece net rakamları,
animasyonlu grafikleri ve tartışma başlatan soruları görür.

## Ekip

```
 Pzt     TREND MADENCİSİ ──── Google Trends, Reddit, YouTube, Ekşi: son 7 günün en çok aranan
                               soruları → 15-20 "ilk 3 saniye" kancası (hook bankası)
 05:00   ARAŞTIRMACI ──────── nişteki büyük sayfaları kendisi bulur, en iyi gönderilerini inceler
 06:00   FİKİR AJANI ──────── hook bankasından günün konusunu seçer (reel %70 / carousel %30)
           │
         VERİ ARAŞTIRMACISI ─ güncel fiyatları kaynağıyla toplar → maliyet tablosu
           │                   (toplamları Python yeniden hesaplar: hesap hatası olamaz)
         HOOK YAZARI ──────── tablodaki en şaşırtıcı rakamdan 8 farklı kanca, en iyisini seçer
           │
         İÇERİK ÜRETİCİ ───── sahneler + seslendirme metni + Reels / TikTok / YouTube metinleri
           │       ▲
         TASARIMCI ────────── animasyonlu çubuk grafikler (çubuklar büyür, rakamlar sayar)
           │       │ REVİZYON
         MÜDÜR ───┴────────── 100 puan: hook, değer, RAKAM DOĞRULUĞU, akış, özgünlük...
           │                   tabloyla uyuşmayan tek rakam bile varsa onay yok
         VİDEO KURGUCU ────── 1080x1920, 45 sn Reels (+ ses klonu ve müzik varsa onlar da)
           ▼
 */30dk  YAYINCI ──────────── Instagram'a yükler, ilk yorumu (tartışma sorusu) yazar,
                               TikTok + YouTube Shorts paketini GitHub bildirimi olarak gönderir
 */2sa   TOPLULUK ─────────── yorumlara yanıt verir
 Pzt     ANALİST ──────────── haftalık rapor + "öğrenilenler" (tüm ajanlar bunu okur)
```

## Kurulum durumu

| Adım | Durum |
|---|---|
| Instagram hesabı + Facebook sayfası + bağlantı | ✅ |
| Meta uygulaması (YZ Pratik Ajan) + izinler | ✅ |
| Süresiz sistem kullanıcısı tokeni → `IG_ACCESS_TOKEN` | ✅ |
| `ANTHROPIC_API_KEY` | Senin eklemen gerekiyor ([console.anthropic.com](https://console.anthropic.com)) |
| Instagram kullanıcı adını `gercekmaliyet` yapmak | Senin yapman gerekiyor (Instagram → Profili düzenle) |
| Ses klonu (isteğe bağlı) | Aşağıya bak |

`IG_USER_ID` ve `FB_PAGE_ID` gerekmiyor; sistem token'dan kendisi buluyor.

## Ses klonu (isteğe bağlı ama önerilir)

Kendi sesinin klonu marka güvenini ciddi şekilde artırır. Ayarlanmazsa videolar sessiz çıkar,
ekranda yazı ve (varsa) müzikle oynar.

1. [elevenlabs.io](https://elevenlabs.io)'da hesap aç. Ses klonu için ücretli plan gerekiyor.
2. **Voices → Add voice → Instant Voice Clone** ile 1-3 dakikalık temiz bir kayıt yükle.
3. Repo **Settings → Secrets → Actions** altına iki değer ekle:
   - `ELEVENLABS_API_KEY`: profil → API Keys
   - `ELEVENLABS_VOICE_ID`: sesin ayarlarındaki Voice ID

Arka plan müziği için `assets/music/` klasörüne **telifsiz** bir mp3 koyman yeterli.

## TikTok ve YouTube Shorts

İki platform da denetimden (audit) geçmemiş uygulamaların API ile yüklediği videoları
**gizli** yayınlıyor. Bu yüzden şu an şöyle çalışıyor: her Reels yayınlandığında GitHub'da
**"📤 TikTok + YouTube'a paylaş"** başlıklı bir issue açılıyor. İçinde videonun indirme linki,
TikTok açıklaması, hashtag'ler, YouTube başlığı (seri numaralı), açıklaması ve etiketleri hazır
duruyor. Telefondan bir dakikada paylaşılıyor. Denetim onaylanınca otomatik yüklemeye geçilebilir.

## Günlük kullanım

| İstediğin | Yapman gereken |
|---|---|
| Her içeriği önce görmek | `config.yaml` → `insan_onayi: true`. İçerikler Pull Request olarak gelir: **Merge** = yayınla |
| Raporlar | Her pazartesi **Issues**'da haftalık rapor açılır |
| Kuyruk | `data/queue/` (iptal için dosyayı sil) |
| Neden reddedildi? | `data/rejected/`: müdürün gerekçesi ve rakam hataları |
| Bu hafta hangi sorular trend? | `data/hook_bank.json` |
| Maliyet tablosu ve kaynaklar | Her içeriğin JSON'unda `veri` alanı |
| Günde 2 içerik | `config.yaml` → `gunluk_gonderi: 2` ve iki paylaşım saati |

## Bilmen gerekenler

- **Tahmini Claude maliyeti:** Opus 5.5 ile günde 1 içerik için ayda yaklaşık 30-50 $. Web
  araştırmaları bu tutara dahil. `modeller.varsayilan: "claude-sonnet-5-5"` yaparsan kabaca yarıya iner.
- **Medya barındırma:** Instagram videoyu herkese açık bir adresten çekiyor. Varsayılan olarak bu
  public reponun raw adresi kullanılıyor. Repo şişmesin diye 3 haftadan eski videolar silinir.
- **Rakam güvenliği:** Veri güveni "düşük" çıkan konular hiç üretilmez. Tahmini kalemler grafikte
  `*` ile işaretlenir. Fiyat tarihi her içerikte yazar.
- **Yeni hesap:** İlk 2 hafta günde 1 içerikle başla. Ara sıra hesaba girip elle de etkileşim yap.
- **DM yanıtı:** Meta uygulama incelemesi gerektiriyor, o yüzden kapalı (`dm_yaniti: false`).

## Dosya yapısı

```
config.yaml          ← tek ayar dosyası (niş, ton, renkler, formatlar, saatler)
pipeline.py          ← arastir | uret | yayinla | topluluk | analiz | durum
agents/
  researcher.py      trend madencisi + büyük sayfa analizi
  strategist.py      fikir ajanı          data_researcher.py  veri araştırmacısı
  hook_writer.py     hook yazarı          creator.py          içerik üretici
  designer.py        grafik/slayt         video.py            video kurgucu
  voice.py           ElevenLabs ses       manager.py          müdür
  publisher.py       yayıncı + çapraz yayın paketi
  community.py       topluluk             analyst.py          analist
  producer.py        üretim hattı         instagram.py / llm.py  API bağlantıları
data/                hook_bank, research, queue, published, rejected, reports, learnings.md
media/generated/     üretilen görseller ve videolar
```
