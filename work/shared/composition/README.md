# Original composition in REAPER

Use this toolkit to choose a backing, program the parts, and render them into REAPER. Follow the [production skill](../../../.agents/skills/music-production/SKILL.md#2-arrange-and-edit-in-reaper) for the arrangement workflow.

## Choose a backing for the passage

Start with the moment the backing has to serve. Pick a representative vocal or melody phrase, including the lead-in, a held note or strong accent, and the space before the next phrase. For an original instrumental, use a rough melody or chord sketch as the anchor. Note the felt pulse, downbeat, subdivisions, bass movement, and the change in energy the passage needs. For an existing vocal, also mark where the lead climbs or breathes. [Vocal phrasing method](../../../.agents/skills/music-production/references/rendered-mix-review.md#arrange-around-an-existing-vocal-performance)

| If the passage needs… | How to find a candidate | How to tell it fits |
| --- | --- | --- |
| A convincing drummer or a different drum tone | Choose a drum kit once you know the groove you want. Shortlist sounds by attack, decay, room sound, and available velocity layers. For example, try a dry acoustic kit for a restrained verse or a shorter electronic kit when a sustained bass needs room. Start with the local [instrument options](#instruments-and-midi-tools). | Play the same MIDI groove through the candidate kits at matched level. Check kick decay against the bass, snare attack and decay around the vocal, and whether soft hits and fills still have enough range. Once a kit fits, adjust the performance to it. |
| A groove or palette to try under a lead | Search YouTube by artist **and** musical traits. A query like `Travis Scott type beat sparse half-time 145 bpm instrumental` is more useful than an artist name alone. Try broad descriptors if the results cluster around the same sound. Verify the actual recording’s beat grid, downbeat, local chord movement, and usable sections. A grid labeled 145 can also feel like 72.5. | Put the same lead phrase over the strongest candidates. Use modest pitch or tempo changes if they preserve the performance. Check where stressed words land, whether long notes agree with the chords, and what happens at the next phrase boundary. If only the drums fit, use their placement and density as a reference for an original backing. If the whole passage fits and the brief calls for an existing beat, test a second section before committing. |
| A motif, fill, or rhythm tailored to the song | Pick the simplest rule that gives the desired motion. Use a repeating step pattern for a stable pocket, a small rotation for syncopation, or a gradual change in note density, length, or velocity for a build. For pitched parts, pick notes from the chord or voice them against the melody at each change. | Compare the plain pattern with one variation. For example, use pluck hits on sixteenth-note steps 0, 5, and 10 of a bar, then move step 5 to 7 on alternate bars. Keep the downbeat anchored and leave out a hit if it collides with the lead’s pickup. Keep the rule if the phrase sounds more intentional at the same tempo and level. |

When the choice is unclear, render a short comparison in REAPER, usually four to eight bars. Keep the lead and comparison range fixed, match perceived backing level, and change one thing at a time where possible. Listen through an entrance and an exit. Favor the take whose accents, bass and chords, phrasing, and density serve that passage. Keep the chosen MIDI or source URL and time range with the song, plus any useful tempo, pitch, or bar offset. These approaches can work together. An artist type beat can suggest a pocket, a drum kit can supply the sound, and a rule can vary the fill at the end of each phrase. [Section compatibility guide](../../../.agents/skills/music-production/references/section-compatibility.md)

## Instruments and MIDI tools

Write the selected parts as editable MIDI and print stems when the arrangement is ready or the project needs to travel. For acoustic parts, note length, articulation, velocity, and register matter as much as the library.

| Tool | Use in this workspace |
| --- | --- |
| music21 | Build chord progressions, spell pitches, check harmony and transpose passages in musical time. [Roman numerals](https://music21.org/music21docs/usersGuide/usersGuide_23_romanNumerals.html) |
| pretty_midi | Write or revise melodies, voicings, drum patterns and controller curves with note times in seconds. [Project](https://github.com/craffel/pretty-midi) |
| Mido | Write MIDI messages, tempo events and tick-based arrangements. Use REAPER MCP’s `create_midi_item` and `insert_midi_notes` for direct edits in beats. [Mido](https://mido.readthedocs.io/en/stable/files/midi.html) · [ReaScript API](https://www.reaper.fm/sdk/reascript/reascripthelp) |
| FluidSynth and GeneralUser GS | Render a full MIDI arrangement to WAV from the command line. Use it to sketch instrumentation and voicings. Keep the SoundFont’s license with the bank. [FluidSynth](https://www.fluidsynth.org/wiki/Download/) · [GeneralUser GS](https://schristiancollins.com/generaluser.php) |
| sfizz VST3 | Play SFZ instruments directly in REAPER. The local library includes the FreePats Upright Piano KW and Spanish Classical Guitar. Use the licensed AVL Black Pearl kit for velocity-layered acoustic drums. [sfizz](https://sfz.tools/sfizz/downloads/) · [FreePats piano](https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html) · [FreePats guitar](https://freepats.zenvoid.org/Guitar/acoustic-guitar.html) · [AVL](https://www.bandshed.net/avldrumkits/) |
| Surge XT VST3 | Use a REAPER track for hands-on patches and parameter automation. Useful for subtractive sounds, wavetable motion, FM and string-model textures. Pedalboard can host the VST3 and render MIDI offline. [Surge XT](https://surge-synthesizer.github.io/downloads/) |
| Csound | Render an original sound from a text score. Use FM for struck or metallic tones, oscillator banks for additive synthesis, and delays or waveguides for physical models. The producer tag uses an original bass part built from three harmonics. [FM](https://csound.com/manual/opcodes/foscil/) · [Csound manual](https://csound.com/manual/) |

Decent Sampler is useful when an instrument ships as a `.dspreset` or `.dslibrary`. For orchestral strings and flute, BBC Symphony Orchestra Discover has a free plugin and requires a Spitfire login. Pianoteq offers physical models for piano and nylon guitar. Steven Slate Drums 5.5 Free offers a dedicated acoustic kit. These vendor instruments are options for sessions that need their libraries. [Decent Sampler](https://www.decentsamples.com/product/decent-sampler-plugin/) · [BBC Discover](https://www.spitfireaudio.com/products/bbc-symphony-orchestra-discover) · [Pianoteq](https://www.modartt.com/user_manual?product=pianoteq) · [Slate](https://stevenslatedrums.com/ssd5/free)

When writing an intro or turnaround for an existing beat, use its rhythm as a reference. Compare the active subdivisions, phrase length, register, and density before adding notes. In “Muh Pe Lovey Dovey,” syncopated synth plucks, a filtered pulse, and metal ticks were scored around the existing drum pocket. Keep the source rhythm and the new parts on separate tracks so they can be balanced independently.

### Free instrument libraries checked locally

These are SFZ libraries under `work/shared/composition/instruments/`. Load the patch in sfizz and check that the notes and articulations needed for the song render.

| Library | When to use it | Checked patches |
| --- | --- | --- |
| Unreal Instruments Standard Guitar | For electric guitar when picking and articulation shape the performance. Program the keyswitches before the notes. Add the amp, cabinet, or fuzz after the DI signal. The library is free under the author's terms. | `01-Standard Guitar KSOP.sfz` rendered sustain, palm mute, and slide-in on the same pitch. MIDI keys 24, 27, and 33 select them. [Developer page](https://unreal-instruments.wixsite.com/unreal-instruments/standard-guitar) |
| Growlybass | For electric bass that needs distinct plucked attacks, held notes, or short answers to the kick. | The CC0 library's `growlybass_clean.sfz` and `growlybass_vicious.sfz` rendered a held line and a short articulation. [Source](https://github.com/sfzinstruments/karoryfer.growlybass) |
| VSCO 2 CE | For distinct orchestral gestures, such as a sustained flute answer or a short string figure. Add other patches from the same library when a score calls for them. | The local CC0 subset includes `FluteStac.sfz`, `FluteExpVib.sfz`, and `SViolinPizz.sfz`. [Developer page](https://versilian-studios.com/vsco-community/) |
| FreePats Synthesizer Percussion | For a compact electronic kit when the arrangement needs short, synthetic hits. For live drums, start with the existing Black Pearl kit. Use human-played MIDI timing and velocities when the pocket calls for them. | The CC0 `SynthesizerPercussion-20220718.sfz` rendered the test hits. [FreePats kit](https://freepats.zenvoid.org/Percussion/electric-percussion.html) · [Groove MIDI dataset](https://magenta.withgoogle.com/datasets/groove) |

For evolving synths, start with Surge XT. For visual modular patching, [Cardinal](https://github.com/DISTRHO/Cardinal) is a free, open-source option to evaluate. [TONE3000](https://www.tone3000.com/plugin) is a free, open-source amp and cabinet option to evaluate with a dry guitar or bass render.

## Reproduce the checked renders

The local interpreter is `work/shared/environments/composition-venv/bin/python`. Surge XT 1.3.4 and sfizz 1.2.3 are installed as user-local VST3 plug-ins and both loaded in REAPER. The sfizz renderer uses its version 5 VST3 state to set the SFZ path. MIDI rendering defaults to 512-sample blocks. The new libraries were checked with `--buffer-size 128`. Some patches emitted buffer warnings, so verify the expected notes on a fresh render before relying on it.

```sh
dir=work/shared/composition
py=work/shared/environments/composition-venv/bin/python
"$py" "$dir/check_composition.py"
fluidsynth -ni -g .55 -r 48000 -F "$dir/verification/GeneralUser GS.wav" \
  "$dir/instruments/GeneralUser GS/GeneralUser-GS.sf2" "$dir/verification/instrument_check.mid"
"$py" "$dir/render_sfizz.py" "$dir/verification/piano_check.mid" \
  "$dir/instruments/FreePats/UprightPianoKW-SFZ+FLAC-20220221/UprightPianoKW-20220221.sfz" \
  "$dir/verification/FreePats Upright.wav"
```
