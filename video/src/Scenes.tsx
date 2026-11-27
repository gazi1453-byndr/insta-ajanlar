import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {fitSize, sp, SOFT, tl} from './motion';
import {Bar, CountText, glass, Kinetic, Num, PAD, ZONE_BOTTOM, ZONE_TOP} from './parts';
import {Palette, Row, Scene} from './types';
import {Visual} from './Visuals';

type P = {s: Scene; p: Palette; period: string};
const W = 1080 - 2 * PAD;

const Zone: React.FC<{children: React.ReactNode; align?: 'center' | 'flex-start'}> = ({children, align = 'center'}) => (
  <AbsoluteFill style={{top: ZONE_TOP, height: ZONE_BOTTOM - ZONE_TOP, left: PAD, width: W, justifyContent: align}}>{children}</AbsoluteFill>
);

const AccentRule: React.FC<{p: Palette; delay?: number}> = ({p, delay = 0}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return <div style={{width: 150 * sp(f, fps, delay), height: 12, borderRadius: 6, background: p.accent, marginBottom: 36}} />;
};

const Body: React.FC<{text: string; p: Palette; delay: number; size?: number; center?: boolean}> = ({text, p, delay, size = 46, center}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!text) return null;
  const s = sp(f, fps, delay, SOFT);
  return (
    <div lang="tr" style={{fontFamily: 'Inter', fontWeight: 400, fontSize: size, lineHeight: 1.34, color: '#CBD5E1', marginTop: 34,
      opacity: s, transform: `translateY(${(1 - s) * 30}px)`, textAlign: center ? 'center' : 'left'}}>
      <CountText text={text} delay={delay} accent={p.accent} />
    </div>
  );
};

// ---------------------------------------------------------------- hook: tam ekran kinetik başlık
export const Hook: React.FC<P> = ({s, p}) => {
  const size = fitSize(s.baslik, W, s.visual ? 116 : 132, 76, s.visual ? 3 : 4, 0.56);
  return (
    <Zone>
      <AccentRule p={p} />
      <Kinetic text={s.baslik} accent={p.accent} stagger={3}
        style={{fontFamily: 'InterDisplay', fontWeight: 900, fontSize: size, lineHeight: 1.04, letterSpacing: -2, color: p.text}} />
      <Body text={s.metin} p={p} delay={14} />
      {s.visual && (
        <div style={{marginTop: 44}}>
          <Visual kind={s.visual} accent={p.accent} text={p.text} panel={p.panel} height={340} />
        </div>
      )}
    </Zone>
  );
};

// ---------------------------------------------------------------- cam kart
export const Card: React.FC<P> = ({s, p}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const k = sp(f, fps, 0, SOFT);
  const size = fitSize(s.baslik, W - 140, 96, 60, 4, 0.56);
  return (
    <Zone>
      <div style={{...glass(p.panel), padding: '64px 64px 64px 76px', position: 'relative', transform: `scale(${0.94 + 0.06 * k})`}}>
        <div style={{position: 'absolute', left: 0, top: 60, bottom: 60, width: 12, borderRadius: 6, background: p.accent}} />
        <Kinetic text={s.baslik} accent={p.accent} delay={2}
          style={{fontFamily: 'InterDisplay', fontWeight: 900, fontSize: size, lineHeight: 1.08, letterSpacing: -1, color: p.text}} />
        <Body text={s.metin} p={p} delay={12} size={46} />
      </div>
    </Zone>
  );
};

// ---------------------------------------------------------------- büyük ortalı ifade
export const Statement: React.FC<P> = ({s, p}) => {
  const size = fitSize(s.baslik, W, 108, 70, 4, 0.56);
  return (
    <Zone>
      <Kinetic text={s.baslik} accent={p.accent} stagger={4}
        style={{fontFamily: 'InterDisplay', fontWeight: 900, fontSize: size, lineHeight: 1.06, letterSpacing: -1.5, color: p.text, justifyContent: 'center', textAlign: 'center'}} />
      <Body text={s.metin} p={p} delay={14} size={42} center />
      {s.visual && (
        <div style={{marginTop: 40}}>
          <Visual kind={s.visual} accent={p.accent} text={p.text} panel={p.panel} height={280} />
        </div>
      )}
    </Zone>
  );
};

