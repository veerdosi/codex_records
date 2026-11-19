"""Expand the approved Facts / 712PM handoff into a full arrangement."""
import json
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
from pedalboard import Reverb
from scipy import signal
import soundfile as sf

from audition import (
    BAR, HERE, JOIN, REFERENCE_OFFSET, SR,
    db, extract, fade, filt, frames, load, respeed, rms,
)

BEAT = BAR / 4
FIRST_HOOK = 4
# Preserve the original chant's placement relative to the drum transients.
HOOK_OFFSET = .1856
KANYE = 12
APPROVED_KANYE = 20
# Measured from each Facts excerpt's native drum phase to the local 712PM grid.
KANYE_OFFSET = .2434
APPROVED_KANYE_OFFSET = .0898
FUTURE = 28
SECOND_HOOK = 50
OUTRO = 58
END = 62
OUTPUT = HERE / "yeezy_season_712_candidate.mp3"


def place(bus, sample, at):
    first = frames(at)
    assert 0 <= first and first + len(sample) <= len(bus)
    bus[first:first + len(sample)] += sample


def fit_count(audio, count):
    if len(audio) < count:
        return np.pad(audio, ((0, count - len(audio)), (0, 0)))
    return audio[:count].copy()


def aligned_bed(track, raw_start, count):
    start = frames(raw_start - REFERENCE_OFFSET)
    sample = track[start:start + count]
    assert len(sample) == count
    return sample.copy()


def original_at(track, raw_start, count):
    start = frames(raw_start)
    sample = track[start:start + count]
    assert len(sample) == count
    return sample.copy()


def approved_gain(original, instrumental):
    start = JOIN - 8 * BAR - .62
    count = frames(JOIN + 8 * BAR) - frames(start)
    album = filt(original_at(original, start, count), "lowpass", 115)
    clean = filt(aligned_bed(instrumental, start, count), "lowpass", 115)
    assert np.corrcoef(album[:, 0], clean[:, 0])[0, 1] > .99
    return float(np.sum(album * clean) / np.sum(clean * clean))


def prepared_kanye(vocals, offset, first, last, target_db, attack=.036, release=.09):
    dry = extract(vocals, first - offset, last - offset)
    vocal = fade(filt(respeed(dry), "highpass", 97), attack, release)
    return vocal * db(target_db) / rms(vocal)


def reduced_bass(bed, points):
    low = signal.sosfiltfilt(
        signal.butter(2, 145, btype="lowpass", fs=SR, output="sos"), bed, axis=0
    ).astype(np.float32)
    t = np.arange(len(bed)) / SR
    amount = np.interp(t, [a for a, _ in points], [b for _, b in points]).astype(np.float32)
    return bed - low * amount[:, None]


