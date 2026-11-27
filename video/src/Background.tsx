import React from 'react';
import {AbsoluteFill, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {Palette} from './types';

/** Düz lacivert yerine: yavaş kayan ızgara + nefes alan ışık noktaları + süzülen ışık hüzmesi.
 *  Hepsi düşük kontrast (%60 zemin rengini bozmaz). */
export const Background: React.FC<{p: Palette}> = ({p}) => {
  const f = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const t = f / fps;
  const grid = 96;
  const off = (t * 16) % grid;
  const beamX = -700 + ((t * 70) % (width + 1400));
  const dots = Array.from({length: 22}, (_, i) => ({
    x: random(`x${i}`) * width,
    y: random(`y${i}`) * height,
    r: 3 + random(`r${i}`) * 5,
    ph: random(`p${i}`) * Math.PI * 2,
    sp: 0.4 + random(`s${i}`) * 0.8,
  }));
  return (
    <AbsoluteFill style={{background: p.bg, overflow: 'hidden'}}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(1100px 800px at 50% ${-6 + 3 * Math.sin(t * 0.5)}%, ${p.accent}26, transparent 62%),
                       radial-gradient(900px 700px at 50% 112%, #1E3A8A33, transparent 60%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(#ffffff0f 1.5px, transparent 1.5px), linear-gradient(90deg, #ffffff0f 1.5px, transparent 1.5px)`,
          backgroundSize: `${grid}px ${grid}px`,
          backgroundPosition: `${off}px ${off * 0.55}px`,
          WebkitMaskImage: 'radial-gradient(ellipse 75% 60% at 50% 45%, black 25%, transparent 85%)',
          maskImage: 'radial-gradient(ellipse 75% 60% at 50% 45%, black 25%, transparent 85%)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: beamX,
          top: -500,
          width: 420,
          height: height + 1000,
          transform: 'rotate(20deg)',
          background: `linear-gradient(90deg, transparent, ${p.accent}12, #ffffff0a, ${p.accent}12, transparent)`,
          filter: 'blur(40px)',
        }}
      />
      {dots.map((d, i) => {
        const a = 0.25 + 0.35 * (0.5 + 0.5 * Math.sin(t * d.sp * 2 + d.ph));
        const y = (d.y - t * 12 * d.sp + height) % height;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: d.x,
              top: y,
              width: d.r * 2,
              height: d.r * 2,
              borderRadius: '50%',
              background: i % 3 === 0 ? p.accent : '#CBD5E1',
              opacity: a * 0.55,
              boxShadow: `0 0 ${d.r * 5}px ${d.r * 1.5}px ${i % 3 === 0 ? p.accent + '55' : '#ffffff22'}`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
