"""Compare sample-aligned vocal candidates against a verified lead and optional interferer."""

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf


def db_ratio(numerator, denominator):
    if denominator == 0:
        return None
    return round(float(20 * np.log10(max(numerator / denominator, 1e-10))), 2)


def read(path):
    audio, rate = sf.read(path, always_2d=True, dtype='float64')
    if not audio.size or not np.isfinite(audio).all():
        raise ValueError(f'Empty or non-finite audio in {path}')
    return audio, rate


def measure(lead, candidate, interference=None):
    references = [lead.ravel()]
    if interference is not None:
        references.append(interference.ravel())
    design = np.column_stack(references)
    target = candidate.ravel()
    gains, _, rank, _ = np.linalg.lstsq(design, target, rcond=None)
    if rank < len(references):
        raise ValueError('Reference stems must have independent signal')
    retained = gains[0] * references[0]
    result = {
        'lead_gain_db': db_ratio(abs(gains[0]), 1),
        'lead_polarity_inverted': bool(gains[0] < 0),
        'non_lead_residual_db': db_ratio(np.linalg.norm(target - retained), np.linalg.norm(retained)),
    }
    if interference is not None:
        result['interference_gain_db'] = db_ratio(abs(gains[1]), 1)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lead', type=Path)
    parser.add_argument('candidates', nargs='+', type=Path)
    parser.add_argument('--interference', type=Path, help='Known competing stem from a controlled mixture')
    args = parser.parse_args()
    lead, rate = read(args.lead)

    def aligned(path):
        audio, audio_rate = read(path)
        if audio_rate != rate or audio.shape != lead.shape:
            raise ValueError(f'{path} must match the lead’s length, channels, and sample rate')
        return audio

    try:
        interference = aligned(args.interference) if args.interference else None
        results = {str(path): measure(lead, aligned(path), interference) for path in args.candidates}
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
