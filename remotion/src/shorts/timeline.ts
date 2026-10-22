import type {PremiumLessonProps} from '../lesson/types';
import {buildLessonTimeline, getLessonDurationInFrames, validateLessonProps} from '../lesson/timeline';

export type PremiumShortProps = PremiumLessonProps & {
  /** Select complete chapters in source order; never trim narration. */
  readonly chapterIds?: readonly string[];
};
export const shortsCanvas = {width: 1080, height: 1920, fps: 30} as const;
// Editorial limit includes opening and closing cards.
export const MAX_SHORT_FRAMES = 180 * shortsCanvas.fps;

export const selectShortLesson = (props: PremiumShortProps): PremiumLessonProps => {
  validateLessonProps(props);
  let chapters = props.chapters;
  if (props.chapterIds !== undefined) {
    if (!Array.isArray(props.chapterIds) || !props.chapterIds.length ||
        props.chapterIds.some((id) => typeof id !== 'string') ||
        new Set(props.chapterIds).size !== props.chapterIds.length) {
      throw new Error('Shorts chapterIds must be a nonempty list of unique chapter ids');
    }
    const selected = new Set(props.chapterIds);
    chapters = props.chapters.filter((chapter) => selected.has(chapter.id));
    if (chapters.length !== selected.size) {
      throw new Error('Shorts chapterIds contains an unknown chapter');
    }
  }
  if (chapters.some((chapter) => chapter.media && !chapter.media.captions?.length)) {
    throw new Error('Shorts media requires original word-timed captions; export with --require-captions');
  }
  const lesson: PremiumLessonProps = {...props, chapters};
  if (getLessonDurationInFrames(lesson) > MAX_SHORT_FRAMES) {
    throw new Error('Shorts exceeds the 180-second editorial limit; select fewer complete chapters');
  }
  return lesson;
};
export const buildShortTimeline = (props: PremiumShortProps) =>
  buildLessonTimeline(selectShortLesson(props));
export const getShortDurationInFrames = (props: PremiumShortProps): number =>
  getLessonDurationInFrames(selectShortLesson(props));
