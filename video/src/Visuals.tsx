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

// ---------------------------------------------------------------- yolda giden araba (sarı coupé-SUV, yandan; logosuz vektör)
const Car: React.FC<V> = ({accent, text, height = 300}) => {
  const {f, fps, t} = useT();
  const arrive = sp(f, fps, 2, {damping: 15, stiffness: 120, mass: 1});
  const x = (1 - arrive) * -760;
  const bob = Math.sin(t * 9) * 1.1 * arrive; // süspansiyon: yalnız gövde salınır
  const roll = (x + t * 520) / 44; // tekerlek dönüşü (radyan)
  const dash = -(t * 520) % 80;
  const WY = 196; // tekerlek merkezi
  const wheel = (cx: number) => (
    <g transform={`translate(${cx} ${WY})`}>
      <circle r={46} fill="#07090E" />
      <circle r={46} fill="none" stroke="#1F2937" strokeWidth={2.5} />
      <circle r={39} fill="none" stroke="#0F141C" strokeWidth={4} />
      <circle r={35} fill="#111827" />
      <circle r={23} fill="#1F2937" />
      <rect x={8} y={-24} width={13} height={19} rx={4} fill="#FACC15" />
      <g transform={`rotate(${(roll * 180) / Math.PI})`}>
        {[0, 72, 144, 216, 288].map((a) => (
          <g key={a} transform={`rotate(${a})`}>
            <path d="M-2 -9 L-9 -33 L-4 -34 L1.5 -9 Z" fill="url(#car-spoke)" />
            <path d="M2 -9 L9 -33 L4 -34 L-1.5 -9 Z" fill="url(#car-spoke)" opacity={0.8} />
          </g>
        ))}
        <circle r={34} fill="none" stroke="url(#car-lip)" strokeWidth={2.5} />
        <circle r={9} fill="#374151" stroke="#9CA3AF" strokeWidth={2} />
        <circle r={3.2} fill="#0B0F17" />
      </g>
    </g>
  );
  const body =
    'M60 186 Q44 184 44 168 L46 142 Q48 126 64 120 L110 112 Q140 104 170 98 ' +
    'C220 84 270 58 340 50 Q400 44 450 50 C490 56 515 76 545 98 L600 108 ' +
    'Q650 116 668 132 Q680 142 678 160 L676 180 Q674 194 656 194 ' +
    'L590 194 A60 60 0 0 0 470 194 L240 194 A60 60 0 0 0 120 194 Z';
  const glass = 'M204 100 C246 84 284 62 342 56 Q400 50 446 54 C480 60 500 76 526 96 L526 100 L204 108 Z';
  return (
    <svg viewBox="0 0 700 270" width="100%" height={height} style={{overflow: 'visible'}}>
      <defs>
        <linearGradient id="car-paint" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#FEF08A" />
          <stop offset="0.3" stopColor="#FACC15" />
          <stop offset="0.48" stopColor="#FDE047" />
          <stop offset="0.58" stopColor="#EAB308" />
          <stop offset="1" stopColor="#A16207" />
        </linearGradient>
        <linearGradient id="car-glass" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#334155" />
          <stop offset="0.55" stopColor="#020617" />
          <stop offset="1" stopColor="#0F172A" />
        </linearGradient>
        <linearGradient id="car-glare" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#FFFFFF" stopOpacity={0} />
          <stop offset="0.5" stopColor="#FFFFFF" stopOpacity={0.2} />
          <stop offset="1" stopColor="#FFFFFF" stopOpacity={0} />
        </linearGradient>
        <linearGradient id="car-spoke" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#4B5563" />
          <stop offset="0.5" stopColor="#9CA3AF" />
          <stop offset="1" stopColor="#374151" />
        </linearGradient>
        <linearGradient id="car-lip" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#D1D5DB" />
          <stop offset="1" stopColor="#374151" />
        </linearGradient>
        <linearGradient id="car-beam" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#F0F9FF" stopOpacity={0.75} />
          <stop offset="0.35" stopColor="#BAE6FD" stopOpacity={0.3} />
          <stop offset="1" stopColor="#BAE6FD" stopOpacity={0} />
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
          <rect key={k} x={-40 - k * 30 - ((t * 400 + k * 50) % 60)} y={100 + k * 28} width={70 + k * 20} height={4} rx={2}
            fill={text} opacity={0.22 * arrive} />
        ))}
        {/* yumuşak zemin gölgesi */}
        <ellipse cx={360} cy={240} rx={318} ry={10} fill="#000" opacity={0.65} filter="url(#car-soft)" />
        {/* ön LED huzmesi */}
        <path d="M672 132 L730 104 L730 170 L672 140 Z" fill="url(#car-beam)" opacity={arrive} />
        <g transform={`translate(0 ${bob})`}>
          {/* çamurluk içleri */}
          <circle cx={180} cy={WY} r={54} fill="#04060A" />
          <circle cx={530} cy={WY} r={54} fill="#04060A" />
          {/* gövde */}
          <path d={body} fill="url(#car-paint)" />
          <g clipPath="url(#car-clip)">
            {/* siyah alt kaplama (marşpiye + tamponlar) */}
            <path d="M0 172 L700 166 L700 210 L0 210 Z" fill="#0B0F17" />
            <path d="M0 172 L700 166" stroke="#FDE047" strokeOpacity={0.35} strokeWidth={1.5} />
            {/* omuz ve gövde kırımları */}
            <path d="M64 136 Q360 118 668 132" fill="none" stroke="#FFFBEB" strokeOpacity={0.8} strokeWidth={2.5} />
            <path d="M250 158 Q370 150 470 152" fill="none" stroke="#854D0E" strokeOpacity={0.55} strokeWidth={2} />
            <path d="M170 104 Q350 80 540 100" fill="none" stroke="#FFFBEB" strokeOpacity={0.4} strokeWidth={2} />
          </g>
          {/* siyah çamurluk kavisleri */}
          <path d="M112 194 A68 68 0 0 1 248 194" fill="none" stroke="#0B0F17" strokeWidth={12} />
          <path d="M462 194 A68 68 0 0 1 598 194" fill="none" stroke="#0B0F17" strokeWidth={12} />
          {/* koyu camlar + siyah direkler */}
          <path d={glass} fill="url(#car-glass)" stroke="#0B0F17" strokeWidth={4} strokeLinejoin="round" />
          <path d="M392 50 L406 51 L408 104 L392 105 Z" fill="#0B0F17" />
          <path d="M276 70 L286 66 L292 106 L280 107 Z" fill="#0B0F17" />
          <path d="M310 106 L356 58 L378 55 L332 105 Z" fill="url(#car-glare)" />
          <path d="M426 103 L458 58 L476 64 L446 102 Z" fill="url(#car-glare)" />
          {/* kapı çizgileri, kollar, siyah ayna */}
          <path d="M400 106 L398 168 M282 108 Q272 140 270 168 M526 100 Q532 118 526 136" fill="none"
            stroke="#713F12" strokeOpacity={0.55} strokeWidth={2} />
          <rect x={330} y={118} width={30} height={6} rx={3} fill="#A16207" />
          <rect x={458} y={116} width={30} height={6} rx={3} fill="#A16207" />
          <path d="M516 86 Q532 78 548 82 L550 96 L524 98 Z" fill="#0B0F17" stroke="#374151" strokeWidth={1.2} />
          {/* ön LED far: keskin beyaz çizgi */}
          <path d="M616 116 L670 128 L666 134 L612 122 Z" fill="#BAE6FD" filter="url(#car-glow)" />
          <path d="M616 116 L670 128 L666 134 L612 122 Z" fill="#F8FAFC" />
          {/* arka stop: ince kırmızı LED */}
          <path d="M48 140 L104 126" stroke="#EF4444" strokeWidth={6} strokeLinecap="round" filter="url(#car-glow)" />
          <path d="M48 140 L104 126" stroke="#FCA5A5" strokeWidth={2.5} strokeLinecap="round" />
          {/* ön hava girişi */}
          <path d="M626 178 L668 174" stroke="#FACC15" strokeOpacity={0.6} strokeWidth={3} strokeLinecap="round" />
        </g>
        {wheel(180)}
        {wheel(530)}
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

