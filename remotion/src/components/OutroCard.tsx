import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {BrandHeader} from './BrandHeader';
import {theme} from '../design/theme';

type Props = {
  readonly series: string;
  readonly level: string;
  readonly title: string;
};

export const OutroCard = ({series, level, title}: Props) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const opacity = interpolate(frame, [0, Math.min(17, durationInFrames / 2)],
                              [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{
      background: 'radial-gradient(ellipse at 35% 50%, #163B60, ' +
                  theme.canvas + ' 70%)', color: theme.text,
      fontFamily: theme.font, overflow: 'hidden',
    }}>
      <BrandHeader series={series} level={level}/>
      <div style={{
        position: 'absolute', left: theme.horizontalSafe,
        right: theme.horizontalSafe, top: 300,
        opacity, display: 'flex', flexDirection: 'column', gap: 34,
      }}>
        <div style={{fontSize: 23, fontWeight: 800, letterSpacing: 6,
                     color: theme.signal}}>
          LESSON CHAPTERS COMPLETE
        </div>
        <h2 style={{fontSize: 82, lineHeight: 1.13, maxWidth: 1500,
                    margin: 0, fontWeight: 820, letterSpacing: -2}}>
          Keep exploring.
        </h2>
        <div style={{height: 8, width: 170, borderRadius: 5,
                     background: theme.accent}}/>
        <div style={{fontSize: 34, color: theme.subdued, maxWidth: 1260,
                     lineHeight: 1.4, overflowWrap: 'anywhere'}}>
          {title}
        </div>
      </div>
    </AbsoluteFill>
  );
};
