import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {countProgress, fmt, sp} from './motion';

export const PAD = 72;
export const ZONE_TOP = 250;
export const ZONE_BOTTOM = 1250; // altında karaoke altyazı bölgesi

const NUM_RE = /(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?(\s*(?:TL|lira))|%\s?(\d+)(?:,(\d+))?/g;

/** Metindeki TL ve % tutarlarını 0'dan hedefe sayarak, vurgu renginde gösterir. */
export const CountText: React.FC<{text: string; delay?: number; accent: string}> = ({text, delay = 0, accent}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const k = countProgress(f, fps, delay);
  const re = new RegExp(NUM_RE.source, 'g');
  const out: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const num = {color: accent, fontVariantNumeric: 'tabular-nums' as const};
    if (m[4] !== undefined) {
      const d = m[5] ? m[5].length : 0;
      const v = parseFloat(m[4] + (m[5] ? '.' + m[5] : ''));
      out.push(<span key={i++} style={num}>%{fmt(v * k, d)}</span>);
    } else {
      const d = m[2] ? 2 : 0;
      const v = parseInt(m[1].replace(/\./g, ''), 10) + (m[2] ? parseInt(m[2].padEnd(2, '0'), 10) / 100 : 0);
      out.push(<span key={i++} style={num}>{fmt(v * k, d)}{m[3]}</span>);
    }
    last = re.lastIndex;
  }
  if (last < text.length) out.push(text.slice(last));
  return <>{out}</>;
};

/** Kinetik başlık: kelimeler sırayla aşağıdan yaylı yükselir. Rakamlar sayaçla gelir. */
export const Kinetic: React.FC<{text: string; delay?: number; stagger?: number; accent: string; style?: React.CSSProperties}> = ({
  text,
  delay = 0,
  stagger = 3,
  accent,
  style,
}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const tokens = text.replace(/(\d)\s+(TL|lira)\b/g, '$1 $2').split(/\s+/).filter(Boolean);
  return (
    <div lang="tr" style={{display: 'flex', flexWrap: 'wrap', columnGap: '0.26em', ...style}}>
      {tokens.map((w, i) => {
        const s = sp(f, fps, delay + i * stagger);
        return (
          <span key={i} style={{display: 'inline-block', transform: `translateY(${(1 - s) * 60}px)`, opacity: Math.min(1, s * 1.4)}}>
            <CountText text={w} delay={delay + i * stagger} accent={accent} />
          </span>
        );
      })}
    </div>
  );
};

export const glass = (panel: string): React.CSSProperties => ({
  background: `linear-gradient(180deg, ${panel}E6, ${panel}C7)`,
  border: '1.5px solid rgba(255,255,255,0.09)',
  borderRadius: 44,
  boxShadow: '0 30px 80px rgba(0,0,0,0.45), inset 0 1.5px 0 rgba(255,255,255,0.08)',
  backdropFilter: 'blur(24px)',
});

/** Yatay bar: yaylı büyür. */
export const Bar: React.FC<{ratio: number; delay: number; color: string; height?: number}> = ({ratio, delay, color, height = 26}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = sp(f, fps, delay);
  return (
    <div style={{height, borderRadius: height / 2, background: 'rgba(255,255,255,0.07)', overflow: 'hidden'}}>
      <div
        style={{
          width: `${Math.max(1.5, Math.min(100, ratio * 100 * s))}%`,
          height: '100%',
          borderRadius: height / 2,
          background: `linear-gradient(90deg, ${color}, ${color}CC)`,
          boxShadow: `0 0 24px ${color}55`,
        }}
      />
    </div>
  );
};

export const Num: React.FC<{value: number; delay?: number; suffix?: string; style?: React.CSSProperties}> = ({
  value,
  delay = 0,
  suffix = ' TL',
  style,
}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const k = countProgress(f, fps, delay);
  const d = Math.abs(value - Math.round(value)) >= 0.005 ? 2 : 0;
  return <span style={{fontVariantNumeric: 'tabular-nums', ...style}}>{fmt(d ? value * k : Math.round(value * k), d)}{suffix}</span>;
};
