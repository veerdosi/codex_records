"""Prepare the two tempo mixes from the v1 arrangement and source stems."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[5]
here = Path(__file__).resolve().parent
variant = sys.argv[1]
assert variant in ('native','fixed')
stage = here/variant
existing = (here.parent/'source_tempo/build.py').read_text()
existing = existing.replace('stage = Path(__file__).resolve().parent','stage = Path(__file__).resolve().parent/'+repr(variant))
existing = existing.replace('root = stage.parents[4]', 'root = stage.parents[5]')
existing = existing.replace("sources = stage.parents[1]", "sources = stage.parents[2]")
existing = existing.replace("with ThreadPoolExecutor(4) as pool:\n    list(pool.map(restore,stems))","")
existing = existing.replace("if start+1e-7<t<end-1e-7", "if start+1e-7<t<end-1e-7 and (not definitions[bars.index(t)-1][2] or not definitions[bars.index(t)][2])")
existing = existing.replace("np.arange(left,right,.125),right","np.arange(left,right,.125), [b for b in bars if left<b<right],right")
existing = existing.replace("revised.replace('Muh Po Lovey Dovey v1','Muh Pe Lovey Dovey v2')","revised.replace('Muh Pe Lovey Dovey v1', title).replace('Muh Po Lovey Dovey v1', title)")
existing = existing.replace("revised = re.sub(r'^  TEMPO 80\\b','  TEMPO 90',revised,flags=re.M)","revised = re.sub(r'^  TEMPO 80\\b',f'  TEMPO {definitions[0][1]}',revised,flags=re.M)")
existing = existing.replace("    |Farebi at 90 BPM. Four instrumental tempo ramps connect both Namastute verses at their native 80 BPM.", "    |"+("Farebi 90 BPM, Namastute 80 BPM. Eased ramps with a chorus-tempo lead-in." if variant=='native' else "Constant 85 BPM, pitch preserved."))
title = 'Muh Pe Lovey Dovey v2' if variant=='native' else 'Muh Pe Lovey Dovey v3'
if variant=='fixed':
    existing = existing.replace("        elif stem and bpm == 90:", "        elif stem:")
    existing = existing.replace("            source_offset *= 8/9", "            source_offset *= 8/9\n            rate_factor = bpm/90")
exec(compile(existing, str(here.parent/'source_tempo/build.py'),'exec'),{'__file__':__file__, 'title':title})
