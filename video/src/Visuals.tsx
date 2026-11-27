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

// ---------------------------------------------------------------- yolda giden araba (gerçekçi sedan, yandan)
const Car: React.FC<V> = ({accent, text, height = 300}) => {
  const {f, fps, t} = useT();
  const arrive = sp(f, fps, 2, {damping: 15, stiffness: 120, mass: 1});
  const x = (1 - arrive) * -760;
  const bob = Math.sin(t * 9) * 1.2 * arrive; // süspansiyon: yalnız gövde salınır
  const roll = (x + t * 520) / 40; // tekerlek dönüşü (radyan)
  const dash = -(t * 520) % 80;
  const WY = 200; // tekerlek merkezi
  const wheel = (cx: number) => (
    <g transform={`translate(${cx} ${WY})`}>
      <circle r={41} fill="#0A0D13" />
      <circle r={41} fill="none" stroke="#1F2937" strokeWidth={3} />
      <circle r={35} fill="none" stroke="#111827" strokeWidth={6} />
      <circle r={28} fill="url(#car-rim)" />
      <circle r={20} fill="#1F2937" />
      <rect x={6} y={-22} width={13} height={18} rx={4} fill="#DC2626" />
      <g transform={`rotate(${(roll * 180) / Math.PI})`}>
        {[0, 72, 144, 216, 288].map((a) => (
          <path key={a} d="M-4 -6 L-6.5 -26 Q0 -28.5 6.5 -26 L4 -6 Z" fill="url(#car-spoke)" transform={`rotate(${a})`} />
        ))}
        <circle r={27} fill="none" stroke="#E5E7EB" strokeWidth={2.5} />
        <circle r={8} fill="#9CA3AF" stroke="#E5E7EB" strokeWidth={2} />
        {[0, 72, 144, 216, 288].map((a) => (
          <circle key={a} cx={0} cy={-4.5} r={1.4} fill="#374151" transform={`rotate(${a})`} />
        ))}
      </g>
    </g>
  );
  const body =
    'M54 198 Q44 196 44 184 L44 166 Q44 152 56 146 L78 136 Q96 128 126 125 L214 118 ' +
    'C238 112 262 84 300 70 Q326 61 372 60 L410 61 Q446 63 470 78 L520 110 ' +
    'Q560 116 612 124 Q644 130 654 146 Q660 158 658 176 Q656 196 640 198 ' +
    'L576 198 A56 56 0 0 0 464 198 L226 198 A56 56 0 0 0 114 198 Z';
  return (
    <svg viewBox="0 0 700 270" width="100%" height={height} style={{overflow: 'visible'}}>
      <defs>
        <linearGradient id="car-paint" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#FFFFFF" />
          <stop offset="0.28" stopColor="#E2E8F0" />
          <stop offset="0.55" stopColor="#B8C2D0" />
          <stop offset="0.62" stopColor="#F1F5F9" />
          <stop offset="1" stopColor="#64748B" />
        </linearGradient>
        <linearGradient id="car-glass" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#334155" />
          <stop offset="0.55" stopColor="#0F172A" />
          <stop offset="1" stopColor="#1E293B" />
        </linearGradient>
        <linearGradient id="car-glare" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#FFFFFF" stopOpacity={0} />
          <stop offset="0.5" stopColor="#FFFFFF" stopOpacity={0.28} />
          <stop offset="1" stopColor="#FFFFFF" stopOpacity={0} />
        </linearGradient>
        <radialGradient id="car-rim" cx="0.35" cy="0.3" r="0.8">
          <stop offset="0" stopColor="#F8FAFC" />
          <stop offset="0.6" stopColor="#94A3B8" />
          <stop offset="1" stopColor="#475569" />
        </radialGradient>
        <linearGradient id="car-spoke" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#CBD5E1" />
          <stop offset="0.5" stopColor="#F8FAFC" />
          <stop offset="1" stopColor="#94A3B8" />
        </linearGradient>
        <radialGradient id="car-beam" cx="0" cy="0.5" r="1">
          <stop offset="0" stopColor="#FEF9C3" stopOpacity={0.6} />
          <stop offset="1" stopColor="#FEF9C3" stopOpacity={0} />
        </radialGradient>
        <filter id="car-soft" x="-20%" y="-200%" width="140%" height="500%">
          <feGaussianBlur stdDeviation="6" />
        </filter>
        <clipPath id="car-clip"><path d={body} /></clipPath>
      </defs>
      {/* yol */}
      <line x1={0} y1={242} x2={700} y2={242} stroke="#ffffff22" strokeWidth={3} />
      <line x1={0} y1={242} x2={700} y2={242} stroke={accent} strokeOpacity={0.55} strokeWidth={4}
        strokeDasharray="40 40" strokeDashoffset={dash} />
      <g transform={`translate(${x} 0)`}>
        {/* hız çizgileri */}
        {[0, 1, 2].map((k) => (
          <rect key={k} x={-40 - k * 30 - ((t * 400 + k * 50) % 60)} y={110 + k * 28} width={70 + k * 20} height={5} rx={2.5}
            fill={text} opacity={0.25 * arrive} />
        ))}
        {/* zemin gölgesi */}
        <ellipse cx={350} cy={240} rx={300} ry={9} fill="#000" opacity={0.6} filter="url(#car-soft)" />
        <g transform={`translate(0 ${bob})`}>
          {/* çamurluk içleri */}
          <circle cx={170} cy={WY} r={50} fill="#05070C" />
          <circle cx={520} cy={WY} r={50} fill="#05070C" />
          {/* gövde */}
          <path d={body} fill="url(#car-paint)" />
          <g clipPath="url(#car-clip)">
            {/* alt marşpiye gölgesi + omuz parlaması */}
            <rect x={0} y={176} width={700} height={30} fill="#0F172A" opacity={0.35} />
            <path d="M60 150 Q330 136 650 142" fill="none" stroke="#FFFFFF" strokeOpacity={0.85} strokeWidth={3} />
            <path d="M120 170 Q330 162 600 166" fill="none" stroke="#475569" strokeOpacity={0.5} strokeWidth={2} />
          </g>
          {/* camlar */}
          <path d="M226 118 C248 110 270 88 302 76 Q328 68 360 67 L360 116 Z" fill="url(#car-glass)" />
          <path d="M372 67 L408 68 Q440 70 462 84 L500 112 L372 116 Z" fill="url(#car-glass)" />
          <path d="M250 116 L300 72 L330 70 L278 116 Z" fill="url(#car-glare)" />
          <path d="M392 116 L432 70 L452 76 L414 116 Z" fill="url(#car-glare)" />
          {/* kapı çizgileri, kollar, ayna */}
          <path d="M366 118 L364 192 M236 120 Q232 160 240 190 M500 116 Q503 132 497 144" fill="none" stroke="#334155" strokeOpacity={0.55} strokeWidth={2} />
          <rect x={300} y={132} width={30} height={7} rx={3.5} fill="#94A3B8" />
          <rect x={428} y={132} width={30} height={7} rx={3.5} fill="#94A3B8" />
          <path d="M488 104 Q500 96 512 100 L514 112 L494 114 Z" fill="#CBD5E1" stroke="#64748B" strokeWidth={1.5} />
          {/* farlar ve stop */}
          <path d="M622 134 Q644 134 652 146 L626 146 Z" fill="#F8FAFC" />
          <path d="M628 134 L700 104 L700 180 L628 146 Z" fill="url(#car-beam)" />
          <path d="M46 152 L66 146 L66 158 L46 162 Z" fill="#EF4444" />
          <ellipse cx={56} cy={154} rx={18} ry={8} fill="#EF4444" opacity={0.35} filter="url(#car-soft)" />
          {/* ön tampon hava girişi */}
          <path d="M606 182 L650 180" stroke="#1E293B" strokeWidth={5} strokeLinecap="round" />
        </g>
        {wheel(170)}
        {wheel(520)}
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
