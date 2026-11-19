"""Render a six-BPM linear ramp using the existing REAPER arrangement."""
from pathlib import Path
import json
import sys

here = Path(__file__).resolve().parent
old = here.parent/'piano_returns'
sys.path.insert(0,str(old))
code = (old/'build.py').read_text()
code = code.replace("existing=(here.parent/'source_tempo/build.py').read_text()",
    "existing=(here.parent/'source_tempo/build.py').read_text().replace('elif stem and bpm == 90:', 'elif stem and bpm != 80:').replace('            source_offset *= 8/9', '            source_offset *= 8/9\\n            rate_factor = bpm / 90')")
code = code.replace(",'  TEMPO 90',",",'  TEMPO 88',")
code = code.replace('(1.75,-3.4),(2,-4),(2.40,-2.6),(3.80,-1.8)',
                    '(1.75,-1.45),(2,-1.8),(2.40,-1.25),(3.80,-.8)')
code = code.replace(
    """    pans += [(t(-.10),0),(t(0),-1),(t(1.81),-1),
             (t(1.98),1),(t(3.80),1),(t(4.02),0)]""",
    """    pans += [(t(0)-.020,0),(t(0),-1),(t(1)-.010,-1),
             (t(1)+.010,1),(t(2)-.010,1),(t(2)+.010,0)]""")
code = code.replace(
    '(-.25,0),(0,-1),(1.75,-1.45),(2,-1.8),(2.40,-1.25),(3.80,-.8),(4.12,0)',
    '(-.18,0),(0,-.55),(.93,-1.2),(1.08,-1.2),(1.83,-.7),(2.12,0)')
# The one-beat lead-in to each pickup is defined in musical time. Sample
# starts and gain automation use this same map.
exec(compile(code,str(old/'build.py'),'exec'),{'__file__':__file__})
