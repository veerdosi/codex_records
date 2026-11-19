import { resolve } from 'node:path';
import { call, withReaper } from '../../shared/reaper.mjs';
import { clip, render, session, title } from './arrange.mjs';

const kanyeRate = 80 / 81.9856;
const beatOffset = .192;
const verseStart = 18;
const returnStart = 57;

async function deleteItemsAt(trackIndex, positions) {
  const { items } = await call('list_media_items', { trackIndex });
  const matches = items.filter(item => positions.some(position => Math.abs(item.position - position) < .002));
  if (matches.length !== positions.length) throw Error('Unexpected item positions on track ' + trackIndex);
  for (const item of matches.sort((a,b) => b.itemIndex - a.itemIndex)) {
    await call('delete_media_item', { trackIndex, itemIndex: item.itemIndex });
  }
}

async function setTrim(trackIndex, points) {
  await call('clear_envelope', { trackIndex, envelopeIndex: 0 });
  await call('insert_envelope_points', {
    trackIndex, envelopeIndex: 0, points: JSON.stringify(points.map(([time,db]) => ({time,db,shape:0})))
  });
}

await withReaper(async () => {
  const tracks = await call('list_tracks');
  const verse = await call('list_media_items', { trackIndex:4 });
  if (tracks.length !== 6 || tracks[4].name !== 'Kanye West | Verse' ||
      verse.total !== 1 || Math.abs(verse.items[0].position - 31.844676) > .001) {
    throw Error('Expected the original 50 Calls arrangement.');
  }
  const { regions } = await call('list_regions');
  await call('save_project', { path:resolve(session,'Backups','50 Calls before verse extension.rpp') });

  for (const [index, stem] of ['Drums','Bass','Guitar'].entries()) {
    const guitar = index === 2;
    await deleteItemsAt(index, [6,30,45]);
    await clip(index, `Hook-${stem}.wav`, 24+beatOffset, 36+beatOffset+.026, 6,
      { fadeIn:guitar ? .028 : .004, fadeOut:guitar ? .064 : .028 });
    await clip(index, `Verse-Long-${stem}.wav`, 2+beatOffset, 41+beatOffset+.038, verseStart,
      { fadeIn:guitar ? .032 : .006, fadeOut:guitar ? .080 : .045 });
    await clip(index, `Hook-${stem}.wav`, 36+beatOffset, 48+beatOffset+.032, returnStart,
      { fadeIn:guitar ? .048 : .007, fadeOut:guitar ? .088 : .034 });
  }
  await clip(0,'Verse-Percussion.wav',0,12,18,{fadeIn:.13,fadeOut:1.28,volume:-8.8});
  await deleteItemsAt(3, [6.248,45.248]);
  await clip(3,'Juice-hook-roformer.wav',24.44,35.74,6.248,{fadeIn:.024,fadeOut:.085});
  await clip(3,'Juice-hook-roformer.wav',36.44,47.8,57.248,{fadeIn:.024,fadeOut:.092,volume:-.35});

  await deleteItemsAt(4, [verse.items[0].position]);
  const extendedStart = 3.925;
  await clip(4,'Kanye-verse-extended.wav',extendedStart,26.89,18 + (67 + extendedStart - 70.56) / kanyeRate,
    {rate:kanyeRate,fadeIn:.030,fadeOut:.047,volume:-.15});
  await clip(4,'Kanye-verse-tail.wav',17.31,28.674,verse.items[0].position + 12,
    {rate:kanyeRate,fadeIn:.031,fadeOut:.048});
  const pickup = (await call('list_media_items',{trackIndex:5})).items[0];
  await call('set_media_item_properties',{trackIndex:5,itemIndex:pickup.itemIndex,position:55.5});

  await setTrim(0,[[0,0],[17.82,0],[18,-1.3],[29.84,-1.3],[30,-1.8],[53.92,-1.8],
    [54.2,-3.5],[56.94,-50],[59.96,-50],[60.01,-4.3],[62.95,-4.3],[63.01,0],
    [68.36,.15],[68.98,-5]]);
  await setTrim(1,[[0,0],[17.88,0],[18.23,.6],[29.8,.6],[30.1,.35],[53.72,.35],[56.94,-9],
    [57.02,-12],[59.94,-12],[60.02,-2.7],[62.95,-2.7],[63.04,0],[68.64,0],[69,-1.5]]);
  await setTrim(2,[[0,.6],[3.5,.85],[5.9,0],[17.75,0],[18.25,.55],[29.9,.55],[30.16,.15],
    [53.9,.15],[56.5,-.2],[57.01,.25],[60,.25],[61,-.1],[63.05,.4],[69,0]]);
  for (const region of regions) await call('delete_region',{regionIndex:region.index});
  for (const [start,end,name] of [
    [0,6,'Guitar intro'],[6,18,'First chorus'],[18,42,'Kanye | verse opening'],
    [42,57,'Kanye | verse payoff'],[57,63,'Final chorus | stripped return'],
    [63,69,'Final chorus | full groove'],[69,75,'Guitar outro']
  ]) await call('add_region',{start,end,name});

  console.log(JSON.stringify(await render('Premaster extended verse')));
  console.log(JSON.stringify(await render('$track',{
    source:'stems',outputDirectory:resolve(session,'Renders/Extended Stems')
  },[0,1,2,3,4,5])));
  await call('save_project',{path:resolve(session,title+'.rpp'),overwrite:true});
});
