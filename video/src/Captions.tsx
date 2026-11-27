import React from 'react';
import {useCurrentFrame, useVideoConfig, spring} from 'remotion';
import {Palette, Phrase, Scene} from './types';

export const CAPTION_Y = 1300; // alt-orta bölge (Instagram arayüzünün üstünde)

/** Karaoke altyazı: konuşmayla kelime kelime senkron; okunan kelime o sahnenin vurgu renginde ve hafif büyür. */
export const Captions: React.FC<{phrases: Phrase[]; p: Palette; scenes?: Scene[]}> = ({phrases, p: base, scenes = []}) => {
  const f = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const cur = scenes.find((s) => f >= s.from && f < s.from + s.frames);
  const p = cur?.tone === 'warn' ? {...base, accent: base.warn} : base;
  const t = f / fps;
  const idx = phrases.findIndex((ph, i) => t >= ph.s && t < (phrases[i + 1]?.s ?? ph.e + 0.4) && t < ph.e + 0.4);
  if (idx < 0) return null;
  const ph = phrases[idx];
  const inP = spring({frame: f - Math.round(ph.s * fps), fps, config: {damping: 16, stiffness: 260}});
  return (
    <div
      lang="tr"
      style={{
        position: 'absolute',
        left: 90,
        width: width - 180,
        top: CAPTION_Y,
        height: 200,
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'center',
        alignContent: 'center',
        gap: '4px 26px',
        transform: `scale(${0.9 + 0.1 * inP})`,
        opacity: Math.min(1, inP * 1.5),
      }}
    >
      {ph.words.map((w, i) => {
        const active = t >= w.s && t < (ph.words[i + 1]?.s ?? ph.e + 0.4);
        const past = t >= w.s;
        const pop = active ? spring({frame: f - Math.round(w.s * fps), fps, config: {damping: 12, stiffness: 320}}) : 1;
        return (
          <span
            key={i}
            style={{
              fontFamily: 'InterDisplay',
              fontWeight: 900,
              fontSize: 72,
              lineHeight: 1.05,
              textTransform: 'uppercase',
              letterSpacing: -1,
              color: active ? p.accent : p.text,
              opacity: past ? 1 : 0.5,
              transform: `translateY(${active ? -6 * pop : 0}px) scale(${active ? 1.04 : 1})`,
              transformOrigin: 'center bottom',
              whiteSpace: 'nowrap',
              display: 'inline-block',
              textShadow: '0 6px 24px rgba(0,0,0,.75), 0 2px 4px rgba(0,0,0,.9)',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {w.t}
          </span>
        );
      })}
    </div>
  );
};