// ---------------------------------------------------------------- take-away kahve + öğle yemeği tabağı
const Coffee: React.FC<V> = ({accent, text, height = 300}) => {
  const {f, fps, t} = useT();
  const drop = sp(f, fps, 2, {damping: 13, stiffness: 160, mass: 1});
  const slide = sp(f, fps, 8, {damping: 16, stiffness: 120, mass: 1});
  const cupY = (1 - drop) * -260;
  const plateX = (1 - slide) * 520;
  const steam = (i: number) => {
    const p = (t * 0.55 + i / 3) % 1;
    const sway = Math.sin(t * 2.4 + i * 2) * 8;
    return (
      <path key={i} d={`M${178 + i * 22} 52 c ${-14 + sway} -18, ${14 + sway} -30, 0 -50 c ${-12 + sway} -16, ${10 + sway} -28, 0 -44`}
        fill="none" stroke={text} strokeWidth={5} strokeLinecap="round"
        opacity={drop * 0.5 * Math.sin(Math.PI * p)} transform={`translate(0 ${-p * 26})`} />
    );
  };
  return (
    <svg viewBox="0 0 700 300" width="100%" height={height} style={{overflow: 'visible'}}>
      <defs>
        <linearGradient id="cf-cup" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#CBD5E1" />
          <stop offset="0.35" stopColor="#F8FAFC" />
          <stop offset="1" stopColor="#94A3B8" />
        </linearGradient>
        <linearGradient id="cf-lid" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#334155" />
          <stop offset="1" stopColor="#0F172A" />
        </linearGradient>
        <radialGradient id="cf-plate" cx="0.5" cy="0.4" r="0.6">
          <stop offset="0" stopColor="#F8FAFC" />
          <stop offset="0.75" stopColor="#E2E8F0" />
          <stop offset="1" stopColor="#94A3B8" />
        </radialGradient>
        <filter id="cf-soft" x="-20%" y="-200%" width="140%" height="500%">
          <feGaussianBlur stdDeviation="7" />
        </filter>
        <filter id="cf-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="4" />
        </filter>
      </defs>
      {/* masa çizgisi + gölgeler */}
      <line x1={20} y1={276} x2={680} y2={276} stroke="#ffffff22" strokeWidth={3} />
      <ellipse cx={200} cy={274} rx={86} ry={9} fill="#000" opacity={0.55 * drop} filter="url(#cf-soft)" />
      <ellipse cx={470 + plateX} cy={272} rx={180} ry={12} fill="#000" opacity={0.5 * slide} filter="url(#cf-soft)" />

      {/* tabak: kenarda neon vurgu halkası, pilav + köfte + salata, çatal-bıçak */}
      <g transform={`translate(${plateX} 0)`} opacity={Math.min(1, slide * 1.4)}>
        <rect x={660} y={168} width={10} height={96} rx={5} fill="#CBD5E1" />
        <path d="M656 168 L656 200 M665 168 L665 200 M674 168 L674 200" stroke="#CBD5E1" strokeWidth={4} strokeLinecap="round" />
        <path d="M694 164 Q712 200 698 262 L690 262 L690 164 Z" fill="#CBD5E1" />
        <ellipse cx={470} cy={236} rx={176} ry={38} fill="url(#cf-plate)" />
        <ellipse cx={470} cy={236} rx={176} ry={38} fill="none" stroke={accent} strokeWidth={3} opacity={0.9} />
        <ellipse cx={470} cy={236} rx={176} ry={38} fill="none" stroke={accent} strokeWidth={6} opacity={0.35} filter="url(#cf-glow)" />
        <ellipse cx={470} cy={234} rx={128} ry={25} fill="#F1F5F9" stroke="#CBD5E1" strokeWidth={2} />
        <path d="M372 236 Q392 196 438 198 Q470 200 476 236 Z" fill="#FEF3C7" />
        {[0, 1, 2].map((i) => (
          <g key={i}>
            <ellipse cx={392 + i * 26} cy={226 - (i % 2) * 4} rx={5} ry={3} fill="#FDE68A" />
          </g>
        ))}
        {[0, 1, 2].map((i) => {
          const s = sp(f, fps, 18 + i * 4, {damping: 11, stiffness: 220, mass: 1});
          return <ellipse key={i} cx={500 + i * 32} cy={226 - (1 - s) * 90} rx={17} ry={12} fill={i === 1 ? '#78350F' : '#92400E'} opacity={s} />;
        })}
        <path d="M486 242 Q520 230 572 240 Q548 252 500 250 Z" fill="#22C55E" opacity={0.85} />
        <circle cx={560} cy={238} r={7} fill="#EF4444" />
      </g>

      {/* take-away kahve bardağı: kapak, vurgu renkli kılıf, buhar */}
      <g transform={`translate(0 ${cupY})`}>
        {[0, 1, 2].map(steam)}
        <path d="M128 92 L272 92 L252 268 Q250 274 244 274 L156 274 Q150 274 148 268 Z" fill="url(#cf-cup)" />
        <path d="M120 74 Q120 64 130 64 L270 64 Q280 64 280 74 L282 92 L118 92 Z" fill="url(#cf-lid)" />
        <rect x={178} y={56} width={44} height={10} rx={4} fill="#1E293B" />
        <path d="M138 152 L262 152 L254 222 L146 222 Z" fill={accent} />
        <path d="M138 152 L262 152 L254 222 L146 222 Z" fill="none" stroke={accent} strokeWidth={6} opacity={0.45} filter="url(#cf-glow)" />
        <path d="M150 166 L250 166" stroke="#0B1220" strokeOpacity={0.25} strokeWidth={3} />
        <path d="M148 208 L252 208" stroke="#0B1220" strokeOpacity={0.25} strokeWidth={3} />
        <path d="M146 100 L160 262" stroke="#FFFFFF" strokeOpacity={0.55} strokeWidth={6} strokeLinecap="round" />
      </g>
    </svg>
  );
};

