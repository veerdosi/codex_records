import { homedir } from 'node:os';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';
import { call, withReaper } from '../../shared/reaper.mjs';

const here=dirname(fileURLToPath(import.meta.url));
const cfg=JSON.parse(readFileSync(resolve(here,'analysis/arrangement.json')));
const title='Muh Pe Lovey Dovey';
const session=resolve(homedir(),'Library/Application Support/REAPER/MCP Sessions',title);
const projectPath=resolve(session,title+'.rpp');
const artist=cfg.artist;
const tracks=cfg.tracks;
const duration=cfg.duration;

async function place(t, f, s, len, pos, db=0, fadeInLength=.008, fadeOutLength=.034) {
  const {items}=await call('list_media_items',{trackIndex:t});
  if(items.some(x=>x.name===f && Math.abs(x.position-pos)<.001 && Math.abs(x.length-len)<.001)) return;
  const staging=Math.max(pos,...items.map(x=>x.position+x.length+.01));
  const x=await call('insert_audio_file',{trackIndex:t,filePath:resolve(session,'Media',f),position:staging});
  if(s || Math.abs(x.length-len)>.006) await call('trim_media_item',{
    trackIndex:t,itemIndex:x.itemIndex,trimStart:s,trimEnd:Math.max(0,x.length-s-len)
  });
  await call('set_media_item_properties',{trackIndex:t,itemIndex:x.itemIndex,position:pos,
    length:len,volume:db,fadeInLength,fadeOutLength});
}

async function render(filePattern, opts={}, selected) {
  await call('set_render_settings',{
    outputDirectory:resolve(session,selected?'Renders/Stems':'Renders'),
    filePattern,format:'wav',source:selected?'stems':'master',
    sampleRate:48000,channels:2,bounds:'custom',startTime:0,endTime:duration,
    ...(opts.format==='mp3'?{}:{bitDepth:'24'}),
    normalize:'off',limit:false,...opts
  });
  await call('run_action',{action:40100});
  await call('run_action',{action:40101});
  return call('render_project',{overwrite:true,analyze:false,...(selected?{tracks:selected}:{})});
}
async function setVol(index,db) {
  return call('set_track_property',{trackIndex:index,property:'volume',value:db});
}
await withReaper(async()=>{
  const mode=process.argv[2];
  const project=await call('get_project_info');
  if (mode==='arrange' || mode==='init' || mode==='populate') {
    if (mode!=='populate') {
    if (project.trackCount || project.name || project.isPlaying || project.isRecording) {
      throw Error('Expected a stopped blank REAPER project.');
    }
    await call('set_project_tempo',{bpm:84});
    await call('set_project_settings',{title,author:artist,sampleRate:48000,useProjectSampleRate:true,
      repeat:false,notes:'Farebi × Namastute. 84 BPM. Audio stems from Demucs and Rubber Band R3; original MIDI and Csound score in the song work folder.'});
    const ops=tracks.flatMap(([name,,volume],i)=>[
      {op:'add_track',name,as:'$t'+i},{op:'set_track',track:'$t'+i,volume}
    ]);
    await call('run_plan',{ops,label:'Create Farebi and Namastute tracks'});
    for (let i=0;i<tracks.length;i++) await call('set_track_info',{track:i,color:tracks[i][1]});
    for(const [start,end,name] of cfg.regions) await call('add_region',{start,end,name});
    } else if (project.tempo!==84 || project.trackCount!==tracks.length ||
               (await call('list_tracks')).map(t=>t.name).join('|')!==tracks.map(t=>t[0]).join('|')) {
      throw Error('Expected the staged project.');
    }
    if (mode==='init') {
      console.log(await call('save_project',{path:projectPath,overwrite:true}));
      return;
    }
    for (let i=0;i<tracks.length;i++) {
      for(const clip of cfg.items.filter(x=>x[0]===i)) await place(...clip);
      console.log('Arranged',tracks[i][0]);
    }
    await call('save_project',{path:projectPath,overwrite:true});
    console.log(await render('Premaster'));
    console.log(await render('$track',{},tracks.map((_,i)=>i)));
  } else {
    const live=await call('list_tracks');
    if(project.tempo!==84 || project.trackCount!==tracks.length || project.isPlaying ||
       live.map(t=>t.name).join('\n')!==tracks.map(t=>t[0]).join('\n')) throw Error('Unexpected active REAPER session.');
    for (let i=0;i<tracks.length;i++) await setVol(i,tracks[i][2]);
    if(mode==='reconcile') {
      const before=JSON.parse(readFileSync(resolve(here,'analysis/layout_before_trim.json'))).items;
      const eq=(a,b)=>a.every((v,i)=>v===b[i]);
      for(const old of before.filter(a=>!cfg.items.some(b=>eq(a,b)))) {
        const [trackIndex,file,,len,pos]=old;
        const {items}=await call('list_media_items',{trackIndex});
        const item=items.find(x=>x.name===file && Math.abs(x.length-len)<.001 && Math.abs(x.position-pos)<.001);
        if (item) await call('delete_media_item',{trackIndex,itemIndex:item.itemIndex});
      }
      for(const clip of cfg.items.filter(a=>!before.some(b=>eq(a,b)))) await place(...clip);
      await call('save_project',{path:projectPath,overwrite:true});
    }
    if(mode==='master') {
      console.log(await render(title,{format:'mp3',mp3Bitrate:320,normalize:'lufs_i',
        normalizeTarget:-14.2,limit:true,limitCeiling:-1.55,limitTruePeak:true,
        metadata:{title,artist,album:'unfinished'}}));
    } else {
      console.log(await render('Premaster'));
      console.log(await render('$track',{},tracks.map((_,i)=>i)));
    }
    await call('save_project',{path:projectPath,overwrite:true});
  }
});
