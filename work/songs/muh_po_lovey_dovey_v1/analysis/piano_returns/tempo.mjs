import fs from 'node:fs';
import {withReaper,call} from '../../../../shared/reaper.mjs';
const stage=process.argv[2];
await withReaper(async()=>{
 const project=await call('get_project_info');
 if(project.trackCount||project.name) throw Error('Expected blank REAPER tab');
 const name='native';
 const points=JSON.parse(fs.readFileSync(stage+'/'+name+'/tempo.json'));
 const map=await call('get_tempo_map');
 for(let i=map.count-1;i>=0;i--) await call('delete_tempo_marker',{index:i});
 let t=0;
 for(let i=0;i<points.length-1;i++){
  const [a,bpm,linear]=points[i], [b,end]=points[i+1];
  await call('add_tempo_marker',{position:t,bpm,linear,...(i===0?{timeSigNumerator:4,timeSigDenominator:4}:{})});
  t+=(b-a)*80/(linear?(bpm+end)/2:bpm);
 }
 await call('save_project',{path:stage+'/'+name+'/Tempo map.rpp',overwrite:true});
 console.log(name,t);
});
