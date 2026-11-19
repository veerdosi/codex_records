import { resolve } from 'node:path';
import { call, withReaper } from '../../../shared/reaper.mjs';
import { session, render } from '../arrange.mjs';

await withReaper(async () => {
  const {trackCount,tempo} = await call('get_project_info');
  if (trackCount !== 6 || tempo !== 80) throw Error('Expected the 50 Calls session.');
  console.log(JSON.stringify(await render('$track', {
    source:'stems', outputDirectory:resolve(session,'Renders/Stems')
  }, [0,1,2,3,4,5])));
  for (const [name, tracks, startTime, durationSeconds] of [
    ['verse',[2,4],32,11], ['hook',[2,3],7,22]
  ]) {
    try {
      const masking = await call('measure_masking', { tracks, startTime, durationSeconds });
      console.log(JSON.stringify({ name, masking }));
    } catch (err) {
      console.error(err.message);
    }
  }
});