def assemble():
    original = load(HERE / "sources/712pm.wav")
    instrumental = load(HERE / "sources/712pm_instrumental.wav")
    facts = load(HERE / "stems/facts_vocals.wav")
    extra = load(HERE / "stems/facts_extra_vocals.wav")
    gain = approved_gain(original, instrumental)
    total = frames(END * BAR)
    splice = frames(APPROVED_KANYE * BAR)
    # This cut jumps back exactly 32 bars in the instrumental. All following
    # material runs on the native 712PM timeline through the approved join.
    overlap = frames(.042)
    intro_from = JOIN + 4 * BAR
    later_from = JOIN - 8 * BAR
    opening = aligned_bed(instrumental, intro_from, splice + overlap) * gain
    opening = reduced_bass(opening, [
        (0, .96), (2.4, .87), (4.7, .42), (FIRST_HOOK * BAR - .31, 0),
    ])
    count = total - splice + overlap
    later = aligned_bed(instrumental, later_from - overlap / SR, count) * gain
    original_later = original_at(original, later_from - overlap / SR, count)
    t = later_from + (np.arange(count) - overlap) / SR
    vocal_mix = np.interp(t, [JOIN - .09, JOIN + .07, 89.065, 89.20], [0, 1, 1, 0])
    later += (original_later - later) * vocal_mix[:, None].astype(np.float32)
    transition = np.sin(np.linspace(0, np.pi / 2, 2 * overlap, dtype=np.float32)) ** 2
    start, end = splice - overlap, splice + overlap
    mix = np.empty((total, 2), np.float32)
    mix[:start] = opening[:start]
    mix[start:end] = opening[start:end] * (1 - transition[:, None])
    mix[start:end] += later[:2 * overlap] * transition[:, None]
    mix[end:] = later[2 * overlap:]

    hook = prepared_kanye(facts, 17, 27.43, 37.22, -16.1)
    for bar, throw_gain in ((FIRST_HOOK, .17), (SECOND_HOOK, .23)):
        position = bar * BAR + HOOK_OFFSET
        place(mix, hook, position)
        tail_length = frames(.47)
        tail = fade(filt(filt(hook[-tail_length:], "highpass", 315), "lowpass", 3400),
                    .023, .13)
        at = position + (len(hook) - len(tail)) / SR
        for beats, balance in ((1.5, [.59, 1.20]), (3, [1.12, .48])):
            place(mix, tail[:, ::-1] * np.array(balance) * throw_gain / beats, at + beats * BEAT)

    preceding = prepared_kanye(extra, 50, 54.53, 67.43, -16.4)
    place(mix, preceding, KANYE * BAR + KANYE_OFFSET)

    # Keep the audition take and gain, and correct its placement on the grid.
    chosen_from, chosen_to = 37.47, 50.73
    approved = prepared_kanye(facts, 17, chosen_from, chosen_to, -16.4)
    start = APPROVED_KANYE * BAR + APPROVED_KANYE_OFFSET
    place(mix, approved, start)

    # Resolve on the original strings. Carry the last chord into the room.
    outro_start = frames((OUTRO + 1.5) * BAR)
    mix[outro_start:] = reduced_bass(mix[outro_start:], [(0, 0), (.90, .65), (2.7, .90)])
    room_input = np.zeros((frames(3.5), 2), np.float32)
    room_input[:frames(.75)] = fade(mix[-frames(2.0):-frames(1.25)], .03, .14)
    reverb = Reverb(room_size=.76, damping=.72, wet_level=1, dry_level=0, width=.92)
    tail = filt(reverb(room_input.T.copy(), SR).T, "highpass", 200)
    mix = np.pad(mix, ((0, frames(1.05)), (0, 0)))
    at = len(mix) - frames(3.05)
    mix[at:] += tail[:len(mix) - at] * .28
    mix[-frames(2.50):] *= np.cos(
        np.linspace(0, np.pi / 2, frames(2.50), dtype=np.float32)
    )[:, None] ** 2
    mix = fade(mix, .16, .2)
    assert np.isfinite(mix).all()
    print("Sections", {key: round(bar * BAR, 3) for key, bar in (
        ("hook", FIRST_HOOK), ("Kanye", KANYE), ("approved excerpt", APPROVED_KANYE),
        ("Future", FUTURE), ("reprise", SECOND_HOOK), ("outro", OUTRO),
    )})
    return mix


def loudness(path):
    output = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
         "loudnorm=I=-13.6:TP=-1.4:LRA=8:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(re.findall(r"\{[^{}]+\}", output.stderr)[-1])


def master(mix):
    with tempfile.TemporaryDirectory(prefix="numbers-full-", dir=HERE) as temp:
        premaster = Path(temp) / "premaster.wav"
        candidate = Path(temp) / "did_the_numbers.mp3"
        sf.write(premaster, mix, SR, subtype="FLOAT")
        gain = -13.6 - float(loudness(premaster)["input_i"])
        effects = (
            f"volume={gain:.4f}dB,aresample=88200,"
            "alimiter=limit=0.8414:attack=4:release=55:level=false:latency=true,aresample=44100"
        )
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(premaster),
                        "-af", effects, "-metadata", "title=YEEZY SEASON 7:12",
                        "-metadata", "artist=Kanye West, Future & Veer",
                        "-metadata", "album=deus complex",
                        "-c:a", "libmp3lame", "-b:a", "320k", str(candidate)], check=True)
        result = loudness(candidate)
        assert float(result["input_tp"]) < -.9 and -14.3 < float(result["input_i"]) < -12.9, result
        print("Master", result)
        candidate.replace(OUTPUT)


if __name__ == "__main__":
    master(assemble())
