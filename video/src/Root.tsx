import React from 'react';
import {Composition} from 'remotion';
import {Video} from './Video';
import {defaultProps, VideoProps} from './types';

export const Root: React.FC = () => (
  <Composition
    id="GercekMaliyet"
    component={Video}
    width={1080}
    height={1920}
    fps={60}
    durationInFrames={defaultProps.durationInFrames}
    defaultProps={defaultProps}
    calculateMetadata={({props}: {props: VideoProps}) => ({
      durationInFrames: props.durationInFrames,
      fps: props.fps,
      width: props.width,
      height: props.height,
    })}
  />
);
