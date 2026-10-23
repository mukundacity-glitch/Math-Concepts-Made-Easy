import storyboard from './storyboard.json';

export type SceneName = 'opening' | 'machine' | 'algebra' | 'verify' | 'graph' |
  'domain' | 'notation' | 'practice' | 'recap';
export type Beat = {
  readonly id: string;
  readonly scene: SceneName;
  readonly stage: number;
  readonly title: string;
  readonly speech: string;
  readonly holdSeconds: number;
  readonly durationInFrames: number;
  readonly audioSrc?: string;
  readonly audioSha256?: string;
};
export type InverseProps = {readonly beats: readonly Beat[]};
export const previewBeats: readonly Beat[] = storyboard.beats.map((beat) => ({
  ...beat, scene: beat.scene as SceneName,
  durationInFrames: Math.ceil((beat.speech.split(/\s+/).length / 2.35 + beat.holdSeconds) * 30),
}));
export const validateBeats = (beats: readonly Beat[]): void => {
  if (!Array.isArray(beats) || beats.length !== previewBeats.length) {
    throw new Error('The complete inverse-functions storyboard is required');
  }
  beats.forEach((beat, index) => {
    const expected = previewBeats[index];
    if (beat.id !== expected.id || beat.scene !== expected.scene || beat.stage !== expected.stage ||
        beat.speech !== expected.speech || beat.holdSeconds !== expected.holdSeconds ||
        !Number.isSafeInteger(beat.durationInFrames) || beat.durationInFrames < 45 ||
        beat.durationInFrames > 1800) {
      throw new Error('Missing, stale, reordered or invalid beat: ' + expected.id);
    }
    if (beat.audioSrc !== undefined && (!/^inverse\/audio\/[a-z]+-\d{2}\.wav$/.test(beat.audioSrc) ||
      !/^[a-f0-9]{64}$/.test(beat.audioSha256 ?? ''))) {
      throw new Error('Unsafe or unverified narration asset: ' + beat.id);
    }
  });
  if (beats.some((beat) => beat.audioSrc) && beats.some((beat) => !beat.audioSrc)) {
    throw new Error('Partially narrated lessons cannot render');
  }
};
export const totalFrames = (beats: readonly Beat[]): number => {
  validateBeats(beats);
  return beats.reduce((total, beat) => total + beat.durationInFrames, 0);
};
export const chapterRange = (beats: readonly Beat[], scene: SceneName) => {
  let from = 0;
  for (const beat of beats) {
    if (beat.scene === scene) break;
    from += beat.durationInFrames;
  }
  return {from, duration: beats.filter((beat) => beat.scene === scene)
    .reduce((total, beat) => total + beat.durationInFrames, 0)};
};
export const activeBeat = (beats: readonly Beat[], scene: SceneName, frame: number) => {
  const chapter = beats.filter((beat) => beat.scene === scene);
  let start = 0;
  for (const beat of chapter) {
    if (frame < start + beat.durationInFrames) return {beat, frame: frame - start};
    start += beat.durationInFrames;
  }
  return {beat: chapter[chapter.length - 1], frame: 0};
};
