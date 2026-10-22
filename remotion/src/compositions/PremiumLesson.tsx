import {AbsoluteFill, Sequence} from 'remotion';
import type {PremiumLessonProps} from '../lesson/types';
import {buildLessonTimeline} from '../lesson/timeline';
import {TitleCard} from '../components/TitleCard';
import {SceneFrame} from '../components/SceneFrame';
import {OutroCard} from '../components/OutroCard';
import {theme} from '../design/theme';

/**
 * Phase 4 Step 2 composition: visual shell and chapter frame schedule ONLY.
 * Video clips, their exact timings, audio, captions and Shorts are NOT
 * introduced until the separately approved steps that follow.
 */
export const PremiumLesson = (props: PremiumLessonProps) => {
  const timeline = buildLessonTimeline(props);
  return (
    <AbsoluteFill style={{backgroundColor: theme.canvas}}>
      {timeline.map((segment) => (
        <Sequence key={segment.kind === 'chapter' ? segment.chapter.id : segment.kind}
                  from={segment.start}
                  durationInFrames={segment.durationInFrames}
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
