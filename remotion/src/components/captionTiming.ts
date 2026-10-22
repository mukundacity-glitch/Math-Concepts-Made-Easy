import type {Caption} from '@remotion/captions';

/** A frame inside its chapter Sequence uses chapter-relative timestamps. */
export const captionAtFrame = (
  captions: readonly Caption[], frame: number, fps: number,
): Caption | null => {
  if (!Number.isFinite(frame) || !Number.isFinite(fps) || fps <= 0) {
    return null;
  }
  const timeMs = frame * 1000 / fps;
  return captions.find((caption) => (
    caption.startMs <= timeMs && timeMs < caption.endMs
  )) ?? null;
};
