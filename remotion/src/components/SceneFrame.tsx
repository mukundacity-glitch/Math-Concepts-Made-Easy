import {AbsoluteFill, staticFile, useVideoConfig} from 'remotion';
import {Audio, Video} from '@remotion/media';
import type {LessonChapter} from '../lesson/types';

type Props = {
  readonly series: string;
  readonly level: string;
  readonly chapter: LessonChapter;
  readonly index: number;
  readonly count: number;
  readonly lessonTitle: string;
};

/** Teaching pixels occupy the canvas; captions are exported as optional sidecars. */
export const SceneFrame = ({chapter}: Props) => {
  const {fps} = useVideoConfig();
  if (!chapter.media) {
    return <AbsoluteFill style={{backgroundColor: '#20252B', color: '#F7F3EA',
      justifyContent: 'center', alignItems: 'center', fontFamily: 'Arial', fontSize: 72}}>
      {chapter.title}
    </AbsoluteFill>;
  }
  return <AbsoluteFill data-visual-slot="manim-connected" style={{backgroundColor: '#20252B'}}>
    <Video src={staticFile(chapter.media.videoSrc)} muted premountFor={fps}
      objectFit="contain" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}/>
    <Audio src={staticFile(chapter.media.audioSrc)} premountFor={fps}/>
  </AbsoluteFill>;
};
