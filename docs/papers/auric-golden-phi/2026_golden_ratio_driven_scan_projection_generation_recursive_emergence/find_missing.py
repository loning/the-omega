#!/usr/bin/env python3
from pathlib import Path

sections_dir = Path('sections')
cn_files = {}
en_files = set()

for tex_file in sections_dir.rglob('*.tex'):
    if 'generated' in tex_file.parts:
        continue
    if tex_file.name.endswith('_en.tex'):
        en_files.add(tex_file.stem[:-3])
    else:
        cn_files[tex_file.stem] = tex_file

missing_files = []
for stem, path in cn_files.items():
    if stem not in en_files:
        missing_files.append(str(path))

for f in sorted(missing_files):
    print(f)
