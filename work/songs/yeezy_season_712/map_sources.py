from pathlib import Path
import json
import numpy as np
import soundfile as sf
import soxr
from faster_whisper import WhisperModel

root = Path(__file__).resolve().parent
model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=3,
                     download_root=str(Path(__file__).resolve().parents[2] / "shared/models"), local_files_only=True)
for p in sorted((root / "sources").glob("*.wav")):
    y, sr = sf.read(p, always_2d=True, dtype="float32")
    x = soxr.resample(y.mean(1), sr, 16000)
    segments, _ = model.transcribe(x, language="en", word_timestamps=True,
                                   condition_on_previous_text=False, beam_size=4)
    rows = [{"start": s.start, "end": s.end, "text": s.text,
             "words": [{"start": w.start, "end": w.end, "text": w.word} for w in s.words]}
            for s in segments]
    (root / (p.stem + "_words.json")).write_text(json.dumps(rows))
    print(p.stem, len(x)/16000, [(round(s["start"],2), round(s["end"],2),s["text"]) for s in rows], flush=True)
