#!/usr/bin/env python3
"""Encode reviewed source assets without upscaling or content edits. Requires Pillow."""
from pathlib import Path
from PIL import Image
import json, hashlib
root=Path(__file__).resolve().parents[2]
p=root/'docs/visual-storytelling/asset-manifest.json'
m=json.loads(p.read_text());runtime={}
for a in m['assets']:
 source=root/a['master'];im=Image.open(source).convert('RGB')
 a['masterSha256']=hashlib.sha256(source.read_bytes()).hexdigest();a['outputs']=[]
 widths=sorted(set([min(320,im.width),min(640,im.width),min(1280,im.width)]))
 for w in widths:
  h=round(im.height*w/im.width)
  out=root/f"frontend/public/assets/visual-storytelling/{a['file']}-{w}.webp"
  im.resize((w,h),Image.Resampling.LANCZOS).save(out,'WEBP',quality=84,method=6)
  size=out.stat().st_size
  assert size<=180000, f'{out} exceeds 180 KB budget'
  a['outputs'].append({'src':'/assets/visual-storytelling/'+out.name,'width':w,'height':h,'bytes':size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()})
 runtime[a['id']]={k:a[k] for k in ['file','alt','width','height','outputs']}
p.write_text(json.dumps(m,indent=2)+'\n')
(root/'frontend/src/pages/public/storytelling/assets.json').write_text(json.dumps(runtime,indent=2)+'\n')
print(sum(o['bytes'] for a in m['assets'] for o in a['outputs']), 'bytes across',sum(len(a['outputs']) for a in m['assets']),'variants')
