import { homedir } from 'node:os';
import { resolve } from 'node:path';
import { call, withReaper } from '../../shared/reaper.mjs';
import { album, title } from './arrange.mjs';

const session = resolve(homedir(),'Library/Application Support/REAPER/MCP Sessions/50 Calls Interlude');
const projectPath = resolve(session,'50 Calls Vocal Repair.rpp');
const trackIndex = 4;

async function render(filePattern,extra={},tracks) {
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
    throw Error('Expected the stopped 50 Calls vocal repair project.');
  }
  const {items} = await call('list_media_items',{trackIndex});
  const old = items.find(item=>item.name==='Kanye-verse-tail.wav');
  if (!old || items.length!==2 || Math.abs(old.position-42.344676)>.001) {
    throw Error('Expected the current interlude vocal edit.');
  }
  const offset = 17.31;
  const end = 28.654;
  await call('delete_media_item',{trackIndex,itemIndex:old.itemIndex});
  const item = await call('insert_audio_file',{
    trackIndex,position:old.position,filePath:resolve(session,'Media','Kanye-verse-isolated-tail.wav')
  });
  await call('trim_media_item',{
    trackIndex,itemIndex:item.itemIndex,trimStart:offset,trimEnd:item.length-end
  });
  await call('set_media_item_properties',{
    trackIndex,itemIndex:item.itemIndex,position:old.position,length:(end-offset)/old.playRate,
    fadeInLength:old.fadeInLength,fadeOutLength:.024,playRate:old.playRate,volume:old.volume
  });
  await render('Interlude premaster repaired');
  await render('Repaired Kanye',{source:'stems'},[4]);
  await render('50 Calls repaired',{
    format:'mp3',mp3Bitrate:320,normalize:'lufs_i',normalizeTarget:-14.2,
    limit:true,limitCeiling:-1.55,limitTruePeak:true,
    metadata:{title,artist:'Kanye West, Juice WRLD & Veer',album}
  });
  await call('save_project',{path:projectPath,overwrite:true});
});
