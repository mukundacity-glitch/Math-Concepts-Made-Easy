import type {LessonChapter, LessonSegment, PremiumLessonProps} from './types';

const MAX_CHAPTERS = 40;
const MAX_LESSON_FRAMES = 30 * 60 * 60 * 3;
const STAGES = new Set(['concept', 'worked_example', 'practice', 'recap', 'other']);

const requireText = (value: unknown, field: string, limit: number) => {
  if (typeof value !== 'string' || !value.trim() || value.length > limit) {
    throw new Error(field + ' must contain 1–' + limit + ' meaningful characters');
  }
};

const requireFrames = (value: number, field: string, min: number) => {
  if (!Number.isSafeInteger(value) || value < min) {
    throw new Error(field + ' requires an integer of at least ' + min + ' frames');
  }
};

export const validateLessonProps = (props: PremiumLessonProps): void => {
  requireText(props.series, 'series', 100);
  requireText(props.level, 'level', 60);
  requireText(props.title, 'title', 160);
  requireText(props.tagline, 'tagline', 240);
  requireFrames(props.introFrames, 'introFrames', 30);
  requireFrames(props.outroFrames, 'outroFrames', 30);
  if (!Array.isArray(props.chapters) || props.chapters.length === 0 ||
      props.chapters.length > MAX_CHAPTERS) {
    throw new Error('lesson needs 1–' + MAX_CHAPTERS + ' chapters');
  }
  const ids = new Set<string>();
  for (const chapter of props.chapters as LessonChapter[]) {
    requireText(chapter.id, 'chapter.id', 64);
    if (!/^[A-Za-z0-9_-]+$/.test(chapter.id) || ids.has(chapter.id)) {
      throw new Error('chapter ids must be unique and URL-safe');
    }
    ids.add(chapter.id);
    requireText(chapter.title, 'chapter.title', 140);
    requireText(chapter.learningGoal, 'chapter.learningGoal', 260);
    if (!STAGES.has(chapter.stage)) {
      throw new Error('unsupported chapter stage: ' + chapter.stage);
    }
    requireFrames(chapter.durationInFrames, 'chapter.durationInFrames', 45);
  }
  const total = props.introFrames + props.outroFrames +
    props.chapters.reduce((sum, chapter) => sum + chapter.durationInFrames, 0);
  if (!Number.isSafeInteger(total) || total > MAX_LESSON_FRAMES) {
    throw new Error('lesson timeline exceeds supported frame count');
  }
};

export const buildLessonTimeline = (props: PremiumLessonProps): readonly LessonSegment[] => {
  validateLessonProps(props);
  const segments: LessonSegment[] = [];
  let start = 0;
  segments.push({kind: 'intro', start, durationInFrames: props.introFrames});
  start += props.introFrames;
  for (const [index, chapter] of props.chapters.entries()) {
    segments.push({kind: 'chapter', start, index, chapter,
                   durationInFrames: chapter.durationInFrames});
    start += chapter.durationInFrames;
  }
  segments.push({kind: 'outro', start, durationInFrames: props.outroFrames});
  return segments;
};

export const getLessonDurationInFrames = (props: PremiumLessonProps): number => {
  const timeline = buildLessonTimeline(props);
  const last = timeline[timeline.length - 1];
  return last.start + last.durationInFrames;
};
