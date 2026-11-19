---
name: music-production
description: Build or revise private song mixes and original backing tracks, from pairing and stem separation through REAPER arrangement, mastering, and MP3 delivery. Also use for this workspace’s song folders and music metadata.
---

# Music production

Use [AGENTS.md](../../../AGENTS.md) for song locations, approved versions, and metadata. Follow the user’s brief for the performers, samples, length, and structure.

- **For a new production**, prepare the sources, arrange in REAPER, review the render, then deliver.
- **For a revision**, check the approved MP3 and matching editable project. Locate the relevant passage, then start with the arrangement or render step that addresses the issue. A new pairing or a source replacement goes through source preparation for the affected parts.
- **For organization or metadata only**, use the workspace conventions and the delivery checks for the requested change.

## 1. Prepare the sources and choose passages

- Reuse a verified recording or stem when it matches the performance and release. For YouTube, use `yt-dlp` on the verified URL, preferably the artist’s official audio. Check the version, duration, and audio stream before separation. Decode the best available source to WAV and record the URL and version under the song’s `sources/`.
- When choosing a pairing or a handoff, use the [section compatibility guide](references/section-compatibility.md) to compare the actual passages under the proposed tempo, pitch, and bar offsets. Check cadence and complete vocal edges when substituting an a cappella.
- If separation is needed, use BS-RoFormer for vocal extraction or REAPER MCP’s Demucs tool for drums, bass, and melodic parts. When bleed interferes, consider a cleaner source, a local edit, or `bs_roformer_karaoke_frazer_becruily.ckpt` in `work/shared/models/roformer/`. If trying this checkpoint, compare the raw and processed lead at the overlap. It worked on a controlled blend and barely changed the embedded sample in “I Wonder.” With aligned reference stems, `work/shared/separation_check/stem_reference_check.py` can measure lead retention and interference separately.

## 2. Arrange and edit in REAPER

- Use REAPER MCP for track setup, edits, automation, FX, and rendering. Run `node work/shared/reaper.mjs get_project_info` from the workspace and identify the active project before editing. If media imports from Documents stall, use a working copy under REAPER’s application-support folder. Prefer stock FX when practical for project portability.
- When choosing a kit, a type beat, or an approach to writing original parts, start with [choosing a backing for the passage](../../../work/shared/composition/README.md#choose-a-backing-for-the-passage). The same toolkit lists instruments and render commands. Keep the MIDI with the song.
- When fitting a new backing to an existing lead, use [the vocal phrasing method](references/rendered-mix-review.md#arrange-around-an-existing-vocal-performance) during arrangement. Use [section compatibility](references/section-compatibility.md) for handoff design, including [stereo movement](references/section-compatibility.md#when-to-use-a-leftright-handoff). For a difficult transition, sample flip, or genre change, look up a relevant example in the [production reference library](../../../work/shared/production_references/README.md).
- Use `detect_transients` to locate rhythmic anchors, `detect_chords` to check harmony against bass movement, and Whisper to narrow the search for word edges. Confirm words and tails on the isolated lead. If the same performance repeats later, align the repeats to help identify the intended first consonant.

## 3. Review the render and master

- For a difficult balance, timing, phrasing, harmony, or transition issue, use the [rendered-mix review](references/rendered-mix-review.md). For a local repair, compare before-and-after premaster renders with matching bounds and FX history. Use `verify_edit` for timing or gain checks, and compare matching stem renders if a range render fails the null check.
- Fix vocal and backing balance on the tracks before mastering. Check active verses and choruses and preserve dynamics that serve the arrangement.
- Render the whole song, confirm every section plays, and bring any missing media online before rerendering. Measure integrated LUFS and true peak on the premaster and encoded MP3. Around −14 LUFS and −1.3 dBTP is a starting point. Check that limiting preserves the intended dynamics.

## 4. Deliver

Keep trial renders in the song’s work folder. Put the verified stereo MP3 in the release folder listed in [AGENTS.md](../../../AGENTS.md) and the editable session in `reaper/<Title>/` with linked media. Verify duration, decoding, Title, Artist, and Album before replacing an approved export. For tag-only edits, verify that the encoded audio packets match the original. Share the workspace-local result.

After approval, clear superseded previews, diagnostic bus renders, and disposable render sessions. Keep the final project’s media, source recordings, MIDI, code, and useful analysis reports. Preserve older inputs that a current production script still needs.

## Local analysis tools

Python environments are in `work/shared/environments/`, Beat This dependencies in `work/shared/beat_deps/`, models in `work/shared/models/`, and reusable DSP in `work/shared/dsp.py`. The REAPER MCP analysis sidecar uses this workspace’s `audio-venv` via `~/.reaper-mcp/sidecar-venv`. Update that link if the workspace moves.
