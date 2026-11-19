import { resolve } from 'node:path';
import { call, withReaper } from '../../shared/reaper.mjs';
import { album, clip, render, session, title } from './arrange.mjs';

await withReaper(async () => {
  const { items } = await call('list_media_items', { trackIndex:2 });
  const verse = items.find(item => Math.abs(item.position - 30) < .001);
  if (!verse || !JSON.stringify(verse).includes('Verse-Guitar.wav')) throw Error('Expected the original verse guitar item.');
  await call('delete_media_item', { trackIndex:2, itemIndex:items.indexOf(verse) });
  await clip(2, 'Verse-Guitar-clean.wav', 2.192, 17.23, 30, { fadeIn:.032, fadeOut:.080 });

  console.log(JSON.stringify(await render('Premaster')));
  console.log(JSON.stringify(await render('$track', {
    source:'stems', outputDirectory:resolve(session,'Renders/Stems')
  },[0,1,2,3,4,5])));
  console.log(JSON.stringify(await call('verify_edit', {
    trackIndex:2, startTime:39.5, durationSeconds:4.5, expect:'changed',
    referencePath:resolve(import.meta.dirname,'analysis/before_guitar_overlap.wav')
  })));
  console.log(JSON.stringify(await render(title, {
    format:'mp3', mp3Bitrate:320, normalize:'lufs_i', normalizeTarget:-13.8,
    limit:true, limitCeiling:-1.5, limitTruePeak:true,
    metadata:{title, artist:'Kanye West, Juice WRLD & Veer', album}
  })));
  await call('save_project', { path:resolve(session,title+'.rpp'), overwrite:true });
});