// ---------------------------------------------------------------- modern apartman silüeti + anahtar
const Apartment: React.FC<V> = ({accent, text, panel, height = 300}) => {
  const {f, fps, t} = useT();
  const rise = sp(f, fps, 0, {damping: 16, stiffness: 120, mass: 1});
  const key = sp(f, fps, 16, {damping: 10, stiffness: 140, mass: 1});
  const swing = Math.sin(t * 2.2) * 6 * key;
  const blocks = [
    {x: 150, w: 150, top: 46, cols: 4, rows: 10},
    {x: 300, w: 120, top: 116, cols: 3, rows: 7},
  ];
  return (
    <svg viewBox="0 0 700 300" width="100%" height={height} style={{overflow: 'visible'}}>
      <defs>
        <linearGradient id="ap-glass" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={panel} />
          <stop offset="1" stopColor="#0B1220" />
        </linearGradient>
        <clipPath id="ap-rise"><rect x={0} y={276 - 240 * rise} width={700} height={240 * rise} /></clipPath>
        <filter id="ap-glow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="5" />
        </filter>
        <filter id="ap-soft" x="-20%" y="-200%" width="140%" height="500%">
          <feGaussianBlur stdDeviation="7" />
        </filter>
      </defs>
      <line x1={40} y1={276} x2={680} y2={276} stroke="#ffffff22" strokeWidth={3} />
      <ellipse cx={290} cy={276} rx={170} ry={8} fill="#000" opacity={0.5 * rise} filter="url(#ap-soft)" />
      <g clipPath="url(#ap-rise)">
        {blocks.map((b, bi) => {
          const cw = b.w / b.cols;
          const rh = (276 - b.top - 40) / b.rows;
          return (
            <g key={bi}>
              <rect x={b.x} y={b.top} width={b.w} height={276 - b.top} fill="url(#ap-glass)" stroke={text} strokeOpacity={0.22} strokeWidth={2} />
              <line x1={b.x} y1={b.top} x2={b.x + b.w} y2={b.top} stroke={accent} strokeWidth={4} />
              <line x1={b.x} y1={b.top} x2={b.x + b.w} y2={b.top} stroke={accent} strokeWidth={8} opacity={0.45} filter="url(#ap-glow)" />
              {Array.from({length: b.rows * b.cols}, (_, k) => {
                const r = Math.floor(k / b.cols);
                const c = k % b.cols;
                const on = ((k * 7 + bi * 3) % 5 === 0);
                const lit = sp(f, fps, 10 + ((k * 3) % 23), {damping: 20, stiffness: 160, mass: 1});
                return (
                  <rect key={k} x={b.x + c * cw + cw * 0.22} y={b.top + 14 + r * rh} width={cw * 0.56} height={rh * 0.58} rx={2}
                    fill={on ? accent : text} opacity={(on ? 0.9 : 0.14) * lit} />
                );
              })}
              {bi === 0 && <rect x={b.x + b.w / 2 - 16} y={250} width={32} height={26} rx={3} fill={accent} opacity={0.85} />}
            </g>
          );
        })}
      </g>
      {/* anahtar: yaylı düşer, hafifçe sallanır */}
      <g transform={`translate(${470 + (1 - key) * 120} ${(1 - key) * -180}) rotate(${-18 + swing} 70 120)`} opacity={Math.min(1, key * 1.5)}>
        <circle cx={70} cy={120} r={40} fill="none" stroke={accent} strokeWidth={16} opacity={0.4} filter="url(#ap-glow)" />
        <circle cx={70} cy={120} r={40} fill="none" stroke={accent} strokeWidth={12} />
        <circle cx={70} cy={120} r={16} fill="none" stroke={text} strokeOpacity={0.35} strokeWidth={3} />
        <rect x={106} y={113} width={118} height={14} rx={7} fill={accent} />
        <path d="M184 127 L184 150 L198 150 L198 127 Z M206 127 L206 142 L220 142 L220 127 Z" fill={accent} />
      </g>
    </svg>
  );
};

