# GERÇEK MALİYET — Tasarım Sistemi

Apple Human Interface Guidelines estetiğinden uyarlanmıştır: yüksek tipografi kalitesi, cömert boşluk, cam ve gölge derinliği, fizik tabanlı akıcı hareket.
Üretilen **her görsel, kapak, carousel ve video bu kurallara uyar**.
Uygulandığı yerler:

- Video: `video/` (Remotion)
- Yedek motor ve görseller: `agents/designer.py`, `agents/motion.py`

---

## 1. İlkeler

1. **Netlik:** Ekranda tek bir ana mesaj olur. Rakam her zaman en büyük ve en parlak öğedir.
2. **Saygı (deference):** Arka plan ve süsler içeriğin önüne geçmez. Arka plan hareketlidir ama düşük kontrastlıdır.
3. **Derinlik:** Katmanlar cam ve gölgeyle ayrılır; kenarlığa değil derinliğe güvenilir.
4. **Tempo:** Hiçbir sahne ekranda 3–3,5 sn'den uzun "durağan" kalmaz. Altyazı, sayaç, yavaş yakınlaşma ya da arka plan sürekli bir şeyi hareket ettirir.

## 2. Tipografi

SF Pro'nun lisansı Apple platformları dışında kullanıma izin vermez. Bu yüzden onun açık kaynak karşılığı olan **Inter** (SIL OFL) kullanılır.
Dosyalar `assets/fonts/` altındadır; lisans metni `OFL.txt`.

| Rol | Yazı tipi | Ağırlık | Boyut (1080 px genişlik) | Satır aralığı | Harf aralığı |
|---|---|---|---|---|---|
| Dev rakam (reveal/spot) | Inter Display | 900 Black | 150–180 | 1.05 | −3/−4 px |
| Hook başlığı | Inter Display | 900 | 80–132 (sığdır) | 1.04 | −2 px |
| Sahne başlığı | Inter Display | 900 | 60–96 | 1.08 | −1 px |
| Karaoke altyazı | Inter Display | 900, BÜYÜK HARF (`lang="tr"`) | 72 | 1.05 | −1 px |
| Gövde metni | Inter | 400 | 42–46 | 1.34 | 0 |
| Etiket / rozet | Inter | 700 | 26–36 | 1.2 | +0.5…+8 px (BÜYÜK HARF etiketlerde) |

Kurallar:

- Rakamlarda `tabular-nums` kullanılır; sayaç ilerlerken rakamlar yerinde titremez.
- Para biçimi Türkçe olur: `61.438,50 TL`, `%46`. Yüzde işareti başa yazılır.
- Bir ekranda en fazla 3 yazı boyutu bulunur. Hiyerarşi önce boyutla, sonra renkle kurulur.
- Satır başına en fazla yaklaşık 28 karakter (başlık) ve 40 karakter (gövde) olur.

## 3. Renk (60-30-10)

| Pay | Token | Renk | Kullanım |
|---|---|---|---|
| %60 | `arka_plan` | `#0B1220` | Zemin (gece laciverti) |
| %30 | `panel` | `#18233A` | Cam kartlar, tablo zemini |
| %10 | `vurgu` | `#22C55E` | Rakamlar, aktif altyazı kelimesi, marka şeridi, barlar |
| — | `yazi` | `#F8FAFC` | Başlık ve gövde |
| — | `yazi_ikincil` | `#94A3B8` | Dönem, kaynak, etiket |
| — | `uyari` | `#F43F5E` | Yalnızca zam veya kayıp vurgusu, seyrek |

- Vurgu rengi yalnızca **anlam taşıyan** yerde kullanılır: para, aktif kelime, ilerleme.
- Kontrast her metinde en az 7:1 (AAA) olur. İkincil metin 4,5:1'in altına inmez.
- Grafikte yalnızca vurgunun tonları ve nötr griler bulunur; gökkuşağı kullanılmaz.

## 4. Yerleşim (1080×1920)

```
  0 ─ ilerleme çubuğu (10 px, vurgu)
130 ─ marka şeridi: "GERÇEK MALİYET #N · ALT SERİ"  ·  @kullanıcı
250 ┐
    │  İÇERİK BÖLGESİ (dikeyde ortalı)
    │  kenar boşluğu 72 px, 8 px ızgara
1250┘
1300─ KARAOKE ALTYAZI (alt-orta, 200 px)
1520─ kaynak satırı (24 px)
1560+ Instagram arayüzü: önemli içerik konmaz
```

- **Sahne çeşitliliği:** aynı kutu art arda tekrarlanmaz. Kullanılan sahne tipleri:
  - `hook`: tam ekran kinetik başlık
  - `card`: cam kart
  - `statement`: ortalı dev ifade
  - `spot`: dev tek rakam
  - `grafik`: yüzdeli kırılım barları
  - `reveal`: GERÇEK MALİYET, kırılımla birlikte
  - `sonuc`: kaydetmelik özet
- **Cam kart:** dikey gradyan panel (`#18233A`, %78–90 opak), 44 px köşe, 1,5 px beyaz %9 kenar, `0 30 80 rgba(0,0,0,.45)` gölge ve iç üst ışık.
- **Kırılım:** her kalem bir satırdır. Satırda etiket, `%pay` çipi ve tutar bulunur; altında 24–30 px yuvarlak bar uzanır. En fazla 6 kalem gösterilir, kalanı "Diğer"e toplanır.

## 5. Hareket

| Öğe | Değer |
|---|---|
| Sahne geçişi | Dikey itme. Yay: `damping 14, stiffness 180, mass 1`. 10. karede %90'a ulaşır (60 fps), hafif taşar. |
| Hareket bulanıklığı | Geçiş hızıyla orantılı, yalnızca dikey (`feGaussianBlur 0 σ`), en fazla σ = 18 |
| Kinetik yazı | Kelimeler 3 kare arayla 60 px aşağıdan yaylı yükselir |
| Sayaç | 0 → hedef, 0,8 sn, easeOutExpo. Rakam bitince 'damga' yayı (`damping 9`) |
| Bar | Yaylı büyür, satırlar 6 kare arayla gelir |
| Yaşayan kare | İçerik sahne boyunca %2,5 yavaş yakınlaşır. Izgara, ışık hüzmesi ve noktalar sürekli akar. |
| FPS | 60 |

## 6. Ses

| Öğe | Kural |
|---|---|
| Ses | ElevenLabs (`eleven_multilingual_v2`, stability 0.45, similarity 0.80) varsa o kullanılır; yoksa Edge `tr-TR-AhmetNeural +%18` |
| Sessizlik | Her sahnenin baş ve son sessizliği kelime zamanlarına göre kırpılır |
| Müzik | `assets/music`, yaklaşık %9 seste, sonda 1,5 sn kararma |
| Efekt | Her geçişte `whoosh` (%35), rakam damgasında `pop` (%30) |
| Süre | 35–42 sn. Ara sahneler en fazla 4 sn. Ses yüksekliği −14 LUFS. |

## 7. Yapılmayacaklar

- Düz, hareketsiz arka plan.
- Aynı cam kutunun art arda üç sahnede kullanılması.
- Emoji ile ekran yazısı (yazı tipinde yoktur, kutu □ çıkar).
- 3 sn'den uzun hiçbir şeyin değişmediği an.
- Rakamın birden fazla yazı boyutunda tekrarlanması.
- Vurgu renginin süs için kullanılması.
