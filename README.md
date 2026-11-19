# codex_records

Veer’s music production workspace for remixes, original backing arrangements, producer tags, album artwork, and visualizers. REAPER projects and programmable audio tools hold the production work, with finished releases in `outputs/`.

## Start here

Read [AGENTS.md](AGENTS.md) for the song index, folder layout, and metadata conventions. The [music-production skill](.agents/skills/music-production/SKILL.md) gives the workflow and reading order for choosing passages, arranging, reviewing rendered mixes, mastering, and delivery.

The skill links to the [composition toolkit](work/shared/composition/README.md), [production reference library](work/shared/production_references/README.md), [section compatibility guide](.agents/skills/music-production/references/section-compatibility.md), and [rendered-mix review](.agents/skills/music-production/references/rendered-mix-review.md) as each task needs them.

## Contents

| Path | Contents |
| --- | --- |
| `outputs/deus complex/audio/` | Album masters |
| `outputs/deus complex/visuals/` | Album cover and full-length visualizers |
| `outputs/single/`, `outputs/unfinished/`, `outputs/archived/` | Standalone releases, work in progress, and archived masters |
| `reaper/` | Editable REAPER sessions with relative media references |
| `work/songs/` | Song-specific arrangement code, MIDI, source information, and analysis |
| `work/shared/` | Reusable DSP, REAPER MCP client, composition tools, and reference notes |
| `work/visuals/` | Artwork and visualizer code |
| `.agents/skills/music-production/` | Production skill and its supporting guides |

## Run locally

The working installation is at `~/Documents/code/github/codex_records`. REAPER, REAPER MCP, FFmpeg, yt-dlp, Rubber Band, and the Python packages used by each production provide the local tools. Instrument installation details and composition dependencies are listed in the [composition toolkit](work/shared/composition/README.md).

With REAPER and its MCP bridge running, check the active project from the repository root.

```sh
node work/shared/reaper.mjs get_project_info
```

The client uses the user-local REAPER MCP installation at `~/.local/share/reaper-mcp/`. The audio sidecar links to `work/shared/environments/audio-venv` through `~/.reaper-mcp/sidecar-venv`.

Finished outputs, downloaded sources, separated stems, instrument libraries, model weights, datasets, local runtimes, and intermediate renders are excluded from Git. They remain in the local workspace. A fresh clone needs the corresponding assets and dependencies to render the sessions. Some historical revision scripts also require their original intermediate inputs. First-party production code, MIDI, guides, and session files are included.

Source performances and contributing artists are credited in [AGENTS.md](AGENTS.md) and the MP3 metadata. Reference recordings and techniques are documented in the [production reference library](work/shared/production_references/README.md).
