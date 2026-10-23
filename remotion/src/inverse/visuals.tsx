import type {ReactNode} from 'react';
import {interpolate, Easing, staticFile} from 'remotion';
import {activeBeat, type InverseProps, type SceneName} from './timeline';
import {useCurrentFrame} from 'remotion';

export const colors = {
  paper: '#F4F0E7', ink: '#172A35', slate: '#20262B', white: '#FFFDF4',
  teal: '#006A70', mint: '#63EED7', gold: '#EDBB63', coral: '#C15B48', muted: '#AAAFAE',
};
export const ease = (frame: number, length = 24) => interpolate(frame, [0, length], [0, 1], {
  extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.16, 1, 0.3, 1),
});
export const useBeat = (props: InverseProps, scene: SceneName) =>
  activeBeat(props.beats, scene, useCurrentFrame());
export const Text = ({x = 960, y, size = 64, color = colors.ink, children, anchor = 'middle',
  math = false, opacity = 1}: {x?: number; y: number; size?: number; color?: string;
  children: ReactNode; anchor?: 'middle' | 'start' | 'end'; math?: boolean; opacity?: number}) => (
  <text x={x} y={y} textAnchor={anchor} fill={color} fontSize={size} opacity={opacity}
    fontFamily={math ? 'Georgia, DejaVu Serif, serif' : 'Arial, Helvetica, sans-serif'}
    fontWeight={math ? 400 : 500} letterSpacing={math ? 0 : -1}>{children}</text>
);
export const Reveal = ({frame, children}: {frame: number; children: ReactNode}) => (
  <g opacity={ease(frame, 15)} style={{translate: `0px ${(1 - ease(frame)) * 16}px`}}>{children}</g>
);
export const Stage = ({title, chapter, dark = false, children}: {
  title: string; chapter: string; dark?: boolean; children: ReactNode;
}) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="100%" height="100%"
    style={{position: 'absolute', inset: 0, background: dark ? colors.slate : colors.paper}}>
    <defs>
      <radialGradient id="light"><stop stopColor={dark ? '#364047' : '#FFFFFF'} stopOpacity=".45"/>
        <stop offset="1" stopColor={dark ? colors.slate : colors.paper} stopOpacity="0"/></radialGradient>
      <marker id="arrow" markerWidth="12" markerHeight="12" refX="9" refY="5" orient="auto-start-reverse">
        <path d="M1,1 L9,5 L1,9" fill="none" stroke="context-stroke" strokeWidth="1.6"/>
      </marker>
    </defs>
    <rect width="1920" height="1080" fill="url(#light)"/>
    <image href={staticFile("branding/math-concepts-made-easy-logo.webp")} x={112} y={39} width={84} height={84}/>
    <text x={220} y={101} fontSize={38} fontWeight={700} fontFamily="Arial, Helvetica, sans-serif">
      <tspan fill={dark ? colors.white : colors.ink}>MATH CONCEPTS </tspan>
      <tspan fill={dark ? colors.gold : colors.teal}>MADE EASY</tspan>
    </text>
    <Text x={1808} y={100} size={30} color={dark ? colors.white : colors.ink} anchor="end">{chapter}</Text>
    <Text x={112} y={206} size={62} color={dark ? colors.white : colors.ink} anchor="start">{title}</Text>
    {children}
  </svg>
);
export const Arrow = ({x1, y1, x2, y2, color = colors.teal, progress = 1, dashed = false}: {
  x1: number; y1: number; x2: number; y2: number; color?: string; progress?: number; dashed?: boolean;
}) => <path d={`M ${x1} ${y1} L ${x2} ${y2}`} fill="none" stroke={color} strokeWidth={4}
  pathLength={1} strokeDasharray={dashed ? '0.015 0.015' : 1} strokeDashoffset={dashed ? 0 : 1 - progress}
  markerEnd={progress > .95 ? 'url(#arrow)' : undefined}/>;
export const Fraction = ({top, bottom, x = 960, y, size = 86, color = colors.ink}: {
  top: string; bottom: string; x?: number; y: number; size?: number; color?: string;
}) => {
  const width = Math.max(top.length, bottom.length) * size * .53 + 36;
  return <g><Text x={x} y={y - 23} size={size} color={color} math>{top}</Text>
    <line x1={x - width / 2} x2={x + width / 2} y1={y} y2={y} stroke={color} strokeWidth={3}/>
    <Text x={x} y={y + size + 8} size={size} color={color} math>{bottom}</Text></g>;
};
export const Equation = ({children, y = 490, color = colors.ink, size = 100}: {
  children: ReactNode; y?: number; color?: string; size?: number;
}) => <Text y={y} size={size} color={color} math>{children}</Text>;
export const Footer = ({children, dark = false}: {children: ReactNode; dark?: boolean}) =>
  <Text y={955} size={38} color={dark ? colors.muted : '#656C6C'}>{children}</Text>;
