"""Test the selected phrases over the released 712PM instrumental."""
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
from scipy import signal
import soundfile as sf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from dsp import SR, db, fade, filt, load

FUTURE_BPM = 147
KANYE_BPM = 142
BAR = 240 / FUTURE_BPM
JOIN = 56.07
REFERENCE_OFFSET = .75


def frames(time):
    return round(time * SR)


def extract(audio, start, end):
    return audio[frames(start):frames(end)].copy()


def rms(audio):
    return float(np.sqrt(np.mean(audio * audio)))


def respeed(audio):
    with tempfile.TemporaryDirectory(prefix="facts-audition-") as d:
        source, dest = (Path(d) / filename for filename in ("source.wav", "dest.wav"))
        sf.write(source, audio, SR, subtype="FLOAT")
        subprocess.run(["rubberband", "-q", "-3", "--centre-focus", "-t",
                        str(KANYE_BPM / FUTURE_BPM), str(source), str(dest)], check=True)
        return load(dest)


def render():
    original = load(HERE / "sources/712pm.wav")
    instrumental = load(HERE / "sources/712pm_instrumental.wav")
    vocals = load(HERE / "stems/facts_vocals.wav")
    start, end = JOIN - 8 * BAR - .62, JOIN + 8 * BAR
    source = extract(original, start, end)
    backing = extract(instrumental, start - REFERENCE_OFFSET, end - REFERENCE_OFFSET)
    backing = backing[:len(source)]
    source = source[:len(backing)]

    # Align and match the official instrumental to the album mix on the low end.
    a = filt(source, "lowpass", 115)
    b = filt(backing, "lowpass", 115)
    reference_gain = float(np.sum(a * b) / np.sum(b * b))
    correlation = np.corrcoef(a[:, 0], b[:, 0])[0, 1]
    assert correlation > .96
    backing *= reference_gain
    t = start + np.arange(len(backing)) / SR
    switch = np.interp(t, [JOIN - .09, JOIN + .07], [0, 1]).astype(np.float32)
    mix = backing + (source - backing) * switch[:, None]

    clip_from, clip_to = 37.47, 50.73
    dry = extract(vocals, clip_from - 17, clip_to - 17)
    lead = filt(respeed(dry), "highpass", 97)
    lead = fade(lead, .036, .09)
    lead *= db(-16.4) / rms(lead)
    first = frames((JOIN - 8 * BAR) + (clip_from - 37.56) * KANYE_BPM / FUTURE_BPM - start)
    last = first + len(lead)
    assert last <= frames(JOIN - start)
    mix[first:last] += lead
    mix = fade(mix, .13, .46)
    assert np.isfinite(mix).all()
    output = HERE / "facts_712pm_audition.mp3"
    with tempfile.TemporaryDirectory(prefix="facts-audition-") as d:
        wav = Path(d) / "premaster.wav"
        sf.write(wav, mix, SR, subtype="FLOAT")
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-af",
             "volume=-6.3dB,aresample=88200,alimiter=limit=0.8414:attack=4:release=55:level=false:latency=true,aresample=44100",
             "-b:a", "320k", str(output)], check=True,
        )
    print("Instrumental alignment", REFERENCE_OFFSET, "seconds, low-band correlation", round(correlation, 4))
    print("Kanye time ratio", round(KANYE_BPM / FUTURE_BPM, 4))
    print("Kanye vocal / beat", round(20 * np.log10(rms(lead) / rms(backing[first:last])), 2), "dB RMS")
    print("Handoff", round(JOIN - start, 3), "seconds into audition")


if __name__ == "__main__":
    render()
