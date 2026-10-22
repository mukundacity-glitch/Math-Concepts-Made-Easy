export type LessonStage = 'concept' | 'worked_example' | 'practice' | 'recap' | 'other';

export type LessonChapter = {
  readonly id: string;
  readonly stage: LessonStage;
  readonly title: string;
  readonly learningGoal: string;
  readonly durationInFrames: number;
};

export type PremiumLessonProps = {
  readonly series: string;
  readonly level: string;
  readonly title: string;
  readonly tagline: string;
  readonly chapters: readonly LessonChapter[];
  readonly introFrames: number;
  readonly outroFrames: number;
};

export type LessonSegment =
  | {readonly kind: 'intro'; readonly start: number; readonly durationInFrames: number}
  | {readonly kind: 'chapter'; readonly start: number; readonly durationInFrames: number; readonly index: number; readonly chapter: LessonChapter}
  | {readonly kind: 'outro'; readonly start: number; readonly durationInFrames: number};
