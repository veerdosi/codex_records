# Music production workspace

Read [the production skill](.agents/skills/music-production/SKILL.md) before creating, revising, tagging, or organizing a mix. It gives the reading order and links to the guides for each task. Use this file for workspace paths, the master index, and metadata conventions.

## Where files belong

- Keep one approved MP3 per song. Put the Kanye-centered album’s masters in `outputs/deus complex/audio/` and its cover and visualizers in `outputs/deus complex/visuals/`. Use `outputs/single/` for standalone releases, `outputs/unfinished/` for **unfinished**, and `outputs/archived/` for archived songs. Keep both versions together when the user requests a comparison.
- `work/songs/<title_slug>/` holds that song’s source recordings, stems, arrangement scripts, analysis, and previews. For new work, use `sources/`, `stems/`, `analysis/`, and `previews/` as needed. Keep superseded renders in `previous_exports/` or `alternates/` when useful.
- `work/shared/` holds reusable code, runtimes, models, and evaluation tools. Put audio caches under the song or experiment that uses them.
- `work/experiments/` holds active trials and [lessons from retired pairings](work/experiments/LESSONS.md). Record useful findings before retiring a draft.
- `reaper/<Title>/` holds the editable `.rpp` and its `Media/` folder. Use relative media paths so they can move together.

| Song folder                         | Approved export                                 | Source performances                                                                                                                     |
| ----------------------------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `work/songs/go_back_to_the_part_where_i_leave/` | `outputs/deus complex/audio/go_back_to_the_part_where_i_leave.mp3` | Kanye West’s “Runaway,” 21 Savage’s “Said N Done,” Eminem’s “Love the Way You Lie,” and Veer’s original piano and rewind edit. |
| `work/songs/blame_me_for_everything/` | `outputs/archived/blame_me_for_everything.mp3` | Kanye West’s “Runaway” pre-choruses, choruses and both Kanye verses, 21 Savage’s “Creepin’” verse, and Veer’s original backing and answering piano parts. |
| `work/songs/yeezy_season_712/`      | `outputs/archived/yeezy_season_712.mp3`     | Kanye West’s “Facts” and Future’s “712PM”                                                                                               |
| `work/songs/for_my_kids_kids/`      | `outputs/deus complex/audio/for_my_kids_kids.mp3`     | Kanye West’s “Off The Grid” vocals over Yeat’s “Monëy So Big” instrumental. |
| `work/songs/the_things_i_created/`  | `outputs/deus complex/audio/the_things_i_created.mp3` | Kanye West’s “I Wonder,” Travis Scott’s “HYAENA” and “COFFEE BEAN,” and Labi Siffre’s “My Song” |
| `work/songs/this_must_be_heaven/`   | `outputs/deus complex/audio/this_must_be_heaven.mp3`  | Kanye West’s “Touch the Sky” and Tame Impala’s “Breathe Deeper,” with a “Powerlines” outro |
| `work/songs/50_calls/`              | `outputs/deus complex/audio/50_calls.mp3`             | Kanye West’s “Wouldn’t Leave” and Juice WRLD’s “Cigarettes” |
| `work/songs/sunn_raha_hai_under_glass/` | `outputs/single/sunn_raha_hai_under_glass_dream_pop.mp3` (dream pop) | Shreya Ghoshal’s “Sunn Raha Hai” vocal with Veer’s dream-pop arrangement. Shoegaze session retained in `reaper/`. |
| `work/songs/muh_po_lovey_dovey_v1/` | `outputs/single/muh_pe_lovey_dovey_v1.mp3` (85 BPM) and `outputs/archived/muh_pe_lovey_dovey_v2.mp3` (82–88 BPM ramps) | Chaar Diwaari and Raftaar’s “Farebi” chorus and instrumental, Encore ABJ and Calm’s “Namastute” verses, and Veer’s original intro parts |

## Name and tag the master

- Take the title from a distinctive lyric, moment, or musical idea in the mix. Let the source artists’ naming sensibilities guide the wording and capitalization.
- Keep the chosen title in Title, credit the contributing artists and direct sample artists plus **Veer** in Artist, and use the matching album folder name in Album. These three tags are the default.
- Use the same lowercase, underscore-separated title slug for the MP3 filename and song work folder. When renaming a master, update its tag, filename, folder, and the index above together. Copy the audio stream when changing tags on an existing master.
