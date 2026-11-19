import { homedir } from 'node:os';
import { resolve } from 'node:path';
import { call, withReaper } from '../../shared/reaper.mjs';

export const title = '50 Calls';
export const album = 'deus complex';
export const session = resolve(homedir(), 'Library/Application Support/REAPER/MCP Sessions', title);
export const duration = 75;
const downbeat = .192;
const kanyeRate = 80 / 81.9856;
const kanyeAnchor = 32.51;

const tracks = [
  ['Cigarettes | Drums', '#6D83AC', -7.3],
  ['Cigarettes | Bass', '#6D83AC', -7.4],
  ['Cigarettes | Guitar', '#6D83AC', -5.3],
  ['Juice WRLD | Refrain', '#617F69', -5.6],
  ['Kanye West | Verse', '#B88E69', -5.8],
  ['Guitar | Return pickup', '#89946F', -12]
];

export async function clip(trackIndex, file, start, end, position, options = {}) {
  const { rate = 1, fadeIn = .007, fadeOut = .025, volume = 0 } = options;
  const { items } = await call('list_media_items', { trackIndex });
  const stagingPosition = Math.max(position, ...items.map(item => item.position + item.length + .01));
  const item = await call('insert_audio_file', {
    trackIndex, filePath: resolve(session, 'Media', file), position: stagingPosition
  });
  await call('trim_media_item', {
    trackIndex, itemIndex: item.itemIndex, trimStart: start, trimEnd: Math.max(0, item.length - end)
  });
  await call('set_media_item_properties', {
    trackIndex, itemIndex: item.itemIndex, position, length: (end - start) / rate,
    playRate: rate, fadeInLength: fadeIn, fadeOutLength: fadeOut, volume
  });
}

async function trimEnvelope(trackIndex, entries) {
  const { envelopeIndex } = await call('create_track_envelope', { trackIndex, envelopeName: 'Trim Volume' });
  await call('insert_envelope_points', {
    trackIndex, envelopeIndex,
    points: JSON.stringify(entries.map(([time, db]) => ({ time, db, shape: 0 })))
  });
  await call('set_envelope_properties', { trackIndex, envelopeIndex, visible: true, armed: false });
}

export async function render(filePattern, extra = {}, tracks) {
  await call('set_render_settings', {
    outputDirectory: resolve(session, 'Renders'), filePattern, format: 'wav', source: 'master',
    bounds: 'custom', startTime: 0, endTime: duration, sampleRate: 44100, channels: 2,
    ...(extra.format === 'mp3' ? {} : { bitDepth: '24' }), normalize: 'off', limit: false, ...extra
  });
  await call('run_action', { action: 40100 });
  await call('run_action', { action: 40101 });
  return call('render_project', { analyze: false, overwrite: true, ...(tracks ? { tracks } : {}) });
}

if (process.argv[2] === 'arrange') await withReaper(async () => {
  const status = await call('get_project_info');
  if (status.trackCount || status.name || status.isPlaying || status.isRecording) {
    throw Error('Expected a blank, stopped REAPER tab.');
  }

  await call('set_project_tempo', { bpm: 80 });
  await call('set_project_settings', {
    title, author: 'Kanye West, Juice WRLD & Veer', sampleRate: 44100, useProjectSampleRate: true, repeat: false
  });
  const ops = tracks.flatMap(([name, , volume], index) => [
    { op: 'add_track', name, as: '$track' + index },
    { op: 'set_track', track: '$track' + index, volume }
  ]);
  await call('run_plan', { ops, label: 'Create 50 Calls tracks', dryRun: true });
  await call('run_plan', { ops, label: 'Create 50 Calls tracks' });
  for (let i = 0; i < tracks.length; i++) await call('set_track_info', { track: i, color: tracks[i][1] });

  await clip(2, 'Hook-Guitar.wav', downbeat, 6 + downbeat + .028, 0, { fadeIn: .12, fadeOut: .052 });
  for (const [trackIndex, stem] of ['Drums','Bass','Guitar'].entries()) {
    await clip(trackIndex, `Hook-${stem}.wav`, 24 + downbeat, 48 + downbeat + .026, 6, {
      fadeIn: stem === 'Guitar' ? .028 : .004, fadeOut: stem === 'Guitar' ? .064 : .028
    });
    await clip(trackIndex, `Verse-${stem}.wav`, 2 + downbeat, 17 + downbeat + .038, 30, {
      fadeIn: stem === 'Guitar' ? .032 : .006, fadeOut: stem === 'Guitar' ? .080 : .045
    });
    await clip(trackIndex, `Hook-${stem}.wav`, 24 + downbeat, 48 + downbeat + .032, 45, {
      fadeIn: stem === 'Guitar' ? .048 : .007, fadeOut: stem === 'Guitar' ? .088 : .034
    });
  }
  await clip(2, 'Hook-Guitar.wav', downbeat, 6 + downbeat, 69, { fadeIn: .072, fadeOut: 1.62, volume: -1 });
  await clip(1, 'Verse-Bass.wav', 2 + downbeat, 5 + downbeat, 69, { fadeIn: .028, fadeOut: 1.55, volume: -3.3 });
  for (const position of [6, 45]) {
    await clip(3, 'Juice-hook.wav', 24.46, 47.79, position + 24.46 - 24 - downbeat, {
      fadeIn: .021, fadeOut: .08, volume: position === 45 ? -.3 : 0
    });
  }
  const verseStart = 17.31;
  await clip(4, 'Kanye-verse.wav', verseStart, 28.71, 30 + (17 + verseStart - kanyeAnchor) / kanyeRate, {
    rate: kanyeRate, fadeIn: .031, fadeOut: .16
  });
  await clip(5, 'Guitar-pickup.wav', 0, 1.5, 43.5, { fadeIn: .07, fadeOut: .105 });

  await trimEnvelope(0, [
    [0,0],[29.68,0],[30,-1.8],[41.8,-1.8],[43.2,-4.0],[44.25,-12],
    [44.91,-50],[47.96,-50],[48.01,-4.3],[53.95,-4.3],[54.02,-1.75],
    [56.96,-1.75],[57.02,.25],[68.36,.25],[68.98,-5]
  ]);
  await trimEnvelope(1, [
    [0,0],[30,-.9],[42,-.9],[44.92,-9],[45.02,-12],[47.94,-12],
    [48.02,-2.7],[53.97,-2.7],[54.05,0],[68.64,0],[69,-1.5]
  ]);
  await trimEnvelope(2, [
    [0,0],[29.72,0],[30.28,-1.2],[42.3,-1.2],[44.5,-.2],[45.01,.25],
    [48,.25],[49.0,-.1],[54.0,0],[57,.4],[69,0]
  ]);

  for (const [start, end, name] of [
    [0,6,'Guitar intro'], [6,30,'Refrain'], [30,45,'Verse'],
    [45,57,'Refrain | return'], [57,69,'Refrain | full groove'], [69,75,'Guitar outro']
  ]) await call('add_region', { start, end, name });

  for (const index of [3,4]) {
    await call('add_fx', { trackIndex: index, fxName: 'ReaEQ (Cockos)' });
    await call('add_fx', { trackIndex: index, fxName: 'ReaComp (Cockos)' });
  }

  await call('save_project', { path: resolve(session, title + '.rpp') });
  console.log(JSON.stringify(await render('Premaster A')));
});
