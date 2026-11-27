// The studio's Remotion compositions (1080x1920, 30 fps). Each takes its data as props (--props=<file.json>).
import React from 'react';
import {Composition, AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig} from 'remotion';
import {Race} from './Race.jsx';

const Smoke = () => {                      // the smallest composition: studio.py demo renders it to prove the engine works
  const f = useCurrentFrame(), {fps} = useVideoConfig(), s = spring({frame: f, fps, config: {damping: 12, mass: .6}});
  return <AbsoluteFill style={{background: '#101426', justifyContent: 'center', alignItems: 'center'}}>
    <div style={{color: '#fff', fontSize: 150, fontWeight: 900, fontFamily: 'Arial, sans-serif', transform: `scale(${s}) translateY(${interpolate(f, [0, 20], [200, 0], {extrapolateRight: 'clamp'})}px)`}}>STUDIO</div>
  </AbsoluteFill>;
};

export const Root = () => <>
  <Composition id="Smoke" component={Smoke} durationInFrames={45} fps={30} width={1080} height={1920} />
  <Composition id="Race" component={Race} durationInFrames={750} fps={30} width={1080} height={1920} defaultProps={{T: 25}}
    calculateMetadata={({props}) => ({durationInFrames: Math.round((props.T || 25) * 30)})} />
</>;
