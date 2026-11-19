import { homedir } from 'node:os';
import { resolve } from 'node:path';
import { call, withReaper } from '../../shared/reaper.mjs';
import { album, title } from './arrange.mjs';

const session = resolve(homedir(),'Library/Application Support/REAPER/MCP Sessions/50 Calls Interlude');
const projectPath = resolve(session,title+'.rpp');
const duration = 84;
const rate = 80 / 81.9856;

async function itemAt(trackIndex,position) {
  const {items} = await call('list_media_items',{trackIndex});
  const item = items.find(item=>Math.abs(item.position-position) < .002);
  if (!item) throw Error(`Expected an item on track ${trackIndex} at ${position}s.`);
  return item;
}

async function edit(trackIndex,from,properties) {
  const {itemIndex} = await itemAt(trackIndex,from);
  await call('set_media_item_properties',{trackIndex,itemIndex,...properties});
}

async function insert(trackIndex,file,start,length,position,options={}) {
  const {items} = await call('list_media_items',{trackIndex});
  const stagingPosition = Math.max(position,...items.map(item=>item.position+item.length+.01));
  const item = await call('insert_audio_file',{
    trackIndex,filePath:resolve(session,'Media',file),position:stagingPosition
  });
  await call('trim_media_item',{
    trackIndex,itemIndex:item.itemIndex,trimStart:start,trimEnd:Math.max(0,item.length-start-length)
  });
  await call('set_media_item_properties',{
    trackIndex,itemIndex:item.itemIndex,position,length,...options
  });
}

async function envelope(trackIndex,points) {
  await call('clear_envelope',{trackIndex,envelopeIndex:0});
  await call('insert_envelope_points',{
    trackIndex,envelopeIndex:0,points:JSON.stringify(points.map(([time,db])=>({time,db,shape:0})))
  });
}

async function render(filePattern,extra={},tracks) {
  await call('set_render_settings',{
    outputDirectory:resolve(session,'Renders'),filePattern,format:'wav',source:'master',
    bounds:'custom',startTime:0,endTime:duration,sampleRate:44100,channels:2,
    ...(extra.format==='mp3'?{}:{bitDepth:'24'}),normalize:'off',limit:false,...extra
  });
  await call('run_action',{action:40100});
  await call('run_action',{action:40101});
  console.log(JSON.stringify(await call('render_project',{
    overwrite:true,analyze:false,...(tracks?{tracks}:{})
  })));
}

await withReaper(async()=>{
  const project = await call('get_project_info');
  if (project.name!==projectPath || project.tempo!==80 || project.trackCount!==6 ||
      project.isPlaying || project.isRecording) throw Error('Expected the stopped 50 Calls interlude session.');
  if (process.argv[2]==='arrange-interlude') {
    const tracks = await call('list_tracks');
    if (tracks[3].name!=='Juice WRLD | Refrain' || tracks[4].name!=='Kanye West | Verse' ||
        tracks[5].name!=='Guitar | Return pickup') throw Error('Unexpected 50 Calls source session.');
    const {items:drums} = await call('list_media_items',{trackIndex:0});
    const percussion = drums.find(item=>item.name==='Verse-Percussion.wav');
    if (!percussion) throw Error('Expected the previous verse percussion item.');
    await call('delete_media_item',{trackIndex:0,itemIndex:percussion.itemIndex});
    for (const i of [0,1,2]) {
      await edit(i,6,{position:12});
      await edit(i,18,{position:24,length:36.035});
      await edit(i,57,{position:60});
    }
    await edit(2,0,{length:12.028,fadeOutLength:.085});
    await edit(2,69,{position:72,length:12,fadeInLength:.095,fadeOutLength:2.0,volume:-1});
    await edit(1,69,{position:72,length:6,fadeInLength:.063,fadeOutLength:2.8,volume:-3.8});
    await insert(1,'Verse-Bass.wav',2.192,6.035,6,{
      fadeInLength:1.4,fadeOutLength:.065,volume:-3.7
    });
    await edit(3,6.248,{position:12.248});
    await edit(3,57.248,{position:60.248,volume:-.2});
    await edit(4,18.3740593,{
      position:30.3740593,length:(15.305-3.925)/rate,fadeOutLength:.04
    });
    await edit(4,43.844676,{position:42.344676});
    const pickup = await itemAt(5,55.5);
    await call('delete_media_item',{trackIndex:5,itemIndex:pickup.itemIndex});
    await call('set_track_info',{track:5,name:'Upright piano | Responses',color:'#AA987D'});
    await call('set_track_property',{trackIndex:5,property:'volume',value:5.7});
    await insert(5,'Interlude piano.wav',0,84,0,{fadeOutLength:.48});

    await envelope(0,[
      [0,-4],[11.97,-2.5],[12.01,-1.6],[13.2,-.55],[23.72,-.55],[24.02,-3.6],
      [35.6,-3.6],[36.06,-3.0],[38.0,-.9],[53.45,-.9],[54.0,-15],[54.48,-48],
      [59.96,-48],[62.96,-48],[63.01,-5.0],[65.96,-5.0],[66.04,-.95],[71.65,-.95],[72,-8]
    ]);
    await envelope(1,[
      [0,-5],[6,-4],[10.8,-1.4],[11.93,-.5],[12.05,0],[23.68,0],[24.1,-3.3],
      [26.4,-3.0],[29.8,.45],[30.2,.45],[41.8,.45],[42.4,.1],[53.42,.1],
      [54.18,-4.9],[57.7,-6.5],[59.95,-10],[60.05,-12],[62.96,-12],[63.02,-3.8],
      [65.93,-3.8],[66.05,-.4],[71.72,-.4],[72,-1.6],[77.7,-4.1]
    ]);
    await envelope(2,[
      [0,.35],[6,.55],[11.88,.4],[12.06,-.2],[23.72,-.2],[24.16,.55],
      [29.85,.55],[30.32,.15],[53.82,.15],[54.35,.25],[59.87,.15],
      [60.09,.30],[62.97,.30],[63.2,0],[66.05,.05],[71.7,.05],[72,.25],[84,-.7]
    ]);
    const {regions} = await call('list_regions');
    for (const region of regions) await call('delete_region',{regionIndex:region.index});
    for (const [start,end,name] of [
      [0,12,'Guitar intro'],[12,24,'Juice | First chorus'],[24,30,'Instrumental answer'],
      [30,54,'Kanye | Eight bars'],[54,60,'Instrumental release'],
      [60,72,'Juice | Final chorus'],[72,84,'Guitar and piano outro']
    ]) await call('add_region',{start,end,name});
    await call('save_project',{path:projectPath,overwrite:true});
    await render('Interlude premaster');
    await render('$track',{source:'stems',outputDirectory:resolve(session,'Renders/Stems')},[0,1,2,3,4,5]);
  } else if (process.argv[2]==='master') {
    if ((await call('list_tracks'))[5].name!=='Upright piano | Responses') {
      throw Error('Expected the revised arrangement.');
    }
    await call('set_track_property',{trackIndex:5,property:'volume',value:5.7});
    await render('Interlude premaster');
    await render(title,{
      format:'mp3',mp3Bitrate:320,normalize:'lufs_i',normalizeTarget:-14.2,
      limit:true,limitCeiling:-1.55,limitTruePeak:true,
      metadata:{title,artist:'Kanye West, Juice WRLD & Veer',album}
    });
    await call('save_project',{path:projectPath,overwrite:true});
  }
});
