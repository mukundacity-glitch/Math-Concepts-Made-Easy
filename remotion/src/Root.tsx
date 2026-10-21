import React from 'react';
import {AbsoluteFill, Composition, interpolate, useCurrentFrame, useVideoConfig, Img, staticFile} from 'remotion';
import katex from 'katex';
import 'katex/dist/katex.min.css';

export type Visual = {
  model: 'function_machine' | 'coordinate_graph' | 'unit_circle' | 'number_line' | 'area_tiles' | 'probability_tree' | 'data_plot' | 'vectors' | 'equation_steps' | 'countable_objects' | 'algebra_area';
  labels?: string[];
  values?: number[];
  points?: number[][][];
  xRange?: [number, number];
  yRange?: [number, number];
  angle?: number;
  showValues?: boolean;
  static?: boolean;
  remove?: number;
};
export type Beat = {text: string; start: number; end: number};
export type Panel = {title: string; start: number; end: number; lines: string[]; lineStarts: number[]; visual: Visual; artwork?: string};
export type Props = {
  title: string; stage: string; label: string; duration: number;
  panels?: Panel[]; pauses?: {start:number;seconds:number}[]; artwork?: string;
  styleName: string; lines: string[]; lineStarts: number[];
  visual: Visual; beats: Beat[]; pauseStart?: number; pauseSeconds?: number;
};
const tokens = {
  width: 1920, height: 1080, margin: 80, gap: 48,
  title: 62, text: 38, math: 46, label: 26,
};
const palettes = {
  paper: {bg:'#F6F3EA',ink:'#142C36',muted:'#53696B',accent:'#006D77',other:'#AA4B21',grid:'#CBD5CF',card:'#FFFFFF'},
  midnight: {bg:'#0C1726',ink:'#EDF5FF',muted:'#A6B8CE',accent:'#55DDD2',other:'#FFBF69',grid:'#26374E',card:'#13243A'},
  blueprint: {bg:'#EAF1FB',ink:'#142E5A',muted:'#4A6587',accent:'#2355BB',other:'#A24924',grid:'#CCD9ED',card:'#FFFFFF'},
};
const clamp = {extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;
const colors = (name: string) => palettes[name as keyof typeof palettes] ?? palettes.paper;
const Formula: React.FC<{text: string; color: string}> = ({text,color}) => (
  <div style={{color,fontSize:tokens.math,lineHeight:1.6,overflowWrap:'anywhere'}} dangerouslySetInnerHTML={{__html:katex.renderToString(text,{throwOnError:true,displayMode:true,strict:'ignore'})}} />
);

const Diagram: React.FC<{visual: Visual; progress: number; palette: ReturnType<typeof colors>; visibleValues: number}> = ({visual,progress,palette,visibleValues}) => {
  const ink = palette.ink;
  const accent = palette.accent;
  const other = palette.other;
  const values = visual.values ?? [];
  const labels = visual.labels ?? [];
  const reveal = Math.max(0.02,progress);
  const xRange = visual.xRange ?? [-5,5];
  const yRange = visual.yRange ?? [-5,5];
  const x = (value:number) => 65+(value-xRange[0])/(xRange[1]-xRange[0])*810;
  const y = (value:number) => 565-(value-yRange[0])/(yRange[1]-yRange[0])*500;
  const axes = <g stroke={palette.grid} strokeWidth={3}>
    <line x1={65} y1={y(0)} x2={875} y2={y(0)}/><line x1={x(0)} y1={65} x2={x(0)} y2={565}/>
    {[0,1,2,3,4,5,6,7,8,9,10].map(index=><g key={index} opacity={0.4}><text x={65+81*index} y={y(0)+26} fill={ink} stroke="none" textAnchor="middle" fontSize={18}>{Number((xRange[0]+index*(xRange[1]-xRange[0])/10).toFixed(1))}</text><text x={x(0)-12} y={65+50*index} fill={ink} stroke="none" textAnchor="end" fontSize={18}>{Number((yRange[1]-index*(yRange[1]-yRange[0])/10).toFixed(1))}</text><line x1={65+81*index} y1={65} x2={65+81*index} y2={565}/><line x1={65} y1={65+50*index} x2={875} y2={65+50*index}/></g>)}
  </g>;
  let content:React.ReactNode;
  switch (visual.model) {
    case 'function_machine': {
      const centers = labels.map((_,index)=>140+index*(660/Math.max(1,labels.length-1)));
      content = <g>{centers.map((center,index)=><g key={index} opacity={interpolate(progress,[index/Math.max(1,labels.length)*0.5,index/Math.max(1,labels.length)*0.5+0.15],[0,1],clamp)}>
        <rect x={center-110} y={225} width={220} height={160} rx={24} fill={palette.card} stroke={index%2?other:accent} strokeWidth={5}/>
        <text x={center} y={315} textAnchor="middle" fill={ink} fontSize={Math.min(38,320/Math.max(1,labels[index].length))}>{labels[index]}</text>
        {index<centers.length-1 && <path d={`M${center+115},305 H${centers[index+1]-120} l-15,-10 m15,10 l-15,10`} stroke={accent} strokeWidth={5} fill="none"/>}
      </g>)}<circle cx={90+progress*760} cy={420} r={15} fill={other}/>
      {visual.showValues!==false && values.map((value,index)=><text key={index} x={centers[index]??800} y={180} textAnchor="middle" fontSize={44} fill={accent} opacity={index<visibleValues?1:0}>{value}</text>)}
      </g>;
      break;
    }
    case 'coordinate_graph':
      content = <g>{axes}{(visual.points??[]).map((series,index)=>{
        const shown=series.slice(0,Math.max(2,Math.ceil(series.length*reveal)));
        const point=shown[shown.length-1];
        return <g key={index}><polyline points={shown.map(pair=>`${x(pair[0])},${y(pair[1])}`).join(' ')} fill="none" stroke={index%2?other:accent} strokeWidth={6}/>{point&&<circle cx={x(point[0])} cy={y(point[1])} r={9} fill={index%2?other:accent}/>}<text x={80} y={610+index*32} fill={index%2?other:accent} fontSize={26}>{labels[index]}</text></g>;
      })}<text x={875} y={y(0)-15} fill={ink} fontSize={28}>x</text><text x={x(0)+15} y={65} fill={ink} fontSize={28}>y</text></g>;
      break;
    case 'unit_circle': {
      const angle = progress*(visual.angle??Math.PI*2);
      const pointX=345+205*Math.cos(angle), pointY=320-205*Math.sin(angle);
      content=<g><line x1={85} y1={320} x2={610} y2={320} stroke={palette.grid} strokeWidth={3}/><line x1={345} y1={60} x2={345} y2={580} stroke={palette.grid} strokeWidth={3}/><circle cx={345} cy={320} r={205} fill="none" stroke={ink} strokeWidth={4}/><path d={`M345,320 L${pointX},${pointY} L${pointX},320 Z`} stroke={accent} fill={accent} fillOpacity={0.12} strokeWidth={4}/><circle cx={pointX} cy={pointY} r={12} fill={other}/>{visual.showValues!==false&&<><text x={640} y={260} fill={accent} fontSize={36}>cos θ = {Math.cos(angle).toFixed(2)}</text><text x={640} y={330} fill={other} fontSize={36}>sin θ = {Math.sin(angle).toFixed(2)}</text></>}<text x={640} y={400} fill={ink} fontSize={32}>θ = {(angle/Math.PI).toFixed(2)}π</text></g>;
      break;
    }
    case 'number_line': {
      const position=values[0]??0;
      content=<g><line x1={65} y1={320} x2={875} y2={320} stroke={ink} strokeWidth={4}/>{Array.from({length:11},(_,index)=><g key={index}><line x1={65+81*index} y1={305} x2={65+81*index} y2={335} stroke={ink} strokeWidth={3}/><text x={65+81*index} y={385} fill={ink} textAnchor="middle" fontSize={30}>{(xRange[0]+index*(xRange[1]-xRange[0])/10).toFixed(1)}</text></g>)}<circle cx={x(position*progress)} cy={320} r={16} fill={accent}/></g>;
      break;
    }
    case 'countable_objects': {
      const count=values.reduce((sum,value)=>sum+value,0);
      content=<g>{Array.from({length:count},(_,index)=>{
        const positionX=150+(index%6)*120,positionY=150+Math.floor(index/6)*140;
        const removed=index>=count-(visual.remove??0);
        return <g key={index} transform={`translate(${positionX},${positionY})`} opacity={removed?interpolate(progress,[0.4,0.7],[1,0],clamp):1}>
          <path d="M0,-20 C-42,-55 -64,-8 -38,30 C-22,55 -8,42 0,42 C12,42 27,55 42,28 C65,-10 40,-55 0,-20" fill={index<(values[0]??0)?accent:other}/><path d="M0,-22 Q-4,-48 8,-58" stroke={ink} strokeWidth={6} fill="none"/><path d="M7,-47 Q37,-68 36,-43 Q21,-32 7,-47" fill={palette.muted}/>
          <text y={86} fill={ink} fontSize={26} textAnchor="middle">{index+1}</text>
          {removed&&<path d="M-40,-40 L40,40 M40,-40 L-40,40" stroke={other} strokeWidth={6} opacity={interpolate(progress,[0.4,0.7],[0,1],clamp)}/>}
        </g>;
      })}<text x={80} y={50} fill={ink} fontSize={30}>{labels[0]??''}</text></g>;
      break;
    }
    case 'algebra_area': {
      const a=values[0]??2,b=values[1]??3;
      const unit=Math.min(56,240/b,500/a);
      content=<g><rect x={160} y={100} width={220} height={220} fill={accent} opacity={0.85}/><text x={270} y={220} fill={palette.card} fontSize={42} textAnchor="middle">x²</text>
        {Array.from({length:a},(_,index)=><g key={`a${index}`} opacity={interpolate(progress,[0.1,0.4],[0,1],clamp)}><rect x={386+index*unit} y={100} width={unit-6} height={220} fill={other}/><text x={410+index*unit} y={220} fill={palette.card} fontSize={26} textAnchor="middle">x</text></g>)}
        {Array.from({length:b},(_,index)=><g key={`b${index}`} opacity={interpolate(progress,[0.3,0.6],[0,1],clamp)}><rect x={160} y={326+index*unit} width={220} height={unit-6} fill={other}/><text x={270} y={360+index*unit} fill={palette.card} fontSize={26} textAnchor="middle">x</text></g>)}
        {Array.from({length:a*b},(_,index)=><rect key={`u${index}`} x={386+index%a*unit} y={326+Math.floor(index/a)*unit} width={unit-6} height={unit-6} fill={accent} opacity={interpolate(progress,[0.5,0.8],[0,1],clamp)}/>)}
        <text x={160} y={65} fill={ink} fontSize={34}>x + {a}</text><text x={75} y={300} fill={ink} fontSize={34} transform="rotate(-90 75 300)">x + {b}</text>
        <text x={160} y={610} fill={ink} fontSize={34}>{a+b} x-tiles · {a*b} unit tiles</text></g>;
      break;
    }
    case 'area_tiles': {
      const across=values[0]??3, down=values[1]??2;
      const cell=Math.min(100,700/across,450/down);
      content=<g>{Array.from({length:across*down},(_,index)=><rect key={index} x={130+(index%across)*cell} y={140+Math.floor(index/across)*cell} width={cell-6} height={cell-6} rx={8} fill={index<across?accent:other} opacity={interpolate(progress,[index/Math.max(1,across*down)*0.6,index/Math.max(1,across*down)*0.6+0.2],[0,1],clamp)}/>)}<text x={130} y={110} fill={ink} fontSize={36}>{labels[0]??`${across} × ${down}`}</text></g>;
      break;
    }
    case 'probability_tree':
      content=<g>{labels.map((label,index)=>{const pointY=120+index*100;return <g key={index} opacity={interpolate(progress,[index/labels.length*0.5,index/labels.length*0.5+0.2],[0,1],clamp)}><line x1={150} y1={320} x2={650} y2={pointY} stroke={accent} strokeWidth={5}/><circle cx={650} cy={pointY} r={12} fill={other}/><text x={680} y={pointY+10} fill={ink} fontSize={32}>{label}</text></g>;})}</g>;
      break;
    case 'data_plot': {
      const maximum=Math.max(1,...values);
      const barWidth=700/Math.max(1,values.length);
      content=<g><line x1={100} y1={530} x2={850} y2={530} stroke={ink} strokeWidth={3}/>{values.map((value,index)=><g key={index}><rect x={120+index*barWidth} y={530-value/maximum*360*progress} width={barWidth*0.65} height={value/maximum*360*progress} fill={index%2?other:accent} rx={8}/><text x={120+index*barWidth} y={580} fill={ink} fontSize={28}>{labels[index]??String(index+1)}</text><text x={120+index*barWidth} y={500-value/maximum*360*progress} fill={ink} fontSize={30}>{value}</text></g>)}</g>;
      break;
    }
    case 'vectors':
      content=<g>{axes}{(visual.points??[]).map((segment,index)=><g key={index}><line x1={x(segment[0][0])} y1={y(segment[0][1])} x2={x(segment[0][0]+(segment[1][0]-segment[0][0])*progress)} y2={y(segment[0][1]+(segment[1][1]-segment[0][1])*progress)} stroke={index%2?other:accent} strokeWidth={7}/><circle cx={x(segment[1][0])} cy={y(segment[1][1])} r={8} fill={other}/><text x={x(segment[1][0])+15} y={y(segment[1][1])} fill={ink} fontSize={28}>{labels[index]}</text></g>)}</g>;
      break;
    default:
      content=<g>{labels.map((label,index)=><g key={index} opacity={interpolate(progress,[index/Math.max(1,labels.length)*0.6,index/Math.max(1,labels.length)*0.6+0.2],[0,1],clamp)}><rect x={90} y={80+index*180} width={760} height={160} rx={16} fill={palette.card} stroke={palette.grid} strokeWidth={2}/><foreignObject x={120} y={90+index*180} width={700} height={140}><div style={{color:ink,fontSize:label.length>120?26:32,lineHeight:1.3,overflowWrap:"anywhere",height:"100%",display:"flex",alignItems:"center"}}>{label}</div></foreignObject></g>)}</g>;
  }
  return <svg viewBox="0 0 940 680" width="100%" height="100%" style={{overflow:'hidden',fontFamily:'Arial, sans-serif'}}>{content}</svg>;
};

export const MathScene: React.FC<Props> = input => {
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  const seconds=frame/fps;
  const currentPanel=input.panels?.find(panel=>seconds>=panel.start && seconds<panel.end) ?? input.panels?.[0];
  const props={...input,...(currentPanel?{title:currentPanel.title,lines:currentPanel.lines,lineStarts:currentPanel.lineStarts,visual:currentPanel.visual,artwork:currentPanel.artwork}: {})};
  const panelStart=currentPanel?.start??0;
  const panelEnd=currentPanel?.end??props.duration;
  const palette=colors(props.styleName);
  const currentPause=props.pauses?.find(pause=>seconds>=pause.start&&seconds<pause.start+pause.seconds);
  const pauseActive=Boolean(currentPause);
  const activeLine=Math.max(0,props.lineStarts.reduce((current,start,index)=>seconds>=start?index:current,0));
  const groupStart=Math.floor(activeLine/3)*3;
  const activeBeat=props.beats.find(beat=>seconds>=beat.start && seconds<=beat.end);
  const firstMath=props.lineStarts[0];
  const revealEnd=firstMath!==undefined && firstMath>panelStart+0.5?firstMath:panelEnd-1;
  const progress=props.visual.static?1:interpolate(frame,[panelStart*fps,Math.max(panelStart*fps+fps,revealEnd*fps)],[0,1],clamp);
  const story=Boolean(props.artwork);
  return <AbsoluteFill style={{backgroundColor:palette.bg,color:palette.ink,fontFamily:'Arial, sans-serif',padding:tokens.margin,boxSizing:'border-box'}}>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',fontSize:tokens.label,color:palette.muted,letterSpacing:2}}><span>MATH CONCEPTS MADE EASY</span><span>{props.label.toUpperCase()}</span></div>
    <h1 style={{fontSize:tokens.title,margin:'36px 0 24px',fontWeight:700,lineHeight:1.15,maxWidth:1660}}>{props.title}</h1>
    <div style={{height:4,width:100,backgroundColor:palette.accent,marginBottom:32}}/>
    <div style={{display:'grid',gridTemplateColumns:story?'1fr':props.stage==='worked_example'?'1fr 1.2fr':'1.2fr 1fr',gap:tokens.gap,flex:1,minHeight:0}}>
      <div style={{border:`2px solid ${palette.grid}`,borderRadius:28,backgroundColor:palette.card,overflow:'hidden',position:'relative'}}>
        {story?<><Img src={staticFile(props.artwork!)} style={{width:'100%',height:'100%',objectFit:'contain',scale:interpolate(frame,[0,props.duration*fps],[1,1.08],clamp)}}/><div style={{position:'absolute',bottom:32,left:24,right:24,backgroundColor:palette.card,padding:20,borderRadius:16,display:'flex',justifyContent:'space-around',color:palette.ink,fontSize:tokens.text}}><span>01 · Wash</span><span>→</span><span>02 · Dry</span></div></>:<Diagram visual={props.visual} progress={progress} palette={palette} visibleValues={props.lines.length?props.lineStarts.filter(start=>seconds>=start).length+1:Math.floor(progress*3)+1}/> }
        {pauseActive&&<div style={{position:'absolute',inset:0,backgroundColor:palette.card,display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',gap:32}}><div style={{fontSize:tokens.text}}>Your turn. Think it through.</div><div style={{fontSize:150,color:palette.accent}}>{Math.ceil((currentPause?.seconds??0)-(seconds-(currentPause?.start??0)))}</div></div>}
      </div>
      <div style={{display:story?'none':'flex',flexDirection:'column',justifyContent:'center',gap:20,minWidth:0}}>
        {props.lines.slice(groupStart,groupStart+3).map((line,index)=>{
          const lineIndex=groupStart+index;
          const start=props.lineStarts[lineIndex]??0;
          return <div key={lineIndex} style={{padding:'16px 24px',borderRadius:18,backgroundColor:lineIndex===activeLine?palette.card:'transparent',borderLeft:`5px solid ${lineIndex===activeLine?palette.accent:palette.grid}`,opacity:interpolate(seconds,[start,start+0.35],[0,1],clamp)}}><Formula text={line} color={lineIndex===activeLine?palette.ink:palette.muted}/></div>;
        })}
        {props.lines.length===0&&<div style={{fontSize:tokens.text,lineHeight:1.5}}>{props.title}</div>}
      </div>
    </div>
    <div style={{fontSize:tokens.label,color:palette.muted,marginTop:28,display:'flex',justifyContent:'space-between'}}><span>{pauseActive?'Solve before the answer appears':props.visual.model.replaceAll('_',' ').toUpperCase()}</span><span>Understand • Work it out • Check</span></div>
  </AbsoluteFill>;
};

export const Root:React.FC=()=> <Composition id="MathScene" component={MathScene} width={tokens.width} height={tokens.height} fps={30} durationInFrames={300}
  defaultProps={{title:'Composition: order changes the answer',stage:'concept',label:'Function machine',duration:10,styleName:'paper',lines:['g(2)=2+3=5','f(g(2))=5^2=25'],lineStarts:[0,4],visual:{model:'function_machine',labels:['Input','g: +3','f: square'],values:[2,5,25]},beats:[]}}
  calculateMetadata={({props})=>({durationInFrames:Math.max(1,Math.ceil(props.duration*30))})}/>;
