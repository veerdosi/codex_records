# Production references

Open [Production References.rpp](<Production References.rpp>) in REAPER and jump to the labeled markers. The 33 excerpts cover 18 examples. Source and result play consecutively where both are available. Item gain aims for −18 LUFS with peak headroom, and each clip plays at its original speed. The [manifest](manifest.json) records source URLs, exact excerpt boundaries, approximate cue times and ways to try each technique. [Measurements](measurements.json) gives clip levels and positions in the session.

Use this library to find a recording that addresses the musical problem at hand. The [section guide](../../../.agents/skills/music-production/references/section-compatibility.md#build-a-handoff) covers building your own handoff, and the [rendered-mix review](../../../.agents/skills/music-production/references/rendered-mix-review.md) covers checking the result.

## Listening index

| Reference | Listen for |
| --- | --- |
| [KENDRICK MADE CA$INO, 13:54](https://www.youtube.com/watch?v=so5KJzTXRVo&t=834s) | The verse phrase restarts as the beat comes forward. |
| [DJ Earworm, 0:36](https://www.youtube.com/watch?v=iNzrwh2Z2hQ&t=36s) | Two vocal phrases trade space over one backing. |
| [DJ Trayze, 1:21](https://www.youtube.com/watch?v=_w7ED8EedNY&t=81s) | A shared word connects tracks across genres. |
| [Crossfader, 2:59 and 9:33](https://www.youtube.com/watch?v=vdbcvsUKY2s&t=179s) | Two ways to repeat a phrase and return to the beat, using a shortening loop and slip mode. |
| [J Dilla, “Don’t Cry,” 0:34](https://www.youtube.com/watch?v=x-23FpWsTKk&t=34s) | The opening source gives way to a new pocket built from reordered slices of the same performance. The adjacent Tracklib excerpt breaks down the source. |
| [Kanye West, “Through the Wire,” 0:20](https://www.youtube.com/watch?v=AE8y25CcE6s&t=20s) | A sped-up Chaka Khan refrain becomes a recurring hook. |
| [9th Wonder, 3:05](https://www.youtube.com/watch?v=23vumiogTQk&t=185s) | He describes and plays the beginning, middle and ending he builds with sample chops. |
| [Eminem, “Stan,” 0:25](https://www.youtube.com/watch?v=7u1Jj6aRIec&t=25s) | Dido’s refrain establishes the scene, then the verse enters after its second pass. |
| [Flume, “Tennis Court,” 1:28](https://www.youtube.com/watch?v=8ATu1BiOPZA&t=88s) | Lorde’s same vocal phrase sets up a drop with a different drum pocket, bass and texture. |
| [Postmodern Jukebox, “Creep,” 0:25](https://www.youtube.com/watch?v=m3lF2qEA2cw&t=25s) | A new vocal performance and rhythm section turn the same song into a jazz arrangement. |
| [JAY-Z and Linkin Park, “Numb / Encore,” 0:18](https://www.youtube.com/watch?v=_1oO4wzPCmE&t=18s) | Two source passages and the mashup show how a recognizable keyboard line can carry a new rap entrance. |
| [JAY-Z and Linkin Park, “Dirt Off Your Shoulder / Lying From You,” 0:22](https://www.youtube.com/watch?v=MG2S0ns8Dj8&t=22s) | A short rhythmic release makes room for the guitar lift and complete incoming phrase. |
| [Eminem and Rihanna, “Love the Way You Lie,” 0:17](https://www.youtube.com/watch?v=ozPOI0TJHCg&t=17s) | The rap pickup precedes the full drum entrance. In the return handoff, the sung hook follows a shorter rhythmic release. |
| [21 Savage and Metro Boomin, “Said N Done,” 0:03](https://www.youtube.com/watch?v=_zXBotJmdOs&t=3s) | A Stephanie Mills sample provides a stable melodic color while the low-end pulse sets up the verse. |
| [DJ Dahi, “a lot,” 3:43](https://www.youtube.com/watch?v=WwYX6iIodqI&t=223s) | The producer plays the drum layers. The finished excerpt shows how the repeating soul backing keeps its character as the hook becomes a verse. |
| [Edwin Birdsong → Daft Punk → Kanye West](https://www.youtube.com/watch?v=PsO6ZnUZI0g) | Hear a keyboard figure become a house loop and the resulting vocoder phrase become a rap hook. |
| [Yeah Yeah Yeahs → A-Trak → Nia Archives](https://www.youtube.com/watch?v=FrnDC94_Tic&t=34s) | Three versions trace a rock motif into house and then jungle. A-Trak’s walkthrough plays the chopped string and bass ideas. |

For a vocal handoff, audition the outgoing line, the incoming pickup and the bass change together. In a rewind edit, mark the complete phrase and the beat it returns to. For a sample flip, start by assigning the source phrase a job in the arrangement, such as a refrain or a response to the drums. For a genre change, compare the drums, bass and chord rhythm under the same vocal phrase before layering more instruments.

For joins that lose clarity, start with the “a lot” and “Numb / Encore” comparisons. Mark which musical element survives the handoff and where the incoming phrase lands relative to the drums.

## Tempo changes in Mijael’s Travis Scott edit

- Around 4:37, “sdp interlude” reaches its sparse tail. “MY EYES” comes in over it, and the faster beat takes over around 4:49. The low end falls away before the new groove arrives while the pitched layers overlap. I measured about 108 BPM in the opening groove and 147 BPM in the faster section. [Listen from 4:37](https://youtu.be/NtaGzRXRYrQ?t=277)
- Around 7:52, “CAROUSEL” starts coming in while a replayed low-end passage from earlier in the edit keeps the “MY EYES” pulse. That low end gives way to the “CAROUSEL” beat around 8:05, which settles near 93 BPM. The earlier bass passage matches the audio in the handoff, and the steady pulse continues through the overlap. [Listen from 7:52](https://youtu.be/NtaGzRXRYrQ?t=472)

For a DJ-style tempo change, let a recognizable chord or rhythmic layer carry across the join. Set the new groove down on a phrase boundary and pass the low end to it cleanly. If the chorus already has a pickup, try a brief space in the drums and bass and let the vocal and chord carry that space. Give the ramp, fill, or drop a clear job before adding another cue.

## Downloaded datasets

| Dataset | What to pull from it |
| --- | --- |
| [Raveform ZIP](datasets/raveform/raveform.zip) · [project](https://mir-aidj.github.io/raveform/) | The archive contains mix links, cue times, beat alignment paths and 1,423 annotated track structures. For a first example, look up `mix0006` in `raveform/mixes.jsonl` and `raveform/alignments/mix0006.align.jsonl`. The alignments place the Foul Play to FBD Project overlap at 71:35–71:53 in the [Fabio & Grooverider set](https://soundcloud.com/ethereal94/fabio-grooverider-kiss-100-fm-2nd-march-1994). Use the times as audition cues. |
| [Sample100](datasets/sample100/readme.md) and [extended annotations](datasets/sample100_ext/README.md) · [source](https://github.com/chymaera96/NeuralSampleID) | Source and reuse relationships with annotated time windows. [S038](datasets/sample100_ext/annotations/S038.json) maps Dido to “Stan” and supplied the windows for the audition pair. [S073](datasets/sample100_ext/annotations/S073.json) points to an Orange Krush drum sample in “We Major.” |
| [Groove MIDI](datasets/groove_midi/groove/info.csv) · [project](https://magenta.withgoogle.com/datasets/groove) | 1,150 human-played MIDI files with tempo, style and drummer metadata. Compare [two performances](datasets/groove_midi/groove/drummer1/eval_session/6_hiphop-groove6_87_beat_4-4.mid) of the [same 87 BPM hip-hop groove](datasets/groove_midi/groove/drummer5/eval_session/6_hiphop-groove6_87_beat_4-4.mid) with an [84 BPM funk pattern](datasets/groove_midi/groove/drummer1/eval_session/5_funk-groove5_84_beat_4-4.mid). Load them on the same drum kit to compare kick placement, ghost notes and velocity. |
