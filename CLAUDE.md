# insta-ajanlar — proje kuralları

## Görsel ve video (ZORUNLU)

- Üretilen **her görsel, kapak, carousel ve video grafiği** [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) kurallarına uyar:
  - Inter tipografi hiyerarşisi
  - 60-30-10 palet
  - Yerleşim bölgeleri
  - Yay ve sayaç hareket değerleri
  - Ses kuralları
- Kuralı değiştirmek gerekirse önce `DESIGN_SYSTEM.md` güncellenir, sonra kod.
- Video motoru `video/` klasöründeki Remotion projesidir. Sahne bileşenleri `video/src/Scenes.tsx`, hareket sabitleri `video/src/motion.ts` içindedir. Python tarafı (`agents/video.py`) bu motora sahne verisini ve kelime zamanlarını verir. Node yoksa Pillow yedek motoru (`agents/motion.py`) çalışır.
- Yeni görsel bileşen eklerken iki motor da tasarım sistemine uygun tutulur.

## Araçlar

- Video analiz: `python tools/video_analiz.py <dosya|link>`. MCP sunucusu `video-analiz` (`.mcp.json`) aynı işi yapar.
- Telifsiz müzik ve efekt üretimi: `python tools/ses_uret.py`.
- `GEMINI_API_KEY` yerelde `.env` dosyasında tutulur (git'e girmez). Kaydetmek için: `python tools/anahtar_kaydet.py`.

## Güvenlik

- Anahtar ve token asla koda ya da commit'e girmez. GitHub'da Secrets kullanılır, yerelde `.env`.
