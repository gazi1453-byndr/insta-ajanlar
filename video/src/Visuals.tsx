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

// ---------------------------------------------------------------- yolda giden araba (aerodinamik C-segment sedan, yandan)
const Car: React.FC<V> = ({accent, text, height = 300}) => {
  const {f, fps, t} = useT();
  const arrive = sp(f, fps, 2, {damping: 15, stiffness: 120, mass: 1});
  const x = (1 - arrive) * -760;
  const bob = Math.sin(t * 9) * 1.1 * arrive; // süspansiyon: yalnız gövde salınır
  const roll = (x + t * 520) / 40; // tekerlek dönüşü (radyan)
  const dash = -(t * 520) % 80;
  const WY = 200; // tekerlek merkezi
  const wheel = (cx: number) => (
    <g transform={`translate(${cx} ${WY})`}>
      <circle r={42} fill="#07090E" />
      <circle r={42} fill="none" stroke="#1F2937" strokeWidth={2.5} />
      <circle r={36} fill="none" stroke="#0F141C" strokeWidth={5} />
      <circle r={31} fill="#1E293B" />
      <circle r={20} fill="#334155" />
      <rect x={7} y={-21} width={12} height={17} rx={4} fill="#B91C1C" />
      <g transform={`rotate(${(roll * 180) / Math.PI})`}>
        {[0, 72, 144, 216, 288].map((a) => (
          <g key={a} transform={`rotate(${a})`}>
            <path d="M-1.5 -8 L-7 -29 L-3.5 -29.5 L1 -8 Z" fill="url(#car-spoke)" />
            <path d="M1.5 -8 L7 -29 L3.5 -29.5 L-1 -8 Z" fill="url(#car-spoke)" opacity={0.85} />
          </g>
        ))}
        <circle r={30} fill="none" stroke="url(#car-lip)" strokeWidth={3} />
        <circle r={8.5} fill="#475569" stroke="#CBD5E1" strokeWidth={2} />
        <circle r={3} fill="#0F172A" />
      </g>
    </g>
  );
  const body =
    'M58 196 Q46 194 46 182 L46 164 Q46 150 58 146 L98 138 Q124 132 152 126 ' +
    'C200 112 252 78 322 64 Q372 54 420 58 C454 62 480 80 512 104 L560 112 ' +
    'Q620 120 648 134 Q664 142 664 160 L662 178 Q660 196 642 196 ' +
    'L581 196 A56 56 0 0 0 469 196 L231 196 A56 56 0 0 0 119 196 Z';
  const glass = 'M196 122 C232 108 268 84 322 72 Q370 63 416 66 C446 70 468 84 494 106 L494 110 L196 124 Z';
  return (
    <svg viewBox="0 0 700 270" width="100%" height={height} style={{overflow: 'visible'}}>
      <defs>
        <linearGradient id="car-paint" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#CBD5E1" />
          <stop offset="0.38" stopColor="#94A3B8" />
          <stop offset="0.47" stopColor="#E2E8F0" />
          <stop offset="0.56" stopColor="#94A3B8" />
          <stop offset="1" stopColor="#475569" />
        </linearGradient>
        <linearGradient id="car-glass" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#1E293B" />
          <stop offset="0.6" stopColor="#020617" />
          <stop offset="1" stopColor="#0F172A" />
        </linearGradient>
        <linearGradient id="car-glare" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#FFFFFF" stopOpacity={0} />
          <stop offset="0.5" stopColor="#FFFFFF" stopOpacity={0.22} />
          <stop offset="1" stopColor="#FFFFFF" stopOpacity={0} />
        </linearGradient>
        <linearGradient id="car-spoke" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#94A3B8" />
          <stop offset="0.5" stopColor="#F1F5F9" />
          <stop offset="1" stopColor="#64748B" />
        </linearGradient>
        <linearGradient id="car-lip" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#F8FAFC" />
          <stop offset="1" stopColor="#64748B" />
        </linearGradient>
        <linearGradient id="car-beam" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#E0F2FE" stopOpacity={0.75} />
          <stop offset="0.35" stopColor="#7DD3FC" stopOpacity={0.3} />
          <stop offset="1" stopColor="#7DD3FC" stopOpacity={0} />
        </linearGradient>
        <filter id="car-soft" x="-20%" y="-200%" width="140%" height="500%">
          <feGaussianBlur stdDeviation="6" />
        </filter>
        <filter id="car-glow" x="-50%" y="-300%" width="200%" height="700%">
          <feGaussianBlur stdDeviation="3" />
        </filter>
        <clipPath id="car-clip"><path d={body} /></clipPath>
      </defs>
      {/* yol */}
      <line x1={0} y1={242} x2={700} y2={242} stroke="#ffffff22" strokeWidth={3} />
      <line x1={0} y1={242} x2={700} y2={242} stroke={accent} strokeOpacity={0.55} strokeWidth={4}
        strokeDasharray="40 40" strokeDashoffset={dash} />
      <g transform={`translate(${x} 0)`}>
        {/* hareket çizgileri */}
        {[0, 1, 2].map((k) => (
          <rect key={k} x={-40 - k * 30 - ((t * 400 + k * 50) % 60)} y={110 + k * 28} width={70 + k * 20} height={4} rx={2}
            fill={text} opacity={0.22 * arrive} />
        ))}
        {/* yumuşak zemin gölgesi */}
        <ellipse cx={355} cy={240} rx={312} ry={10} fill="#000" opacity={0.65} filter="url(#car-soft)" />
        {/* ön LED huzmesi (buz mavisi) */}
        <path d="M656 140 L720 112 L720 176 L656 146 Z" fill="url(#car-beam)" opacity={arrive} />
        <g transform={`translate(0 ${bob})`}>
          {/* çamurluk içleri */}
          <circle cx={175} cy={WY} r={50} fill="#04060A" />
          <circle cx={525} cy={WY} r={50} fill="#04060A" />
          {/* gövde */}
          <path d={body} fill="url(#car-paint)" />
          <g clipPath="url(#car-clip)">
            <rect x={0} y={178} width={700} height={30} fill="#0F172A" opacity={0.45} />
            <path d="M58 154 Q350 138 652 146" fill="none" stroke="#F8FAFC" strokeOpacity={0.75} strokeWidth={2.5} />
            <path d="M240 172 Q360 165 466 168" fill="none" stroke="#1E293B" strokeOpacity={0.5} strokeWidth={2} />
            <path d="M150 128 Q330 96 500 108" fill="none" stroke="#F8FAFC" strokeOpacity={0.35} strokeWidth={2} />
          </g>
          {/* koyu camlar + siyah direkler */}
          <path d={glass} fill="url(#car-glass)" stroke="#0B1220" strokeWidth={3} strokeLinejoin="round" />
          <path d="M372 64 L386 65 L388 112 L372 113 Z" fill="#0B1220" />
          <path d="M262 88 L272 84 L276 119 L264 120 Z" fill="#0B1220" />
          <path d="M296 118 L340 70 L362 67 L318 117 Z" fill="url(#car-glare)" />
          <path d="M408 113 L438 70 L456 76 L428 112 Z" fill="url(#car-glare)" />
          {/* kapı çizgileri, gömme kollar, ayna */}
          <path d="M380 114 L378 184 M262 121 Q250 150 246 184 M494 110 Q499 128 494 142" fill="none"
            stroke="#1E293B" strokeOpacity={0.55} strokeWidth={2} />
          <rect x={316} y={130} width={28} height={5} rx={2.5} fill="#334155" />
          <rect x={440} y={128} width={28} height={5} rx={2.5} fill="#334155" />
          <path d="M486 100 Q500 92 514 96 L516 108 L494 110 Z" fill="#1E293B" stroke="#64748B" strokeWidth={1.2} />
          {/* ön LED far: keskin buz mavisi çizgi */}
          <path d="M606 130 L656 140 L652 145 L604 135 Z" fill="#7DD3FC" filter="url(#car-glow)" />
          <path d="M606 130 L656 140 L652 145 L604 135 Z" fill="#E0F2FE" />
          {/* arka stop: ince kırmızı LED çizgisi */}
          <path d="M50 151 L96 141" stroke="#EF4444" strokeWidth={6} strokeLinecap="round" filter="url(#car-glow)" />
          <path d="M50 151 L96 141" stroke="#FCA5A5" strokeWidth={2.5} strokeLinecap="round" />
          {/* alt ızgara ve difüzör */}
          <path d="M612 178 L656 174" stroke="#0F172A" strokeWidth={5} strokeLinecap="round" />
          <path d="M52 186 L92 186" stroke="#0F172A" strokeWidth={4} strokeLinecap="round" />
        </g>
        {wheel(175)}
        {wheel(525)}
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
