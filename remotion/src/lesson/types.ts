import type {Caption} from '@remotion/captions';

export type LessonStage = 'concept' | 'worked_example' | 'practice' | 'recap' | 'other';

/** A prepared Manim video and its original TTS soundtrack.
 * Paths are remotion/public/ relative: never user-controlled remote URLs.
 * Video is deliberately muted in the compositor so audio is not doubled.
 */
export type ManimSceneMedia = {
  readonly kind: 'manim_scene';
  readonly sceneId: number;
  readonly videoSrc: string;
  readonly audioSrc: string;
  readonly videoSha256: string;
  readonly audioSha256: string;
  readonly durationSeconds: number;
  /** Original Edge-TTS word timings, grouped into readable scene-local pages. */
  readonly captions?: readonly Caption[];
  readonly captionsSha256?: string;
};

export type LessonChapter = {
  readonly id: string;
  readonly stage: LessonStage;
  readonly title: string;
  readonly learningGoal: string;
  readonly durationInFrames: number;
  readonly media?: ManimSceneMedia;
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
