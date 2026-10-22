import {AbsoluteFill, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Audio, Video} from '@remotion/media';
import {BrandHeader} from './BrandHeader';
import type {LessonChapter} from '../lesson/types';
import {theme} from '../design/theme';
import {CaptionLane} from './CaptionLane';

const stageLabels = {
  concept: 'THE CONCEPT',
  worked_example: 'WORKED EXAMPLE',
  practice: 'YOUR TURN',
  recap: 'RECAP',
  other: 'LESSON CHAPTER',
} as const;

type Props = {
  readonly series: string;
  readonly level: string;
  readonly chapter: LessonChapter;
  readonly index: number;
  readonly count: number;
  readonly lessonTitle: string;
};

export const SceneFrame = ({series, level, chapter, index, count, lessonTitle}: Props) => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  const reveal = interpolate(frame, [0, Math.min(12, durationInFrames / 3)],
                             [0, 1], {extrapolateRight: 'clamp'});
  const progress = (index + 1) / count;
  const hasCaptions = Boolean(chapter.media?.captions?.length);
  return (
    <AbsoluteFill style={{
      background: 'linear-gradient(118deg, ' + theme.canvas + ', ' + theme.deep + ')',
      color: theme.text, fontFamily: theme.font, overflow: 'hidden',
    }}>
      <BrandHeader series={series} level={level}
                   chapterLabel={'CHAPTER ' + String(index + 1).padStart(2, '0') +
                                 '  /  ' + String(count).padStart(2, '0')}/>
      <div style={{
        position: 'absolute', top: 145, left: theme.horizontalSafe,
        right: theme.horizontalSafe, display: 'flex',
        alignItems: 'baseline', justifyContent: 'space-between', gap: 60,
        opacity: reveal,
      }}>
        <h2 style={{
          margin: 0, fontWeight: 820, fontSize: 47, lineHeight: 1.1,
          overflowWrap: 'anywhere', maxWidth: 1170,
        }}>{chapter.title}</h2>
        <div style={{color: theme.signal, fontWeight: 760, fontSize: 20,
                     letterSpacing: 4, textAlign: 'right', flexShrink: 0}}>
          {stageLabels[chapter.stage]}
        </div>
      </div>

      <div style={{
        position: 'absolute', top: 236, left: theme.horizontalSafe,
        right: theme.horizontalSafe, bottom: hasCaptions ? 258 : 134,
        display: 'flex', gap: 28, opacity: reveal,
      }}>
        {/* Step 3: render verified Manim pixels; neutral placeholder only when no package is supplied. */}
        <div data-visual-slot={chapter.media ? "manim-connected" : "manim-pending"} style={{
          position: 'relative', flex: 1, minWidth: 0, borderRadius: 28,
          border: '2px solid ' + theme.stroke,
          background: 'radial-gradient(ellipse at 50% 38%, #16395B, ' +
                      theme.deep + ' 82%)',
          overflow: 'hidden', display: 'flex', alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 24px 60px ' + theme.shadow,
        }}>
          {chapter.media ? (
            <>
              {/* The original Manim scene remains pixel-for-pixel intact,
                  with no re-typeset math, fake operators or recomputed graphs. */}
              <Video
                src={staticFile(chapter.media.videoSrc)}
                muted
                premountFor={fps}
                objectFit="contain"
                style={{position: 'absolute', inset: 0, width: '100%',
                        height: '100%', background: theme.deep}}
              />
              {/* A separate original Cell-3 soundtrack avoids double audio
                  when a Manim MP4 already embeds its own audio stream. */}
              <Audio src={staticFile(chapter.media.audioSrc)} premountFor={fps}/>
            </>
          ) : (
          <div style={{
            width: '86%', height: '72%', border: '2px dashed ' + theme.stroke,
            borderRadius: 21, display: 'flex', alignItems: 'center',
            justifyContent: 'center', flexDirection: 'column',
            textAlign: 'center', gap: 25, padding: 25,
          }}>
            <div style={{fontSize: 69, opacity: 0.25, fontWeight: 760}}>◈</div>
            <div style={{fontWeight: 760, letterSpacing: 3, fontSize: 26,
                         color: theme.subdued}}>
              MATHEMATICAL VISUAL AREA
            </div>
            <div style={{fontSize: 19, color: theme.quiet, lineHeight: 1.4,
                         maxWidth: 760}}>
              Verified Manim video will appear here in Phase 4 Step 3.
              No mathematical explanation is fabricated by this layout.
            </div>
          </div>
          )}
        </div>
        <aside style={{
          width: 338, flexShrink: 0, background: theme.surfaceRaised,
          border: '1px solid ' + theme.stroke, borderRadius: 28,
          padding: '38px 28px', display: 'flex', flexDirection: 'column',
          gap: 30, minWidth: 0,
        }}>
          <div style={{fontSize: 18, color: theme.signal, letterSpacing: 3,
                       fontWeight: 780}}>LEARNING FOCUS</div>
          <div style={{fontSize: 27, fontWeight: 720, lineHeight: 1.4,
                       overflowWrap: 'anywhere'}}>
            {chapter.learningGoal}
          </div>
          <div style={{flex: 1}}/>
          <div style={{height: 1, background: theme.stroke}}/>
          <div style={{color: theme.subdued, fontSize: 18, lineHeight: 1.4}}>
            {lessonTitle}
          </div>
        </aside>
      </div>
      {/* Dedicated space beneath the media, never drawn on top of equations. */}
      {chapter.media?.captions && (
        <CaptionLane captions={chapter.media.captions} frame={frame} fps={fps}/>
      )}
      <div style={{
        position: 'absolute', left: theme.horizontalSafe, right: theme.horizontalSafe,
        bottom: 69, display: 'flex', alignItems: 'center', gap: 34,
      }}>
        <div style={{color: theme.quiet, fontSize: 19, width: 225,
                     letterSpacing: 2}}>
          CHAPTER PROGRESS
        </div>
        <div style={{flex: 1, height: 6, borderRadius: 4,
                     background: theme.stroke, overflow: 'hidden'}}>
          <div style={{width: String(progress * 100) + '%', height: '100%',
                       borderRadius: 4, background: theme.accent}}/>
        </div>
        <div style={{fontWeight: 790, color: theme.accent, fontSize: 20,
                     fontVariantNumeric: 'tabular-nums'}}>
          {index + 1} / {count}
        </div>
      </div>
    </AbsoluteFill>
  );
};
