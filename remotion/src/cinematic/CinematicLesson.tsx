import {useMemo} from 'react';
import {AbsoluteFill, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Audio} from '@remotion/media';
import {Stage, Text, colors} from '../inverse/visuals';
import {MathBoard} from '../math-board/MathBoard';
import {cueFrame, type SpeechBeat} from '../math-board/timeline';

import {cinematicFrames, chapterDuration, type CinematicProps, type Chapter, type Diagram} from './timeline';
export {cinematicFrames} from './timeline';
export type {CinematicProps} from './timeline';

const FunctionDiagram = ({diagram, dark, beats}: {diagram: Diagram; dark: boolean; beats: readonly SpeechBeat[]}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const reveal = interpolate(frame, [0, 2 * fps], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const unit = 90, centerX = 1260, centerY = 600;
  const ink = dark ? colors.white : colors.ink, accent = dark ? colors.mint : colors.teal;
  let wasValid = false;
  const path = diagram.points.map((point) => {
    if (!point || Math.abs(point.y) > 3.3) {wasValid = false; return '';}
    const prefix = wasValid ? 'L' : 'M'; wasValid = true;
    return `${prefix}${centerX + point.x * unit},${centerY - point.y * unit}`;
  }).join(' ');
  return <g>
    {[-3,-2,-1,0,1,2,3].map((tick) => <g key={tick}>
      <line x1={centerX + tick * unit} x2={centerX + tick * unit} y1={300} y2={900} stroke={ink} opacity={.12}/>
      <line x1={945} x2={1575} y1={centerY + tick * unit} y2={centerY + tick * unit} stroke={ink} opacity={.12}/>
      {tick !== 0 && <text x={centerX + tick * unit} y={centerY + 35} fill={ink} fontSize={27} textAnchor="middle">{tick}</text>}
    </g>)}
    <path d={`M945 ${centerY} H1600 M${centerX} 925 V275`} fill="none" stroke={ink} strokeWidth={3}/>
    <path d={path} fill="none" stroke={accent} strokeWidth={6} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - reveal}/>
    <Text x={112} y={385} size={44} anchor="start" color={ink}>Input → Output</Text>
    {(diagram.sampleCues ? diagram.samples : []).map((point, index) => <g key={point.x} opacity={interpolate(frame,
      [diagram.sampleCues?.[index] ? cueFrame(diagram.sampleCues[index], beats, fps) : 0,
       (diagram.sampleCues?.[index] ? cueFrame(diagram.sampleCues[index], beats, fps) : 0) + .3 * fps], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}>
      <Text x={112} y={490 + index * 95} size={58} anchor="start" color={ink} math>{`${point.x} → ${Number(point.y.toPrecision(5))}`}</Text>
      {Math.abs(point.y) <= 3.3 && <circle cx={centerX + point.x * unit} cy={centerY - point.y * unit} r={8} fill={dark ? colors.gold : colors.coral}/>}
    </g>)}
    <Text x={1260} y={980} size={40} color={ink} math>{diagram.equation}</Text>
  </g>;
};

const CinematicChapter = ({chapter, day, title, index, previewMode}: {previewMode?: boolean; chapter: Chapter; day: number; title: string; index: number}) => {
  const frame = useCurrentFrame();
  const duration = chapterDuration(chapter);
  const mainTitle = chapter.id === 'opening' ? title : chapter.title;
  return <Stage title={mainTitle} chapter={previewMode ? 'SILENT PREVIEW · ESTIMATED TIMING' : `${String(index + 1).padStart(2, '0')} / DAY ${day}`} dark={chapter.dark}>
    {chapter.board.length ? <MathBoard board={chapter.board} beats={chapter.beats} dark={chapter.dark} states={chapter.boardStates}/> :
      chapter.diagram ? <FunctionDiagram diagram={chapter.diagram} dark={chapter.dark} beats={chapter.beats}/> : <>
        <Text y={550} size={chapter.id === 'opening' ? 180 : 104} color={chapter.dark ? colors.gold : colors.teal} math>
          {chapter.id === 'opening' && frame < chapter.beats[0].durationInFrames ? '?' : `Day ${day}`}
        </Text>
        <Text y={755} size={52} color={chapter.dark ? colors.white : colors.ink}>
          {chapter.id === 'opening' ? 'See it. Work it out. Understand why.' : chapter.title}
        </Text>
      </>}
    <rect x={112} y={1034} height={4} width={1696 * Math.min(1, frame / duration)} fill={chapter.dark ? colors.mint : colors.teal}/>
  </Stage>;
};

export const CinematicLesson = (props: CinematicProps) => {
  useMemo(() => cinematicFrames(props), [props]);
  const {fps} = useVideoConfig();
  let cursor = 0;
  return <AbsoluteFill>{props.chapters.map((chapter, index) => {
    const from = cursor; cursor += chapterDuration(chapter);
    let audioCursor = 0;
    return <Sequence key={chapter.id} from={from} durationInFrames={chapterDuration(chapter)} premountFor={fps} name={chapter.title}>
      <CinematicChapter chapter={chapter} day={props.day} title={props.title} index={index} previewMode={props.previewMode}/>
      {chapter.beats.map((beat) => {
        const audioFrom = audioCursor; audioCursor += beat.durationInFrames;
        return beat.audioSrc ? <Sequence key={beat.id} from={audioFrom} durationInFrames={beat.durationInFrames} premountFor={fps}>
          <Audio src={staticFile(beat.audioSrc)} premountFor={fps}/>
        </Sequence> : null;
      })}
    </Sequence>;
  })}</AbsoluteFill>;
};
