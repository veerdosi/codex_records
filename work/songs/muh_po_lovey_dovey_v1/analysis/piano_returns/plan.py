"""Place matching two-bar tempo curves on the extended v2 arrangement."""
from pathlib import Path
import json
here=Path(__file__).resolve().parent
def ramp(start,left,right):
    total=480/85
    points=[[start,left,True]]
    t=start
    for a,b,f in [(left,left+(right-left)*.1,.125),
                  (left+(right-left)*.1,left+(right-left)*.9,.75),
                  (left+(right-left)*.9,right,.125)]:
        t+=total*f*(a+b)/160
        points.append([t,b,True])
    assert abs(t-start-6)<1e-10
    points[-1]=[start+6,right,False]
    return points

plans={
 'native':[[0,90,False],*ramp(30,90,80),*ramp(93.681,80,90),
           *ramp(129,90,80),*ramp(180.777375,80,90),[229.5,90,False]],
 'fixed':[[0,85,False],[223.5,85,False]],
}
for key,points in plans.items():
    (here/key/'tempo.json').write_text(json.dumps(points))
