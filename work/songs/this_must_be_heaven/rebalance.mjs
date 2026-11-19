import { homedir } from 'node:os';
import { resolve } from 'node:path';
import { call, withReaper } from '../../shared/reaper.mjs';

const session = resolve(homedir(), 'Library/Application Support/REAPER/MCP Sessions/Up for Air');
const duration = 71 * 240 / 105;

function interpolate(points, time) {
  const i = points.findIndex(point => point[0] >= time);
  if (i === 0) return points[0][1];
  if (i === -1) return points.at(-1)[1];
  const [a, left] = points[i - 1];
  const [b, right] = points[i];
  return left + (right - left) * (time - a) / (b - a);
}

async function writeTrim(trackIndex, extra) {
  const { points } = await call('get_envelope_points', { trackIndex, envelopeIndex: 0 });
  const original = points.map(({ time, db }) => [time, db]);
  const times = [...new Set([...original, ...extra].map(point => point[0]))].sort((a, b) => a - b);
  const result = times.map(time => ({
    time, db: interpolate(original, time) + interpolate(extra, time), shape: 0
  }));
  await call('clear_envelope', { trackIndex, envelopeIndex: 0 });
  await call('insert_envelope_points', { trackIndex, envelopeIndex: 0, points: JSON.stringify(result) });
}

await withReaper(async () => {
  const tracks = await call('list_tracks');
  const verse = await call('list_media_items', { trackIndex: 4 });
  if (tracks.length !== 6 || tracks[3].name !== 'Kevin Parker | Hook' || tracks[3].fxCount !== 2 ||
      Math.abs(verse.items[1].position - 86.232737717851) > .001) throw Error('Expected the original Up for Air mix.');

  for (const [trackIndex, chorus, verseOne, recessed] of [
    [0, -.6, .48, 1.65],
    [1, -.72, .4, 1.95],
    [2, -1.15, .28, 1.88],
  ]) {
    await writeTrim(trackIndex, [
      [0,0],[7.05,0],[7.65,chorus],[26.15,chorus],[27.38,verseOne],
      [65.75,verseOne],[68.05,chorus],[83.25,chorus],[85.1,0],
      [91.75,0],[95.1,recessed],[109.6,recessed],[112.05,-.46],
      [122.78,-.46],[124.05,chorus],[143.0,chorus],[144.7,0],
    ]);
  }

  await call('set_multiple_fx_parameters', { updates: [
    {trackIndex:3,fxIndex:0,paramIndex:0,value:76},
    {trackIndex:3,fxIndex:1,paramIndex:6,value:.625},
    {trackIndex:3,fxIndex:1,paramIndex:7,value:.279},
    {trackIndex:3,fxIndex:1,paramIndex:8,value:.325},
  ] });
  await call('set_track_property', { trackIndex: 3, property: 'volume', value: -5.22 });
  await call('set_media_items_properties', { items: [1,2].map(itemIndex => ({
    trackIndex:4,itemIndex,position:verse.items[itemIndex].position + .022
  })) });
  const eq = await call('get_fx_parameters', { trackIndex: 3, fxIndex: 1, namePattern: 'Band 3' });
  console.log('Hook presence EQ', JSON.stringify(eq.parameters.map(x=>[x.name,x.formattedValue])));

  await call('set_render_settings', {
    outputDirectory: resolve(session,'Balance After'), filePattern: '$track', format: 'wav',
    source: 'stems', bounds: 'custom', startTime: 0, endTime: duration,
    sampleRate: 44100, channels: 2, bitDepth: '24', normalize: 'off', limit: false
  });
  console.log(JSON.stringify(await call('render_project',{ tracks:[0,1,2,3,4,5], analyze:false })));
});
