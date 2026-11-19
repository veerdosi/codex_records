from pathlib import Path
import subprocess
import re
import numpy as np
import soundfile as sf

root = Path.home() / 'Library/Application Support/REAPER/MCP Sessions/50 Calls/Renders'
sr = 44100
names = ['Cigarettes _ Drums','Cigarettes _ Bass','Cigarettes _ Guitar',
         'Juice WRLD _ Refrain','Kanye West _ Verse','Guitar _ Return pickup']
drums, bass, guitar, juice, kanye, pickup = [
    sf.read(root/'Stems'/f'{name}.wav', dtype='float32')[0] for name in names
]

def rms(audio):
    return 20*np.log10(max(1e-9,np.sqrt(np.mean(audio*audio))))

def integrated(audio):
    result = subprocess.run(
        ['ffmpeg','-hide_banner','-f','f32le','-ar',str(sr),'-ac','2','-i','pipe:0',
         '-af','ebur128','-f','null','-'],
        input=audio.astype('<f4').tobytes(), capture_output=True, check=True
    )
    return float(re.findall(rb'I:\s+(-?[\d.]+) LUFS', result.stderr)[-1])

bed, lead = drums+bass+guitar+pickup, juice+kanye
for label, a, b in [
    ('intro',0,6),('first hook',6,30),('verse',31.9,43.5),
    ('return opening',45,48),('return build',48,57),('return full',57,69),('outro',69,75)
]:
    part = slice(round(a*sr), round(b*sr))
    levels = [integrated(audio[part]) for audio in [bed,lead,drums,bass,guitar,bed+lead]]
    print(label, 'bed/lead/drum/bass/guitar/mix', levels, 'vocal–bed', round(levels[1]-levels[0],1))
for edge in [6,30,45,48,57,69]:
    idx = round(edge*sr)
    step = np.max(abs(np.diff((bed+lead)[idx-60:idx+60],axis=0)))
    print(f'edit {edge}s sample step {20*np.log10(step):.1f} dBFS')