// ---------------------------------------------------------------- tek rakam spotu
export const Spot: React.FC<P> = ({s, p}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = sp(f, fps, 0.8 * fps);
  const str = tl(s.spotValue ?? 0);
  const size = Math.min(178, Math.floor((W / str.length) * 1.68));
  return (
    <Zone>
      <Kinetic text={s.baslik} accent={p.accent} style={{fontFamily: 'InterDisplay', fontWeight: 600, fontSize: 54, lineHeight: 1.15, color: p.text}} />
      <div style={{marginTop: 30, fontFamily: 'InterDisplay', fontWeight: 900, fontSize: size, letterSpacing: -3, color: p.accent,
        textShadow: `0 0 70px ${p.accent}66`, transform: `scale(${1 + 0.06 * (1 - pop)})`, transformOrigin: 'left center'}}>
        <Num value={s.spotValue ?? 0} delay={4} suffix={s.spotSuffix ?? ' TL'} />
      </div>
      <Body text={s.metin} p={p} delay={16} size={42} />
    </Zone>
  );
};

// ---------------------------------------------------------------- kırılım satırları
const Rows: React.FC<{rows: Row[]; p: Palette; delay: number; big?: boolean}> = ({rows, p, delay, big}) => {
  const vmax = Math.max(...rows.map((r) => r.value), 1);
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <div style={{display: 'flex', flexDirection: 'column', gap: big ? 34 : 24}}>
      {rows.map((r, i) => {
        const d = delay + i * 6;
        const k = sp(f, fps, d, SOFT);
        return (
          <div key={i} style={{opacity: k, transform: `translateX(${(1 - k) * -40}px)`}}>
            <div style={{display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 12, gap: 20}}>
              <div style={{fontFamily: 'Inter', fontWeight: 700, fontSize: big ? 38 : 34, color: p.text, flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                {r.label}{r.est ? ' *' : ''}
              </div>
              {r.pct !== undefined && (
                <div style={{fontFamily: 'Inter', fontWeight: 700, fontSize: 28, color: p.bg, background: r.color ?? p.accent, borderRadius: 999, padding: '4px 14px'}}>
                  %<Num value={r.pct} delay={d} suffix="" />
                </div>
              )}
              <div style={{fontFamily: 'InterDisplay', fontWeight: 900, fontSize: big ? 46 : 40, color: r.color ?? p.text}}>
                <Num value={r.value} delay={d} />
              </div>
            </div>
            <Bar ratio={r.value / vmax} delay={d} color={r.color ?? p.accent} height={big ? 30 : 24} />
          </div>
        );
      })}
    </div>
  );
};

export const Grafik: React.FC<P> = ({s, p, period}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const rows = s.rows ?? [];
  const tk = sp(f, fps, 10 + rows.length * 6, SOFT);
  return (
    <Zone>
      <Kinetic text={s.baslik} accent={p.accent} style={{fontFamily: 'InterDisplay', fontWeight: 900, fontSize: fitSize(s.baslik, W, 72, 52, 2), lineHeight: 1.08, color: p.text}} />
      <div style={{fontFamily: 'Inter', fontSize: 30, color: p.text2, margin: '14px 0 44px'}}>{period}</div>
      <Rows rows={rows} p={p} delay={6} big={rows.length <= 4} />
      {s.total !== undefined && (
        <div style={{...glass(p.panel), marginTop: 46, padding: '30px 40px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          border: `3px solid ${p.accent}`, opacity: tk, transform: `translateY(${(1 - tk) * 40}px)`}}>
          <div style={{fontFamily: 'Inter', fontWeight: 700, fontSize: 32, color: p.text2, maxWidth: 420}}>{s.totalLabel}</div>
          <div style={{fontFamily: 'InterDisplay', fontWeight: 900, fontSize: 66, color: p.accent}}>
            <Num value={s.total} delay={10 + rows.length * 6} />
          </div>
        </div>
      )}
    </Zone>
  );
};

// ---------------------------------------------------------------- imza sahnesi: GERÇEK MALİYET
export const Reveal: React.FC<P> = ({s, p}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const v = s.value ?? 0;
  const str = tl(v);
  const size = Math.min(170, Math.floor((W / str.length) * 1.68));
  const stamp = sp(f, fps, Math.round(0.8 * fps), {damping: 9, stiffness: 220, mass: 1});
  const maasK = sp(f, fps, Math.round(0.9 * fps), SOFT);
  return (
    <Zone>
      <div style={{fontFamily: 'Inter', fontWeight: 700, fontSize: 36, letterSpacing: 8, color: p.text2}}>{s.label}</div>
      <div style={{fontFamily: 'InterDisplay', fontWeight: 900, fontSize: size, letterSpacing: -4, color: p.accent, lineHeight: 1.1,
        textShadow: `0 0 80px ${p.accent}77`, transform: `scale(${f > 0.8 * fps ? 1 + 0.1 * (1 - stamp) : 1})`, transformOrigin: 'left center', margin: '10px 0 18px'}}>
        <Num value={v} />
      </div>
      {s.maas && (
        <div style={{alignSelf: 'flex-start', fontFamily: 'Inter', fontWeight: 700, fontSize: 38, color: p.text, background: 'rgba(255,255,255,0.08)',
          border: `2px solid ${p.accent}`, borderRadius: 999, padding: '12px 28px', opacity: maasK, transform: `translateY(${(1 - maasK) * 24}px)`}}>
          = {s.maas}
        </div>
      )}
      {s.rows && s.rows.length > 1 && (
        <div style={{marginTop: 50}}>
          <Rows rows={s.rows} p={p} delay={Math.round(1.0 * fps)} />
        </div>
      )}
    </Zone>
  );
};

// ---------------------------------------------------------------- son kare: kaydetmelik özet
export const Sonuc: React.FC<P> = ({s, p, period}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const rows = s.rows ?? [];
  const pulse = 1 + 0.04 * Math.sin((f / fps) * Math.PI * 2);
  const ck = sp(f, fps, 10 + rows.length * 5, SOFT);
  return (
    <Zone>
      <div style={{...glass(p.panel), padding: '50px 54px'}}>
        <div style={{fontFamily: 'Inter', fontWeight: 700, fontSize: 28, letterSpacing: 3, color: p.accent}}>ÖZET · KAYDET, LAZIM OLACAK</div>
        {(s.title ?? s.baslik) !== s.question && (
          <div lang="tr" style={{fontFamily: 'InterDisplay', fontWeight: 900, fontSize: fitSize(s.title ?? s.baslik, W - 110, 52, 38, 2), lineHeight: 1.1, color: p.text, margin: '16px 0 6px'}}>{s.title ?? s.baslik}</div>
        )}
        <div style={{fontFamily: 'Inter', fontSize: 26, color: p.text2, marginBottom: 22}}>{period}</div>
        {rows.map((r, i) => {
          const last = i === rows.length - 1;
          const k = sp(f, fps, 6 + i * 5, SOFT);
          return (
            <div key={i} style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '13px 0',
              borderTop: i ? '1px solid rgba(148,163,184,0.25)' : 'none', opacity: k, transform: `translateX(${(1 - k) * 50}px)`}}>
              <div style={{fontFamily: 'Inter', fontWeight: last ? 800 : 600, fontSize: last ? 38 : 32, color: last ? p.accent : p.text,
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 520}}>{r.label}{r.est ? ' *' : ''}</div>
              <div style={{fontFamily: 'InterDisplay', fontWeight: 900, fontSize: last ? 44 : 34, color: last ? p.accent : r.color ?? p.text}}>
                <Num value={r.value} delay={6 + i * 5} />
              </div>
            </div>
          );
        })}
        {s.maas && <div style={{fontFamily: 'Inter', fontWeight: 700, fontSize: 32, color: p.accent, marginTop: 14, opacity: ck}}>= {s.maas}</div>}
      </div>
      <div lang="tr" style={{fontFamily: 'InterDisplay', fontWeight: 900, fontSize: 48, lineHeight: 1.12, color: p.text, margin: '36px 0 22px', opacity: ck}}>
        {s.question}
      </div>
      {s.cta && (
        <div style={{alignSelf: 'flex-start', fontFamily: 'Inter', fontWeight: 800, fontSize: 32, color: p.bg, background: p.accent,
          borderRadius: 999, padding: '16px 34px', transform: `scale(${pulse * ck})`, transformOrigin: 'left center', boxShadow: `0 10px 40px ${p.accent}55`}}>
          {s.cta}
        </div>
      )}
    </Zone>
  );
};

export const SCENES: Record<Scene['kind'], React.FC<P>> = {
  hook: Hook,
  card: Card,
  statement: Statement,
  spot: Spot,
  grafik: Grafik,
  reveal: Reveal,
  sonuc: Sonuc,
};
