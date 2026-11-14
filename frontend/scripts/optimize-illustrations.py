#!/usr/bin/env python3
"""Re-encode selected, lossless masters; no network or image-generation calls.
Run from the repository root: python3 frontend/scripts/optimize-illustrations.py
Requires Pillow with WebP support. Does not change artwork or remove alpha.
"""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
manifest_file = ROOT / 'docs/illustrations/asset-manifest.json'
manifest = json.loads(manifest_file.read_text())
output = ROOT / 'frontend/public/assets/illustrations'
output.mkdir(parents=True, exist_ok=True)
for item in manifest['assets']:
    master_path = ROOT / item['master']
    master = Image.open(master_path).convert('RGBA')
    assert master.getextrema()[3][0] == 0, f'{master_path}: no transparent pixels'
    item['masterSha256'] = hashlib.sha256(master_path.read_bytes()).hexdigest()
    item['outputs'] = []
    for width in item['widths']:
        height = width * 2 // 3
        # Contain the entire composition; never crop hardware to fill a slot.
        scaled = ImageOps.contain(master, (width, height), Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        canvas.alpha_composite(scaled, ((width-scaled.width)//2, (height-scaled.height)//2))
        target = output / f"{item['file']}-{width}.webp"
        canvas.save(target, 'WEBP', quality=82, alpha_quality=100, method=6)
        size = target.stat().st_size
        assert size <= (190_000 if width == 1440 else 140_000 if width == 960 else 65_000), f'{target}: exceeds byte budget'
        item['outputs'].append({'file': str(target.relative_to(ROOT)), 'width': width, 'height': height, 'bytes': size, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
manifest_file.write_text(json.dumps(manifest, indent=2) + '\n')
print(f"Encoded {sum(len(a['outputs']) for a in manifest['assets'])} images; {sum(o['bytes'] for a in manifest['assets'] for o in a['outputs']):,} bytes across all responsive variants.")
