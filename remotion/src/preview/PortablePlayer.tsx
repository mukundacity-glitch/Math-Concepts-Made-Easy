import {useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Player, type PlayerRef} from '@remotion/player';
import {CinematicLesson, cinematicFrames, type CinematicProps} from '../cinematic/CinematicLesson';
import {PreviewAssets} from './PreviewAssets';

declare const __LESSON__: CinematicProps;
declare const __ASSETS__: Readonly<Record<string, string>>;
declare const __CHECKPOINTS__: Readonly<Record<string, number>>;
const Lesson = (props: CinematicProps) => <PreviewAssets.Provider value={__ASSETS__}>
  <CinematicLesson {...props}/>
</PreviewAssets.Provider>;
const Preview = () => {
  const player = useRef<PlayerRef>(null);
  const [error, setError] = useState('');
  return <main>
    <header><h1>Elimination lesson</h1><span>{__LESSON__.previewMode ? 'Silent preview' : 'Ryan narration · measured timing'}</span></header>
    <Player ref={player} component={Lesson} inputProps={__LESSON__}
      durationInFrames={cinematicFrames(__LESSON__)} compositionWidth={1920} compositionHeight={1080}
      fps={30} controls clickToPlay doubleClickToFullscreen style={{width:'100%', aspectRatio:'16 / 9'}}
      errorFallback={({error: failure}) => <p role="alert">{failure.message}</p>}/>
    <nav aria-label="Lesson checkpoints">{Object.entries(__CHECKPOINTS__).map(([name, frame]) =>
      <button key={name} type="button" onClick={() => {
        try {player.current?.seekTo(frame); setError('');}
        catch (failure) {setError(String(failure));}
      }}>{name}</button>)}</nav>
    {error && <p role="alert">{error}</p>}
  </main>;
};
const root = document.getElementById('elimination-player');
if (!root) throw new Error('Missing preview root');
createRoot(root).render(<Preview/>);
