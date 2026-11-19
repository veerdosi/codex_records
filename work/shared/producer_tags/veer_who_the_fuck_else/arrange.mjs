import { homedir } from 'node:os';
import { resolve } from 'node:path';
import { call, withReaper } from '../../reaper.mjs';

const title = 'Veer Producer Tag';
const session = resolve(homedir(),'Library/Application Support/REAPER/MCP Sessions','Veer Producer Tag Beat');
const duration = 2.58;
const tracks = [
  {name:'Veer | Recorded vocal', file:'Veer first take.wav', at:.205, gain:-2, fadeIn:.015, fadeOut:.030, color:'#6D9484'},
  {name:'Vocal reflection', file:'Short reflection.wav', at:.205, gain:0, fadeIn:.006, fadeOut:.040, color:'#6D9484'},
  {name:'Upright piano', file:'Upright.wav', at:0, gain:.7, fadeIn:.006, fadeOut:.028, color:'#A37C5F'},
  {name:'Synth bass', file:'Bass.wav', at:0, gain:-7.5, fadeIn:.006, fadeOut:.028, color:'#A37C5F'},
  {name:'Black Pearl drums', file:'Drums.wav', at:0, gain:1.6, fadeIn:.003, fadeOut:.028, color:'#A37C5F'},
];

async function render(filePattern, extra={}, selection) {
  await call('set_render_settings',{
    outputDirectory:resolve(session,'Renders'),filePattern,format:'wav',source:'master',
    bounds:'custom',startTime:0,endTime:duration,sampleRate:48000,channels:2,bitDepth:'24',
    normalize:'off',limit:false,...extra
  });
  await call('run_action',{action:40100});
  await call('run_action',{action:40101});
  console.log(JSON.stringify(await call('render_project',{
    overwrite:true,analyze:false,...(selection?{tracks:selection}:{})
  })));
}

await withReaper(async()=>{
  const project = await call('get_project_info');
  if (project.isPlaying || project.isRecording) throw Error('Expected a stopped tag project.');
  if (process.argv[2] === 'arrange') {
    if (project.name || project.trackCount) throw Error('Expected a blank REAPER tab.');
    await call('set_project_tempo',{bpm:96});
    await call('set_project_settings',{title,author:'Veer',sampleRate:48000,useProjectSampleRate:true});
    await call('run_plan',{label:'Build the Veer tag beat',ops:tracks.flatMap(({name,gain},i)=>[
      {op:'add_track',name,as:'$tag'+i},{op:'set_track',track:'$tag'+i,volume:gain}
    ])});
    for (const [trackIndex,track] of tracks.entries()) {
      await call('set_track_info',{track:trackIndex,color:track.color});
      const item = await call('insert_audio_file',{
        trackIndex,filePath:resolve(session,'Media',track.file),position:track.at
      });
      await call('set_media_item_properties',{
        trackIndex,itemIndex:item.itemIndex,fadeInLength:track.fadeIn,fadeOutLength:track.fadeOut
      });
    }
    const {fxIndex} = await call('add_fx',{trackIndex:0,fxName:'ReaComp (Cockos)'});
    const values = {0:.1778,1:.0111,2:.021,3:.019,7:.0043,13:.08};
    await call('set_multiple_fx_parameters',{
      updates:Object.entries(values).map(([paramIndex,value])=>({
        trackIndex:0,fxIndex,paramIndex:Number(paramIndex),value
      }))
    });
    const {envelopeIndex} = await call('create_track_envelope',{trackIndex:2,envelopeName:'Trim Volume'});
    await call('insert_envelope_points',{trackIndex:2,envelopeIndex,points:JSON.stringify(
      [[0,0],[.13,0],[.23,-3],[.43,-3],[.58,0]].map(([time,db])=>({time,db,shape:0}))
    )});
    await call('set_envelope_properties',{trackIndex:2,envelopeIndex,visible:true,armed:false});
    await call('add_region',{start:0,end:duration,name:'Veer. Who the fuck else?'});
    await call('save_project',{path:resolve(session,title+'.rpp'),overwrite:true});
    await render('Tag premaster');
    await render('$track',{source:'stems',outputDirectory:resolve(session,'Renders/Stems')},[0,1,2,3,4]);
  } else if (process.argv[2] === 'master') {
    const existing = await call('list_tracks');
    if (existing.length!==tracks.length || existing.some((track,i)=>track.name!==tracks[i].name)) {
      throw Error('Expected the Veer beat arrangement.');
    }
    await render('veer_tag',{
      normalize:'lufs_i',normalizeTarget:-14.5,limit:true,limitCeiling:-1.65,limitTruePeak:true,
      metadata:{title:'Veer. Who the fuck else?',artist:'Veer'}
    });
    await call('save_project',{path:resolve(session,title+'.rpp'),overwrite:true});
  }
});
