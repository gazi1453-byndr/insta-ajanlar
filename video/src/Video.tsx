import React from 'react';
import {AbsoluteFill, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFont} from '@remotion/fonts';
import {Background} from './Background';
import {Captions} from './Captions';
import {sp, SPRING, TRANSITION_FRAMES} from './motion';
import {PAD} from './parts';
import {SCENES} from './Scenes';
import {Palette, Scene, VideoProps} from './types';

/** Sahne tonu: 'warn' maliyet/kayıp sahnelerinde vurgu rengini uyarı rengine çevirir. */
export const toned = (p: Palette, s?: Scene): Palette => (s?.tone === 'warn' ? {...p, accent: p.warn} : p);

// DESIGN_SYSTEM.md §2 — Inter (metin) + Inter Display (başlık/rakam), yerel dosyalardan
for (const [family, file, weight] of [
  ['Inter', 'fonts/regular.ttf', '400'],
  ['Inter', 'fonts/bold.ttf', '700'],
  ['InterDisplay', 'fonts/semibold.ttf', '600'],
  ['InterDisplay', 'fonts/display.ttf', '900'],
] as const) {
  loadFont({family, url: staticFile(file), weight});
}

/** Sahne geçişi: yaylı dikey itme (damping 14, stiffness 180) + hıza bağlı dikey hareket bulanıklığı;
 *  içerik sahne boyunca çok yavaş yakınlaşır (hiçbir kare tamamen durağan kalmaz). */
const SceneWrap: React.FC<{i: number; scene: Scene; last: boolean; children: React.ReactNode}> = ({i, scene, last, children}) => {
  const f = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const D = height * 0.5;
  const enter = (fr: number) => (i === 0 ? 1 : sp(fr, fps, 0, SPRING));
  const exit = (fr: number) => (!last && fr >= scene.frames ? sp(fr - scene.frames, fps, 0, SPRING) : 0);
  const y = (1 - enter(f)) * D - exit(f) * D;
  const v = Math.abs((enter(f) - enter(f - 1)) - (exit(f) - exit(f - 1))) * D;
  const blur = Math.min(18, v * 0.22);
  const opacity = Math.min(1, enter(f) * 1.5) * (1 - Math.min(1, exit(f) * 1.3));
  const drift = 1 + 0.025 * Math.min(1, f / Math.max(1, scene.frames));
  const id = `mb${i}`;
  return (
    <AbsoluteFill style={{transform: `translateY(${y}px) scale(${drift})`, opacity, filter: blur > 0.6 ? `url(#${id})` : undefined}}>
      <svg width={0} height={0} style={{position: 'absolute'}}>
        <filter id={id} x="-5%" y="-25%" width="110%" height="150%">
          <feGaussianBlur stdDeviation={`0 ${blur.toFixed(2)}`} />
        </filter>
      </svg>
      {children}
    </AbsoluteFill>
  );
};

const Brand: React.FC<VideoProps> = ({brand, palette: p, durationInFrames}) => {
  const f = useCurrentFrame();
  const label = `${brand.name}${brand.no ? ` #${brand.no}` : ''}${brand.label ? ` · ${brand.label}` : ''}`;
  return (
    <>
      <div style={{position: 'absolute', left: 0, top: 0, height: 10, width: `${(100 * f) / durationInFrames}%`, background: p.accent}} />
      <div style={{position: 'absolute', top: 130, left: PAD, right: PAD, display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
        <div lang="tr" style={{fontFamily: 'Inter', fontWeight: 700, fontSize: label.length > 30 ? 25 : 29, letterSpacing: 0.5, color: p.bg, background: p.accent,
          borderRadius: 999, padding: '10px 22px', whiteSpace: 'nowrap', maxWidth: 700, overflow: 'hidden', textOverflow: 'ellipsis'}}>{label}</div>
        <div style={{fontFamily: 'Inter', fontWeight: 700, fontSize: 26, color: p.text, whiteSpace: 'nowrap'}}>@{brand.handle}</div>
      </div>
    </>
  );
};

export const Video: React.FC<VideoProps> = (props) => {
  const {scenes, palette: p, phrases, sources, period} = props;
  return (
    <AbsoluteFill style={{background: p.bg}}>
      <Background p={p} />
      {scenes.map((s, i) => {
        const last = i === scenes.length - 1;
        const C = SCENES[s.kind] ?? SCENES.card;
        return (
          <Sequence key={i} from={s.from} durationInFrames={s.frames + (last ? 0 : TRANSITION_FRAMES)} layout="none">
            <SceneWrap i={i} scene={s} last={last}>
              <C s={s} p={toned(p, s)} period={period} />
            </SceneWrap>
          </Sequence>
        );
      })}
      <Brand {...props} />
      <Captions phrases={phrases} p={p} scenes={scenes} />
      <div lang="tr" style={{position: 'absolute', left: PAD, right: PAD, top: 1520, fontFamily: 'Inter', fontSize: 24, color: p.text2}}>{sources}</div>
    </AbsoluteFill>
  );
};
