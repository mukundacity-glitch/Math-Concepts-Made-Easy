import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {PremiumLessonProps} from '../lesson/types';
import {BrandHeader} from './BrandHeader';
import {theme} from '../design/theme';

export const TitleCard = ({series, title, tagline, level}: PremiumLessonProps) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const opacity = Math.min(
    interpolate(frame, [0, Math.min(20, durationInFrames / 3)], [0, 1],
                {extrapolateRight: 'clamp'}),
    interpolate(frame, [Math.max(0, durationInFrames - 14), durationInFrames - 1],
                [1, 0], {extrapolateLeft: 'clamp'}),
  );
  const entrance = interpolate(frame, [0, Math.min(fps, durationInFrames / 2)],
                               [42, 0], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{
      background: 'radial-gradient(ellipse at 84% 30%, #183E65 0%, ' +
                  theme.canvas + ' 63%)',
      color: theme.text, fontFamily: theme.font,
      overflow: 'hidden',
    }}>
      <BrandHeader series={series} level={level}/>
      <div style={{
        position: 'absolute', left: theme.horizontalSafe,
        top: 250, right: 300, opacity, transform: 'translateY(' + entrance + 'px)',
      }}>
        <div style={{color: theme.signal, fontSize: 22, fontWeight: 750,
                     letterSpacing: 7, textTransform: 'uppercase'}}>
          YOUR NEXT BIG IDEA
        </div>
        <h1 style={{fontSize: 94, lineHeight: 1.09, margin: '38px 0 34px',
                    fontWeight: 820, letterSpacing: -3, maxWidth: 1450,
                    overflowWrap: 'anywhere'}}>
          {title}
        </h1>
        <div style={{width: 192, height: 8, borderRadius: 6,
                     background: theme.accent, marginBottom: 48}}/>
        <p style={{color: theme.subdued, fontSize: 33, lineHeight: 1.35,
                   maxWidth: 1250, margin: 0, overflowWrap: 'anywhere'}}>
          {tagline}
        </p>
      </div>
      <div aria-hidden="true" style={{
        position: 'absolute', right: 130, bottom: 110,
        width: 350, height: 350, border: '3px solid ' + theme.stroke,
        borderRadius: 68, transform: 'rotate(24deg)', opacity: 0.38,
      }}/>
    </AbsoluteFill>
  );
};
