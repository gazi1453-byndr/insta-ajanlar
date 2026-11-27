import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {sp, SOFT} from './motion';

/** Konuya özel hareketli görseller (vektör, telifsiz). DESIGN_SYSTEM.md §4: vurgu rengi yalnızca anlam taşıyan yerde. */
type V = {accent: string; text: string; panel: string; height?: number};

const useT = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return {f, fps, t: f / fps};
};

// ---------------------------------------------------------------- yolda giden araba
const Car: React.FC<V> = ({accent, text, panel, height = 300}) => {
  const {f, fps, t} = useT();
  const arrive = sp(f, fps, 2, {damping: 15, stiffness: 120, mass: 1});
  const x = (1 - arrive) * -760;
  const bob = Math.sin(t * 9) * 1.6 * arrive;
  const roll = (x + t * 520) / 42; // tekerlek dönüşü (radyan)
  const dash = -(t * 520) % 80;
  const wheel = (cx: number) => (
    <g transform={`translate(${cx} 192)`}>
      <circle r={44} fill="#0B1220" />
      <circle r={30} fill="#1E293B" stroke="#CBD5E1" strokeWidth={4} />
      <g transform={`rotate(${(roll * 180) / Math.PI})`}>
        {[0, 60, 120].map((a) => (
          <rect key={a} x={-3} y={-28} width={6} height={56} rx={3} fill="#CBD5E1" transform={`rotate(${a})`} />
        ))}
      </g>
      <circle r={7} fill={accent} />
    </g>
  );
  return (
    <svg viewBox="0 0 700 270" width="100%" height={height} style={{overflow: 'visible'}}>
      <defs>
        <linearGradient id="carBody" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={text} />
          <stop offset="1" stopColor="#CBD5E1" />
        </linearGradient>
        <radialGradient id="beam" cx="0" cy="0.5" r="1">
          <stop offset="0" stopColor="#FEF9C3" stopOpacity={0.55} />
          <stop offset="1" stopColor="#FEF9C3" stopOpacity={0} />
        </radialGradient>
      </defs>
      <line x1={0} y1={242} x2={700} y2={242} stroke="#ffffff22" strokeWidth={3} />
      <line x1={0} y1={242} x2={700} y2={242} stroke={accent} strokeOpacity={0.55} strokeWidth={4}
        strokeDasharray="40 40" strokeDashoffset={dash} />
      <g transform={`translate(${x} ${bob})`}>
        {[0, 1, 2].map((k) => (
          <rect key={k} x={-40 - k * 30 - ((t * 400 + k * 50) % 60)} y={110 + k * 28} width={70 + k * 20} height={5} rx={2.5}
            fill={text} opacity={0.25 * arrive} />
        ))}
        <ellipse cx={330} cy={236} rx={300} ry={10} fill="#000" opacity={0.35} />
        <path d="M40 172 L72 122 Q92 96 132 93 L252 89 Q300 58 362 56 L470 58 Q522 61 562 108 L606 120 Q632 127 632 150 L632 180 Q632 192 619 192 L40 192 Q26 192 26 180 Z"
          fill="url(#carBody)" />
        <path d="M268 92 Q308 66 362 64 L412 64 L418 108 L262 110 Z" fill={panel} />
        <path d="M430 64 L468 66 Q508 70 540 106 L436 108 Z" fill={panel} />
        <rect x={60} y={140} width={560} height={9} rx={4.5} fill={accent} />
        <circle cx={620} cy={138} r={9} fill="#FEF9C3" />
        <path d="M628 130 L700 100 L700 176 L628 146 Z" fill="url(#beam)" />
        {wheel(162)}
        {wheel(512)}
      </g>
    </svg>
  );
};

// ---------------------------------------------------------------- akaryakıt pompası
const Pump: React.FC<V> = ({accent, text, panel, height = 300}) => {
  const {f, fps, t} = useT();
  const k = sp(f, fps, 2, SOFT);
  const liters = Math.min(50, t * 14);
  return (
    <svg viewBox="0 0 520 300" width="100%" height={height}>
      <g transform={`translate(${(1 - k) * -60} 0)`} opacity={k}>
        <rect x={120} y={20} width={190} height={260} rx={26} fill={panel} stroke="#ffffff22" strokeWidth={3} />
        <rect x={142} y={44} width={146} height={70} rx={12} fill="#0B1220" />
        <text x={215} y={92} textAnchor="middle" fontFamily="InterDisplay" fontWeight={900} fontSize={38} fill={accent}
          style={{fontVariantNumeric: 'tabular-nums'}}>{liters.toFixed(1)} L</text>
        <rect x={142} y={134} width={146} height={14} rx={7} fill="#ffffff14" />
        <rect x={142} y={134} width={146 * (liters / 50)} height={14} rx={7} fill={accent} />
        <path d="M310 70 Q380 70 380 140 L380 200 Q380 220 400 220 L420 220" fill="none" stroke={text} strokeWidth={10} strokeLinecap="round" />
        <path d="M410 206 L470 196 L476 214 L420 236 Z" fill={text} />
        {[0, 1, 2].map((i) => {
          const p = ((t * 1.6 + i / 3) % 1);
          return <circle key={i} cx={474} cy={226 + p * 60} r={7 * (1 - p * 0.4)} fill={accent} opacity={1 - p} />;
        })}
      </g>
    </svg>
  );
};

