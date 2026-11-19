import { resolve } from 'node:path';
import { call, withReaper } from '../../shared/reaper.mjs';
import { album, title, session, render } from './arrange.mjs';

await withReaper(async () => {
  const tracks = await call('list_tracks');
  if (tracks.length !== 6 || tracks[3].name !== 'Juice WRLD | Refrain' ||
      tracks[4].name !== 'Kanye West | Verse') throw Error('Expected the 50 Calls session.');
  if (process.argv[2] === 'premaster') {
    console.log(JSON.stringify(await render('Premaster A')));
    for (const fxIndex of [0,1]) {
      const { parameters } = await call('get_fx_parameters', { trackIndex: 4, fxIndex });
      console.log(JSON.stringify(parameters.map(x=>[x.paramIndex,x.name,x.value,x.formattedValue])));
    }
  } else if (process.argv[2] === 'master') {
    console.log(JSON.stringify(await render('50 Calls', {
      format:'mp3', mp3Bitrate:320, normalize:'lufs_i', normalizeTarget:-13.8,
      limit:true, limitCeiling:-1.5, limitTruePeak:true,
      metadata:{title, artist:'Kanye West, Juice WRLD & Veer', album}
    })));
    await call('save_project', { path: resolve(session, title + '.rpp'), overwrite: true });
  }
});
