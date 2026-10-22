import type {CSSProperties} from 'react';
import {theme} from '../design/theme';

type Props = {
  readonly series: string;
  readonly level: string;
  readonly chapterLabel?: string;
};

const labelStyle: CSSProperties = {
  letterSpacing: 4,
  fontSize: 21,
  fontWeight: 750,
  color: theme.subdued,
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
};

export const BrandHeader = ({series, level, chapterLabel}: Props) => (
  <header style={{
    position: 'absolute',
    top: theme.verticalSafe,
    left: theme.horizontalSafe,
    right: theme.horizontalSafe,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 48,
    minHeight: 40,
  }}>
    <div style={{display: 'flex', alignItems: 'center', minWidth: 0, gap: 20}}>
      <div aria-hidden="true" style={{
        width: 13, height: 36, borderRadius: 5,
        background: theme.accent, boxShadow: '0 0 26px rgba(250,204,21,.24)',
      }}/>
      <span style={{...labelStyle, color: theme.text}}>{series.toUpperCase()}</span>
    </div>
    <div style={{...labelStyle, textAlign: 'right', fontSize: 18, maxWidth: 650}}>
      {chapterLabel ?? level}
    </div>
  </header>
);
