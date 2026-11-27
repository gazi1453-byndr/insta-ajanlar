export type Palette = {bg: string; panel: string; accent: string; warn: string; text: string; text2: string};

export type Row = {label: string; value: number; pct?: number; est?: boolean; color?: string};

export type Word = {t: string; s: number; e: number};
export type Phrase = {s: number; e: number; words: Word[]};

export type Scene = {
  kind: 'hook' | 'card' | 'statement' | 'spot' | 'grafik' | 'reveal' | 'sonuc';
  baslik: string;
  metin: string;
  from: number; // kare
  frames: number; // kare
  visual?: string; // konu görseli: araba, benzin, ev, telefon, market, para
  // grafik
  mode?: 'breakdown' | 'compare';
  rows?: Row[];
  totalLabel?: string;
  total?: number;
  // reveal
  label?: string;
  value?: number;
  maas?: string;
  // spot
  spotValue?: number;
  spotSuffix?: string;
  // sonuc
  question?: string;
  cta?: string;
};

export type VideoProps = {
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  palette: Palette;
  brand: {name: string; no: number; label: string; handle: string};
  period: string;
  sources: string;
  scenes: Scene[];
  phrases: Phrase[];
};

export const defaultProps: VideoProps = {
  fps: 60,
  width: 1080,
  height: 1920,
  durationInFrames: 600,
  palette: {bg: '#0B1220', panel: '#18233A', accent: '#22C55E', warn: '#F43F5E', text: '#F8FAFC', text2: '#94A3B8'},
  brand: {name: 'GERÇEK MALİYET', no: 1, label: 'A MI B Mİ?', handle: 'gercek.maliyet'},
  period: '1 yıl · Kasım 2026 fiyatları',
  sources: 'Kaynak: örnek',
  scenes: [
    {kind: 'hook', baslik: 'Clio mu Egea mı? 1 yılın gerçek maliyeti', metin: '', from: 0, frames: 150},
    {kind: 'grafik', baslik: 'Yıllık kalem kalem', metin: '', from: 150, frames: 240, mode: 'breakdown', totalLabel: 'TOPLAM', total: 120000,
      rows: [{label: 'Yakıt', value: 60000, pct: 50}, {label: 'Kasko', value: 36000, pct: 30}, {label: 'Bakım', value: 24000, pct: 20}]},
    {kind: 'reveal', baslik: '', metin: '', from: 390, frames: 210, label: 'GERÇEK MALİYET', value: 120000, maas: 'Asgari ücretle ≈ 128 gün çalışma',
      rows: [{label: 'Yakıt', value: 60000, pct: 50}, {label: 'Kasko', value: 36000, pct: 30}, {label: 'Bakım', value: 24000, pct: 20}]},
  ],
  phrases: [],
};
