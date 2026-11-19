import { resolve } from 'node:path';
import { homedir } from 'node:os';
import { call, withReaper } from '../../shared/reaper.mjs';

const session = resolve(homedir(), 'Library/Application Support/REAPER/MCP Sessions/Up for Air');
const bar = 240 / 105;
const tameGrid = 0.268;
const kanyeGrid = 0.0806588 + 40 * 240 / 106.7086;
const kanyeRate = 105 / 106.7086;
const beatFiles = ['Tame-drums.wav', 'Tame-bass.wav', 'Tame-keys-and-guitars.wav'];
const extensionFiles = ['Tame-drums-extended.wav', 'Tame-bass-extended.wav', 'Tame-keys-extended.wav'];

async function clip(trackIndex, filename, start, end, position, options = {}) {
  const { rate = 1, fadeIn = .01, fadeOut = .02, volume = 0 } = options;
  const filePath = resolve(session, 'Media', filename);
  const item = await call('insert_audio_file', { trackIndex, filePath, position });
  const itemIndex = item.itemIndex;
  if (start > 0 || item.length - end > 1e-5) {
    await call('trim_media_item', {
      trackIndex, itemIndex, trimStart: start, trimEnd: Math.max(0, item.length - end)
    });
  }
  await call('set_media_item_properties', {
    trackIndex, itemIndex, position, length: (Math.min(end, item.length) - start) / rate,
    playRate: rate, fadeInLength: fadeIn, fadeOutLength: fadeOut, volume
  });
}

async function setTrim(trackIndex, points) {
  await call('clear_envelope', { trackIndex, envelopeIndex: 0 });
  await call('insert_envelope_points', {
    trackIndex, envelopeIndex: 0,
    points: JSON.stringify(points.map(([time, db]) => ({ time, db, shape: 0 })))
  });
}

await withReaper(async () => {
  const state = await call('get_project_info');
  const regions = await call('list_regions');
  if (state.trackCount !== 5 || state.tempo !== 105 || state.isPlaying || state.isRecording ||
      regions.regions.map(x => x.name).join('|') !== 'Intro|Chorus|Kanye verse|Final chorus|Instrumental resolve') {
    throw Error('Expected the original Up for Air project in REAPER.');
  }

  await call('set_media_items_properties', { items: [0, 1, 2].map(trackIndex => ({
    trackIndex, itemIndex: 3, fadeOutLength: trackIndex === 0 ? .025 : .065
  })) });
  for (let trackIndex = 0; trackIndex < 3; trackIndex++) {
    const overlap = trackIndex === 0 ? .025 : .065;
    await clip(trackIndex, extensionFiles[trackIndex], tameGrid + 42 * bar - 86 - overlap,
      tameGrid + 57 * bar - 86, 39 * bar - overlap, {
        fadeIn: overlap, fadeOut: trackIndex === 2 ? .07 : .016,
        volume: trackIndex === 2 ? .45 : 0
      });
    await clip(trackIndex, beatFiles[trackIndex], tameGrid + 31 * bar,
      tameGrid + 41 * bar, 54 * bar, {
        fadeIn: trackIndex === 2 ? .08 : .01,
        fadeOut: trackIndex === 2 ? 2.12 : 1.72,
        volume: trackIndex === 2 ? .55 : 0
      });
  }

  const versePosition = t => 37 * bar + (t - kanyeGrid) / kanyeRate;
  await clip(4, 'Kanye-verse-two.wav', 19.68, 51.77, versePosition(91.68), {
    rate: kanyeRate, fadeIn: .028, fadeOut: .095, volume: .2
  });
  await clip(4, 'Kanye-verse-two-tail.wav', 6.94, 10.91, versePosition(123.94), {
    rate: kanyeRate, fadeIn: .024, fadeOut: .09, volume: .2
  });

  const hookPosition = 55 * bar + 71.83 - (tameGrid + 32 * bar);
  await clip(3, 'Tame-hook.wav', 71.83, 91.65, hookPosition, {
    fadeIn: .09, fadeOut: .37, volume: .65
  });

  const sample = await call('add_track', { name: 'Tame Impala | Powerlines outro sample' });
  await call('set_track_info', { track: sample.index, color: '#CBAB61' });
  await call('set_track_property', { trackIndex: sample.index, property: 'volume', value: -6.75 });
  await clip(sample.index, 'Powerlines-outro.wav', 0, 8 * bar, 63 * bar, {
    fadeIn: 1.7, fadeOut: 2.3
  });

  await setTrim(0, [[0,-16],[1,-13],[2*bar-.12,-10],[2*bar+.10,-1.6],[3*bar,0],
    [29*bar-.12,0],[29*bar+.12,.48],[37*bar-.08,.48],[37*bar+.10,-3.4],
    [38*bar,-2],[39*bar,0],[53*bar,0],[54*bar-.1,-1.4],[54*bar+.12,.52]]);
  await setTrim(1, [[0,-8],[1.2*bar,-6],[2*bar+.16,0],[37*bar,0],[38*bar,-.65],[39*bar,0]]);
  await setTrim(2, [[0,0],[12*bar-.12,0],[12*bar+.12,-.65],[28*bar,-.65],[29*bar,0],
    [37*bar,0],[38*bar,-.8],[53*bar,-.8],[54*bar,.2],[63*bar,.2]]);

  await call('edit_region', { regionIndex: 3, name: 'Verse 1' });
  await call('edit_region', { regionIndex: 4, name: 'Chorus 2' });
  await call('edit_region', { regionIndex: 5, name: 'Verse 2', end: 55 * bar });
  await call('add_region', { name: 'Final chorus', start: 55 * bar, end: 63 * bar });
  await call('add_region', { name: 'Outro • Powerlines', start: 63 * bar, end: 71 * bar });
  await call('set_cursor_position', { position: 0 });

  await call('set_render_settings', {
    outputDirectory: session, filePattern: 'Up for Air Full QA', format: 'wav',
    source: 'master', bounds: 'custom', startTime: 0, endTime: 71 * bar,
    sampleRate: 44100, channels: 2, bitDepth: '24', normalize: 'off', limit: false
  });
  await call('save_project', { path: resolve(session, 'Up for Air Full.rpp') });
  console.log(JSON.stringify(await call('render_project', { analyze: false })));
});
