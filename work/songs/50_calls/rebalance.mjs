import { resolve } from 'node:path';
import { call, withReaper } from '../../shared/reaper.mjs';
import { clip, session, render, title } from './arrange.mjs';

async function envelope(trackIndex, entries) {
  await call('clear_envelope', { trackIndex, envelopeIndex: 0 });
  await call('insert_envelope_points', {
    trackIndex, envelopeIndex: 0,
    points: JSON.stringify(entries.map(([time, db]) => ({ time, db, shape: 0 })))
  });
}

await withReaper(async () => {
  const tracks = await call('list_tracks');
  const hook = await call('list_media_items', { trackIndex: 3 });
  if (tracks[3]?.name !== 'Juice WRLD | Refrain' || tracks[4]?.name !== 'Kanye West | Verse' ||
      tracks[4].fxCount !== 2 || hook.items.length !== 2) throw Error('Expected the 50 Calls premaster.');

  await call('delete_media_item', { trackIndex: 3, itemIndex: 1 });
  await call('delete_media_item', { trackIndex: 3, itemIndex: 0 });
  for (const position of [6,45]) {
    await clip(3, 'Juice-hook-roformer.wav', 24.44, 47.80, position + .248, {
      fadeIn: .024, fadeOut: .092, volume: position === 45 ? -.35 : 0
    });
  }

  await envelope(1, [
    [0,0],[29.88,0],[30.23,.35],[42,.35],[44.92,-9],[45.02,-12],[47.94,-12],
    [48.02,-2.7],[53.97,-2.7],[54.05,0],[68.64,0],[69,-1.5]
  ]);
  await envelope(2, [
    [0,.6],[3.5,.85],[5.9,0],[29.72,0],[30.28,.15],[42.3,.15],
    [44.5,-.2],[45.01,.25],[48,.25],[49.0,-.1],[54.0,0],[57,.4],[69,0]
  ]);

  await call('set_track_property', { trackIndex:4, property:'volume', value:-6.45 });
  await call('add_fx', { trackIndex:2, fxName:'ReaEQ (Cockos)' });
  const settings = (trackIndex, fxIndex, values) => Object.entries(values).map(([paramIndex, value]) => ({
    trackIndex, fxIndex, paramIndex: Number(paramIndex), value
  }));
  await call('set_multiple_fx_parameters', { updates: [
    ...settings(2,0,{6:.600,7:.22,8:.31}),
    ...settings(3,1,{0:.152,1:.0091,2:.021,3:.022,7:.0037,13:.09}),
    ...settings(4,1,{0:.139,1:.0111,2:.024,3:.023,7:.0047,13:.10})
  ] });
  await call('add_fx', { trackIndex:4, fxName:'ReaVerbate (Cockos)' });
  await call('set_multiple_fx_parameters', { updates: [
    ...settings(4,2,{0:.039,2:.135,3:.73,4:.70,5:.024,6:.40,7:.012})
  ] });
  await call('save_project', { path:resolve(session,title+'.rpp'), overwrite:true });
  console.log(JSON.stringify(await render('Premaster B')));
  console.log(JSON.stringify(await render('$track', {
    source:'stems', outputDirectory:resolve(session,'Renders/Stems')
  },[0,1,2,3,4,5])));
});