// ---------------------------------------------------------------- ev (çizilerek gelir, ışıklar yanar)
const House: React.FC<V> = ({accent, text, height = 300}) => {
  const {f, fps} = useT();
  const draw = sp(f, fps, 0, SOFT);
  const light = (d: number) => sp(f, fps, 18 + d, SOFT);
  const L = 1800;
  return (
    <svg viewBox="0 0 520 300" width="100%" height={height}>
      <path d="M80 140 L260 30 L440 140 L440 280 L80 280 Z M210 280 L210 200 L310 200 L310 280" fill="none" stroke={text}
        strokeWidth={8} strokeLinejoin="round" strokeDasharray={L} strokeDashoffset={L * (1 - draw)} />
      {[[120, 160], [350, 160]].map(([x, y], i) => (
        <rect key={i} x={x} y={y} width={56} height={48} rx={6} fill={accent} opacity={light(i * 6)}
          style={{filter: `drop-shadow(0 0 18px ${accent})`}} />
      ))}
      <rect x={340} y={58} width={34} height={60} fill={text} opacity={draw} />
    </svg>
  );
};

// ---------------------------------------------------------------- telefon (bildirimler düşer)
const Phone: React.FC<V> = ({accent, text, panel, height = 300}) => {
  const {f, fps} = useT();
  const k = sp(f, fps, 0, SOFT);
  return (
    <svg viewBox="0 0 520 300" width="100%" height={height}>
      <g transform={`translate(0 ${(1 - k) * 80})`} opacity={k}>
        <rect x={190} y={10} width={150} height={290} rx={30} fill={panel} stroke={text} strokeWidth={6} />
        <rect x={238} y={22} width={54} height={10} rx={5} fill="#0B1220" />
        {[0, 1, 2].map((i) => {
          const s = sp(f, fps, 10 + i * 9);
          return (
            <g key={i} transform={`translate(${(1 - s) * 120} 0)`} opacity={s}>
              <rect x={204} y={60 + i * 62} width={122} height={48} rx={12} fill={i === 0 ? accent : '#ffffff1f'} />
              <rect x={216} y={72 + i * 62} width={70} height={8} rx={4} fill={i === 0 ? '#0B1220' : text} opacity={0.8} />
              <rect x={216} y={88 + i * 62} width={46} height={8} rx={4} fill={i === 0 ? '#0B1220' : text} opacity={0.5} />
            </g>
          );
        })}
      </g>
    </svg>
  );
};

// ---------------------------------------------------------------- market arabası
const Cart: React.FC<V> = ({accent, text, height = 300}) => {
  const {f, fps, t} = useT();
  const k = sp(f, fps, 2, {damping: 16, stiffness: 120, mass: 1});
  const x = (1 - k) * -520;
  return (
    <svg viewBox="0 0 520 300" width="100%" height={height}>
      <line x1={0} y1={286} x2={520} y2={286} stroke="#ffffff22" strokeWidth={3} />
      <g transform={`translate(${x} 0)`}>
        <path d="M70 60 L120 60 L160 210 L400 210 L440 100 L140 100" fill="none" stroke={text} strokeWidth={10} strokeLinejoin="round" strokeLinecap="round" />
        {[0, 1, 2, 3].map((i) => {
          const s = sp(f, fps, 14 + i * 5);
          return <rect key={i} x={170 + i * 55} y={110 - (1 - s) * 140} width={44} height={88} rx={8} fill={i % 2 ? '#CBD5E1' : accent} opacity={s} />;
        })}
        {[190, 370].map((cx) => (
          <g key={cx} transform={`translate(${cx} 252) rotate(${(t * 400 + x) % 360})`}>
            <circle r={22} fill="#0B1220" stroke={text} strokeWidth={6} />
            <rect x={-2} y={-18} width={4} height={36} fill={text} />
          </g>
        ))}
      </g>
    </svg>
  );
};

// ---------------------------------------------------------------- para (madeni paralar yağar, kule yükselir)
const Coins: React.FC<V> = ({accent, text, height = 300}) => {
  const {f, fps} = useT();
  const stacks = [5, 8, 11];
  return (
    <svg viewBox="0 0 520 300" width="100%" height={height}>
      {stacks.map((n, si) => (
        <g key={si} transform={`translate(${130 + si * 130} 0)`}>
          {Array.from({length: n}, (_, i) => {
            const s = sp(f, fps, si * 4 + i * 2, {damping: 11, stiffness: 200, mass: 1});
            const y = 270 - i * 18 - (1 - s) * 300;
            return (
              <g key={i} opacity={Math.min(1, s * 2)}>
                <ellipse cx={0} cy={y + 8} rx={52} ry={14} fill="#15803D" />
                <ellipse cx={0} cy={y} rx={52} ry={14} fill={i === n - 1 ? accent : '#86EFAC'} stroke={text} strokeOpacity={0.3} />
              </g>
            );
          })}
        </g>
      ))}
    </svg>
  );
};

export const VISUALS: Record<string, React.FC<V>> = {
  araba: Car,
  benzin: Pump,
  ev: House,
  telefon: Phone,
  market: Cart,
  para: Coins,
};

export const Visual: React.FC<V & {kind?: string}> = ({kind, ...p}) => {
  const C = (kind && VISUALS[kind]) || null;
  return C ? <C {...p} /> : null;
};
