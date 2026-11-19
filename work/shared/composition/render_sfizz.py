"""Render a MIDI file through sfizz's VST3 using the requested SFZ instrument."""
from argparse import ArgumentParser
from pathlib import Path
import struct
from xml.etree import ElementTree as ET

import mido
from pedalboard import load_plugin
import soundfile as sf

# JUCE MemoryBlock uses little-endian six-bit groups and its own alphabet.
ALPHABET = '.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+'

def load_instrument(plugin, instrument):
    state = plugin.raw_state
    if state[:4] != b'VC2!':
        raise ValueError('Unrecognized Pedalboard VST3 state.')
    size = struct.unpack_from('<I', state, 4)[0]
    document = ET.fromstring(state[8:8+size])
    component = document.find('IComponent')
    if component is None or not component.text:
        raise ValueError('sfizz component state is missing.')
    length, encoded = component.text.split('.', 1)
    value = sum(ALPHABET.index(char) << (6*i) for i, char in enumerate(encoded))
    chunk = value.to_bytes(int(length), 'little')
    version, name_size = struct.unpack_from('<Qi', chunk)
    if version != 5 or not 1 <= name_size <= len(chunk)-12:
        raise ValueError(f'Unsupported sfizz state version {version}.')
    name = str(instrument.resolve(strict=True)).encode() + b'\0'
    chunk = chunk[:8] + struct.pack('<i', len(name)) + name + chunk[12+name_size:]
    value = int.from_bytes(chunk, 'little')
    encoded = ''.join(ALPHABET[(value >> bit) & 63] for bit in range(0, 8*len(chunk), 6))
    component.text = f'{len(chunk)}.{encoded}'
    xml = ET.tostring(document, encoding='utf-8', xml_declaration=True)
    plugin.raw_state = state[:4] + struct.pack('<I', len(xml)) + xml + state[8+size:]

def render(midi, instrument, output, buffer_size=512):
    if instrument.suffix.lower() != '.sfz':
        raise ValueError('Expected an SFZ instrument file.')
    vst3 = Path.home() / 'Library/Audio/Plug-Ins/VST3/sfizz.vst3'
    plugin = load_plugin(str(vst3), plugin_name='sfizz')
    load_instrument(plugin, instrument)
    position = 0.0
    messages = []
    for event in mido.MidiFile(midi):
        position += event.time
        if not event.is_meta:
            messages.append((event.bytes(), position))
    audio = plugin.process(messages, duration=position+.9, sample_rate=48000,
                           num_channels=2, buffer_size=buffer_size)
    if not abs(audio).max() > 1e-5:
        raise RuntimeError('The SFZ render is silent. Check its sample paths and MIDI range.')
    sf.write(output, audio.T, 48000, subtype='PCM_24')

if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('midi', type=Path)
    parser.add_argument('instrument', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--buffer-size', type=int, choices=(128, 256, 512), default=512,
                        help='Use 128 if a patch reports temporary buffer errors.')
    args = parser.parse_args()
    render(args.midi, args.instrument, args.output, args.buffer_size)
