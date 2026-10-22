import {AbsoluteFill, Sequence, useVideoConfig} from 'remotion';
import {buildLessonTimeline} from '../lesson/timeline';
import {selectShortLesson, shortsCanvas, type PremiumShortProps} from '../shorts/timeline';
import {ShortCard, ShortChapter} from '../shorts/ShortSlides';
import {theme} from '../design/theme';

/** One data-driven template keeps original video, narration and captions together. */
export const PremiumShort = (props: PremiumShortProps) => {
  const {fps} = useVideoConfig();
  if (fps !== shortsCanvas.fps) {
    throw new Error('Shorts must use the verified media bridge frame rate of 30 FPS');
  }
  const lesson = selectShortLesson(props);
  const timeline = buildLessonTimeline(lesson);
  return (
    <AbsoluteFill style={{backgroundColor: theme.canvas}}>
      {timeline.map((segment) => (
        <Sequence key={segment.kind === 'chapter' ? segment.chapter.id : segment.kind}
                  from={segment.start} durationInFrames={segment.durationInFrames}
                  premountFor={fps}
                  name={segment.kind === 'chapter' ? segment.chapter.title : segment.kind}>
          {segment.kind === 'chapter' ? (
            <ShortChapter series={lesson.series} chapter={segment.chapter}
                          index={segment.index} count={lesson.chapters.length}/>
          ) : (
            <ShortCard lesson={lesson} closing={segment.kind === 'outro'}/>
          )}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
