import type {Caption} from '@remotion/captions';
import {captionAtFrame} from './captionTiming';
import {theme} from '../design/theme';

type Props = {
  readonly captions: readonly Caption[];
  readonly frame: number;
  readonly fps: number;
};

/**
 * Deliberately OUTSIDE the actual Manim media rectangle; captions never
 * cover verified equations, variable/operator colors, or geometric figures.
 */
export const CaptionLane = ({captions, frame, fps}: Props) => {
  const caption = captionAtFrame(captions, frame, fps);
  return (
    <div data-caption-lane="scene-local" style={{
      position: 'absolute',
      left: theme.horizontalSafe,
      right: theme.horizontalSafe,
      bottom: 132,
      height: 109,
      borderRadius: 22,
      border: '1px solid ' + theme.stroke,
      background: '#071529',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '9px 45px',
      boxSizing: 'border-box',
      color: theme.text,
      textAlign: 'center',
      overflow: 'hidden',
    }}>
      {caption ? (
        <span data-caption-active="true" style={{
          fontSize: 34, lineHeight: 1.25,
          fontWeight: 750,
          color: theme.text,
          textWrap: 'balance',
          maxWidth: '100%',
          fontFamily: theme.font,
          overflowWrap: 'break-word',
        }}>
          {caption.text}
        </span>
      ) : null}
    </div>
  );
};