// ---------------------------------------------------------------- butik dükkan tentesi + evrak çantası
const Shop: React.FC<V> = ({accent, text, panel, height = 300}) => {
  const {f, fps, t} = useT();
  const unroll = sp(f, fps, 2, {damping: 14, stiffness: 140, mass: 1});
  const glow = sp(f, fps, 14, SOFT);
  const bag = sp(f, fps, 18, {damping: 9, stiffness: 170, mass: 1});
  const stripes = 7;
  const sw = 300 / stripes;
  const scallop = Array.from({length: stripes}, (_, i) => `Q${60 + i * sw + sw / 2} ${118 + 16} ${60 + (i + 1) * sw} 118`).join(' ');
  return (
    <svg viewBox="0 0 700 300" width="100%" height={height} style={{overflow: 'visible'}}>
      <defs>
        <clipPath id="sh-awn"><rect x={40} y={40} width={340} height={110 * unroll} /></clipPath>
        <filter id="sh-glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="6" /></filter>
        <filter id="sh-soft" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="7" /></filter>
        <linearGradient id="sh-bag" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#475569" /><stop offset="1" stopColor="#1E293B" />
        </linearGradient>
      </defs>
      <line x1={20} y1={276} x2={680} y2={276} stroke="#ffffff22" strokeWidth={3} />
      <ellipse cx={210} cy={276} rx={170} ry={8} fill="#000" opacity={0.5} filter="url(#sh-soft)" />
      {/* cephe */}
      <rect x={70} y={70} width={280} height={206} rx={6} fill={panel} stroke={text} strokeOpacity={0.2} strokeWidth={2} />
      {/* vitrin: içeride sıcak ışık + fincan */}
      <rect x={92} y={150} width={150} height={100} rx={6} fill="#0B1220" />
      <rect x={92} y={150} width={150} height={100} rx={6} fill={accent} opacity={0.18 * glow} />
      <g opacity={glow}>
        <path d="M140 196 L190 196 L184 232 Q183 238 177 238 L153 238 Q147 238 146 232 Z" fill={text} opacity={0.85} />
        <path d="M190 204 Q206 204 204 216 Q202 226 188 226" fill="none" stroke={text} strokeOpacity={0.85} strokeWidth={5} />
        {[0, 1].map((i) => (
          <path key={i} d={`M${156 + i * 18} 186 q -8 -10 0 -20 q 8 -10 0 -20`} fill="none" stroke={text} strokeWidth={3}
            opacity={0.5 * Math.abs(Math.sin(t * 2 + i))} />
        ))}
      </g>
      <rect x={260} y={150} width={70} height={126} rx={4} fill="#0B1220" stroke={text} strokeOpacity={0.25} strokeWidth={2} />
      <circle cx={318} cy={214} r={4} fill={accent} />
      {/* tente: çizgili, dalgalı kenar, yukarıdan açılır */}
      <g clipPath="url(#sh-awn)">
        {Array.from({length: stripes}, (_, i) => (
          <path key={i} d={`M${60 + i * sw} 60 L${60 + (i + 1) * sw} 60 L${60 + (i + 1) * sw} 118 L${60 + i * sw} 118 Z`}
            fill={i % 2 ? '#F8FAFC' : accent} />
        ))}
        <path d={`M60 118 ${scallop} L360 118 L360 150 L60 150 Z`} fill="none" />
        <path d={`M60 118 ${scallop}`} fill="none" stroke="#0B1220" strokeOpacity={0.25} strokeWidth={3} />
        {Array.from({length: stripes}, (_, i) => (
          <path key={`s${i}`} d={`M${60 + i * sw} 118 Q${60 + i * sw + sw / 2} 134 ${60 + (i + 1) * sw} 118 Z`}
            fill={i % 2 ? '#F8FAFC' : accent} />
        ))}
        <rect x={56} y={52} width={308} height={10} rx={5} fill="#0B1220" />
      </g>
      <path d="M60 60 L360 60" stroke={accent} strokeWidth={6} opacity={0.4 * unroll} filter="url(#sh-glow)" />
      {/* evrak çantası: yaylı düşer */}
      <g transform={`translate(0 ${(1 - bag) * -220})`} opacity={Math.min(1, bag * 1.6)}>
        <path d="M478 150 L478 132 Q478 120 490 120 L550 120 Q562 120 562 132 L562 150" fill="none" stroke={text} strokeWidth={10} />
        <rect x={430} y={148} width={180} height={128} rx={16} fill="url(#sh-bag)" stroke={text} strokeOpacity={0.3} strokeWidth={2} />
        <rect x={430} y={196} width={180} height={10} fill={accent} />
        <rect x={430} y={196} width={180} height={10} fill={accent} opacity={0.5} filter="url(#sh-glow)" />
        <rect x={506} y={188} width={28} height={26} rx={5} fill="#CBD5E1" stroke="#0B1220" strokeWidth={2} />
      </g>
    </svg>
  );
};

