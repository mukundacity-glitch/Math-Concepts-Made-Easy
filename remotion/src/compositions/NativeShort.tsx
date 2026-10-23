import {AbsoluteFill, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Audio, Video} from '@remotion/media';
import type {Caption} from '@remotion/captions';
import {BrandLogo} from '../components/BrandLogo';
import {captionAtFrame} from '../components/captionTiming';
import {ShortText} from '../shorts/ShortSlides';
import {theme} from '../design/theme';

type Page = {
  durationInFrames: number; videoSrc: string; audioSrc: string; captions: Caption[];
};
export type NativeShortProps = {title: string; label: string; pages: Page[]};

export const nativeShortDuration = (props: NativeShortProps) => {
  if (!props.title || !props.label || !props.pages.length) throw new Error('Incomplete native Short');
  let frames = 0;
  for (const page of props.pages) {
    if (!Number.isInteger(page.durationInFrames) || page.durationInFrames < 30 ||
        !page.captions?.length || !page.videoSrc.startsWith('native-shorts/') ||
        !page.audioSrc.startsWith('native-shorts/')) throw new Error('Invalid native portrait page');
    frames += page.durationInFrames;
  }
  if (frames > 5400) throw new Error('Complete Short exceeds 180 seconds; editorial review required');
  return frames;
};

const TeachingPage = ({page}: {page: Page}) => {
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();
  const caption = captionAtFrame(page.captions, frame, fps);
  return <>
    <div data-native-board style={{position: 'absolute', left: 80, top: 420, width: 840, height: 960}}>
      <Video src={staticFile(page.videoSrc)} muted objectFit="contain" premountFor={fps}
             style={{width: 840, height: 960}}/>
      <Audio src={staticFile(page.audioSrc)} premountFor={fps}/>
    </div>
    <div data-native-caption style={{position: 'absolute', left: 80, top: 1430,
      width: 840, height: 200, color: theme.text}}>
      {caption ? <ShortText text={caption.text} width={840} height={200}
                  fontSize={52} minimumSize={44} weight={600} lineHeight={1.25}/> : null}
    </div>
  </>;
};

/** Separate portrait content. The right rail and bottom 290px stay empty. */
export const NativeShort = (props: NativeShortProps) => {
  const {fps, width, height} = useVideoConfig();
  if (width !== 1080 || height !== 1920 || fps !== 30) throw new Error('Native Shorts require 1080×1920 at 30 FPS');
  nativeShortDuration(props);
  let start = 0;
  return <AbsoluteFill style={{background: '#0B1F38', color: theme.text, fontFamily: theme.font}}>
    <div style={{position: 'absolute', top: 140, left: 80, display: 'flex', alignItems: 'center', gap: 24}}>
      <BrandLogo size={72}/><span style={{fontSize: 24}}>Math Concepts Made Easy</span>
    </div>
    <div style={{position: 'absolute', top: 255, left: 80, width: 840}}>
      <ShortText text={props.title} width={840} height={110} fontSize={56} minimumSize={40} lineHeight={1.1}/>
      <div style={{fontSize: 28, color: theme.subdued, marginTop: 14}}>{props.label}</div>
    </div>
    {props.pages.map((page, index) => {
      const from = start;
      start += page.durationInFrames;
      return <Sequence key={index} from={from} durationInFrames={page.durationInFrames} premountFor={fps}>
        <TeachingPage page={page}/>
      </Sequence>;
    })}
  </AbsoluteFill>;
};
