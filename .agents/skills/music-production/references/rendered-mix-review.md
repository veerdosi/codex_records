# Review a rendered mix

Use this guide when diagnosing an existing mix, fitting backing to a lead, or checking a rendered arrangement. Start with the production question and the bars where it occurs. Use synchronized post-FX, post-fader stems before master dynamics, the premaster, and the approved export. Retain intentional swing, pickups, mutes, and automation in the render. Record the tempo map, downbeats, intended chord or MIDI where available, and the offset of any reference. Compare the mix and candidate at matched loudness, with room before and after the affected phrase.

For a quick A/B, render the same short range and align both clips at the same REAPER position. Measure integrated loudness over the excerpt, apply a fixed gain offset, and remeasure while checking true peak. Keep one version audible at a time and loop the phrase so the comparison stays in time. Use neutral labels when order or expectations may influence a human listener. For instrument choices, compare the solo part and then hear it with the same backing.

## Plots to inspect

- Use a log-frequency spectrogram of the mix and a per-stem band-energy plot on the same time axis. Mark bar lines and section boundaries. Keep an absolute dB scale and consistent limits across versions and stems. A whole-song view locates changes in density. Zoom to a few bars to examine a kick handoff, a pad covering a word, or a delayed entrance.
- For a programmed pitched part, overlay MIDI notes on a constant-Q spectrogram of its isolated render. Align render start, tempo map, and instrument latency first. Read the fundamental alongside harmonics. Treat effects tails, bend, and sample tuning as part of the render.

## Measurements

| Question | Evidence |
| --- | --- |
| Is the lead being covered? | During voiced frames, use REAPER `measure_masking` or aligned stem energies to compare lead and backing in the same bands. Use `analyze_loudness_curve` to locate short-term level changes. Compare the suspect word with its neighbors. If the solo lead dips, try a short gain ride. If the backing masks it, try a small, local EQ cut on the backing. Check the result in the full mix. |
| Did the pulse dip or move at the handoff? | Check stem transients against intended subdivisions and accents. Compare kick and backbeat energy beat by beat on both sides. Compare offsets to the instrument's normal lag. Use beat and bar phase together. |
| Did the intended harmony render? | Check MIDI against the isolated pitched render. Compare bass notes and short-window chroma against intended chord tones, then inspect sustained overlaps in context. Report uncertain or ambiguous labels as such. |
| Is the relevant sound closer to a reference? | Match excerpt role, duration, and level. Compare the target stem or bus when possible. Use a descriptor suited to the question, such as decay, stereo width, band balance, or an audio embedding for broader timbre. Check whether the chosen measure responds to a known change in that attribute. |

Before relying on a new detector, check it on an unchanged control and a known local perturbation, such as a 3 dB fader move, a 30 ms onset shift, or a muted chord tone. Compare results to the expected change and log missed or ambiguous events. Keep thresholds specific to the instrument, arrangement, and detector resolution.

Attach a time, stem, and measurement to each proposed edit. Rerender the same bounds with the same FX history, then compare the targeted reading and check adjacent bars. Audition groove, phrasing, and effect transitions where listening is available. State when the evidence comes from plots and measurements alone.

## Arrange around an existing vocal performance

Use the vocal as a phrasing reference when replacing a backing. Line up the isolated lead, pitched instruments, bass, and drums in the same render. Mark vocal pickups, sustained or rising notes, emphatic words, and breaths between lines. Trace pitch and short-window energy on the lead together to distinguish a melodic lift from a louder consonant. Check the preceding and following beats before interpreting a brief gap as a phrase ending.

Choose a few gestures that matter to the arrangement. A guitar harmony can open under a held note, the rhythm section can ease back under a pickup, and a short answer can occupy a genuine breath. Match the chord under the voice and time arrivals to its phrasing or a deliberate beat accent. Keep the singer’s natural dynamics. Use a small, phrase-specific move before trying a bus compressor or a vocal-driven sidechain. Listen or measure through the next line to check that the backing settles in time.

Compare the old and revised backing at matched level around each gesture. Check when the swell peaks, whether the lead stays clear, and whether the underlying drum pulse carries through. A downbeat alignment check answers a separate question from whether the arrangement supports the rise and fall of a sung line.
