import { homedir } from 'node:os';
import { resolve } from 'node:path';
import { call, withReaper } from '../../shared/reaper.mjs';
import { album,title } from './arrange.mjs';

const session = resolve(homedir(),'Library/Application Support/REAPER/MCP Sessions/50 Calls Interlude');
const projectPath = resolve(session,'50 Calls Clean Voices.rpp');

async function replaceSource(trackIndex, name, file, offset, expectedPosition) {
  const {items} = await call('list_media_items',{trackIndex});
  const old = items.find(item=>item.name===name && Math.abs(item.position-expectedPosition)<.001);
  if (!old) throw Error(`Expected ${name} on track ${trackIndex}.`);
  const staging = Math.max(...items.map(item=>item.position+item.length))+.05;
  await call('delete_media_item',{trackIndex,itemIndex:old.itemIndex});
  const {itemIndex,length} = await call('insert_audio_file',{
    trackIndex,position:staging,filePath:resolve(session,'Media',file)
  });
  await call('trim_media_item',{
    trackIndex,itemIndex,trimStart:offset,trimEnd:length-offset-old.length*old.playRate
  });
  await call('set_media_item_properties',{
    trackIndex,itemIndex,position:old.position,length:old.length,playRate:old.playRate,volume:old.volume,
    fadeInLength:old.fadeInLength,fadeOutLength:old.fadeOutLength
  });
}

async function render(filePattern, extra={}, tracks) {
  await call('set_render_settings',{
    outputDirectory:resolve(session,'Renders'),filePattern,format:'wav',source:'master',
    bounds:'custom',startTime:0,endTime:84,sampleRate:44100,channels:2,
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
  if (project.name!==projectPath || project.isPlaying || project.isRecording || project.trackCount!==6) {
    throw Error('Expected the stopped 50 Calls Clean Voices session.');
  }
  if (process.argv[2] === 'finalize') {
    const tracks = await call('list_tracks');
    const {items} = await call('list_media_items',{trackIndex:4});
    if (!items.some(item=>item.name==='Kanye-verse-entry-clean.wav')) throw Error('Expected the cleanup render session.');
    for (const {itemIndex} of items.toReversed()) await call('delete_media_item',{trackIndex:4,itemIndex});
    for (let fxIndex=0;fxIndex<tracks[4].fxCount;fxIndex++) {
      await call('set_fx_enabled',{trackIndex:4,fxIndex,enabled:0});
    }
    await call('set_track_property',{trackIndex:4,property:'volume',value:0});
    const item = await call('insert_audio_file',{
      trackIndex:4,position:30.25,filePath:resolve(session,'Media','Kanye verse repaired.wav')
    });
    await call('set_media_item_properties',{trackIndex:4,itemIndex:item.itemIndex,fadeInLength:0,fadeOutLength:0});
    await render('Clean voices final premaster');
  } else {
    await replaceSource(2,'Verse-Long-Guitar.wav','Verse-Long-Guitar-clean-vocals.wav',2.192,24);
    await replaceSource(4,'Kanye-verse-extended.wav','Kanye-verse-entry-clean.wav',3.925,30.3740593);
    await replaceSource(4,'Kanye-verse-isolated-tail.wav','Kanye-verse-ending-clean.wav',17.31,42.344676);
    await call('save_project',{path:projectPath,overwrite:true});
    await render('Clean voices premaster');
    await render('$track',{source:'stems',outputDirectory:resolve(session,'Renders/Clean Voice Stems')},[2,4]);
    return;
  }
  await render('50 Calls clean voices',{
    format:'mp3',mp3Bitrate:320,normalize:'lufs_i',normalizeTarget:-14.2,
    limit:true,limitCeiling:-1.55,limitTruePeak:true,
    metadata:{title,artist:'Kanye West, Juice WRLD & Veer',album}
  });
  await call('save_project',{path:projectPath,overwrite:true});
});
