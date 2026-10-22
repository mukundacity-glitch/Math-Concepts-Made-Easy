import {useMemo} from 'react';
import {AbsoluteFill, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Audio, Video} from '@remotion/media';
import type {LessonChapter, PremiumLessonProps} from '../lesson/types';
import {BrandLogo} from '../components/BrandLogo';
import {captionAtFrame} from '../components/captionTiming';
import {theme} from '../design/theme';
import {shortLayout as layout} from './layout';
import {fitShortText} from './textFit';

type TextProps = {
  readonly text: string; readonly width: number; readonly height: number;
  readonly fontSize: number; readonly weight?: number; readonly lineHeight?: number;
};

/** Measure the installed font so accepted metadata never clips or truncates. */
const ShortText = ({text, width, height, fontSize, weight = 750, lineHeight = 1.2}: TextProps) => {
  const fitted = useMemo(() => {
    const context = document.createElement('canvas').getContext('2d');
    if (!context) throw new Error('Shorts needs a canvas context to measure readable text');
    return fitShortText(text, width - 4, height, fontSize, lineHeight, (value, size) => {
      context.font = weight + ' ' + size + 'px ' + theme.font;
      return context.measureText(value).width;
    });
  }, [text, width, height, fontSize, weight, lineHeight]);
  return (
    <span data-short-text="fitted" style={{display: 'block', width, maxHeight: height,
      fontFamily: theme.font, fontWeight: weight, fontSize: fitted.fontSize,
      lineHeight, letterSpacing: 0}}>
      {fitted.lines.map((line, index) => (
        <span key={index} style={{display: 'block', whiteSpace: 'pre'}}>{line}</span>
      ))}
    </span>
  );
};

const ShortBrandHeader = ({series}: {readonly series: string}) => (
  <header style={{position: 'absolute', top: layout.headerTop, left: layout.left,
    width: layout.width, display: 'flex', alignItems: 'center', gap: 24, color: theme.text}}>
    <BrandLogo size={80}/>
    <ShortText text={series} width={650} height={80} fontSize={28} weight={800}/>
  </header>
);

export const ShortCard = ({lesson, closing = false}: {
  readonly lesson: PremiumLessonProps; readonly closing?: boolean;
}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: 'linear-gradient(155deg, #152E4F, #081B33 70%)',
      color: theme.text, fontFamily: theme.font}}>
      <ShortBrandHeader series={lesson.series}/>
      <div style={{position: 'absolute', left: layout.left, width: layout.width,
        top: 376, opacity: interpolate(frame, [0, 10], [0, 1],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
        <div style={{color: theme.signal, marginBottom: 38}}>
          <ShortText text={closing ? 'KEEP BUILDING YOUR UNDERSTANDING' : lesson.level}
                     width={layout.width} height={80} fontSize={30} weight={800}/>
        </div>
        <h1 style={{margin: 0}}>
          <ShortText text={lesson.title} width={layout.width} height={600}
                     fontSize={84} weight={850} lineHeight={1.12}/>
        </h1>
        <div style={{height: 8, width: 112, background: theme.accent, marginTop: 48}}/>
      </div>
      <div style={{position: 'absolute', left: layout.left, width: layout.width,
        top: 1200, color: theme.subdued}}>
        <ShortText text={closing ? 'Continue with the full lesson. Practice each step.' : lesson.tagline}
                   width={layout.width} height={340} fontSize={44} weight={500} lineHeight={1.35}/>
      </div>
      <div style={{position: 'absolute', left: layout.left, top: 1668,
        color: theme.accent, fontSize: 26, fontWeight: 800, letterSpacing: 3}}>
        {closing ? 'LEARN  ·  PRACTICE  ·  MASTER' : 'ONE IDEA AT A TIME'}
      </div>
    </AbsoluteFill>
  );
};

const stageLabels = {
  concept: 'THE CONCEPT', worked_example: 'WORKED EXAMPLE', practice: 'YOUR TURN',
  recap: 'RECAP', other: 'LEARN THE METHOD',
} as const;

export const ShortChapter = ({series, chapter, index, count}: {
  readonly series: string; readonly chapter: LessonChapter;
  readonly index: number; readonly count: number;
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const caption = captionAtFrame(chapter.media?.captions ?? [], frame, fps);
  return (
    <AbsoluteFill style={{background: theme.canvas, color: theme.text, fontFamily: theme.font}}>
      <ShortBrandHeader series={series}/>
      <div style={{position: 'absolute', left: layout.left, width: layout.width, top: layout.titleTop}}>
        <div style={{color: theme.signal, fontSize: 26, fontWeight: 800,
          letterSpacing: 4, marginBottom: 20}}>{stageLabels[chapter.stage]}</div>
        <h2 style={{margin: 0}}>
          <ShortText text={chapter.title} width={layout.width} height={190}
                     fontSize={64} weight={820} lineHeight={1.12}/>
        </h2>
      </div>
      <div data-shorts-media={chapter.media ? 'connected' : 'layout-preview'} style={{
        position: 'absolute', left: layout.left, top: layout.mediaTop,
        width: layout.width, height: layout.mediaHeight, background: theme.deep,
        outline: '2px solid ' + theme.stroke, display: 'flex',
        alignItems: 'center', justifyContent: 'center',
      }}>
        {chapter.media ? (
          <>
            {/* Fit the whole source: cropping an equation can change its meaning. */}
            <Video src={staticFile(chapter.media.videoSrc)} muted premountFor={fps}
                   objectFit="contain" style={{width: '100%', height: '100%'}}/>
            <Audio src={staticFile(chapter.media.audioSrc)} premountFor={fps}/>
          </>
        ) : (
          <div style={{fontSize: 36, color: theme.subdued, textAlign: 'center',
            padding: 64, lineHeight: 1.4}}>Mathematical animation preview</div>
        )}
      </div>
      <div style={{position: 'absolute', left: layout.left, width: layout.width,
        top: layout.focusTop, color: theme.subdued}}>
        <div style={{fontSize: 24, letterSpacing: 3, color: theme.signal,
          fontWeight: 800, marginBottom: 20}}>LEARNING FOCUS</div>
        <ShortText text={chapter.learningGoal} width={layout.width} height={242}
                   fontSize={40} weight={500} lineHeight={1.25}/>
      </div>
      <div data-shorts-caption-lane="scene-local" style={{
        position: 'absolute', left: layout.left, width: layout.width,
        top: layout.captionTop, height: layout.captionHeight,
        background: '#071529', border: '1px solid ' + theme.stroke,
        borderRadius: 24, boxSizing: 'border-box', padding: '24px 32px',
        display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
      }}>
        {caption ? (
          <span data-shorts-caption-active="true">
            <ShortText text={caption.text} width={layout.width - 66} height={162} fontSize={44}/>
          </span>
        ) : null}
      </div>
      <div style={{position: 'absolute', left: layout.left, top: layout.progressTop,
        width: layout.width, display: 'flex', alignItems: 'center', gap: 24}}>
        <div style={{fontSize: 24, color: theme.accent, fontWeight: 800}}>{index + 1} / {count}</div>
        <div style={{height: 6, flex: 1, background: theme.stroke}}>
          <div style={{height: '100%', background: theme.accent,
            width: String(((index + Math.min(1, (frame + 1) / chapter.durationInFrames)) / count) * 100) + '%'}}/>
        </div>
      </div>
    </AbsoluteFill>
  );
};
