import { resolve } from 'node:path';
import { homedir } from 'node:os';
import { call, withReaper } from '../../shared/reaper.mjs';

const session = resolve(homedir(), 'Library/Application Support/REAPER/MCP Sessions/Up for Air');
const bar = 240 / 105;

async function automation(trackIndex, points, created = false) {
  const envelope = created
    ? { envelopeIndex: 0 }
    : await call('create_track_envelope', { trackIndex, envelopeName: 'Trim Volume' });
  const envelopeIndex = envelope.envelopeIndex;
  await call('clear_envelope', { trackIndex, envelopeIndex });
  await call('insert_envelope_points', {
    trackIndex, envelopeIndex,
    points: JSON.stringify(points.map(([time, db]) => ({ time, db, shape: 0 })))
  });
  await call('set_envelope_properties', { trackIndex, envelopeIndex, visible: true, armed: false });
}

await withReaper(async () => {
  const status = await call('get_project_info');
  if (status.trackCount !== 5 || status.tempo !== 105) throw Error('Up for Air is not the current project.');
  const params = (fxIndex, values) => Object.entries(values).map(([paramIndex, value]) => ({
    trackIndex: 4, fxIndex, paramIndex: Number(paramIndex), value
  }));
  await call('set_multiple_fx_parameters', { updates: [
    ...params(0, { 0: 86 }),
    ...params(1, { 0: 0.13, 1: 0.0091, 2: 0.022, 3: 0.021, 13: 0.09 }),
    ...params(2, { 0: 0.065, 2: 0.14, 3: 0.73, 4: 0.82, 5: 0.018, 6: 0.36, 7: 0.015 })
  ] });

  await automation(0, [[0, -16], [1.0, -13], [bar * 2 - .12, -10], [bar * 2 + .10, -1.6],
    [bar * 3, 0], [bar * 29 - .12, 0], [bar * 29 + .12, .48]], true);
  await automation(1, [[0, -8], [bar * 1.2, -6], [bar * 2 + .16, 0],
    [bar * 37, 0], [bar * 38.5, -2]]);
  await automation(2, [[0, 0], [bar * 12 - .12, 0], [bar * 12 + .12, -.65],
    [bar * 28, -.65], [bar * 29, 0]]);

  await call('set_render_settings', {
    outputDirectory: session, filePattern: 'Up for Air QA', format: 'wav', source: 'master',
    bounds: 'custom', startTime: 0, endTime: 39 * bar, sampleRate: 44100, channels: 2,
    bitDepth: '24', normalize: 'off', limit: false
  });
  await call('save_project', { path: resolve(session, 'Up for Air.rpp'), overwrite: true });
  const result = await call('render_project', { analyze: false });
  console.log(JSON.stringify(result));
});