// ---------------------------------------------------------------- iki alyans + yükselen yatırım grafiği
const Rings: React.FC<V> = ({accent, text, height = 300}) => {
  const {f, fps, t} = useT();
  const a = sp(f, fps, 2, {damping: 12, stiffness: 150, mass: 1});
  const b = sp(f, fps, 8, {damping: 12, stiffness: 150, mass: 1});
  const draw = sp(f, fps, 16, {damping: 20, stiffness: 90, mass: 1});
  const sparkle = 0.5 + 0.5 * Math.sin(t * 5);
  const pts = [[430, 250], [480, 232], [520, 238], [565, 196], [605, 170], [650, 118]];
  const line = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x} ${y}`).join(' ');
  const L = 320;
  const ring = (cx: number, cy: number, k: number, from: number, id: string) => (
    <g transform={`translate(${(1 - k) * from} ${(1 - k) * -120})`} opacity={Math.min(1, k * 1.5)}>
      <ellipse cx={cx} cy={cy} rx={78} ry={78} fill="none" stroke={`url(#${id})`} strokeWidth={20} />
      <ellipse cx={cx} cy={cy} rx={78} ry={78} fill="none" stroke="#FFFBEB" strokeOpacity={0.5} strokeWidth={3}
        strokeDasharray="60 430" strokeDashoffset={-t * 40} />
    </g>
  );
  return (
    <svg viewBox="0 0 700 300" width="100%" height={height} style={{overflow: 'visible'}}>
      <defs>
        <linearGradient id="rg-gold" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#FDE68A" /><stop offset="0.5" stopColor="#F59E0B" /><stop offset="1" stopColor="#B45309" />
        </linearGradient>
        <linearGradient id="rg-gold2" x1="1" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#FEF3C7" /><stop offset="0.5" stopColor="#FBBF24" /><stop offset="1" stopColor="#92400E" />
        </linearGradient>
        <filter id="rg-glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="5" /></filter>
        <filter id="rg-soft" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="7" /></filter>
      </defs>
      <line x1={20} y1={276} x2={680} y2={276} stroke="#ffffff22" strokeWidth={3} />
      <ellipse cx={210} cy={272} rx={150} ry={8} fill="#000" opacity={0.5} filter="url(#rg-soft)" />
      {ring(160, 160, a, -200, 'rg-gold')}
      {ring(262, 160, b, 200, 'rg-gold2')}
      {/* pırlanta parıltısı */}
      <g transform={`translate(160 82) scale(${0.6 + 0.4 * sparkle})`} opacity={a}>
        <path d="M0 -18 L5 -5 L18 0 L5 5 L0 18 L-5 5 L-18 0 L-5 -5 Z" fill="#F8FAFC" />
      </g>
      {/* yatırım grafiği: altın çubuklar + çizilen yükselen çizgi */}
      {[0, 1, 2, 3].map((i) => {
        const s = sp(f, fps, 12 + i * 4, {damping: 14, stiffness: 160, mass: 1});
        const h = (40 + i * 34) * s;
        return <rect key={i} x={444 + i * 54} y={276 - h} width={34} height={h} rx={6} fill="#ffffff14" stroke={text} strokeOpacity={0.15} />;
      })}
      <path d={line} fill="none" stroke={accent} strokeWidth={10} opacity={0.4} filter="url(#rg-glow)"
        strokeDasharray={L} strokeDashoffset={L * (1 - draw)} strokeLinecap="round" strokeLinejoin="round" />
      <path d={line} fill="none" stroke={accent} strokeWidth={6} strokeDasharray={L} strokeDashoffset={L * (1 - draw)}
        strokeLinecap="round" strokeLinejoin="round" />
      <path d="M632 112 L654 114 L648 136" fill="none" stroke={accent} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round"
        opacity={draw > 0.95 ? 1 : 0} />
    </svg>
  );
};

export const VISUALS: Record<string, React.FC<V>> = {
  yuzuk: Rings,
  dukkan: Shop,
  konut: Apartment,
  kahve: Coffee,
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
