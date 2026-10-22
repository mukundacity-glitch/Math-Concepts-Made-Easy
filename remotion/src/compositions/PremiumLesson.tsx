import {AbsoluteFill, Sequence, useVideoConfig} from 'remotion';
import type {PremiumLessonProps} from '../lesson/types';
import {buildLessonTimeline} from '../lesson/timeline';
import {TitleCard} from '../components/TitleCard';
import {SceneFrame} from '../components/SceneFrame';
import {OutroCard} from '../components/OutroCard';
import {theme} from '../design/theme';

/**
 * Phase 4 Step 3: opt-in validated Manim chapter media. No captions,
 * Shorts, production publishing, or complete hybrid demo yet.
 */
export const PremiumLesson = (props: PremiumLessonProps) => {
  const timeline = buildLessonTimeline(props);
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{backgroundColor: theme.canvas}}>
      {timeline.map((segment) => (
        <Sequence key={segment.kind === 'chapter' ? segment.chapter.id : segment.kind}
                  from={segment.start}
                  durationInFrames={segment.durationInFrames}
                  premountFor={fps}
                  name={segment.kind === 'chapter' ? segment.chapter.title : segment.kind}>
          {segment.kind === 'intro' ? (
            <TitleCard {...props}/>
          ) : segment.kind === 'outro' ? (
            <OutroCard series={props.series} level={props.level} title={props.title}
                       outroFrames={props.outroFrames}/>
          ) : (
            <SceneFrame series={props.series} level={props.level}
                        lessonTitle={props.title} chapter={segment.chapter}
                        index={segment.index} count={props.chapters.length}/>
          )}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
