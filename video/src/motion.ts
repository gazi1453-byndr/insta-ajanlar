import {interpolate, spring, SpringConfig} from 'remotion';

// DESIGN_SYSTEM.md §5 — hareket sabitleri
export const SPRING: Partial<SpringConfig> = {damping: 14, stiffness: 180, mass: 1};
export const SOFT: Partial<SpringConfig> = {damping: 20, stiffness: 120, mass: 1};
export const TRANSITION_FRAMES = 14; // ~0.23 sn @60fps; yay 10. karede %90'a ulaşır
export const COUNT_SECONDS = 0.8;

export const sp = (frame: number, fps: number, delay = 0, config = SPRING) =>
  spring({frame: frame - delay, fps, config});

export const easeOutExpo = (t: number) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * Math.max(0, t)));

/** 0 → hedef sayaç ilerlemesi (0..1) */
export const countProgress = (frame: number, fps: number, delay = 0, seconds = COUNT_SECONDS) =>
  easeOutExpo(interpolate(frame - delay, [0, seconds * fps], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));

/** Türkçe para/sayı biçimi (Python designer.tl ile aynı): kuruş varsa 2 hane */
export const fmt = (x: number, decimals: number) =>
  x.toLocaleString('tr-TR', {minimumFractionDigits: decimals, maximumFractionDigits: decimals});

export const tl = (x: number, exact = true) => {
  const d = exact && Math.abs(x - Math.round(x)) >= 0.005 ? 2 : 0;
  return fmt(d ? x : Math.round(x), d) + ' TL';
};

/** Uzun metinde yazı boyutunu kutuya sığdır (yaklaşık karakter genişliği ile) */
export const fitSize = (text: string, maxWidth: number, max: number, min: number, lines = 3, charW = 0.56) => {
  for (let s = max; s > min; s -= 2) {
    const perLine = Math.floor(maxWidth / (s * charW));
    const words = text.split(/\s+/);
    let n = 1;
    let cur = 0;
    for (const w of words) {
      if (cur + w.length + (cur ? 1 : 0) > perLine) {
        n++;
        cur = w.length;
      } else cur += w.length + (cur ? 1 : 0);
    }
    if (n <= lines) return s;
  }
  return min;
};
