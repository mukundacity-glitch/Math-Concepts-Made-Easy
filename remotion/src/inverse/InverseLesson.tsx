import {AbsoluteFill, Sequence, staticFile} from 'remotion';
import {Audio} from '@remotion/media';
import {chapterRange, validateBeats, type InverseProps} from './timeline';
import {Opening} from './scenes/Opening';
import {Machine} from './scenes/Machine';
import {Algebra} from './scenes/Algebra';
import {Verify} from './scenes/Verify';
import {Graph} from './scenes/Graph';
import {Domain} from './scenes/Domain';
import {Notation} from './scenes/Notation';
import {Practice} from './scenes/Practice';
import {Recap} from './scenes/Recap';

export const InverseLesson = (props: InverseProps) => {
  validateBeats(props.beats);
  const range = (scene: Parameters<typeof chapterRange>[1]) => chapterRange(props.beats, scene);
  let cursor = 0;
  return <AbsoluteFill style={{backgroundColor: '#20262B'}}>
    <Sequence name="The question" from={range('opening').from} durationInFrames={range('opening').duration}><Opening {...props}/></Sequence>
    <Sequence name="The journey" from={range('machine').from} durationInFrames={range('machine').duration}><Machine {...props}/></Sequence>
    <Sequence name="Build the inverse" from={range('algebra').from} durationInFrames={range('algebra').duration}><Algebra {...props}/></Sequence>
    <Sequence name="Verify both directions" from={range('verify').from} durationInFrames={range('verify').duration}><Verify {...props}/></Sequence>
    <Sequence name="Reflect the graph" from={range('graph').from} durationInFrames={range('graph').duration}><Graph {...props}/></Sequence>
    <Sequence name="Choose the domain" from={range('domain').from} durationInFrames={range('domain').duration}><Domain {...props}/></Sequence>
    <Sequence name="Notation" from={range('notation').from} durationInFrames={range('notation').duration}><Notation {...props}/></Sequence>
    <Sequence name="Independent practice" from={range('practice').from} durationInFrames={range('practice').duration}><Practice {...props}/></Sequence>
    <Sequence name="The idea to keep" from={range('recap').from} durationInFrames={range('recap').duration}><Recap {...props}/></Sequence>
    {props.beats.map((beat) => {
      const from = cursor;
      cursor += beat.durationInFrames;
      return beat.audioSrc ? <Sequence key={beat.id} name={'Voice / ' + beat.id} from={from}
        durationInFrames={beat.durationInFrames}><Audio src={staticFile(beat.audioSrc)}/></Sequence> : null;
    })}
  </AbsoluteFill>;
};
