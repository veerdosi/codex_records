import { resolve } from 'node:path';
import { homedir } from 'node:os';
import { call, withReaper } from '../../shared/reaper.mjs';

const project = resolve(homedir(), 'Library/Application Support/REAPER/MCP Sessions/Up for Air');
const media = file => resolve(project, 'Media', file);
const bar = 240 / 105;
const tameGrid = 0.268;
const kanyeRate = 105 / 106.7086;
const kanyeGrid = 18.061;

const tracks = [
  ['Tame Impala | Drums', 'Tame-drums.wav', '#C27857', -4.8],
  ['Tame Impala | Bass', 'Tame-bass.wav', '#C27857', -5.3],
  ['Tame Impala | Keys & guitars', 'Tame-keys-and-guitars.wav', '#C27857', -4.2],
  ['Kevin Parker | Hook', 'Tame-hook.wav', '#478A88', -5.4],
  ['Kanye West | Verse', 'Kanye-verse.wav', '#846DAB', -4.7]
];

async function clip(trackIndex, start, end, position, options = {}) {
  const { rate = 1, fadeIn = 0.006, fadeOut = 0.014, volume = 0 } = options;
  const item = await call('insert_audio_file', {
    trackIndex, filePath: media(tracks[trackIndex][1]), position
  });
  const itemIndex = item.itemIndex;
  await call('trim_media_item', {
    trackIndex, itemIndex, trimStart: start, trimEnd: item.length - end
  });
  await call('set_media_item_properties', {
    trackIndex, itemIndex, position, length: (end - start) / rate,
    playRate: rate, fadeInLength: fadeIn, fadeOutLength: fadeOut, volume
  });
}

async function stemSegment(trackIndex, sourceBar, count, targetBar, options = {}) {
  const start = tameGrid + sourceBar * bar;
  await clip(trackIndex, start, start + count * bar, targetBar * bar, options);
}

await withReaper(async () => {
  const initial = await call('get_project_info');
  if (initial.trackCount || initial.name || initial.isPlaying || initial.isRecording) {
    throw Error('Expected a blank stopped REAPER project.');
  }
  await call('set_project_tempo', { bpm: 105 });
  await call('set_project_settings', {
    sampleRate: 44100, useProjectSampleRate: true,
    title: 'Up for Air', author: 'Kanye West × Tame Impala', repeat: false
  });
  const ops = tracks.map(([name, , , volume], index) => [
    { op: 'add_track', name, as: '$track' + index },
    { op: 'set_track', track: '$track' + index, volume }
  ]).flat();
  await call('run_plan', { ops, label: 'Create Up for Air tracks', dryRun: true });
  await call('run_plan', { ops, label: 'Create Up for Air tracks' });
  for (let i = 0; i < tracks.length; i++) {
    await call('set_track_info', { track: i, color: tracks[i][2] });
  }

  for (let trackIndex = 0; trackIndex < 3; trackIndex++) {
    const keys = trackIndex === 2;
    await stemSegment(trackIndex, 28, 16, 0, {
      fadeIn: keys ? 0.15 : 0.009, fadeOut: keys ? 0.042 : 0.014
    });
    await stemSegment(trackIndex, 4, 4, 16, {
      fadeIn: keys ? 0.038 : 0.007, fadeOut: keys ? 0.042 : 0.013
    });
    await stemSegment(trackIndex, 16, 8, 20, {
      fadeIn: keys ? 0.038 : 0.007, fadeOut: keys ? 0.055 : 0.012
    });
    await stemSegment(trackIndex, 31, 11, 28, {
      fadeIn: keys ? 0.065 : 0.009, fadeOut: keys ? 1.8 : 0.95,
      volume: keys ? 0.45 : 0
    });
  }

  const chorusStart = tameGrid + 32 * bar;
  await clip(3, 71.83, 91.65, 4 * bar + 71.83 - chorusStart, {
    fadeIn: 0.09, fadeOut: 0.37
  });
  await clip(3, 75.38, 91.65, 29 * bar + 75.38 - chorusStart, {
    fadeIn: 0.085, fadeOut: 0.37, volume: 0.35
  });
  await clip(4, 19.02, 56.23, 12 * bar + (19.02 - kanyeGrid) / kanyeRate, {
    rate: kanyeRate, fadeIn: 0.022, fadeOut: 0.15
  });

  for (const [start, end, name] of [
    [0, 4, 'Intro'],
    [4, 12, 'Chorus'],
    [12, 29, 'Kanye verse'],
    [29, 37, 'Final chorus'],
    [37, 39, 'Instrumental resolve']
  ]) await call('add_region', { start: start * bar, end: end * bar, name });

  await call('save_project', { path: resolve(project, 'Up for Air.rpp') });
  console.log(JSON.stringify(await call('get_project_info')));
});
